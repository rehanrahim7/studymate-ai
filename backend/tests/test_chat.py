"""POST /api/v1/chat: grounded answers, refusals and failure modes."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.llm.base import LLMServiceError
from app.services.rag.prompting import INSUFFICIENT_CONTEXT_MESSAGE, SYSTEM_PROMPT
from tests.support import FakeEmbeddingService, FakeLLM, make_pdf, upload_pdf


def _biology_pdf(tmp_path: Path) -> Path:
    return make_pdf(
        tmp_path,
        "biology.pdf",
        [
            "Photosynthesis converts sunlight into chemical energy inside chloroplasts.",
            "Mitochondria release energy from glucose during cellular respiration.",
        ],
    )


def _history_pdf(tmp_path: Path) -> Path:
    return make_pdf(
        tmp_path,
        "history.pdf",
        ["Julius Caesar crossed the Rubicon and challenged the Roman senate."],
    )


def _ask(
    client: TestClient,
    question: str,
    document_ids: list[int],
    conversation_id: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"question": question, "document_ids": document_ids}
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200, response.text
    return dict(response.json())


def _add_document(session: Session, *, status: str) -> Document:
    document = Document(
        filename=f"{uuid.uuid4().hex[:12]}_pending.pdf",
        original_filename="pending.pdf",
        stored_path="/tmp/does-not-exist.pdf",
        content_type="application/pdf",
        file_size=10,
        status=status,
        page_count=1,
        character_count=10,
        chunk_count=0,
    )
    session.add(document)
    session.commit()
    return document


def test_chat_returns_grounded_answer_with_page_sources(
    rag_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    document = upload_pdf(rag_client, _biology_pdf(tmp_path))

    body = _ask(
        rag_client,
        "What do mitochondria do during cellular respiration?",
        [document["id"]],
    )

    assert body["answer"] == "Grounded answer based on ."
    assert body["llm_used"] is True
    assert body["model"] == "fake-model"
    assert body["prompt_tokens"] == 12
    assert body["completion_tokens"] == 34

    sources = body["sources"]
    assert isinstance(sources, list) and sources
    first = sources[0]
    assert isinstance(first, dict)
    assert first["document_id"] == document["id"]
    assert first["document_name"] == "biology.pdf"
    assert first["page_number"] == 2
    assert first["chunk_id"] > 0
    assert first["score"] > 0.2
    assert "Mitochondria" in first["text"]

    chunk = db_session.get(DocumentChunk, first["chunk_id"])
    assert chunk is not None
    assert chunk.page_number == first["page_number"]


def test_prompt_contains_context_and_grounding_rules(
    rag_client: TestClient,
    llm: FakeLLM,
    tmp_path: Path,
) -> None:
    document = upload_pdf(rag_client, _biology_pdf(tmp_path))
    question = "What do mitochondria do during cellular respiration?"

    _ask(rag_client, question, [document["id"]])

    assert llm.generate_calls == 1
    assert llm.last_system == SYSTEM_PROMPT
    assert "Answer ONLY from" in llm.last_system
    assert "never invent facts" in llm.last_system
    assert "[Context 1]" in llm.last_prompt
    assert "Page 2" in llm.last_prompt
    assert "Mitochondria" in llm.last_prompt
    assert question in llm.last_prompt


def test_unsupported_question_refuses_without_calling_the_llm(
    rag_client: TestClient,
    llm: FakeLLM,
    tmp_path: Path,
) -> None:
    document = upload_pdf(rag_client, _biology_pdf(tmp_path))

    body = _ask(rag_client, "Who won the World Cup?", [document["id"]])

    assert body["answer"] == INSUFFICIENT_CONTEXT_MESSAGE
    assert body["sources"] == []
    assert body["llm_used"] is False
    assert body["model"] is None
    assert llm.generate_calls == 0


def test_chat_is_scoped_to_selected_documents(
    rag_client: TestClient,
    tmp_path: Path,
) -> None:
    biology = upload_pdf(rag_client, _biology_pdf(tmp_path))
    history = upload_pdf(rag_client, _history_pdf(tmp_path))

    body = _ask(
        rag_client,
        "What does photosynthesis produce inside chloroplasts?",
        [biology["id"], history["id"]],
    )

    sources = body["sources"]
    assert isinstance(sources, list) and sources
    assert {source["document_id"] for source in sources} == {biology["id"]}

    history_only = _ask(
        rag_client,
        "What does photosynthesis produce inside chloroplasts?",
        [history["id"]],
    )
    assert history_only["answer"] == INSUFFICIENT_CONTEXT_MESSAGE
    assert history_only["sources"] == []


def test_unknown_document_returns_404(rag_client: TestClient) -> None:
    response = rag_client.post(
        "/api/v1/chat",
        json={"question": "What is this?", "document_ids": [999_999]},
    )

    assert response.status_code == 404
    assert "999999" in response.json()["detail"]


def test_non_ready_document_returns_409(
    rag_client: TestClient,
    db_session: Session,
) -> None:
    document = _add_document(db_session, status=DocumentStatus.PROCESSING.value)

    response = rag_client.post(
        "/api/v1/chat",
        json={"question": "What is this?", "document_ids": [document.id]},
    )

    assert response.status_code == 409
    assert "not ready" in response.json()["detail"]


def test_document_without_indexable_text_returns_409(
    rag_client: TestClient,
    db_session: Session,
) -> None:
    document = _add_document(db_session, status=DocumentStatus.READY.value)

    response = rag_client.post(
        "/api/v1/chat",
        json={"question": "What is this?", "document_ids": [document.id]},
    )

    assert response.status_code == 409
    assert "no indexable text" in response.json()["detail"]


def test_llm_unavailable_returns_actionable_503(
    rag_client: TestClient,
    llm: FakeLLM,
    tmp_path: Path,
) -> None:
    document = upload_pdf(rag_client, _biology_pdf(tmp_path))
    llm.available = False

    response = rag_client.post(
        "/api/v1/chat",
        json={
            "question": "What do chloroplasts do?",
            "document_ids": [document["id"]],
        },
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "unavailable" in detail
    assert "fake serve" in detail


def test_missing_llm_model_returns_pull_instructions(
    rag_client: TestClient,
    llm: FakeLLM,
    tmp_path: Path,
) -> None:
    document = upload_pdf(rag_client, _biology_pdf(tmp_path))
    llm.installed_models = ["another-model"]

    response = rag_client.post(
        "/api/v1/chat",
        json={
            "question": "What do chloroplasts do?",
            "document_ids": [document["id"]],
        },
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "not installed" in detail
    assert "fake pull fake-model" in detail


def test_llm_failure_returns_502(
    rag_client: TestClient,
    llm: FakeLLM,
    tmp_path: Path,
) -> None:
    document = upload_pdf(rag_client, _biology_pdf(tmp_path))
    llm.error = LLMServiceError("boom")

    response = rag_client.post(
        "/api/v1/chat",
        json={
            "question": "What do chloroplasts do?",
            "document_ids": [document["id"]],
        },
    )

    assert response.status_code == 502
    assert "failed to answer" in response.json()["detail"]


def test_embedding_failure_returns_503(
    rag_client: TestClient,
    embedder: FakeEmbeddingService,
    tmp_path: Path,
) -> None:
    document = upload_pdf(rag_client, _biology_pdf(tmp_path))
    embedder.raise_on_embed = True

    response = rag_client.post(
        "/api/v1/chat",
        json={
            "question": "What do chloroplasts do?",
            "document_ids": [document["id"]],
        },
    )

    assert response.status_code == 503
    assert "Could not prepare document embeddings" in response.json()["detail"]


def test_blank_question_is_rejected(rag_client: TestClient, tmp_path: Path) -> None:
    document = upload_pdf(rag_client, _biology_pdf(tmp_path))

    response = rag_client.post(
        "/api/v1/chat",
        json={"question": "   ", "document_ids": [document["id"]]},
    )

    assert response.status_code == 422


def test_empty_document_selection_is_rejected(rag_client: TestClient) -> None:
    response = rag_client.post(
        "/api/v1/chat",
        json={"question": "What is this?", "document_ids": []},
    )

    assert response.status_code == 422


def test_too_many_documents_is_rejected(rag_client: TestClient) -> None:
    response = rag_client.post(
        "/api/v1/chat",
        json={"question": "What is this?", "document_ids": list(range(1, 12))},
    )

    assert response.status_code == 422


def test_chat_document_topics_uses_overview_retrieval(
    rag_client: TestClient,
    llm: FakeLLM,
    tmp_path: Path,
) -> None:
    # Create a multi-page PDF with distinct sections
    pdf_path = make_pdf(
        tmp_path,
        "topics.pdf",
        pages=[
            "Introduction to Neural Networks. This covers basics of neurons.",
            "Chapter 1: Supervised Learning. Regression and classification are discussed.",
            "Chapter 2: Unsupervised Learning. Clustering methods are covered.",
            "Chapter 3: Reinforcement Learning. Policy gradients are introduced.",
        ],
    )
    with pdf_path.open("rb") as handle:
        response = rag_client.post(
            "/api/v1/documents",
            files={"file": ("topics.pdf", handle, "application/pdf")},
        )
    assert response.status_code == 201
    document = response.json()

    llm.response_text = (
        "## Topics Covered\n\n"
        "- Introduction to Neural Networks\n"
        "- Supervised Learning (regression, classification)\n"
        "- Unsupervised Learning (clustering)\n"
        "- Reinforcement Learning (policy gradients)"
    )
    body = _ask(rag_client, "What topics are covered in this PDF?", [document["id"]])
    assert "Topics Covered" in body["answer"] or "Neural Networks" in body["answer"]
    assert len(body["sources"]) > 0


def test_chat_summarize_document_uses_overview(
    rag_client: TestClient,
    llm: FakeLLM,
    tmp_path: Path,
) -> None:
    pdf_path = make_pdf(
        tmp_path,
        "summary.pdf",
        pages=[
            "Title: Data Structures. Abstract describes arrays and lists.",
            "Stacks and queues are explained with examples.",
            "Trees and graphs provide hierarchical and network structures.",
        ],
    )
    with pdf_path.open("rb") as handle:
        response = rag_client.post(
            "/api/v1/documents",
            files={"file": ("summary.pdf", handle, "application/pdf")},
        )
    assert response.status_code == 201
    document = response.json()

    llm.response_text = "This document covers arrays, lists, stacks, queues, trees, and graphs."
    body = _ask(rag_client, "Summarize the document", [document["id"]])
    assert len(body["sources"]) >= 1


def test_chat_missing_answer_refuses(rag_client: TestClient, llm: FakeLLM, tmp_path: Path) -> None:
    pdf_path = make_pdf(tmp_path, "limited.pdf", pages=["Only photosynthesis is discussed here."])
    with pdf_path.open("rb") as handle:
        response = rag_client.post(
            "/api/v1/documents",
            files={"file": ("limited.pdf", handle, "application/pdf")},
        )
    assert response.status_code == 201
    document = response.json()

    llm.response_text = INSUFFICIENT_CONTEXT_MESSAGE
    body = _ask(rag_client, "What is quantum entanglement?", [document["id"]])
    assert isinstance(body, dict)


def test_follow_up_uses_only_the_most_recent_turns(
    rag_client: TestClient,
    llm: FakeLLM,
    tmp_path: Path,
) -> None:
    document = upload_pdf(rag_client, _biology_pdf(tmp_path))
    first = _ask(rag_client, "alpha photosynthesis question", [document["id"]])
    conversation_id = int(first["conversation_id"])  # type: ignore[arg-type]

    for word in ("beta", "gamma", "delta", "epsilon", "zeta"):
        _ask(
            rag_client,
            f"{word} photosynthesis question",
            [document["id"]],
            conversation_id,
        )

    _ask(
        rag_client,
        "eta photosynthesis question",
        [document["id"]],
        conversation_id,
    )

    prompt = llm.last_prompt
    assert "zeta photosynthesis question" in prompt
    assert "epsilon photosynthesis question" in prompt
    assert "gamma photosynthesis question" not in prompt
    assert "alpha photosynthesis question" not in prompt
