"""Lazy access to the optional RAG dependencies.

`faiss` and `numpy` live in the optional `[rag]` extra. Importing them lazily
keeps the rest of the API (uploads, listings, health) working for users who
have not installed the extra yet; only retrieval returns an actionable error.
"""

from __future__ import annotations

from functools import lru_cache
from types import ModuleType

INSTALL_HINT = "Install the retrieval dependencies with: pip install -e '.[rag]'"


class RagDependencyError(RuntimeError):
    """Raised when an optional retrieval dependency is not installed."""


@lru_cache(maxsize=1)
def get_numpy() -> ModuleType:
    try:
        import numpy
    except ImportError as exc:  # pragma: no cover - depends on the local environment
        raise RagDependencyError(f"NumPy is required for retrieval. {INSTALL_HINT}") from exc
    return numpy


@lru_cache(maxsize=1)
def get_faiss() -> ModuleType:
    try:
        import faiss
    except ImportError as exc:  # pragma: no cover - depends on the local environment
        raise RagDependencyError(f"FAISS is required for retrieval. {INSTALL_HINT}") from exc
    return faiss
