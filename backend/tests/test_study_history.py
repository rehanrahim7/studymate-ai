"""Regression tests for saved study history, quiz scoring, and source isolation."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.study import FlashcardDeck, Quiz
from tests.support import FakeLLM, make_pdf, upload_pdf
from tests.test_study_tools import SOURCE_TEXT, VALID_CARDS, VALID_QUIZ

OTHER_TEXT = (
    "The Federal Reserve adjusts interest rates to influence inflation and employment. "
    "Higher interest rates reduce borrowing and spending across the economy. "
    "Lower interest rates encourage investment and hiring by businesses. "
    "The central bank monitors price stability and maximum employment. "
    "Monetary policy affects commercial banks and financial markets."
)
OTHER_CARDS = [
    {
        "question": "What does the Federal Reserve adjust to influence inflation and employment?",
        "answer": "Interest rates.",
    },
    {
        "question": "What do higher interest rates reduce?",
        "answer": "Borrowing and spending.",
    },
    {
        "question": "What does the central bank monitor?",
        "answer": "Price stability and maximum employment.",
    },
]
OTHER_QUIZ = [
    {
        "question": "What does the Federal Reserve adjust to influence inflation?",
        "options": ["Interest rates", "Income taxes", "Tariffs", "Wages"],
        "answer": "Interest rates",
        "explanation": "The Federal Reserve adjusts interest rates to influence inflation.",
    },
    {
        "question": "What do higher interest rates reduce?",
        "options": ["Borrowing and spending", "Employment", "Bank reserves", "Price stability"],
        "answer": "Borrowing and spending",
        "explanation": "Higher interest rates reduce borrowing and spending.",
    },
    {
        "question": "What does the central bank monitor?",
        "options": [
            "Price stability and employment",
            "Corporate profits",
            "Stock prices",
            "Import volumes",
        ],
        "answer": "Price stability and employment",
        "explanation": "The central bank monitors price stability and maximum employment.",
    },
]


def _document(
    client: TestClient, tmp_path: Path, name: str, content: str = SOURCE_TEXT
) -> int:
    pdf = make_pdf(tmp_path, name, pages=[content])
    return int(upload_pdf(client, pdf)["id"])


def _deck(client: TestClient, document_id: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/study/flashcards",
        json={"document_id": document_id, "count": 3},
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def _quiz(client: TestClient, document_id: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/study/quiz",
        json={"document_id": document_id, "count": 3},
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def _answers(questions: list[dict[str, object]]) -> list[str]:
    return [str(question["answer"]) for question in questions]


def test_flashcard_deck_persists_and_reopens(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "history-cards.pdf")
    llm.response_text = json.dumps(VALID_CARDS)

    generated = _deck(rag_client, document_id)
    deck_id = int(generated["id"])

    with SessionLocal() as fresh_session:
        stored = fresh_session.get(FlashcardDeck, deck_id)
        assert stored is not None
        assert stored.get_cards() == VALID_CARDS
        assert stored.source_document_id == document_id
        chunk_ids = stored.get_source_chunk_ids()
        chunks = fresh_session.scalars(
            select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
        ).all()
        assert chunks
        assert all(chunk.document_id == document_id for chunk in chunks)

    reopened = rag_client.get(f"/api/v1/study/flashcards/{deck_id}")
    assert reopened.status_code == 200, reopened.text
    payload = reopened.json()
    assert payload["flashcards"] == VALID_CARDS
    assert payload["title"].startswith("Flashcards")
    assert payload["source_label"] == "history-cards.pdf"

    listed = rag_client.get("/api/v1/study/flashcards?limit=50")
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == deck_id for item in listed.json()["decks"])


def test_quiz_history_submission_and_validation(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "history-quiz.pdf")
    llm.response_text = json.dumps(VALID_QUIZ)

    generated = _quiz(rag_client, document_id)
    quiz_id = int(generated["id"])
    questions = list(generated["questions"])
    assert all(question["correct_answer"] is None for question in questions)

    detail = rag_client.get(f"/api/v1/study/quizzes/{quiz_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "open"
    assert all(question["correct_answer"] is None for question in detail.json()["questions"])

    short = rag_client.post(
        f"/api/v1/study/quizzes/{quiz_id}/submit",
        json={"answers": ["Chemical energy"]},
    )
    assert short.status_code == 422

    invalid = rag_client.post(
        f"/api/v1/study/quizzes/{quiz_id}/submit",
        json={"answers": ["Not an option"] * 3},
    )
    assert invalid.status_code == 422

    submitted = rag_client.post(
        f"/api/v1/study/quizzes/{quiz_id}/submit",
        json={"answers": _answers(VALID_QUIZ)},
    )
    assert submitted.status_code == 200, submitted.text
    result = submitted.json()
    assert result["score"] == 3
    assert result["status"] == "completed"
    assert result["completed_at"] is not None

    reopened = rag_client.get(f"/api/v1/study/quizzes/{quiz_id}")
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["score"] == 3
    assert reopened.json()["questions"][0]["correct_answer"] is not None

    with SessionLocal() as fresh_session:
        stored = fresh_session.get(Quiz, quiz_id)
        assert stored is not None
        assert stored.get_submitted_answers() == _answers(VALID_QUIZ)
        assert stored.score == 3
        assert stored.completed_at is not None

    listed = rag_client.get("/api/v1/study/quizzes?limit=50")
    assert listed.status_code == 200, listed.text
    item = next(entry for entry in listed.json()["quizzes"] if entry["id"] == quiz_id)
    assert item["status"] == "completed"
    assert item["score"] == 3


def test_study_generation_is_scoped_to_each_document(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    first_id = _document(rag_client, tmp_path, "scope-first.pdf")
    second_id = _document(rag_client, tmp_path, "scope-second.pdf", OTHER_TEXT)

    llm.response_text = json.dumps(VALID_CARDS)
    first_deck = _deck(rag_client, first_id)
    first_prompt = llm.last_prompt
    assert "Photosynthesis converts light energy" in first_prompt
    assert "Federal Reserve adjusts interest rates" not in first_prompt

    llm.response_text = json.dumps(OTHER_CARDS)
    second_deck = _deck(rag_client, second_id)
    second_prompt = llm.last_prompt
    assert "Federal Reserve adjusts interest rates" in second_prompt
    assert "Photosynthesis converts light energy" not in second_prompt

    llm.response_text = json.dumps(VALID_QUIZ)
    first_quiz = _quiz(rag_client, first_id)
    assert "Photosynthesis converts light energy" in llm.last_prompt
    assert "Federal Reserve adjusts interest rates" not in llm.last_prompt

    llm.response_text = json.dumps(OTHER_QUIZ)
    second_quiz = _quiz(rag_client, second_id)
    assert "Federal Reserve adjusts interest rates" in llm.last_prompt
    assert "Photosynthesis converts light energy" not in llm.last_prompt

    assert first_deck["source_document_id"] == first_id
    assert second_deck["source_document_id"] == second_id
    assert first_quiz["source_document_id"] == first_id
    assert second_quiz["source_document_id"] == second_id

    with SessionLocal() as fresh_session:
        for deck_id, document_id in (
            (int(first_deck["id"]), first_id),
            (int(second_deck["id"]), second_id),
        ):
            deck = fresh_session.get(FlashcardDeck, deck_id)
            assert deck is not None
            chunks = fresh_session.scalars(
                select(DocumentChunk).where(
                    DocumentChunk.id.in_(deck.get_source_chunk_ids())
                )
            ).all()
            assert chunks
            assert {chunk.document_id for chunk in chunks} == {document_id}


def test_history_survives_source_document_deletion(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "source-delete.pdf")
    llm.response_text = json.dumps(VALID_CARDS)
    deck = _deck(rag_client, document_id)

    llm.response_text = json.dumps(VALID_QUIZ)
    quiz = _quiz(rag_client, document_id)

    conversation = rag_client.post(
        "/api/v1/conversations", json={"title": "Keep this conversation"}
    )
    assert conversation.status_code == 201, conversation.text
    conversation_id = conversation.json()["id"]

    deleted = rag_client.delete(f"/api/v1/documents/{document_id}")
    assert deleted.status_code == 204, deleted.text

    saved_deck = rag_client.get(f"/api/v1/study/flashcards/{deck['id']}")
    assert saved_deck.status_code == 200, saved_deck.text
    deck_payload = saved_deck.json()
    assert deck_payload["flashcards"] == VALID_CARDS
    assert deck_payload["source_document_id"] is None
    assert deck_payload["source_label"] == "source-delete.pdf"
    assert deck_payload["source_available"] is False
    assert deck_payload["source_status"] == "deleted"
    assert deck_payload["source_changed"] is False

    saved_quiz = rag_client.get(f"/api/v1/study/quizzes/{quiz['id']}")
    assert saved_quiz.status_code == 200, saved_quiz.text
    quiz_payload = saved_quiz.json()
    assert quiz_payload["question_count"] == 3
    assert quiz_payload["source_document_id"] is None
    assert quiz_payload["source_label"] == "source-delete.pdf"
    assert quiz_payload["source_available"] is False
    assert quiz_payload["source_status"] == "deleted"

    _document(rag_client, tmp_path, "source-delete.pdf", OTHER_TEXT)
    still_saved_deck = rag_client.get(f"/api/v1/study/flashcards/{deck['id']}")
    still_saved_quiz = rag_client.get(f"/api/v1/study/quizzes/{quiz['id']}")
    assert still_saved_deck.status_code == 200, still_saved_deck.text
    assert still_saved_quiz.status_code == 200, still_saved_quiz.text
    assert still_saved_deck.json()["source_document_id"] is None
    assert still_saved_quiz.json()["source_document_id"] is None
    assert still_saved_deck.json()["source_label"] == "source-delete.pdf"
    assert still_saved_quiz.json()["source_label"] == "source-delete.pdf"

    saved_conversation = rag_client.get(f"/api/v1/conversations/{conversation_id}")
    assert saved_conversation.status_code == 200, saved_conversation.text


def test_source_changes_are_reported_without_replacing_saved_content(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path, db_session: Session
) -> None:
    document_id = _document(rag_client, tmp_path, "source-change.pdf")
    llm.response_text = json.dumps(VALID_CARDS)
    deck = _deck(rag_client, document_id)

    chunk = db_session.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.ordinal)
    ).first()
    assert chunk is not None
    chunk.text = f"{chunk.text} Newly added material."
    db_session.commit()

    reopened = rag_client.get(f"/api/v1/study/flashcards/{deck['id']}")
    assert reopened.status_code == 200, reopened.text
    payload = reopened.json()
    assert payload["source_available"] is True
    assert payload["source_changed"] is True
    assert payload["flashcards"] == VALID_CARDS


def test_study_generation_rejects_non_ready_document(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path, db_session: Session
) -> None:
    document_id = _document(rag_client, tmp_path, "not-ready.pdf")
    document = db_session.get(Document, document_id)
    assert document is not None
    document.status = DocumentStatus.PROCESSING.value
    db_session.commit()

    response = rag_client.post(
        "/api/v1/study/flashcards",
        json={"document_id": document_id, "count": 3},
    )

    assert response.status_code == 409
    assert llm.generate_calls == 0


def test_deleting_saved_study_sets_does_not_delete_source(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "delete-history.pdf")
    llm.response_text = json.dumps(VALID_CARDS)
    deck = _deck(rag_client, document_id)
    llm.response_text = json.dumps(VALID_QUIZ)
    quiz = _quiz(rag_client, document_id)

    deck_delete = rag_client.delete(f"/api/v1/study/flashcards/{deck['id']}")
    quiz_delete = rag_client.delete(f"/api/v1/study/quizzes/{quiz['id']}")

    assert deck_delete.status_code == 204
    assert quiz_delete.status_code == 204
    assert rag_client.get(f"/api/v1/study/flashcards/{deck['id']}").status_code == 404
    assert rag_client.get(f"/api/v1/study/quizzes/{quiz['id']}").status_code == 404
    assert rag_client.get(f"/api/v1/documents/{document_id}").status_code == 200
