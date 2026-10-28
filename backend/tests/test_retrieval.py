"""Retrieval behaviour: relevance, isolation, metadata and index reuse."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document, DocumentStatus
from app.models.embedding import ChunkEmbedding
from app.services.rag.embeddings import EmbeddingError
from app.services.rag.indexer import EmptyDocumentError
from app.services.rag.retriever import (
    DocumentNotReadyError,
    DocumentsNotFoundError,
    Retriever,
)
from tests.support import FakeEmbeddingService, make_pdf, upload_pdf


def _add_document(
    session: Session,
    *,
    status: str,
    chunk_count: int = 0,
    name: str = "pending.pdf",
) -> Document:
    document = Document(
        filename=f"{uuid.uuid4().hex[:12]}_{name}",
        original_filename=name,
        stored_path="/tmp/does-not-exist.pdf",
        content_type="application/pdf",
        file_size=10,
        status=status,
        page_count=1,
        character_count=10,
        chunk_count=chunk_count,
    )
    session.add(document)
    session.commit()
    return document


def _biology_pdf(tmp_path: Path) -> Path:
    return make_pdf(
        tmp_path,
        "biology.pdf",
        [
            "Photosynthesis converts sunlight into chemical energy inside chloroplasts.",
            "Mitochondria release energy from glucose during cellular respiration.",
        ],
    )


def test_retrieval_returns_relevant_chunk_with_page_metadata(
    client: TestClient,
    db_session: Session,
    embedder: FakeEmbeddingService,
    tmp_path: Path,
) -> None:
    document = upload_pdf(client, _biology_pdf(tmp_path))
    retriever = Retriever(db_session, embedder)

    hits = retriever.retrieve(
        [document["id"]],
        "How do chloroplasts use sunlight for photosynthesis?",
    )

    assert hits, "expected at least one relevant chunk"
    assert hits[0].document_id == document["id"]
    assert hits[0].document_name == "biology.pdf"
    assert hits[0].page_number == 1
    assert hits[0].chunk_id > 0
    assert "Photosynthesis" in hits[0].text
    assert hits[0].score > 0.3


def test_retrieval_is_restricted_to_selected_documents(
    client: TestClient,
    db_session: Session,
    embedder: FakeEmbeddingService,
    tmp_path: Path,
) -> None:
    biology = upload_pdf(client, _biology_pdf(tmp_path))
    history = upload_pdf(
        client,
        make_pdf(
            tmp_path,
            "history.pdf",
            ["The Roman senate debated the future of the republic."],
        ),
    )
    retriever = Retriever(db_session, embedder)

    both = retriever.retrieve(
        [biology["id"], history["id"]],
        "photosynthesis chloroplasts sunlight",
    )
    assert both
    assert {hit.document_id for hit in both} == {biology["id"]}

    history_only = retriever.retrieve(
        [history["id"]],
        "photosynthesis chloroplasts sunlight",
    )
    assert all(hit.document_id == history["id"] for hit in history_only)
    assert not any(hit.document_id == biology["id"] for hit in history_only)


def test_second_page_chunk_keeps_its_page_number(
    client: TestClient,
    db_session: Session,
    embedder: FakeEmbeddingService,
    tmp_path: Path,
) -> None:
    document = upload_pdf(client, _biology_pdf(tmp_path))
    retriever = Retriever(db_session, embedder)

    hits = retriever.retrieve(
        [document["id"]],
        "What do mitochondria do during cellular respiration?",
    )

    assert hits
    assert hits[0].page_number == 2
    assert "Mitochondria" in hits[0].text


def test_embeddings_are_cached_and_index_files_are_created(
    client: TestClient,
    db_session: Session,
    embedder: FakeEmbeddingService,
    tmp_path: Path,
) -> None:
    document = upload_pdf(client, _biology_pdf(tmp_path))
    retriever = Retriever(db_session, embedder)
    settings = get_settings()

    retriever.retrieve([document["id"]], "photosynthesis chloroplasts")
    assert embedder.document_batch_calls == 1
    assert len(embedder.embedded_texts) == document["chunk_count"]

    faiss_path = settings.index_dir / f"{document['id']}.faiss"
    metadata_path = settings.index_dir / f"{document['id']}.json"
    assert faiss_path.exists()
    assert metadata_path.exists()

    retriever.retrieve([document["id"]], "photosynthesis chloroplasts")
    assert embedder.document_batch_calls == 1, "cached embeddings must not be recomputed"


def test_deleted_index_rebuilds_from_stored_embeddings(
    client: TestClient,
    db_session: Session,
    embedder: FakeEmbeddingService,
    tmp_path: Path,
) -> None:
    document = upload_pdf(client, _biology_pdf(tmp_path))
    retriever = Retriever(db_session, embedder)
    settings = get_settings()
    document_id = document["id"]

    retriever.retrieve([document_id], "photosynthesis chloroplasts")
    assert embedder.document_batch_calls == 1

    for suffix in (".faiss", ".json"):
        (settings.index_dir / f"{document_id}{suffix}").unlink()

    hits = retriever.retrieve([document_id], "photosynthesis chloroplasts")

    assert hits
    assert embedder.document_batch_calls == 1, "stored vectors should be reused"
    assert embedder.query_calls == 2
    assert (settings.index_dir / f"{document_id}.faiss").exists()


def test_switching_embedding_models_reembeds_chunks(
    client: TestClient,
    db_session: Session,
    embedder: FakeEmbeddingService,
    tmp_path: Path,
) -> None:
    document = upload_pdf(client, _biology_pdf(tmp_path))
    Retriever(db_session, embedder).retrieve([document["id"]], "photosynthesis")

    other_model = FakeEmbeddingService(model_name="fake-embedding-v2")
    Retriever(db_session, other_model).retrieve([document["id"]], "photosynthesis")

    assert other_model.document_batch_calls == 1
    assert len(other_model.embedded_texts) == document["chunk_count"]


def test_deleting_a_document_removes_its_index_and_embeddings(
    client: TestClient,
    db_session: Session,
    embedder: FakeEmbeddingService,
    tmp_path: Path,
) -> None:
    document = upload_pdf(client, _biology_pdf(tmp_path))
    document_id = document["id"]
    Retriever(db_session, embedder).retrieve([document_id], "photosynthesis")
    settings = get_settings()

    assert (settings.index_dir / f"{document_id}.faiss").exists()
    assert (settings.index_dir / f"{document_id}.json").exists()

    assert client.delete(f"/api/v1/documents/{document_id}").status_code == 204

    assert not (settings.index_dir / f"{document_id}.faiss").exists()
    assert not (settings.index_dir / f"{document_id}.json").exists()
    remaining = db_session.scalars(
        select(ChunkEmbedding).where(ChunkEmbedding.document_id == document_id)
    ).all()
    assert remaining == []


def test_unknown_document_is_reported(
    db_session: Session,
    embedder: FakeEmbeddingService,
) -> None:
    retriever = Retriever(db_session, embedder)

    with pytest.raises(DocumentsNotFoundError) as excinfo:
        retriever.retrieve([999_999], "anything")

    assert excinfo.value.document_ids == [999_999]


def test_document_that_is_not_ready_is_rejected(
    db_session: Session,
    embedder: FakeEmbeddingService,
) -> None:
    document = _add_document(db_session, status=DocumentStatus.PROCESSING.value)
    retriever = Retriever(db_session, embedder)

    with pytest.raises(DocumentNotReadyError):
        retriever.retrieve([document.id], "anything")


def test_document_without_chunks_is_rejected(
    db_session: Session,
    embedder: FakeEmbeddingService,
) -> None:
    document = _add_document(db_session, status=DocumentStatus.READY.value, chunk_count=0)
    retriever = Retriever(db_session, embedder)

    with pytest.raises(EmptyDocumentError):
        retriever.retrieve([document.id], "anything")


def test_embedding_failure_is_surfaced(
    client: TestClient,
    db_session: Session,
    embedder: FakeEmbeddingService,
    tmp_path: Path,
) -> None:
    document = upload_pdf(client, _biology_pdf(tmp_path))
    embedder.raise_on_embed = True
    retriever = Retriever(db_session, embedder)

    with pytest.raises(EmbeddingError):
        retriever.retrieve([document["id"]], "photosynthesis")


def test_irrelevant_question_returns_no_hits(
    client: TestClient,
    db_session: Session,
    embedder: FakeEmbeddingService,
    tmp_path: Path,
) -> None:
    document = upload_pdf(client, _biology_pdf(tmp_path))
    retriever = Retriever(db_session, embedder)

    assert retriever.retrieve([document["id"]], "Who won the World Cup?") == []
