"""Retrieval quality regression tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from tests.support import FakeLLM, make_pdf


def _ask(client: TestClient, question: str, document_ids: list[int]):
    response = client.post(
        "/api/v1/chat",
        json={"question": question, "document_ids": document_ids},
    )
    assert response.status_code == 200
    return response.json()


def test_retrieval_respects_document_scope(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    pdf1 = make_pdf(tmp_path, "doc1.pdf", pages=["Quantum entanglement is a phenomenon."])
    pdf2 = make_pdf(tmp_path, "doc2.pdf", pages=["Photosynthesis converts light to energy."])
    
    for pdf in [pdf1, pdf2]:
        with pdf.open("rb") as f:
            rag_client.post("/api/v1/documents", files={"file": (pdf.name, f, "application/pdf")})
    
    docs = rag_client.get("/api/v1/documents").json()["documents"]
    doc1 = next(d for d in docs if d["original_filename"] == "doc1.pdf")
    
    llm.response_text = "Quantum entanglement is a phenomenon."
    result = _ask(rag_client, "What is quantum entanglement?", [doc1["id"]])
    assert "Quantum" in result["answer"]
    # Should not contain photosynthesis from doc2
    assert "Photosynthesis" not in result["answer"]


def test_unsupported_question_refuses(rag_client: TestClient, llm: FakeLLM, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path, "limited.pdf", pages=["Only cats are discussed."])
    with pdf.open("rb") as f:
        rag_client.post("/api/v1/documents", files={"file": ("limited.pdf", f, "application/pdf")})
    
    docs = rag_client.get("/api/v1/documents").json()["documents"]
    doc = docs[0]
    
    llm.response_text = (
        "The uploaded material does not provide enough information to answer that question."
    )
    result = _ask(rag_client, "What is quantum computing?", [doc["id"]])
    assert result["answer"] == (
        "The uploaded material does not provide enough information to answer that question."
    )
    assert result["llm_used"] is False
    assert len(result["sources"]) == 0
