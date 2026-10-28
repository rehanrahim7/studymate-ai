"""FAISS index building, search and persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.rag.vector_store import FaissVectorIndex, VectorIndexError


def test_search_orders_by_cosine_similarity() -> None:
    index = FaissVectorIndex.from_vectors(
        [10, 11, 12],
        [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]],
    )

    hits = index.search([1.0, 0.0], top_k=3)

    assert [hit.chunk_id for hit in hits] == [10, 11, 12]
    assert hits[0].score == pytest.approx(1.0, abs=1e-6)
    assert hits[0].score > hits[1].score > hits[2].score


def test_top_k_is_clamped_to_index_size() -> None:
    index = FaissVectorIndex.from_vectors([1, 2], [[1.0, 0.0], [0.0, 1.0]])

    assert len(index.search([1.0, 0.0], top_k=50)) == 2


def test_empty_index_is_rejected() -> None:
    with pytest.raises(VectorIndexError):
        FaissVectorIndex.from_vectors([], [])


def test_mismatched_ids_and_vectors_are_rejected() -> None:
    with pytest.raises(VectorIndexError):
        FaissVectorIndex.from_vectors([1, 2], [[1.0, 0.0]])


def test_query_dimension_must_match() -> None:
    index = FaissVectorIndex.from_vectors([1], [[1.0, 0.0, 0.0]])

    with pytest.raises(VectorIndexError):
        index.search([1.0, 0.0])


def test_non_finite_vectors_are_rejected() -> None:
    with pytest.raises(VectorIndexError):
        FaissVectorIndex.from_vectors([1], [[float("nan"), 1.0]])


def test_index_round_trips_through_disk(tmp_path: Path) -> None:
    index = FaissVectorIndex.from_vectors([7, 8], [[1.0, 0.0], [0.0, 1.0]])
    path = tmp_path / "test.faiss"

    index.save(path)
    loaded = FaissVectorIndex.load(path, [7, 8])

    assert loaded.size == 2
    assert loaded.dimension == 2
    assert [hit.chunk_id for hit in loaded.search([0.0, 1.0])] == [8, 7]


def test_loading_with_wrong_chunk_count_is_rejected(tmp_path: Path) -> None:
    index = FaissVectorIndex.from_vectors([7, 8], [[1.0, 0.0], [0.0, 1.0]])
    path = tmp_path / "test.faiss"
    index.save(path)

    with pytest.raises(VectorIndexError):
        FaissVectorIndex.load(path, [7])
