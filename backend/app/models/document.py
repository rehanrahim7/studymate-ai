"""ORM models for documents, extracted text pages and retrieval chunks."""

from __future__ import annotations

import enum
import json
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.embedding import ChunkEmbedding, DocumentIndex


def _utcnow() -> datetime:
    return datetime.now(UTC)


class DocumentStatus(enum.StrEnum):
    """Lifecycle of an uploaded document."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Conversation(Base):
    """A chat conversation with persistent history."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="New Chat")
    document_ids: Mapped[str] = mapped_column(Text, default="[]")  # JSON array

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", lazy="selectin"
    )

    def get_document_ids(self) -> list[int]:
        try:
            data = json.loads(self.document_ids)
            if isinstance(data, list):
                return [int(x) for x in data]
            return []
        except (TypeError, ValueError):
            return []

    def set_document_ids(self, ids: list[int]) -> None:
        self.document_ids = json.dumps(ids)


class Message(Base):
    """A message in a conversation."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(32))  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of sources
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    llm_used: Mapped[bool] = mapped_column(Integer, default=0)  # SQLite doesn't have bool

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Document(Base):
    """A PDF uploaded by the user."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(1024))
    content_type: Mapped[str] = mapped_column(String(128), default="application/pdf")
    file_size: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(
        String(32), default=DocumentStatus.PENDING.value, index=True
    )
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    character_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    pages: Mapped[list[DocumentPage]] = relationship(
        back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )
    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )
    index_state: Mapped[DocumentIndex | None] = relationship(
        back_populates="document", cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )

    @property
    def is_ready(self) -> bool:
        return self.status == DocumentStatus.READY.value


class DocumentPage(Base):
    """Text extracted from a single page — used for source references."""

    __tablename__ = "document_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    character_count: Mapped[int] = mapped_column(Integer, default=0)

    document: Mapped[Document] = relationship(back_populates="pages")


class DocumentChunk(Base):
    """A retrieval chunk; its embedding lives in `chunk_embeddings`."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, default=1)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, default="")
    token_estimate: Mapped[int] = mapped_column(Integer, default=0)

    document: Mapped[Document] = relationship(back_populates="chunks")
    embedding: Mapped[ChunkEmbedding | None] = relationship(
        back_populates="chunk", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (Index("ix_chunks_doc_ordinal", "document_id", "ordinal"),)
