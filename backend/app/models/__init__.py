"""Model exports."""

from __future__ import annotations

from app.db.base import Base
from app.models.document import Document, DocumentChunk, DocumentPage, DocumentStatus
from app.models.embedding import ChunkEmbedding, DocumentIndex
from app.models.study import FlashcardDeck, Quiz

__all__ = [
    "Base",
    "ChunkEmbedding",
    "Document",
    "DocumentChunk",
    "DocumentIndex",
    "DocumentPage",
    "DocumentStatus",
    "FlashcardDeck",
    "Quiz",
]
