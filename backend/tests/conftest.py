"""Shared pytest fixtures.

Environment variables are set before the application is imported so that the
test run uses a throw-away SQLite database and upload directory.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

_TMP_DIR = Path(tempfile.mkdtemp(prefix="studymate-tests-"))

os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR / 'test.db'}"
os.environ["STORAGE_DIR"] = str(_TMP_DIR)
os.environ["UPLOAD_DIR"] = str(_TMP_DIR / "uploads")
os.environ["INDEX_DIR"] = str(_TMP_DIR / "indexes")
os.environ["ENVIRONMENT"] = "test"

from sqlalchemy.orm import Session  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services.llm.factory import get_llm_service  # noqa: E402
from app.services.rag.embeddings import get_embedding_service  # noqa: E402
from tests.support import FakeEmbeddingService, FakeLLM  # noqa: E402


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def embedder() -> FakeEmbeddingService:
    return FakeEmbeddingService()


@pytest.fixture
def llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def rag_client(
    client: TestClient,
    embedder: FakeEmbeddingService,
    llm: FakeLLM,
) -> Iterator[TestClient]:
    """API client wired to deterministic embedding and LLM doubles."""
    app.dependency_overrides[get_llm_service] = lambda: llm
    app.dependency_overrides[get_embedding_service] = lambda: embedder
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Build a small, real PDF that contains selectable text."""
    path = tmp_path / "sample.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Neural networks learn representations from data.")
    page.insert_text((72, 96), "Backpropagation adjusts the weights of each layer.")
    document.save(path)
    document.close()
    return path
