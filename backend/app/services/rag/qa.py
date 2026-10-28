"""Grounded question answering: retrieval first, generation second.

The retriever and the LLM are separate collaborators. Retrieval can be tested
(or upgraded, re-ranked, swapped for a hosted vector store) without touching
generation, and another LLM provider only needs to implement `LLMService`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.document import Message
from app.services.llm.base import LLMService, LLMServiceError
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.prompting import (
    INSUFFICIENT_CONTEXT_MESSAGE,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.services.rag.retriever import RetrievedChunk, Retriever


@dataclass(slots=True)
class AnswerResult:
    """An answer plus the real passages it was allowed to use."""

    answer: str
    sources: list[RetrievedChunk]
    model: str | None
    prompt_tokens: int
    completion_tokens: int
    llm_used: bool


class DocumentQAService:
    """Answers questions strictly from retrieved document context."""

    def __init__(
        self,
        session: Session,
        llm: LLMService,
        embedder: EmbeddingService,
        settings: Settings | None = None,
    ) -> None:
        self._llm = llm
        self._settings = settings or get_settings()
        self._retriever = Retriever(session, embedder, self._settings)
        self._session = session

    def answer(
        self,
        document_ids: list[int],
        question: str,
        top_k: int | None = None,
        conversation_id: int | None = None,
        session: Session | None = None,
    ) -> AnswerResult:
        db_session = session or self._session
        chunks = self._retriever.retrieve(document_ids, question, top_k=top_k)

        # No passage clears the relevance threshold. Answer deterministically
        # instead of letting the model guess from outside knowledge.
        if not chunks:
            return AnswerResult(
                answer=INSUFFICIENT_CONTEXT_MESSAGE,
                sources=[],
                model=None,
                prompt_tokens=0,
                completion_tokens=0,
                llm_used=False,
            )

        # Raises LLMUnavailableError with provider-specific, actionable guidance.
        self._llm.check_ready()

        # Build context with conversation history for follow-ups
        history_context = ""
        if conversation_id:
            messages = list(
                db_session.scalars(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at.desc())
                    .limit(6)
                ).all()
            )
            messages.reverse()
            if messages:
                history_parts = [
                    f"{msg.role.upper()}: {msg.content}" for msg in messages
                ]
                history_context = (
                    "\n\nPrevious conversation:\n" + "\n".join(history_parts) + "\n\n"
                )

        prompt = history_context + build_user_prompt(question, chunks)
        try:
            response = self._llm.generate(
                prompt,
                system=SYSTEM_PROMPT,
                temperature=self._settings.answer_temperature,
                max_tokens=self._settings.answer_max_tokens,
                top_p=self._settings.answer_top_p,
                num_predict=self._settings.answer_num_predict,
            )
        except LLMServiceError:
            raise
        except Exception as exc:  # defensive: a provider bug should not leak a 500
            raise LLMServiceError(f"{self._llm.name} failed to generate an answer: {exc}") from exc

        answer = response.text.strip()
        # Safety: strip any accidental [Source N] markers if the model still adds them
        answer = re.sub(r"\[Source\s*\d+\]\s*", "", answer)
        if not answer:
            raise LLMServiceError("The language model returned an empty answer. Please try again.")

        return AnswerResult(
            answer=answer,
            sources=chunks,
            model=response.model or self._llm.model_name,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            llm_used=True,
        )
