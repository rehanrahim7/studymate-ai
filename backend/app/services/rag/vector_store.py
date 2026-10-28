"""FAISS-backed vector index with chunk-id metadata.

Each document gets its own flat index. Vectors are L2-normalised, so inner
product search is equivalent to cosine similarity. A flat index is exact and
plenty fast for the document sizes this app handles.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.rag.dependencies import get_faiss, get_numpy


class VectorIndexError(RuntimeError):
    """Raised when an index cannot be built, loaded or queried."""


@dataclass(frozen=True, slots=True)
class SearchHit:
    """A chunk id and its cosine similarity to the query."""

    chunk_id: int
    score: float


class FaissVectorIndex:
    """Thin, validated wrapper around a FAISS `IndexFlatIP`."""

    def __init__(self, index: Any, chunk_ids: Sequence[int]) -> None:
        if index.ntotal != len(chunk_ids):
            raise VectorIndexError(
                f"Index contains {index.ntotal} vectors but {len(chunk_ids)} chunk ids were given."
            )
        if len(chunk_ids) == 0:
            raise VectorIndexError("An index must contain at least one chunk.")
        self._index = index
        self._chunk_ids = tuple(int(chunk_id) for chunk_id in chunk_ids)

    @property
    def size(self) -> int:
        return int(self._index.ntotal)

    @property
    def dimension(self) -> int:
        return int(self._index.d)

    @property
    def chunk_ids(self) -> tuple[int, ...]:
        return self._chunk_ids

    @classmethod
    def from_vectors(
        cls,
        chunk_ids: Sequence[int],
        vectors: Sequence[Sequence[float]],
    ) -> FaissVectorIndex:
        """Build a normalised inner-product index from parallel inputs."""
        if not chunk_ids:
            raise VectorIndexError("Cannot build an index without chunks.")
        if len(chunk_ids) != len(vectors):
            raise VectorIndexError(
                f"Got {len(chunk_ids)} chunk ids but {len(vectors)} vectors."
            )

        faiss = get_faiss()
        numpy = get_numpy()
        try:
            matrix = numpy.asarray(vectors, dtype=numpy.float32)
        except (TypeError, ValueError) as exc:
            raise VectorIndexError("Embedding vectors are not numeric.") from exc

        if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
            raise VectorIndexError("Embedding vectors must form a non-empty 2-D matrix.")
        if not bool(numpy.all(numpy.isfinite(matrix))):
            raise VectorIndexError("Embedding vectors contain NaN or infinite values.")

        faiss.normalize_L2(matrix)
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        return cls(index, chunk_ids)

    def search(self, query: Sequence[float], top_k: int = 5) -> list[SearchHit]:
        """Return the nearest chunks, highest cosine similarity first."""
        if top_k < 1:
            raise VectorIndexError("top_k must be at least 1.")

        faiss = get_faiss()
        numpy = get_numpy()
        try:
            matrix = numpy.asarray([query], dtype=numpy.float32)
        except (TypeError, ValueError) as exc:
            raise VectorIndexError("Query embedding is not numeric.") from exc

        if matrix.shape != (1, self.dimension):
            raise VectorIndexError(
                f"Query embedding has dimension {matrix.shape[1]}, expected {self.dimension}."
            )
        if not bool(numpy.all(numpy.isfinite(matrix))):
            raise VectorIndexError("Query embedding contains NaN or infinite values.")

        faiss.normalize_L2(matrix)
        k = min(top_k, self.size)
        scores, indices = self._index.search(matrix, k)

        hits: list[SearchHit] = []
        for score, index in zip(scores[0], indices[0], strict=True):
            position = int(index)
            if position < 0:  # FAISS pads with -1 when fewer results exist
                continue
            hits.append(SearchHit(chunk_id=self._chunk_ids[position], score=float(score)))
        return hits

    def save(self, path: Path) -> None:
        """Write the raw FAISS index to disk."""
        get_faiss().write_index(self._index, str(path))

    @classmethod
    def load(cls, path: Path, chunk_ids: Sequence[int]) -> FaissVectorIndex:
        """Load a FAISS index and re-attach the chunk-id mapping."""
        try:
            index = get_faiss().read_index(str(path))
        except Exception as exc:
            raise VectorIndexError(f"Could not read FAISS index {path.name}: {exc}") from exc
        return cls(index, chunk_ids)
