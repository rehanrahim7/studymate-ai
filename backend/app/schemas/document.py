"""Pydantic schemas exposed by the API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer


def _to_utc(value: datetime) -> datetime:
    """Treat naive timestamps as UTC.

    SQLite does not preserve timezone information, so datetimes read back from
    the database are naive. Re-attaching UTC keeps clients from misreading them
    as local time.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


UtcDatetime = Annotated[
    datetime,
    PlainSerializer(_to_utc, return_type=datetime, when_used="json"),
]


class DocumentSummary(BaseModel):
    """Lightweight document representation used in listings."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    original_filename: str
    file_size: int
    status: str
    page_count: int
    character_count: int
    chunk_count: int
    created_at: UtcDatetime


class DocumentDetail(DocumentSummary):
    """Full document representation, including the failure reason if any."""

    error_message: str | None = None
    updated_at: UtcDatetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]
    total: int


class HealthResponse(BaseModel):
    """Payload of `GET /api/v1/health`."""

    status: str = Field(examples=["ok"])
    app: str
    version: str
    environment: str
    database: str = Field(description="'connected' or 'unavailable'")
    llm: str = Field(description="LLM backend status: 'ready', 'unreachable' or 'not_configured'")
