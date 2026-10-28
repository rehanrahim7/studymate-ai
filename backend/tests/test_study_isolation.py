"""Cross-document isolation and persistence checks for study-tool generation."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.models.document import Conversation, Document, DocumentChunk, DocumentStatus, Message
from app.models.study import FlashcardDeck, Quiz
from app.services.study_content import content_tokens, has_source_overlap
from tests.support import FakeLLM, make_pdf, upload_pdf

OCEAN_TEXT = (
    "The research vessel Kelp Runner supports Abyssal Station at 47.2 degrees north. "
    "Abyssal Station sits 3,840 meters below the surface beside the Cerulean Trench. "
    "Chief scientist Dr. Mara Voss leads twelve researchers who study glass squid. "
    "The station pressure hull is rated to 8,200 meters and carries a cobalt blue beacon. "
    "Plankton samples are stored in freezer bay seven at minus 18 degrees Celsius."
)
MOUNTAIN_TEXT = (
    "The High Perch Observatory operates at 5,210 meters on Mount Solenne. "
    "Dr. Ivo Marchetti leads eight astronomers using the Silver Dome telescope. "
    "The primary mirror measures 6.4 meters and is cooled to minus 32 degrees Celsius. "
    "A crimson warning light marks the avalanche shelter beneath the east dome. "
    "The team records 240 clear-sky nights per year and stores plates in vault twelve."
)
OCEAN_CARDS = [
    {
        "question": "Which vessel supports Abyssal Station?",
        "answer": "Kelp Runner.",
    },
    {
        "question": "Who leads the research team at Abyssal Station?",
        "answer": "Dr. Mara Voss.",
    },
    {
        "question": "At what depth is Abyssal Station located?",
        "answer": "3,840 meters below the surface.",
    },
]
MOUNTAIN_CARDS = [
    {
        "question": "Which observatory operates on Mount Solenne?",
        "answer": "High Perch Observatory.",
    },
    {
        "question": "Who leads the astronomy team at High Perch?",
        "answer": "Dr. Ivo Marchetti.",
    },
    {
        "question": "Which telescope is used at High Perch Observatory?",
        "answer": "Silver Dome telescope.",
    },
]
OCEAN_QUIZ = [
    {
        "question": "How deep is Abyssal Station?",
        "options": [
            "3,840 meters below the surface",
            "1,200 meters below the surface",
            "2,500 meters below the surface",
            "47.2 meters below the surface",
        ],
        "answer": "3,840 meters below the surface",
        "explanation": (
            "Abyssal Station sits 3,840 meters below the surface beside the Cerulean Trench."
        ),
    },
    {
        "question": "Which vessel supports Abyssal Station?",
        "options": ["Kelp Runner", "Sea Lark", "Tide Rider", "Cerulean Trench"],
        "answer": "Kelp Runner",
        "explanation": "The Kelp Runner is the research vessel supporting Abyssal Station.",
    },
    {
        "question": "Which animal do researchers study at Abyssal Station?",
        "options": ["Glass squid", "Silver squid", "Blue whale", "Plankton crab"],
        "answer": "Glass squid",
        "explanation": "Researchers at Abyssal Station study glass squid in the Cerulean Trench.",
    },
]
MOUNTAIN_QUIZ = [
    {
        "question": "How high is High Perch Observatory?",
        "options": [
            "1,200 meters on Mount Solenne",
            "2,500 meters on Mount Solenne",
            "5,210 meters on Mount Solenne",
            "6,400 meters on Mount Solenne",
        ],
        "answer": "5,210 meters on Mount Solenne",
        "explanation": "High Perch Observatory operates at 5,210 meters on Mount Solenne.",
    },
    {
        "question": "Who leads the observatory team?",
        "options": ["Dr. Ivo Marchetti", "Dr. Lina Farrow", "Dr. Oren Vale", "Dr. Petra Noll"],
        "answer": "Dr. Ivo Marchetti",
        "explanation": "Dr. Ivo Marchetti leads eight astronomers at High Perch Observatory.",
    },
    {
        "question": "What is the diameter of the primary mirror?",
        "options": ["2.4 meters", "4.8 meters", "6.4 meters", "12 meters"],
        "answer": "6.4 meters",
        "explanation": "The primary mirror at High Perch measures 6.4 meters.",
    },
]
OCEAN_MARKERS = ("Kelp Runner", "Abyssal Station", "Mara Voss", "3,840")
MOUNTAIN_MARKERS = (
    "High Perch Observatory",
    "Mount Solenne",
    "Ivo Marchetti",
    "Silver Dome",
    "5,210",
)


def _upload(client: TestClient, tmp_path: Path, name: str, content: str) -> int:
    pdf = make_pdf(tmp_path, name, pages=[content])
    return int(upload_pdf(client, pdf)["id"])


def _generate(
    client: TestClient,
    llm: FakeLLM,
    endpoint: str,
    document_id: int,
    payload: list[dict[str, object]],
) -> tuple[dict[str, object], str]:
    llm.response_text = json.dumps(payload)
    response = client.post(
        f"/api/v1/study/{endpoint}",
        json={"document_id": document_id, "count": 3},
    )
    assert response.status_code == 200, response.text
    return dict(response.json()), llm.last_prompt


def _answers_by_question(questions: list[dict[str, object]]) -> list[str]:
    return [str(question["answer"]) for question in questions]


def _assert_only_markers(material: str, expected: tuple[str, ...], other: tuple[str, ...]) -> None:
    assert all(marker in material for marker in expected)
    assert all(marker not in material for marker in other)


def test_two_documents_keep_generation_prompts_and_saved_sets_isolated(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    ocean_id = _upload(rag_client, tmp_path, "ocean.pdf", OCEAN_TEXT)
    mountain_id = _upload(rag_client, tmp_path, "mountain.pdf", MOUNTAIN_TEXT)

    ocean_deck, ocean_deck_prompt = _generate(
        rag_client, llm, "flashcards", ocean_id, OCEAN_CARDS
    )
    _assert_only_markers(ocean_deck_prompt, OCEAN_MARKERS, MOUNTAIN_MARKERS)

    mountain_deck, mountain_deck_prompt = _generate(
        rag_client, llm, "flashcards", mountain_id, MOUNTAIN_CARDS
    )
    _assert_only_markers(mountain_deck_prompt, MOUNTAIN_MARKERS, OCEAN_MARKERS)

    ocean_quiz, ocean_quiz_prompt = _generate(rag_client, llm, "quiz", ocean_id, OCEAN_QUIZ)
    _assert_only_markers(ocean_quiz_prompt, OCEAN_MARKERS, MOUNTAIN_MARKERS)

    mountain_quiz, mountain_quiz_prompt = _generate(
        rag_client, llm, "quiz", mountain_id, MOUNTAIN_QUIZ
    )
    _assert_only_markers(mountain_quiz_prompt, MOUNTAIN_MARKERS, OCEAN_MARKERS)

    assert ocean_deck["source_document_id"] == ocean_id
    assert mountain_deck["source_document_id"] == mountain_id
    assert ocean_quiz["source_document_id"] == ocean_id
    assert mountain_quiz["source_document_id"] == mountain_id

    ocean_material = json.dumps(
        [ocean_deck["flashcards"], ocean_quiz["questions"]], ensure_ascii=False
    )
    mountain_material = json.dumps(
        [mountain_deck["flashcards"], mountain_quiz["questions"]], ensure_ascii=False
    )
    _assert_only_markers(ocean_material, OCEAN_MARKERS, MOUNTAIN_MARKERS)
    _assert_only_markers(mountain_material, MOUNTAIN_MARKERS, OCEAN_MARKERS)

    with SessionLocal() as session:
        for model, payload, document_id in (
            (FlashcardDeck, ocean_deck, ocean_id),
            (FlashcardDeck, mountain_deck, mountain_id),
            (Quiz, ocean_quiz, ocean_id),
            (Quiz, mountain_quiz, mountain_id),
        ):
            stored = session.get(model, int(payload["id"]))
            assert stored is not None
            assert stored.source_document_id == document_id
            chunk_ids = stored.get_source_chunk_ids()
            chunks = session.scalars(
                select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
            ).all()
            assert chunks
            assert {chunk.document_id for chunk in chunks} == {document_id}

        ocean_chunks = session.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == ocean_id)
        ).all()
        ocean_tokens = content_tokens(" ".join(chunk.text for chunk in ocean_chunks))
        for question in ocean_quiz["questions"]:
            material = (
                f"{question['question']} {question['options']} {question['explanation']}"
            )
            assert has_source_overlap(material, ocean_tokens)

    ocean_submission = rag_client.post(
        f"/api/v1/study/quizzes/{ocean_quiz['id']}/submit",
        json={"answers": _answers_by_question(OCEAN_QUIZ)},
    )
    mountain_submission = rag_client.post(
        f"/api/v1/study/quizzes/{mountain_quiz['id']}/submit",
        json={"answers": _answers_by_question(MOUNTAIN_QUIZ)},
    )
    assert ocean_submission.status_code == 200, ocean_submission.text
    assert mountain_submission.status_code == 200, mountain_submission.text
    assert ocean_submission.json()["score"] == 3
    assert mountain_submission.json()["score"] == 3


def test_missing_and_unindexed_documents_fail_without_generation(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path, db_session: Session
) -> None:
    missing = rag_client.post(
        "/api/v1/study/flashcards", json={"document_id": 999_999, "count": 3}
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Document not found."

    document = Document(
        filename="unindexed.pdf",
        original_filename="unindexed.pdf",
        stored_path=str(tmp_path / "unindexed.pdf"),
        status=DocumentStatus.READY.value,
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    for endpoint, expected_count in (("flashcards", 3), ("quiz", 3)):
        response = rag_client.post(
            f"/api/v1/study/{endpoint}",
            json={"document_id": document.id, "count": expected_count},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "No content available."

    assert llm.generate_calls == 0


def test_history_and_attempts_survive_database_reopen(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _upload(rag_client, tmp_path, "reopen.pdf", OCEAN_TEXT)

    deck, _ = _generate(rag_client, llm, "flashcards", document_id, OCEAN_CARDS)
    quiz, _ = _generate(rag_client, llm, "quiz", document_id, OCEAN_QUIZ)
    submitted = rag_client.post(
        f"/api/v1/study/quizzes/{quiz['id']}/submit",
        json={"answers": _answers_by_question(OCEAN_QUIZ)},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["score"] == 3

    conversation = rag_client.post(
        "/api/v1/conversations",
        json={"title": "Persistence check", "document_ids": [document_id]},
    )
    assert conversation.status_code == 201, conversation.text
    conversation_id = int(conversation.json()["id"])

    with SessionLocal() as session:
        stored_conversation = session.get(Conversation, conversation_id)
        assert stored_conversation is not None
        stored_conversation.messages.append(
            Message(role="user", content="Keep this message across a database reopen.")
        )
        session.commit()

    engine.dispose()

    reopened_deck = rag_client.get(f"/api/v1/study/flashcards/{deck['id']}")
    reopened_quiz = rag_client.get(f"/api/v1/study/quizzes/{quiz['id']}")
    reopened_conversation = rag_client.get(f"/api/v1/conversations/{conversation_id}")

    assert reopened_deck.status_code == 200, reopened_deck.text
    assert reopened_deck.json()["flashcards"] == OCEAN_CARDS
    assert reopened_quiz.status_code == 200, reopened_quiz.text
    reopened_quiz_payload = reopened_quiz.json()
    assert reopened_quiz_payload["status"] == "completed"
    assert reopened_quiz_payload["score"] == 3
    assert [
        question["selected_answer"] for question in reopened_quiz_payload["questions"]
    ] == _answers_by_question(OCEAN_QUIZ)
    assert reopened_conversation.status_code == 200, reopened_conversation.text
    assert reopened_conversation.json()["messages"][0]["content"] == (
        "Keep this message across a database reopen."
    )

    duplicate = rag_client.post(
        f"/api/v1/study/quizzes/{quiz['id']}/submit",
        json={"answers": _answers_by_question(OCEAN_QUIZ)},
    )
    assert duplicate.status_code == 409
