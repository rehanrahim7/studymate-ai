"""Schema exports."""

from __future__ import annotations

from app.schemas.chat import ChatRequest, ChatResponse, ChatSource
from app.schemas.document import (
    DocumentDetail,
    DocumentListResponse,
    DocumentSummary,
    HealthResponse,
)
from app.schemas.study import (
    Flashcard,
    FlashcardDeckDetail,
    FlashcardDeckListResponse,
    FlashcardDeckSummary,
    FlashcardRequest,
    QuizDetail,
    QuizListResponse,
    QuizQuestionView,
    QuizRequest,
    QuizSubmitRequest,
    QuizSummary,
    SummaryRequest,
    SummaryResponse,
)

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "ChatSource",
    "DocumentDetail",
    "DocumentListResponse",
    "DocumentSummary",
    "Flashcard",
    "FlashcardDeckDetail",
    "FlashcardDeckListResponse",
    "FlashcardDeckSummary",
    "FlashcardRequest",
    "HealthResponse",
    "QuizDetail",
    "QuizListResponse",
    "QuizQuestionView",
    "QuizRequest",
    "QuizSubmitRequest",
    "QuizSummary",
    "SummaryRequest",
    "SummaryResponse",
]
