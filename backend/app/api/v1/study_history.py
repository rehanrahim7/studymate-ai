"""Saved flashcard decks and quizzes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession
from app.models.study import FlashcardDeck, Quiz
from app.schemas.study import (
    FlashcardDeckDetail,
    FlashcardDeckListResponse,
    QuizDetail,
    QuizListResponse,
    QuizSubmitRequest,
)
from app.services.study_history import deck_detail, deck_summary, quiz_detail, quiz_summary

router = APIRouter(prefix="/study", tags=["study"])

HTTP_UNPROCESSABLE_CONTENT = 422


@router.get("/flashcards", response_model=FlashcardDeckListResponse)
def list_flashcard_decks(
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> FlashcardDeckListResponse:
    total = session.scalar(select(func.count()).select_from(FlashcardDeck)) or 0
    decks = session.scalars(
        select(FlashcardDeck)
        .order_by(FlashcardDeck.created_at.desc(), FlashcardDeck.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return FlashcardDeckListResponse(
        decks=[deck_summary(session, deck) for deck in decks],
        total=total,
    )


@router.get("/flashcards/{deck_id}", response_model=FlashcardDeckDetail)
def get_flashcard_deck(deck_id: int, session: DbSession) -> FlashcardDeckDetail:
    deck = session.get(FlashcardDeck, deck_id)
    if deck is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Flashcard deck not found.")
    return deck_detail(session, deck)


@router.delete("/flashcards/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flashcard_deck(deck_id: int, session: DbSession) -> None:
    deck = session.get(FlashcardDeck, deck_id)
    if deck is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Flashcard deck not found.")
    session.delete(deck)
    session.commit()


@router.get("/quizzes", response_model=QuizListResponse)
def list_quizzes(
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> QuizListResponse:
    total = session.scalar(select(func.count()).select_from(Quiz)) or 0
    quizzes = session.scalars(
        select(Quiz)
        .order_by(Quiz.created_at.desc(), Quiz.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return QuizListResponse(
        quizzes=[quiz_summary(session, quiz) for quiz in quizzes],
        total=total,
    )


@router.get("/quizzes/{quiz_id}", response_model=QuizDetail)
def get_quiz(quiz_id: int, session: DbSession) -> QuizDetail:
    quiz = session.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found.")
    return quiz_detail(session, quiz)


@router.post("/quizzes/{quiz_id}/submit", response_model=QuizDetail)
def submit_quiz(
    quiz_id: int, payload: QuizSubmitRequest, session: DbSession
) -> QuizDetail:
    quiz = session.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found.")
    if quiz.is_completed:
        raise HTTPException(status.HTTP_409_CONFLICT, "This quiz has already been submitted.")

    questions = quiz.get_questions()
    if len(payload.answers) != len(questions):
        raise HTTPException(
            HTTP_UNPROCESSABLE_CONTENT,
            f"Expected {len(questions)} answers, received {len(payload.answers)}.",
        )

    score = 0
    for index, item in enumerate(questions):
        options = item.get("options")
        correct_answer = item.get("answer")
        if (
            not isinstance(options, list)
            or not all(isinstance(option, str) for option in options)
            or not isinstance(correct_answer, str)
        ):
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "This quiz is corrupted and cannot be scored.",
            )
        selected = payload.answers[index]
        if selected not in options:
            raise HTTPException(
                HTTP_UNPROCESSABLE_CONTENT,
                f"Answer {index + 1} must exactly match one of the quiz options.",
            )
        if selected == correct_answer:
            score += 1

    quiz.set_submitted_answers(payload.answers)
    quiz.score = score
    quiz.completed_at = datetime.now(UTC)
    try:
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "The quiz could not be submitted. Please try again.",
        ) from exc
    session.refresh(quiz)
    return quiz_detail(session, quiz)


@router.delete("/quizzes/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quiz(quiz_id: int, session: DbSession) -> None:
    quiz = session.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found.")
    session.delete(quiz)
    session.commit()
