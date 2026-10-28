"""Builds and caches per-document FAISS indexes.

Design goals:

* Embeddings are computed once and persisted in `chunk_embeddings`.
* The FAISS index is a rebuildable cache on disk (`storage/indexes`).
* Rebuilding the index never re-embeds chunks when the stored vectors are
  valid — that keeps recovery from a deleted index file cheap.
* A process-wide lock serialises builds, because FAISS files are written from
  FastAPI's threadpool.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.document import Document, DocumentChunk
from app.models.embedding import ChunkEmbedding, DocumentIndex
from app.services.rag.embeddings import EmbeddingError, EmbeddingService
from app.services.rag.serialization import (
    VectorSerializationError,
    decode_vector,
    encode_vector,
)
from app.services.rag.vector_store import FaissVectorIndex, VectorIndexError

logger = logging.getLogger(__name__)

_BUILD_LOCK = threading.Lock()


class DocumentIndexError(RuntimeError):
    """Base class for index-related failures."""


class EmptyDocumentError(DocumentIndexError):
    """Raised when a document has no indexable text."""


class IndexBuildError(DocumentIndexError):
    """Raised when an index cannot be built or persisted."""


@dataclass(frozen=True, slots=True)
class IndexMetadata:
    """Sidecar file describing exactly what a FAISS file contains."""

    document_id: int
    model_name: str
    dimension: int
    chunk_ids: list[int]


@dataclass(slots=True)
class IndexedDocument:
    """A ready-to-query index for one document."""

    document_id: int
    model_name: str
    dimension: int
    index: FaissVectorIndex
    chunk_ids: list[int]
    rebuilt: bool


class IndexFileStore:
    """Reads/writes the FAISS file and its JSON sidecar."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def faiss_path(self, document_id: int) -> Path:
        return self._directory / f"{document_id}.faiss"

    def metadata_path(self, document_id: int) -> Path:
        return self._directory / f"{document_id}.json"

    def read_metadata(self, document_id: int) -> IndexMetadata | None:
        path = self.metadata_path(document_id)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None

        stored_id = raw.get("document_id")
        model_name = raw.get("model_name")
        dimension = raw.get("dimension")
        chunk_ids = raw.get("chunk_ids")
        if (
            not isinstance(stored_id, int)
            or stored_id != document_id
            or not isinstance(model_name, str)
            or not isinstance(dimension, int)
            or not isinstance(chunk_ids, list)
            or not all(isinstance(item, int) for item in chunk_ids)
        ):
            return None

        return IndexMetadata(
            document_id=stored_id,
            model_name=model_name,
            dimension=dimension,
            chunk_ids=[int(item) for item in chunk_ids],
        )

    def load(self, metadata: IndexMetadata) -> FaissVectorIndex | None:
        path = self.faiss_path(metadata.document_id)
        if not path.exists():
            return None
        try:
            index = FaissVectorIndex.load(path, metadata.chunk_ids)
        except VectorIndexError as exc:
            logger.warning(
                "Discarding unreadable index for document %s: %s",
                metadata.document_id,
                exc,
            )
            return None
        if index.dimension != metadata.dimension:
            logger.warning(
                "Discarding index for document %s: dimension %s does not match sidecar %s.",
                metadata.document_id,
                index.dimension,
                metadata.dimension,
            )
            return None
        return index

    def save(self, index: FaissVectorIndex, metadata: IndexMetadata) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        faiss_path = self.faiss_path(metadata.document_id)
        metadata_path = self.metadata_path(metadata.document_id)
        faiss_tmp = faiss_path.with_name(f"{faiss_path.name}.tmp")
        metadata_tmp = metadata_path.with_name(f"{metadata_path.name}.tmp")

        try:
            index.save(faiss_tmp)
            metadata_tmp.write_text(json.dumps(asdict(metadata)), encoding="utf-8")
            faiss_tmp.replace(faiss_path)
            metadata_tmp.replace(metadata_path)
        finally:
            faiss_tmp.unlink(missing_ok=True)
            metadata_tmp.unlink(missing_ok=True)

    def delete(self, document_id: int) -> None:
        for path in (self.faiss_path(document_id), self.metadata_path(document_id)):
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:  # pragma: no cover - best effort cleanup
                logger.warning("Could not delete index file %s: %s", path, exc)


def delete_document_index(document_id: int, settings: Settings | None = None) -> None:
    """Remove cached index files for a document (used when deleting it)."""
    IndexFileStore((settings or get_settings()).index_dir).delete(document_id)


class DocumentIndexService:
    """Ensures a document has embeddings and a queryable FAISS index."""

    def __init__(
        self,
        session: Session,
        embedder: EmbeddingService,
        settings: Settings | None = None,
        store: IndexFileStore | None = None,
    ) -> None:
        self._session = session
        self._embedder = embedder
        self._settings = settings or get_settings()
        self._store = store or IndexFileStore(self._settings.index_dir)

    def ensure_index(self, document: Document) -> IndexedDocument:
        """Return the document index, building it lazily when needed."""
        if not document.is_ready:
            raise DocumentIndexError(
                f"'{document.original_filename}' is not ready (status: {document.status})."
            )

        chunks = list(
            self._session.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document.id)
                .order_by(DocumentChunk.ordinal, DocumentChunk.id)
            )
        )
        chunks = [chunk for chunk in chunks if chunk.text.strip()]
        if not chunks:
            raise EmptyDocumentError(
                f"'{document.original_filename}' has no indexable text."
            )

        with _BUILD_LOCK:
            return self._ensure_locked(document.id, chunks)

    def _ensure_locked(
        self,
        document_id: int,
        chunks: list[DocumentChunk],
    ) -> IndexedDocument:
        model_name = self._embedder.model_name
        chunk_ids = [chunk.id for chunk in chunks]

        metadata = self._store.read_metadata(document_id)
        if (
            metadata is not None
            and metadata.model_name == model_name
            and metadata.chunk_ids == chunk_ids
        ):
            cached = self._store.load(metadata)
            if cached is not None:
                return IndexedDocument(
                    document_id=document_id,
                    model_name=model_name,
                    dimension=cached.dimension,
                    index=cached,
                    chunk_ids=chunk_ids,
                    rebuilt=False,
                )

        vectors = self._vectors_for(document_id, chunks, model_name)

        try:
            index = FaissVectorIndex.from_vectors(chunk_ids, vectors)
        except VectorIndexError as exc:
            raise IndexBuildError(f"Could not build the retrieval index: {exc}") from exc

        new_metadata = IndexMetadata(
            document_id=document_id,
            model_name=model_name,
            dimension=index.dimension,
            chunk_ids=chunk_ids,
        )
        try:
            self._store.save(index, new_metadata)
        except OSError as exc:
            raise IndexBuildError(f"Could not persist the retrieval index: {exc}") from exc

        self._record_state(document_id, model_name, index.dimension, len(chunk_ids))
        return IndexedDocument(
            document_id=document_id,
            model_name=model_name,
            dimension=index.dimension,
            index=index,
            chunk_ids=chunk_ids,
            rebuilt=True,
        )

    def _vectors_for(
        self,
        document_id: int,
        chunks: list[DocumentChunk],
        model_name: str,
    ) -> list[list[float]]:
        """Load cached embeddings and embed only the chunks that are missing."""
        rows = self._session.scalars(
            select(ChunkEmbedding).where(
                ChunkEmbedding.document_id == document_id,
                ChunkEmbedding.model_name == model_name,
            )
        )
        stored: dict[int, list[float]] = {}
        for row in rows:
            try:
                stored[row.chunk_id] = decode_vector(row.vector, dimension=row.dimension)
            except VectorSerializationError as exc:
                logger.warning("Ignoring corrupt embedding for chunk %s: %s", row.chunk_id, exc)

        if len({len(vector) for vector in stored.values()}) > 1:
            logger.warning(
                "Stored embeddings for document %s have mixed dimensions; re-embedding.",
                document_id,
            )
            stored.clear()

        missing = [chunk for chunk in chunks if chunk.id not in stored]
        if missing:
            try:
                new_vectors = self._embedder.embed_documents([chunk.text for chunk in missing])
            except EmbeddingError:
                raise
            except Exception as exc:
                raise EmbeddingError(f"Embedding failed: {exc}") from exc

            if len(new_vectors) != len(missing):
                raise EmbeddingError(
                    f"Embedding model returned {len(new_vectors)} vectors for "
                    f"{len(missing)} chunks."
                )
            dimensions = {len(vector) for vector in new_vectors}
            if len(dimensions) != 1 or 0 in dimensions:
                raise EmbeddingError("Embedding model returned vectors of inconsistent size.")
            dimension = dimensions.pop()

            if stored and any(len(vector) != dimension for vector in stored.values()):
                raise EmbeddingError(
                    "Stored embeddings use a different dimension than the current model. "
                    "Delete the document and upload it again to rebuild its embeddings."
                )

            for chunk, vector in zip(missing, new_vectors, strict=True):
                try:
                    encoded = encode_vector(vector)
                except VectorSerializationError as exc:
                    raise EmbeddingError(str(exc)) from exc

                embedding_row = self._session.get(ChunkEmbedding, chunk.id)
                if embedding_row is None:
                    embedding_row = ChunkEmbedding(
                        chunk_id=chunk.id,
                        document_id=document_id,
                        model_name=model_name,
                        dimension=dimension,
                        vector=encoded,
                    )
                    self._session.add(embedding_row)
                else:
                    embedding_row.document_id = document_id
                    embedding_row.model_name = model_name
                    embedding_row.dimension = dimension
                    embedding_row.vector = encoded
                stored[chunk.id] = [float(value) for value in vector]

            self._session.commit()
            logger.info(
                "Embedded %s new chunk(s) for document %s with %s",
                len(missing),
                document_id,
                model_name,
            )

        return [stored[chunk.id] for chunk in chunks]

    def _record_state(
        self,
        document_id: int,
        model_name: str,
        dimension: int,
        chunk_count: int,
    ) -> None:
        state = self._session.get(DocumentIndex, document_id)
        if state is None:
            state = DocumentIndex(document_id=document_id)
            self._session.add(state)
        state.model_name = model_name
        state.dimension = dimension
        state.chunk_count = chunk_count
        state.built_at = datetime.now(UTC)
        self._session.commit()
