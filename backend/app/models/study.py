"""Persisted flashcard decks and quizzes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class FlashcardDeck(Base):
    """A generated deck retained after the source document is deleted or changed."""

    __tablename__ = "flashcard_decks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_label: Mapped[str] = mapped_column(String(255))
    source_hash: Mapped[str] = mapped_column(String(64))
    source_chunk_ids: Mapped[str] = mapped_column(Text, default="[]")
    cards: Mapped[str] = mapped_column(Text)
    card_count: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (CheckConstraint("card_count >= 1", name="ck_flashcard_decks_count"),)

    def get_cards(self) -> list[dict[str, str]]:
        return _load_card_list(self.cards)

    def set_cards(self, cards: list[dict[str, str]]) -> None:
        self.cards = json.dumps(cards, ensure_ascii=False)
        self.card_count = len(cards)

    def get_source_chunk_ids(self) -> list[int]:
        return _load_int_list(self.source_chunk_ids)

    def set_source_chunk_ids(self, chunk_ids: list[int]) -> None:
        self.source_chunk_ids = json.dumps(chunk_ids)


class Quiz(Base):
    """A generated quiz with its answer key kept on the server."""

    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_label: Mapped[str] = mapped_column(String(255))
    source_hash: Mapped[str] = mapped_column(String(64))
    source_chunk_ids: Mapped[str] = mapped_column(Text, default="[]")
    questions: Mapped[str] = mapped_column(Text)
    question_count: Mapped[int] = mapped_column(Integer)
    submitted_answers: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        CheckConstraint("question_count >= 1", name="ck_quizzes_question_count"),
        CheckConstraint("score IS NULL OR score >= 0", name="ck_quizzes_score_nonnegative"),
    )

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None

    def get_questions(self) -> list[dict[str, Any]]:
        return _load_question_list(self.questions)

    def set_questions(self, questions: list[dict[str, Any]]) -> None:
        self.questions = json.dumps(questions, ensure_ascii=False)
        self.question_count = len(questions)

    def get_source_chunk_ids(self) -> list[int]:
        return _load_int_list(self.source_chunk_ids)

    def set_source_chunk_ids(self, chunk_ids: list[int]) -> None:
        self.source_chunk_ids = json.dumps(chunk_ids)

    def get_submitted_answers(self) -> list[str] | None:
        return _load_optional_string_list(self.submitted_answers)

    def set_submitted_answers(self, answers: list[str]) -> None:
        self.submitted_answers = json.dumps(answers, ensure_ascii=False)


def _load_int_list(value: str) -> list[int]:
    try:
        data = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, int) and not isinstance(item, bool)]


def _load_optional_string_list(value: str | None) -> list[str] | None:
    if value is None:
        return None
    try:
        data = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(data, list):
        return None
    return [item for item in data if isinstance(item, str)]


def _load_card_list(value: str) -> list[dict[str, str]]:
    try:
        data = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []

    cards: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        question = item.get("question")
        answer = item.get("answer")
        if isinstance(question, str) and isinstance(answer, str):
            cards.append({"question": question, "answer": answer})
    return cards


def _load_question_list(value: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]
