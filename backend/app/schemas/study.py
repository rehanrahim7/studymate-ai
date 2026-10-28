"""Schemas for study generation, saved study sets, and quiz submissions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.document import UtcDatetime


class SummaryRequest(BaseModel):
    document_id: int


class SummaryResponse(BaseModel):
    document_id: int
    summary: str


class FlashcardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: int
    count: int = Field(default=10, ge=3, le=20)


class Flashcard(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    answer: str = Field(min_length=1, max_length=4000)


class StudySourceInfo(BaseModel):
    source_document_id: int | None
    source_label: str
    source_hash: str
    source_available: bool
    source_status: str
    source_changed: bool


class FlashcardDeckSummary(StudySourceInfo):
    id: int
    title: str
    card_count: int
    created_at: UtcDatetime


class FlashcardDeckDetail(FlashcardDeckSummary):
    flashcards: list[Flashcard]


class FlashcardDeckListResponse(BaseModel):
    decks: list[FlashcardDeckSummary]
    total: int


class QuizRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: int
    count: int = Field(default=5, ge=3, le=10)


class GeneratedQuizQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1000)
    options: list[str] = Field(min_length=4, max_length=4)
    answer: str = Field(min_length=1, max_length=500)
    explanation: str = Field(min_length=1, max_length=2000)


class QuizQuestionView(BaseModel):
    question: str
    options: list[str]
    selected_answer: str | None = None
    correct_answer: str | None = None
    explanation: str | None = None
    is_correct: bool | None = None


class QuizSummary(StudySourceInfo):
    id: int
    title: str
    question_count: int
    status: Literal["open", "completed"]
    score: int | None = None
    completed_at: UtcDatetime | None = None
    created_at: UtcDatetime


class QuizDetail(QuizSummary):
    questions: list[QuizQuestionView]


class QuizListResponse(BaseModel):
    quizzes: list[QuizSummary]
    total: int


class QuizSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: list[str] = Field(min_length=1, max_length=20)

    @field_validator("answers")
    @classmethod
    def _strip_answers(cls, value: list[str]) -> list[str]:
        return [answer.strip() for answer in value]
