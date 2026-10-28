"""Compact, lossless-enough float32 serialization for stored embeddings."""

from __future__ import annotations

from collections.abc import Sequence

from app.services.rag.dependencies import get_numpy


class VectorSerializationError(RuntimeError):
    """Raised when a stored or generated vector cannot be serialized."""


def encode_vector(values: Sequence[float]) -> bytes:
    """Encode a 1-D vector as little-endian float32 bytes."""
    numpy = get_numpy()
    array = numpy.asarray(values, dtype=numpy.float32)
    if array.ndim != 1 or array.size == 0:
        raise VectorSerializationError("Embedding vectors must be non-empty and one-dimensional.")
    if not bool(numpy.all(numpy.isfinite(array))):
        raise VectorSerializationError("Embedding vectors must contain finite numbers.")
    return bytes(array.tobytes())


def decode_vector(blob: bytes, *, dimension: int | None = None) -> list[float]:
    """Decode bytes produced by `encode_vector`."""
    numpy = get_numpy()
    if not blob:
        raise VectorSerializationError("Stored embedding is empty.")
    array = numpy.frombuffer(blob, dtype=numpy.float32)
    if dimension is not None and array.size != dimension:
        raise VectorSerializationError(
            f"Stored embedding has dimension {array.size}, expected {dimension}."
        )
    return [float(value) for value in array]
