"""Embedding services for the retrieval pipeline.

The pipeline depends on the `EmbeddingService` contract, not on Sentence
Transformers directly. That keeps tests (and a future hosted embedding
provider) free of model downloads, and makes swapping models a one-class
change.
"""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

from app.core.config import Settings, get_settings
from app.services.rag.dependencies import INSTALL_HINT

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    """Raised when texts cannot be embedded."""


class EmbeddingService(ABC):
    """Contract for turning text into dense vectors."""

    model_name: str

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of passages, preserving input order."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single search query."""


class SentenceTransformerEmbeddingService(EmbeddingService):
    """Local Sentence Transformers embeddings.

    The model is loaded on first use, not at import time: the API starts fast
    and documents can be uploaded before the retrieval stack is exercised.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self.model_name = self._settings.embedding_model
        self._model: Any = None
        self._load_lock = threading.Lock()

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        # FastAPI serves requests from a threadpool; avoid loading the model
        # twice when two questions arrive at once.
        with self._load_lock:
            if self._model is not None:
                return self._model

            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover - depends on the environment
                raise EmbeddingError(
                    f"`sentence-transformers` is not installed. {INSTALL_HINT}"
                ) from exc

            try:
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self._settings.embedding_device,
                )
            except Exception as exc:  # pragma: no cover - network / model download issues
                raise EmbeddingError(
                    f"Could not load embedding model '{self.model_name}'. The first run "
                    f"downloads the model from Hugging Face, so check your network "
                    f"connection. ({exc})"
                ) from exc

            logger.info("Loaded embedding model %s", self.model_name)
            return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise EmbeddingError("Cannot embed empty text.")

        model = self._load_model()
        try:
            matrix = model.encode(
                texts,
                batch_size=self._settings.embedding_batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        except Exception as exc:  # pragma: no cover - model/runtime failures
            raise EmbeddingError(
                f"The embedding model '{self.model_name}' failed to encode text: {exc}"
            ) from exc

        vectors = [[float(value) for value in row] for row in matrix]
        dimensions = {len(vector) for vector in vectors}
        if not vectors or len(dimensions) != 1 or 0 in dimensions:
            raise EmbeddingError(
                f"The embedding model '{self.model_name}' returned inconsistent vectors."
            )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise EmbeddingError("Cannot embed an empty question.")
        return self.embed_documents([text])[0]


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Return the process-wide embedding service (model loads lazily)."""
    return SentenceTransformerEmbeddingService(get_settings())
