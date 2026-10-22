"""FastAPI application entrypoint for StudyMate AI."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Prepare the database and storage directories on startup."""
    init_db()
    logger.info("%s ready (environment=%s)", settings.app_name, settings.environment)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "RAG-powered study assistant for academic PDFs. "
        "Upload a document, then chat with it, and generate summaries, "
        "flashcards and quizzes grounded in the source material."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", tags=["meta"], summary="API metadata")
def root() -> dict[str, str]:
    """Point clients at the useful URLs."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
        "api": settings.api_prefix,
    }
