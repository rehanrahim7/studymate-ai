"""ORM models for persisted chunk embeddings and per-document index state.

These live in separate tables (rather than extra columns on `document_chunks`)
so the existing SQLite database keeps working without an ALTER-based migration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document, DocumentChunk


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ChunkEmbedding(Base):
    """Dense vector for one chunk, stored as float32 bytes.

    The chunk primary key makes this a one-to-one cache: re-embedding a chunk
    overwrites the previous vector, while switching models simply rewrites it.
    """

    __tablename__ = "chunk_embeddings"

    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    model_name: Mapped[str] = mapped_column(String(255), index=True)
    dimension: Mapped[int] = mapped_column(Integer)
    vector: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    chunk: Mapped[DocumentChunk] = relationship(back_populates="embedding")


class DocumentIndex(Base):
    """Bookkeeping row describing the last successful FAISS build."""

    __tablename__ = "document_indexes"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    model_name: Mapped[str] = mapped_column(String(255))
    dimension: Mapped[int] = mapped_column(Integer)
    chunk_count: Mapped[int] = mapped_column(Integer)
    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped[Document] = relationship(back_populates="index_state")
