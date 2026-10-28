"""Conversation CRUD and persisted chat history."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document import Message
from tests.support import make_pdf, upload_pdf


def _biology_pdf(tmp_path: Path) -> Path:
    return make_pdf(
        tmp_path,
        "biology-history.pdf",
        ["Photosynthesis converts sunlight into chemical energy inside chloroplasts."],
    )


def _ask(
    client: TestClient,
    question: str,
    document_id: int,
    conversation_id: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"question": question, "document_ids": [document_id]}
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200, response.text
    return dict(response.json())


def test_conversation_crud_round_trip(rag_client: TestClient) -> None:
    title = f"Exam prep {uuid.uuid4().hex[:8]}"

    created = rag_client.post(
        "/api/v1/conversations",
        json={"title": title, "document_ids": [7, 8]},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    conversation_id = body["id"]
    assert body["title"] == title
    assert body["document_ids"] == [7, 8]
    assert body["message_count"] == 0

    listed = rag_client.get("/api/v1/conversations")
    assert listed.status_code == 200
    listed_item = next(item for item in listed.json() if item["id"] == conversation_id)
    assert listed_item["message_count"] == 0

    detail = rag_client.get(f"/api/v1/conversations/{conversation_id}")
    assert detail.status_code == 200
    assert detail.json()["messages"] == []

    renamed = rag_client.patch(
        f"/api/v1/conversations/{conversation_id}",
        json={"title": "Renamed conversation"},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["title"] == "Renamed conversation"
    assert renamed.json()["message_count"] == 0

    deleted = rag_client.delete(f"/api/v1/conversations/{conversation_id}")
    assert deleted.status_code == 204
    assert rag_client.get(f"/api/v1/conversations/{conversation_id}").status_code == 404


def test_chat_persists_messages_and_updates_history(
    rag_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    document = upload_pdf(rag_client, _biology_pdf(tmp_path))
    question = "What does photosynthesis convert?"

    first = _ask(rag_client, question, document["id"])
    conversation_id = int(first["conversation_id"])  # type: ignore[arg-type]

    detail = rag_client.get(f"/api/v1/conversations/{conversation_id}")
    assert detail.status_code == 200
    conversation = detail.json()
    assert conversation["title"] == question
    assert conversation["document_ids"] == [document["id"]]
    assert [message["role"] for message in conversation["messages"]] == ["user", "assistant"]

    user_message, assistant_message = conversation["messages"]
    assert user_message["content"] == question
    assert assistant_message["content"] == first["answer"]
    assert assistant_message["model"] == "fake-model"
    assert assistant_message["llm_used"] is True
    assert assistant_message["sources"]

    _ask(rag_client, "What are chloroplasts?", document["id"], conversation_id)

    updated = rag_client.get(f"/api/v1/conversations/{conversation_id}").json()
    assert len(updated["messages"]) == 4
    assert updated["title"] == question

    listed = rag_client.get("/api/v1/conversations").json()
    listed_item = next(item for item in listed if item["id"] == conversation_id)
    assert listed_item["message_count"] == 4

    deleted = rag_client.delete(f"/api/v1/conversations/{conversation_id}")
    assert deleted.status_code == 204

    remaining = db_session.scalar(
        select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
    )
    assert remaining == 0


def test_missing_conversation_returns_404(rag_client: TestClient) -> None:
    missing_id = 999_999

    assert rag_client.get(f"/api/v1/conversations/{missing_id}").status_code == 404
    assert (
        rag_client.patch(
            f"/api/v1/conversations/{missing_id}",
            json={"title": "Still missing"},
        ).status_code
        == 404
    )
    assert rag_client.delete(f"/api/v1/conversations/{missing_id}").status_code == 404
