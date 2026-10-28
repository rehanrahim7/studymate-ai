"""Health-check endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession, LLMServiceDep
from app.core.config import get_settings
from app.schemas.document import HealthResponse

router = APIRouter(tags=["health"])


def _database_status(session: DbSession) -> str:
    try:
        session.execute(text("SELECT 1"))
        return "connected"
    except SQLAlchemyError:  # pragma: no cover - depends on runtime state
        return "unavailable"


@router.get("/health", response_model=HealthResponse, summary="Service health")
def health(session: DbSession, llm: LLMServiceDep) -> HealthResponse:
    """Report the status of the API, the database and the LLM backend."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        database=_database_status(session),
        llm="ready" if llm.is_available() else "unreachable",
    )
