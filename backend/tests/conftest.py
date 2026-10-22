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
os.environ["ENVIRONMENT"] = "test"

from app.main import app  # noqa: E402  (import must follow the env setup)


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


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
