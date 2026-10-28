"""Regression tests for study-tool generation robustness.

The LLM is always a deterministic double; no live Ollama server is required.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import study as study_api
from app.services.llm.base import LLMServiceError
from tests.support import FakeLLM, make_pdf, upload_pdf

SOURCE_TEXT = (
    "Photosynthesis converts light energy into chemical energy inside chloroplasts. "
    "The light reactions produce ATP and NADPH for the next stage. "
    "The Calvin cycle fixes carbon dioxide into glucose using ATP and NADPH. "
    "Chlorophyll absorbs red and blue light most strongly. "
    "Oxygen is released as a byproduct when water molecules are split."
)

NUMERIC_TEXT = (
    "Fractions and percentages express the same values in different forms. "
    "One half equals 0.5 or 50 percent. One quarter equals 0.25 or 25 percent. "
    "Three quarters equal 0.75 or 75 percent. One whole equals 1 or 100 percent. "
    "A decimal point separates whole numbers from fractional parts. "
    "Percent means per hundred, so 25 percent is twenty five out of one hundred."
)

VALID_CARDS = [
    {
        "question": "What does photosynthesis convert light energy into?",
        "answer": "Chemical energy inside chloroplasts.",
    },
    {
        "question": "Which molecules do the light reactions produce for the next stage?",
        "answer": "ATP and NADPH.",
    },
    {
        "question": "What does the Calvin cycle fix into glucose?",
        "answer": "Carbon dioxide.",
    },
]

VALID_QUIZ = [
    {
        "question": "What does photosynthesis convert light energy into?",
        "options": ["Chemical energy", "Sound energy", "Nuclear energy", "Mechanical energy"],
        "answer": "Chemical energy",
        "explanation": "Photosynthesis stores light energy as chemical energy.",
    },
    {
        "question": "Which organelle contains chlorophyll and carries out photosynthesis?",
        "options": ["Chloroplast", "Mitochondrion", "Nucleus", "Ribosome"],
        "answer": "Chloroplast",
        "explanation": "Chlorophyll inside chloroplasts absorbs light.",
    },
    {
        "question": "What gas does the Calvin cycle fix into glucose?",
        "options": ["Carbon dioxide", "Oxygen", "Nitrogen", "Hydrogen"],
        "answer": "Carbon dioxide",
        "explanation": "The Calvin cycle uses carbon dioxide to build glucose.",
    },
]

NUMERIC_QUIZ = [
    {
        "question": "Which numeric value represents one half?",
        "options": ["0.25", "0.50", "75%", "1"],
        "answer": "0.50",
        "explanation": "One half equals 0.50.",
    },
    {
        "question": "Which percentage represents one quarter?",
        "options": ["10%", "25%", "50%", "75%"],
        "answer": "25%",
        "explanation": "One quarter equals 25 percent.",
    },
    {
        "question": "Which fraction represents three quarters?",
        "options": ["1/4", "1/2", "3/4", "1"],
        "answer": "3/4",
        "explanation": "Three quarters equal 3/4.",
    },
]


def _document(
    client: TestClient,
    tmp_path: Path,
    name: str,
    *,
    content: str = SOURCE_TEXT,
) -> int:
    pdf = make_pdf(tmp_path, name, pages=[content])
    return int(upload_pdf(client, pdf)["id"])


def _answers_by_question(quiz: list[dict[str, object]]) -> dict[str, str]:
    return {str(item["question"]): str(item["answer"]) for item in quiz}


def _submit(
    client: TestClient,
    quiz_id: int,
    questions: list[dict[str, object]],
    answers_by_question: dict[str, str],
) -> object:
    answers = [answers_by_question[str(question["question"])] for question in questions]
    return client.post(
        f"/api/v1/study/quizzes/{quiz_id}/submit",
        json={"answers": answers},
    )


# --- Summary ----------------------------------------------------------------


def test_summary_returns_grounded_markdown(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(
        rag_client,
        tmp_path,
        "summary.pdf",
        content="Neural networks learn representations from data.",
    )
    summary = "## Overview\n\nNeural networks learn representations from data."
    llm.response_text = summary

    response = rag_client.post("/api/v1/study/summary", json={"document_id": document_id})

    assert response.status_code == 200, response.text
    assert response.json() == {"document_id": document_id, "summary": summary}
    assert llm.generate_calls == 1
    assert "Neural networks learn representations" in llm.last_prompt
    assert llm.last_system is not None and "summary" in llm.last_system.lower()


def test_summary_missing_document_returns_404(rag_client: TestClient) -> None:
    response = rag_client.post("/api/v1/study/summary", json={"document_id": 999_999})

    assert response.status_code == 404


def test_summary_empty_output_returns_safe_502(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "summary-empty.pdf")
    llm.response_text = "   "

    response = rag_client.post("/api/v1/study/summary", json={"document_id": document_id})

    assert response.status_code == 502
    assert "invalid response" in response.json()["detail"].lower()


# --- Flashcard success paths -------------------------------------------------


def test_flashcards_valid_json(rag_client: TestClient, llm: FakeLLM, tmp_path: Path) -> None:
    document_id = _document(rag_client, tmp_path, "cards.pdf")
    llm.response_text = json.dumps(VALID_CARDS)

    response = rag_client.post(
        "/api/v1/study/flashcards", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["flashcards"] == VALID_CARDS
    assert payload["card_count"] == 3
    assert payload["source_document_id"] == document_id
    assert payload["source_available"] is True
    assert payload["source_changed"] is False
    assert llm.generate_calls == 1
    assert "exactly 3" in (llm.last_system or "")


def test_flashcards_markdown_fences(rag_client: TestClient, llm: FakeLLM, tmp_path: Path) -> None:
    document_id = _document(rag_client, tmp_path, "cards-fenced.pdf")
    llm.response_text = "```json\n" + json.dumps(VALID_CARDS) + "\n```"

    response = rag_client.post(
        "/api/v1/study/flashcards", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 200
    assert response.json()["flashcards"][0] == VALID_CARDS[0]


def test_flashcards_accepts_object_wrapper(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "cards-wrapped.pdf")
    llm.response_text = json.dumps({"flashcards": VALID_CARDS})

    response = rag_client.post(
        "/api/v1/study/flashcards", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 200
    assert len(response.json()["flashcards"]) == 3


def test_flashcards_repair_retry_succeeds(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "cards-repair.pdf")
    llm.response_texts = [json.dumps(VALID_CARDS[:1]), json.dumps(VALID_CARDS)]

    response = rag_client.post(
        "/api/v1/study/flashcards", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 200, response.text
    assert llm.generate_calls == 2
    assert "previous reply was not usable" in llm.last_prompt
    assert "exactly the requested number" in llm.last_prompt


# --- Flashcard failure paths -------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        "not json at all",
        "",
        '[{"question": "Q", "answer":',
        json.dumps([{"question": "Q"}]),
        json.dumps([{"question": 123, "answer": ["nope"]}]),
        json.dumps([]),
    ],
)
def test_flashcards_invalid_payload_fails_after_retry(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path, payload: str
) -> None:
    document_id = _document(rag_client, tmp_path, "cards-invalid.pdf")
    llm.response_texts = [payload, payload]

    response = rag_client.post(
        "/api/v1/study/flashcards", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 502
    assert llm.generate_calls == 2
    detail = response.json()["detail"]
    assert "grounded" in detail.lower() or "usable" in detail.lower()
    assert "traceback" not in detail.lower()
    assert "not json" not in detail.lower()


def test_flashcards_reject_too_few_items(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "cards-too-few.pdf")
    llm.response_texts = [json.dumps(VALID_CARDS[:1]), json.dumps(VALID_CARDS[:1])]

    response = rag_client.post(
        "/api/v1/study/flashcards", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 502
    assert llm.generate_calls == 2


def test_flashcards_reject_duplicates(rag_client: TestClient, llm: FakeLLM, tmp_path: Path) -> None:
    document_id = _document(rag_client, tmp_path, "cards-duplicates.pdf")
    duplicate_cards = [VALID_CARDS[0], VALID_CARDS[0], VALID_CARDS[1]]
    llm.response_texts = [json.dumps(duplicate_cards), json.dumps(duplicate_cards)]

    response = rag_client.post(
        "/api/v1/study/flashcards", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 502
    assert llm.generate_calls == 2


def test_flashcards_reject_ungrounded_content(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "cards-ungrounded.pdf")
    cards = [
        {
            "question": "What is the capital of France?",
            "answer": "Paris is the capital of France.",
        },
        {
            "question": "Who wrote Hamlet?",
            "answer": "William Shakespeare wrote Hamlet.",
        },
        {
            "question": "What is the largest ocean?",
            "answer": "The Pacific is the largest ocean.",
        },
    ]
    llm.response_texts = [json.dumps(cards), json.dumps(cards)]

    response = rag_client.post(
        "/api/v1/study/flashcards", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 502
    assert llm.generate_calls == 2


def test_flashcards_reject_document_with_too_little_text(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "cards-tiny.pdf", content="Tiny.")

    response = rag_client.post(
        "/api/v1/study/flashcards", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 400
    assert "not contain enough usable text" in response.json()["detail"]
    assert llm.generate_calls == 0


# --- Quiz success and validation --------------------------------------------


def test_quiz_valid_json_hides_answer_key(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "quiz.pdf")
    llm.response_text = json.dumps(VALID_QUIZ)

    response = rag_client.post("/api/v1/study/quiz", json={"document_id": document_id, "count": 3})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["question_count"] == 3
    assert payload["status"] == "open"
    for question in payload["questions"]:
        assert len(question["options"]) == 4
        assert question["correct_answer"] is None
        assert question["explanation"] is None
        assert question["selected_answer"] is None
        assert question["is_correct"] is None
        assert "answer" not in question


def test_quiz_repairs_explanation_that_does_not_explain_answer(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "quiz-mismatched-explanation.pdf")
    mismatched = [
        {
            **VALID_QUIZ[0],
            "explanation": "The light reactions produce ATP and NADPH.",
        },
        *VALID_QUIZ[1:],
    ]
    llm.response_texts = [json.dumps(mismatched), json.dumps(VALID_QUIZ)]

    response = rag_client.post(
        "/api/v1/study/quiz", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 200, response.text
    assert llm.generate_calls == 2
    assert "own correct answer" in llm.last_prompt


def test_quiz_repairs_unsupported_explanation(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "quiz-unsupported-explanation.pdf")
    unsupported = [
        {
            **VALID_QUIZ[0],
            "explanation": (
                "Mitochondria produce loud sound energy during cellular respiration."
            ),
        },
        *VALID_QUIZ[1:],
    ]
    llm.response_texts = [json.dumps(unsupported), json.dumps(VALID_QUIZ)]

    response = rag_client.post(
        "/api/v1/study/quiz", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 200, response.text
    assert llm.generate_calls == 2


def test_quiz_rejects_explanations_that_still_do_not_match_after_repair(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "quiz-bad-explanation.pdf")
    mismatched = [
        {
            **VALID_QUIZ[0],
            "explanation": "The light reactions produce ATP and NADPH.",
        },
        *VALID_QUIZ[1:],
    ]
    llm.response_texts = [json.dumps(mismatched), json.dumps(mismatched)]

    response = rag_client.post(
        "/api/v1/study/quiz", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 502
    assert llm.generate_calls == 2
    detail = response.json()["detail"].lower()
    assert "explanations" in detail
    assert "did not clearly explain" in detail


def test_quiz_submission_is_scored_on_server(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "quiz-submit.pdf")
    llm.response_text = json.dumps(VALID_QUIZ)

    generated = rag_client.post(
        "/api/v1/study/quiz", json={"document_id": document_id, "count": 3}
    )
    assert generated.status_code == 200, generated.text
    quiz = generated.json()
    questions = quiz["questions"]

    submitted = _submit(
        rag_client,
        quiz["id"],
        questions,
        _answers_by_question(VALID_QUIZ),
    )

    assert submitted.status_code == 200, submitted.text
    result = submitted.json()
    assert result["status"] == "completed"
    assert result["score"] == 3
    assert result["completed_at"] is not None
    for question in result["questions"]:
        assert question["correct_answer"] in question["options"]
        assert question["selected_answer"] == question["correct_answer"]
        assert question["is_correct"] is True
        assert question["explanation"]

    duplicate = _submit(
        rag_client,
        quiz["id"],
        questions,
        _answers_by_question(VALID_QUIZ),
    )
    assert duplicate.status_code == 409


def test_quiz_accepts_distinct_numeric_options(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "quiz-numeric.pdf", content=NUMERIC_TEXT)
    llm.response_text = json.dumps(NUMERIC_QUIZ)

    response = rag_client.post(
        "/api/v1/study/quiz", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 200, response.text
    questions = response.json()["questions"]
    assert len(questions) == 3
    assert {len(question["options"]) for question in questions} == {4}


def test_quiz_shuffle_preserves_resolved_answer(
    rag_client: TestClient,
    llm: FakeLLM,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = _document(rag_client, tmp_path, "quiz-shuffle.pdf")
    llm.response_text = json.dumps(VALID_QUIZ)
    monkeypatch.setattr(study_api.random, "shuffle", lambda options: options.reverse())

    generated = rag_client.post(
        "/api/v1/study/quiz", json={"document_id": document_id, "count": 3}
    )

    assert generated.status_code == 200, generated.text
    payload = generated.json()
    for index, question in enumerate(payload["questions"]):
        assert question["options"] == list(reversed(VALID_QUIZ[index]["options"]))

    submitted = _submit(
        rag_client,
        payload["id"],
        payload["questions"],
        _answers_by_question(VALID_QUIZ),
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["score"] == 3


def test_quiz_repairs_equivalent_options(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(
        rag_client, tmp_path, "quiz-repair-equivalent.pdf", content=NUMERIC_TEXT
    )
    ambiguous = [
        {
            "question": "Which value represents one half?",
            "options": ["0.5", "1/2", "0.25", "0.75"],
            "answer": "0.5",
            "explanation": "One half equals 0.5.",
        },
        NUMERIC_QUIZ[1],
        NUMERIC_QUIZ[2],
    ]
    llm.response_texts = [json.dumps(ambiguous), json.dumps(NUMERIC_QUIZ)]

    response = rag_client.post(
        "/api/v1/study/quiz", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 200, response.text
    assert llm.generate_calls == 2
    assert "previous reply was not usable" in llm.last_prompt


@pytest.mark.parametrize(
    "options",
    [
        ["Paris", " paris ", "London", "Rome"],
        ["0.5", ".5", "2", "3"],
        ["0.5", "50%", "2", "3"],
        ["1/2", "0.5", "2", "3"],
        ["1,000", "1000", "2", "3"],
        ["1e3", "1000", "2", "3"],
        ["2", "2.0", "3", "4"],
    ],
)
def test_quiz_rejects_equivalent_options(
    rag_client: TestClient,
    llm: FakeLLM,
    tmp_path: Path,
    options: list[str],
) -> None:
    document_id = _document(rag_client, tmp_path, "quiz-equivalent.pdf", content=NUMERIC_TEXT)
    question = {
        "question": "Which numeric value is correct?",
        "options": options,
        "answer": options[0],
        "explanation": "The first numeric value is correct.",
    }
    llm.response_texts = [json.dumps([question]), json.dumps([question])]

    response = rag_client.post(
        "/api/v1/study/quiz", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 502
    assert llm.generate_calls == 2
    assert "duplicates or equivalent" in response.json()["detail"].lower()


def test_quiz_accepts_answer_index(rag_client: TestClient, llm: FakeLLM, tmp_path: Path) -> None:
    document_id = _document(rag_client, tmp_path, "quiz-index.pdf")
    questions = [
        {
            "question": item["question"],
            "options": item["options"],
            "answer_index": 0,
            "explanation": item["explanation"],
        }
        for item in VALID_QUIZ
    ]
    llm.response_text = json.dumps(questions)

    generated = rag_client.post(
        "/api/v1/study/quiz", json={"document_id": document_id, "count": 3}
    )

    assert generated.status_code == 200, generated.text
    payload = generated.json()
    submitted = _submit(
        rag_client,
        payload["id"],
        payload["questions"],
        _answers_by_question(VALID_QUIZ),
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["score"] == 3


@pytest.mark.parametrize(
    "question",
    [
        {
            "question": "Q",
            "options": ["A", "B", "C", "D"],
            "answer": "Z",
            "explanation": "Missing answer.",
        },
        {
            "question": "Q",
            "options": ["A", "B", "C"],
            "answer": "A",
            "explanation": "Only three options.",
        },
        {
            "question": "Q",
            "options": ["A", "A", "C", "D"],
            "answer": "A",
            "explanation": "Duplicate options.",
        },
        {
            "question": "Q",
            "options": ["A", "B", "C", "D"],
            "answer": "A",
        },
        {
            "question": "",
            "options": ["A", "B", "C", "D"],
            "answer": "A",
            "explanation": "Empty question.",
        },
    ],
)
def test_quiz_rejects_invalid_questions(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path, question: dict[str, object]
) -> None:
    document_id = _document(rag_client, tmp_path, "quiz-invalid.pdf")
    llm.response_texts = [json.dumps([question]), json.dumps([question])]

    response = rag_client.post(
        "/api/v1/study/quiz", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 502
    assert llm.generate_calls == 2


def test_quiz_rejects_duplicate_questions(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "quiz-duplicates.pdf")
    duplicate_questions = [VALID_QUIZ[0], VALID_QUIZ[0], VALID_QUIZ[1]]
    llm.response_texts = [json.dumps(duplicate_questions), json.dumps(duplicate_questions)]

    response = rag_client.post(
        "/api/v1/study/quiz", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 502
    assert llm.generate_calls == 2


def test_quiz_rejects_ungrounded_questions(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "quiz-ungrounded.pdf")
    questions = [
        {
            "question": "What is the capital of France?",
            "options": ["Paris", "London", "Rome", "Berlin"],
            "answer": "Paris",
            "explanation": "Paris is the capital of France.",
        },
        {
            "question": "Who wrote Hamlet?",
            "options": ["Shakespeare", "Tolstoy", "Homer", "Dickens"],
            "answer": "Shakespeare",
            "explanation": "William Shakespeare wrote Hamlet.",
        },
        {
            "question": "What is the largest ocean?",
            "options": ["Pacific", "Atlantic", "Indian", "Arctic"],
            "answer": "Pacific",
            "explanation": "The Pacific is the largest ocean.",
        },
    ]
    llm.response_texts = [json.dumps(questions), json.dumps(questions)]

    response = rag_client.post(
        "/api/v1/study/quiz", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 502
    assert llm.generate_calls == 2


def test_quiz_rejects_too_few_questions(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "quiz-too-few.pdf")
    llm.response_texts = [json.dumps(VALID_QUIZ[:1]), json.dumps(VALID_QUIZ[:1])]

    response = rag_client.post(
        "/api/v1/study/quiz", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 502
    assert llm.generate_calls == 2


# --- Transport failures ------------------------------------------------------


def test_llm_unavailable_returns_503(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "cards-offline.pdf")
    llm.available = False

    response = rag_client.post(
        "/api/v1/study/flashcards", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()
    assert llm.generate_calls == 0


def test_llm_timeout_is_not_retried(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "cards-timeout.pdf")
    llm.errors = [LLMServiceError("Could not reach Ollama at http://127.0.0.1:11434: timed out")]

    response = rag_client.post(
        "/api/v1/study/flashcards", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 502
    assert "did not respond in time" in response.json()["detail"].lower()
    assert llm.generate_calls == 1
    assert "127.0.0.1" not in response.json()["detail"]


def test_llm_error_message_is_not_leaked(
    rag_client: TestClient, llm: FakeLLM, tmp_path: Path
) -> None:
    document_id = _document(rag_client, tmp_path, "cards-error.pdf")
    llm.errors = [LLMServiceError("secret internal failure from provider")]

    response = rag_client.post(
        "/api/v1/study/flashcards", json={"document_id": document_id, "count": 3}
    )

    assert response.status_code == 502
    assert "secret internal failure" not in response.json()["detail"]
    assert llm.generate_calls == 1
