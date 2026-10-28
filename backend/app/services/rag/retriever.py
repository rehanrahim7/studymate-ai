"""Document-scoped semantic retrieval over the stored chunk indexes."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.indexer import DocumentIndexService

logger = logging.getLogger(__name__)


class RetrievalError(RuntimeError):
    """Base class for retrieval failures that map to a client error."""


class DocumentsNotFoundError(RetrievalError):
    """Raised when one or more requested document ids do not exist."""

    def __init__(self, document_ids: list[int]) -> None:
        self.document_ids = document_ids
        joined = ", ".join(str(document_id) for document_id in document_ids)
        super().__init__(f"Document(s) not found: {joined}.")


class DocumentNotReadyError(RetrievalError):
    """Raised when a document is still processing or failed extraction."""

    def __init__(self, document_id: int, filename: str, status: str) -> None:
        self.document_id = document_id
        super().__init__(f"'{filename}' is not ready for questions (status: {status}).")


class TooManyDocumentsError(RetrievalError):
    """Raised when a question targets more documents than the configured limit."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(f"Select at most {limit} documents per question.")


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A matching chunk plus everything needed to cite it."""

    chunk_id: int
    document_id: int
    document_name: str
    page_number: int
    ordinal: int
    text: str
    score: float


_DOCUMENT_LEVEL_PATTERNS = (
    r"what topics",
    r"topics are covered",
    r"cover(ed)?",
    r"summariz(e|ation)",
    r"overview",
    r"table of contents",
    r"what's in this",
    r"what is this (document|pdf|file)",
    r"main (ideas|points|topics)",
)


def _is_document_level_question(question: str) -> bool:
    q = question.lower()
    return any(re.search(pattern, q) for pattern in _DOCUMENT_LEVEL_PATTERNS)


class Retriever:
    """Embeds a question and searches only the selected documents."""

    def __init__(
        self,
        session: Session,
        embedder: EmbeddingService,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._embedder = embedder
        self._settings = settings or get_settings()
        self._indexer = DocumentIndexService(session, embedder, self._settings)

    def retrieve(
        self,
        document_ids: list[int],
        question: str,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """Return the most relevant chunks for `question`, scoped to the documents."""
        query = question.strip()
        if not query:
            raise RetrievalError("The question must not be empty.")

        ids = list(dict.fromkeys(document_ids))
        if not ids:
            raise RetrievalError("Select at least one document.")
        if len(ids) > self._settings.retrieval_max_documents:
            raise TooManyDocumentsError(self._settings.retrieval_max_documents)

        documents = self._session.scalars(
            select(Document).where(Document.id.in_(ids))
        ).all()
        by_id = {document.id: document for document in documents}

        missing = [document_id for document_id in ids if document_id not in by_id]
        if missing:
            raise DocumentsNotFoundError(missing)

        for document_id in ids:
            document = by_id[document_id]
            if document.status != DocumentStatus.READY.value:
                raise DocumentNotReadyError(
                    document.id,
                    document.original_filename,
                    document.status,
                )

        if _is_document_level_question(query) and len(ids) == 1:
            return self._retrieve_document_overview(by_id[ids[0]], top_k)

        return self._retrieve_semantic(ids, query, by_id, top_k)

    def _retrieve_semantic(
        self,
        ids: list[int],
        query: str,
        by_id: dict[int, Document],
        top_k: int | None,
    ) -> list[RetrievedChunk]:
        indexes = [self._indexer.ensure_index(by_id[document_id]) for document_id in ids]
        query_vector = self._embedder.embed_query(query)

        limit = top_k or self._settings.answer_context_chunks or self._settings.retrieval_top_k
        scored: list[tuple[int, int, float]] = []
        for indexed in indexes:
            for hit in indexed.index.search(query_vector, limit):
                if hit.score >= self._settings.retrieval_min_score:
                    scored.append((indexed.document_id, hit.chunk_id, hit.score))

        if not scored:
            return []

        scored.sort(key=lambda item: item[2], reverse=True)
        scored = scored[:limit]

        chunk_ids = [chunk_id for _, chunk_id, _ in scored]
        chunks = self._session.scalars(
            select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
        ).all()
        chunks_by_id = {chunk.id: chunk for chunk in chunks}

        results: list[RetrievedChunk] = []
        for document_id, chunk_id, score in scored:
            chunk = chunks_by_id.get(chunk_id)
            if chunk is None or chunk.document_id != document_id:
                logger.warning("Ignoring stale index entry for chunk %s", chunk_id)
                continue
            document = by_id[document_id]
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    document_name=document.original_filename,
                    page_number=chunk.page_number,
                    ordinal=chunk.ordinal,
                    text=chunk.text,
                    score=score,
                )
            )

        return results

    def _retrieve_document_overview(
        self,
        document: Document,
        top_k: int | None,
    ) -> list[RetrievedChunk]:
        """Gather representative chunks for document-level questions."""
        chunks = list(
            self._session.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document.id)
                .order_by(DocumentChunk.ordinal, DocumentChunk.id)
            )
        )
        chunks = [chunk for chunk in chunks if chunk.text.strip()]
        if not chunks:
            return []

        limit = top_k or self._settings.answer_context_chunks or self._settings.retrieval_top_k
        # Prefer early pages and a spread across the document
        selected: list[DocumentChunk] = []
        seen = set()

        def add(chunk: DocumentChunk) -> None:
            if chunk.id in seen:
                return
            selected.append(chunk)
            seen.add(chunk.id)

        # First few chunks (often cover title/TOC/introduction)
        for chunk in chunks[: max(3, limit)]:
            add(chunk)
        # Spread: take chunks at intervals
        if len(chunks) > limit:
            step = max(1, len(chunks) // max(1, limit))
            for i in range(0, len(chunks), step):
                add(chunks[i])
                if len(selected) >= limit * 2:
                    break
        # Ensure we don't exceed reasonable context
        selected = selected[: min(limit * 2, 12)]

        results: list[RetrievedChunk] = []
        for chunk in selected:
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    document_name=document.original_filename,
                    page_number=chunk.page_number,
                    ordinal=chunk.ordinal,
                    text=chunk.text,
                    score=1.0,
                )
            )
        return results
