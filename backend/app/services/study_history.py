"""Serialization helpers for persisted study sets and their source state."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.study import FlashcardDeck, Quiz
from app.schemas.study import (
    FlashcardDeckDetail,
    FlashcardDeckSummary,
    QuizDetail,
    QuizQuestionView,
    QuizSummary,
    StudySourceInfo,
)
from app.services.study_content import document_content_hash


def study_title(source_label: str, kind: str) -> str:
    stem = Path(source_label).stem.strip() or source_label
    return f"{kind} — {stem}"[:255]


def source_info(
    session: Any, source_document_id: int | None, source_label: str, source_hash: str
) -> StudySourceInfo:
    document = session.get(Document, source_document_id) if source_document_id is not None else None
    source_available = document is not None and document.status == DocumentStatus.READY.value
    if document is None:
        return StudySourceInfo(
            source_document_id=None,
            source_label=source_label,
            source_hash=source_hash,
            source_available=False,
            source_status="deleted",
            source_changed=False,
        )

    chunks = list(
        session.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.ordinal)
        ).all()
    )
    return StudySourceInfo(
        source_document_id=document.id,
        source_label=source_label,
        source_hash=source_hash,
        source_available=source_available,
        source_status=document.status,
        source_changed=document_content_hash(chunks) != source_hash,
    )


def _source_fields(
    session: Any, source_document_id: int | None, source_label: str, source_hash: str
) -> dict[str, Any]:
    info = source_info(session, source_document_id, source_label, source_hash)
    return {
        "source_document_id": info.source_document_id,
        "source_label": info.source_label,
        "source_hash": info.source_hash,
        "source_available": info.source_available,
        "source_status": info.source_status,
        "source_changed": info.source_changed,
    }


def deck_summary(session: Any, deck: FlashcardDeck) -> FlashcardDeckSummary:
    return FlashcardDeckSummary(
        **_source_fields(session, deck.source_document_id, deck.source_label, deck.source_hash),
        id=deck.id,
        title=deck.title,
        card_count=deck.card_count,
        created_at=deck.created_at,
    )


def deck_detail(session: Any, deck: FlashcardDeck) -> FlashcardDeckDetail:
    return FlashcardDeckDetail(
        **deck_summary(session, deck).model_dump(),
        flashcards=deck.get_cards(),
    )


def quiz_summary(session: Any, quiz: Quiz) -> QuizSummary:
    return QuizSummary(
        **_source_fields(session, quiz.source_document_id, quiz.source_label, quiz.source_hash),
        id=quiz.id,
        title=quiz.title,
        question_count=quiz.question_count,
        status="completed" if quiz.is_completed else "open",
        score=quiz.score,
        completed_at=quiz.completed_at,
        created_at=quiz.created_at,
    )


def quiz_detail(session: Any, quiz: Quiz) -> QuizDetail:
    submitted = quiz.get_submitted_answers()
    completed = quiz.is_completed
    views: list[QuizQuestionView] = []

    for index, item in enumerate(quiz.get_questions()):
        question = item.get("question")
        options = item.get("options")
        answer = item.get("answer")
        explanation = item.get("explanation")
        if (
            not isinstance(question, str)
            or not isinstance(options, list)
            or not all(isinstance(option, str) for option in options)
            or not isinstance(answer, str)
            or not isinstance(explanation, str)
        ):
            continue
        selected = submitted[index] if submitted is not None and index < len(submitted) else None
        views.append(
            QuizQuestionView(
                question=question,
                options=options,
                selected_answer=selected if completed else None,
                correct_answer=answer if completed else None,
                explanation=explanation if completed else None,
                is_correct=(selected == answer) if completed and selected is not None else None,
            )
        )

    return QuizDetail(
        **quiz_summary(session, quiz).model_dump(),
        questions=views,
    )
