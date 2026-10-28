"""Study tools: summaries, flashcards, and quizzes."""

from __future__ import annotations

import json
import random
import re
import unicodedata
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from functools import partial
from typing import NoReturn, TypeVar

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession, LLMServiceDep
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.study import FlashcardDeck, Quiz
from app.schemas.study import (
    Flashcard,
    FlashcardDeckDetail,
    FlashcardRequest,
    GeneratedQuizQuestion,
    QuizDetail,
    QuizRequest,
    SummaryRequest,
    SummaryResponse,
)
from app.services.llm.base import LLMResponse, LLMService, LLMServiceError, LLMUnavailableError
from app.services.study_content import (
    InsufficientStudyContentError,
    StudyContext,
    build_study_context,
    content_tokens,
    has_source_overlap,
)
from app.services.study_history import deck_detail, quiz_detail, study_title

router = APIRouter(prefix="/study", tags=["study"])

_T = TypeVar("_T")

_MAX_SAMPLE_CHUNKS = 12
_UNAVAILABLE_MESSAGE = "The local AI engine is unavailable. Start Ollama and try again."
_FAILED_MESSAGE = "The language model could not complete that request. Please try again."
_INVALID_MESSAGE = "The model returned an invalid response. Please try again."
_UNUSABLE_MESSAGE = (
    "The model did not return usable study material grounded in this document. "
    "Please try again."
)
_TIMEOUT_MESSAGE = "The language model did not respond in time. Please try again."
_AMBIGUOUS_QUIZ_MESSAGE = (
    "The model generated quiz options that were duplicates or equivalent. Please try again."
)
_EXPLANATION_GROUNDING_MESSAGE = (
    "The model generated quiz explanations that did not clearly explain the correct "
    "answers using this document. Please try again."
)

_NUMBER_PATTERN = re.compile(
    r"[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?",
    re.ASCII,
)


class StudyOutputError(ValueError):
    """The model answered, but the payload is not usable study material."""


class AmbiguousQuizOptionsError(StudyOutputError):
    """The quiz has duplicate or numerically equivalent answer options."""


class ExplanationGroundingError(StudyOutputError):
    """A quiz explanation is unsupported or does not explain its correct answer."""


def _extract_json(text: str) -> str:
    """Strip optional Markdown fences and surrounding prose from a JSON payload."""
    stripped = text.strip()
    if not stripped:
        raise StudyOutputError("empty response")

    if "```" in stripped:
        fence_start = stripped.find("```")
        block = stripped[fence_start + 3 :]
        if block.lstrip().lower().startswith("json"):
            block = block.lstrip()[4:]
        fence_end = block.find("```")
        if fence_end != -1:
            block = block[:fence_end]
        stripped = block.strip()

    # Some models add a sentence before or after the payload.
    array_start = stripped.find("[")
    object_start = stripped.find("{")
    candidates = [index for index in (array_start, object_start) if index != -1]
    if candidates:
        stripped = stripped[min(candidates) :]
        closing = "]" if stripped.startswith("[") else "}"
        closing_index = stripped.rfind(closing)
        if closing_index == -1:
            raise StudyOutputError("truncated JSON payload")
        stripped = stripped[: closing_index + 1]

    if not stripped:
        raise StudyOutputError("no JSON found")
    return stripped


def _load_json_list(text: str) -> list[object]:
    """Parse a JSON array, accepting a few common object wrappers."""
    payload = json.loads(_extract_json(text))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("flashcards", "questions", "items", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    raise StudyOutputError("expected a JSON array")


def _generate(llm: LLMService, prompt: str, system: str, max_tokens: int) -> LLMResponse:
    return llm.generate(prompt, system=system, temperature=0.2, max_tokens=max_tokens)


def _generate_validated(
    llm: LLMService,
    prompt: str,
    system: str,
    max_tokens: int,
    parse: Callable[[str], list[_T]],
) -> list[_T]:
    """Generate once, then make at most one repair attempt for invalid output.

    Transport failures are never retried here: retrying a timeout multiplies the
    wait for the user without improving the odds. Only unusable payloads (bad
    JSON, wrong shape, invalid fields, or ungrounded content) trigger the single
    repair attempt.
    """
    response = _generate(llm, prompt, system, max_tokens)
    try:
        return parse(response.text)
    except (json.JSONDecodeError, StudyOutputError, ValidationError):
        pass

    repair_prompt = (
        f"{prompt}\n\n"
        "Your previous reply was not usable. Reply with ONLY a raw JSON array, "
        "with exactly the requested number of items. Every item must use facts "
        "and terms from the provided content. For quizzes, every explanation must "
        "explain why its own correct answer is right. No Markdown fences and no "
        "commentary."
    )
    response = _generate(llm, repair_prompt, system, max_tokens)
    return parse(response.text)


def _parse_flashcards(
    text: str, expected: int, source_tokens: frozenset[str]
) -> list[Flashcard]:
    cards: list[Flashcard] = []
    seen_questions: set[str] = set()

    for item in _load_json_list(text):
        if not isinstance(item, dict):
            raise StudyOutputError("flashcard item is not an object")
        question = item.get("question")
        answer = item.get("answer")
        if not isinstance(question, str) or not isinstance(answer, str):
            raise StudyOutputError("flashcard is missing text fields")
        question = question.strip()
        answer = answer.strip()
        if not question or not answer:
            raise StudyOutputError("flashcard has blank fields")

        normalized_question = " ".join(question.casefold().split())
        if normalized_question in seen_questions:
            raise StudyOutputError("duplicate flashcard question")
        seen_questions.add(normalized_question)

        if not has_source_overlap(f"{question} {answer}", source_tokens):
            raise StudyOutputError("flashcard is not grounded in the document")

        cards.append(Flashcard(question=question[:1000], answer=answer[:4000]))

    if len(cards) < expected:
        raise StudyOutputError(f"expected {expected} flashcards, received {len(cards)}")
    return cards[:expected]


def _normalize_option(option: str) -> str:
    """Normalize text for duplicate checks without altering what is displayed."""
    text = unicodedata.normalize("NFKC", option).strip()
    text = text.replace("\u2044", "/").replace("\u2212", "-")
    return " ".join(text.split())


def _parse_decimal(text: str) -> Fraction | None:
    """Parse a plain decimal or thousands-separated number, without eval."""
    candidate = text.strip()
    if not candidate or _NUMBER_PATTERN.fullmatch(candidate) is None:
        return None
    try:
        value = Decimal(candidate.replace(",", ""))
    except InvalidOperation:
        return None
    if not value.is_finite():
        return None
    if value == 0:
        return Fraction(0)
    if abs(value.adjusted()) > 100:
        return None
    return Fraction(value)


def _numeric_option_value(option: str) -> Fraction | None:
    """Return an exact value for simple numbers, percentages, and fractions.

    This deliberately supports only a narrow, safe grammar. It does not parse
    variables, units, radicals, or general mathematical expressions.
    """
    text = _normalize_option(option)
    factor = Fraction(1)
    if text.endswith("%"):
        text = text[:-1].strip()
        factor = Fraction(1, 100)
    if not text:
        return None

    if text.count("/") == 1:
        numerator_text, denominator_text = text.split("/")
        numerator = _parse_decimal(numerator_text)
        denominator = _parse_decimal(denominator_text)
        if numerator is None or denominator is None or denominator == 0:
            return None
        return (numerator / denominator) * factor

    value = _parse_decimal(text)
    return None if value is None else value * factor


def _option_key(option: str) -> tuple[str, object]:
    numeric = _numeric_option_value(option)
    if numeric is not None:
        return ("number", numeric)
    return ("text", _normalize_option(option).casefold())


def _has_equivalent_options(options: list[str]) -> bool:
    keys = [_option_key(option) for option in options]
    return len(set(keys)) != len(keys)


def _resolve_quiz_answer(answer: object, options: list[str]) -> str | None:
    """Resolve an answer given as option text, a zero-based index, or an index string."""
    if isinstance(answer, bool):
        return None
    if isinstance(answer, int):
        return options[answer] if 0 <= answer < len(options) else None
    if isinstance(answer, str):
        text = answer.strip()
        for option in options:
            if option == text:
                return option
        folded = [option.casefold() for option in options]
        if text.casefold() in folded:
            return options[folded.index(text.casefold())]
        if text.isdigit():
            index = int(text)
            return options[index] if 0 <= index < len(options) else None
    return None


def _terms_match(left: str, right: str) -> bool:
    """Match exact terms plus simple singular/plural variants such as chloroplast(s)."""
    if left == right:
        return True
    return len(left) >= 4 and len(right) >= 4 and (left in right or right in left)


def _terms_overlap(left: frozenset[str], right: frozenset[str]) -> bool:
    return any(_terms_match(term, other) for term in left for other in right)


def _supported_term_count(tokens: frozenset[str], source_tokens: frozenset[str]) -> int:
    return sum(
        1
        for token in tokens
        if any(_terms_match(token, source) for source in source_tokens)
    )


def _validate_explanation(
    answer: str,
    explanation: str,
    source_tokens: frozenset[str],
) -> None:
    """Require a substantive, source-supported explanation of the correct answer."""
    explanation_tokens = content_tokens(explanation)
    if len(explanation_tokens) < 3:
        raise ExplanationGroundingError("quiz explanation is too short")

    supported = _supported_term_count(explanation_tokens, source_tokens)
    if supported < 2 or supported * 2 < len(explanation_tokens):
        raise ExplanationGroundingError("quiz explanation is not supported by the document")

    answer_tokens = content_tokens(answer)
    if answer_tokens and not _terms_overlap(explanation_tokens, answer_tokens):
        raise ExplanationGroundingError("quiz explanation does not reference the answer")


def _parse_quiz(
    text: str, expected: int, source_tokens: frozenset[str]
) -> list[GeneratedQuizQuestion]:
    questions: list[GeneratedQuizQuestion] = []
    seen_questions: set[str] = set()

    for item in _load_json_list(text):
        if not isinstance(item, dict):
            raise StudyOutputError("quiz item is not an object")
        question = item.get("question")
        options = item.get("options")
        explanation = item.get("explanation")
        answer = item.get("answer_index", item.get("answer"))

        if not isinstance(question, str) or not question.strip():
            raise StudyOutputError("quiz question is missing text")
        if not isinstance(explanation, str) or not explanation.strip():
            raise StudyOutputError("quiz question is missing an explanation")
        if not isinstance(options, list) or len(options) != 4:
            raise StudyOutputError("quiz question needs exactly four options")
        if any(not isinstance(option, str) or not option.strip() for option in options):
            raise StudyOutputError("quiz option is blank")

        cleaned_options = [option.strip() for option in options]
        if _has_equivalent_options(cleaned_options):
            raise AmbiguousQuizOptionsError("quiz options are duplicate or equivalent")

        resolved = _resolve_quiz_answer(answer, cleaned_options)
        if resolved is None:
            raise StudyOutputError("quiz answer does not match an option")

        cleaned_question = question.strip()
        normalized_question = " ".join(cleaned_question.casefold().split())
        if normalized_question in seen_questions:
            raise StudyOutputError("duplicate quiz question")
        seen_questions.add(normalized_question)

        if not has_source_overlap(
            f"{cleaned_question} {resolved} {explanation}", source_tokens
        ):
            raise StudyOutputError("quiz question is not grounded in the document")

        _validate_explanation(resolved, explanation, source_tokens)

        questions.append(
            GeneratedQuizQuestion(
                question=cleaned_question[:1000],
                options=cleaned_options,
                answer=resolved,
                explanation=explanation.strip()[:2000],
            )
        )

    if len(questions) < expected:
        raise StudyOutputError(f"expected {expected} questions, received {len(questions)}")
    return questions[:expected]


def _raise_generation_error(exc: Exception) -> NoReturn:
    """Map LLM failures to safe, user-facing HTTP errors (no internal details)."""
    if isinstance(exc, LLMUnavailableError):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _UNAVAILABLE_MESSAGE) from exc
    if isinstance(exc, LLMServiceError):
        message = _TIMEOUT_MESSAGE if "timed out" in str(exc).lower() else _FAILED_MESSAGE
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, message) from exc
    raise HTTPException(status.HTTP_502_BAD_GATEWAY, _UNUSABLE_MESSAGE) from exc


def _document_chunks(session: DbSession, document_id: int) -> tuple[Document, list[DocumentChunk]]:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    if document.status != DocumentStatus.READY.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Document not ready.")
    chunks = list(
        session.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.ordinal)
        ).all()
    )
    if not chunks:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No content available.")
    return document, chunks


def _build_context(chunks: list[DocumentChunk], item_count: int) -> StudyContext:
    try:
        return build_study_context(chunks, required_chars=max(200, item_count * 40))
    except InsufficientStudyContentError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


def _sample_context(chunks: list[DocumentChunk], limit: int = _MAX_SAMPLE_CHUNKS) -> str:
    """Keeping the summary path unchanged avoids penalizing short documents."""
    step = max(1, len(chunks) // limit)
    sampled = chunks[::step][:limit]
    return "\n\n".join(f"[Page {chunk.page_number}] {chunk.text}" for chunk in sampled)


def _check_llm_ready(llm: LLMService) -> None:
    try:
        llm.check_ready()
    except LLMUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _UNAVAILABLE_MESSAGE) from exc


def _save_deck(
    session: DbSession,
    document: Document,
    context: StudyContext,
    cards: list[Flashcard],
) -> FlashcardDeckDetail:
    deck = FlashcardDeck(
        title=study_title(document.original_filename, "Flashcards"),
        source_document_id=document.id,
        source_label=document.original_filename,
        source_hash=context.source_hash,
    )
    deck.set_source_chunk_ids([chunk.id for chunk in context.chunks])
    deck.set_cards([card.model_dump() for card in cards])
    session.add(deck)
    try:
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "The generated deck could not be saved. Please try again.",
        ) from exc
    session.refresh(deck)
    return deck_detail(session, deck)


def _save_quiz(
    session: DbSession,
    document: Document,
    context: StudyContext,
    questions: list[GeneratedQuizQuestion],
) -> QuizDetail:
    quiz = Quiz(
        title=study_title(document.original_filename, "Quiz"),
        source_document_id=document.id,
        source_label=document.original_filename,
        source_hash=context.source_hash,
    )
    quiz.set_source_chunk_ids([chunk.id for chunk in context.chunks])
    quiz.set_questions([question.model_dump() for question in questions])
    session.add(quiz)
    try:
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "The generated quiz could not be saved. Please try again.",
        ) from exc
    session.refresh(quiz)
    return quiz_detail(session, quiz)


@router.post("/summary", response_model=SummaryResponse)
def generate_summary(
    payload: SummaryRequest,
    session: DbSession,
    llm: LLMServiceDep,
) -> SummaryResponse:
    document, chunks = _document_chunks(session, payload.document_id)
    context = _sample_context(chunks)

    _check_llm_ready(llm)

    system = (
        "You are an expert study assistant. Generate a clear, structured summary of the "
        "document. Include the main topic, key concepts, important definitions, major "
        "points or processes, and key takeaways. Use headings and bullet points. Only use "
        "information from the provided content."
    )
    prompt = (
        f"Document: {document.original_filename}\n\nContent:\n{context}\n\n"
        "Generate a comprehensive summary."
    )

    try:
        response = _generate(llm, prompt, system, 700)
    except LLMServiceError as exc:
        _raise_generation_error(exc)

    summary = response.text.strip()
    if not summary:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, _INVALID_MESSAGE)
    return SummaryResponse(document_id=document.id, summary=summary)


@router.post("/flashcards", response_model=FlashcardDeckDetail)
def generate_flashcards(
    payload: FlashcardRequest,
    session: DbSession,
    llm: LLMServiceDep,
) -> FlashcardDeckDetail:
    document, chunks = _document_chunks(session, payload.document_id)
    context = _build_context(chunks, payload.count)

    _check_llm_ready(llm)

    system = (
        f"You create study flashcards. Generate exactly {payload.count} flashcards. "
        "Reply with ONLY a JSON array of objects with 'question' and 'answer' string "
        "fields. No Markdown fences and no other text. Keep each answer under 40 words. "
        "Every card must test a specific fact, definition, or relationship stated in the "
        "provided content. Do not ask generic questions that could apply to any document. "
        "Do not repeat a question. Only use information from the provided content."
    )
    prompt = (
        f"Document: {document.original_filename}\n\nContent:\n{context.text}\n\n"
        f"Generate exactly {payload.count} source-grounded flashcards as a JSON array."
    )
    parse = partial(
        _parse_flashcards, expected=payload.count, source_tokens=context.source_tokens
    )

    try:
        cards = _generate_validated(llm, prompt, system, 1200, parse)
    except (LLMServiceError, json.JSONDecodeError, StudyOutputError, ValidationError) as exc:
        _raise_generation_error(exc)

    return _save_deck(session, document, context, cards)


@router.post("/quiz", response_model=QuizDetail)
def generate_quiz(
    payload: QuizRequest,
    session: DbSession,
    llm: LLMServiceDep,
) -> QuizDetail:
    document, chunks = _document_chunks(session, payload.document_id)
    context = _build_context(chunks, payload.count)

    _check_llm_ready(llm)

    system = (
        f"You create multiple-choice quizzes. Generate exactly {payload.count} questions. "
        "Reply with ONLY a JSON array of objects with these fields: 'question' (string), "
        "'options' (array of exactly 4 distinct strings), 'answer' (the exact text of the "
        "correct option), and 'explanation' (one short sentence explaining why the correct "
        "option is right, using the provided content; do not give an unrelated fact). "
        "Do not include two options that are mathematically equivalent. Every question must "
        "test a specific fact or relationship stated in the provided content; do not ask "
        "generic questions that could apply to any document. Do not repeat a question. No "
        "Markdown fences and no other text. Only use information from the provided content."
    )
    prompt = (
        f"Document: {document.original_filename}\n\nContent:\n{context.text}\n\n"
        f"Generate exactly {payload.count} source-grounded quiz questions as a JSON array."
    )
    parse = partial(_parse_quiz, expected=payload.count, source_tokens=context.source_tokens)

    try:
        questions = _generate_validated(llm, prompt, system, 1200, parse)
    except AmbiguousQuizOptionsError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, _AMBIGUOUS_QUIZ_MESSAGE) from exc
    except ExplanationGroundingError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, _EXPLANATION_GROUNDING_MESSAGE
        ) from exc
    except (LLMServiceError, json.JSONDecodeError, StudyOutputError, ValidationError) as exc:
        _raise_generation_error(exc)

    for question in questions:
        # `answer` stores the option text, so a shuffle cannot change which
        # displayed option is correct. The key is never returned before submission.
        random.shuffle(question.options)

    return _save_quiz(session, document, context, questions)
