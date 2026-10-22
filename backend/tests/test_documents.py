"""Document upload, listing and deletion tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pymupdf
from fastapi.testclient import TestClient


def test_upload_extracts_text_and_creates_chunks(client: TestClient, sample_pdf: Path) -> None:
    with sample_pdf.open("rb") as handle:
        response = client.post(
            "/api/v1/documents",
            files={"file": (sample_pdf.name, handle, "application/pdf")},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "sample.pdf"
    assert body["status"] == "ready"
    assert body["page_count"] == 1
    assert body["character_count"] > 0
    assert body["chunk_count"] >= 1
    assert body["error_message"] is None


def test_documents_are_listed_after_upload(client: TestClient, sample_pdf: Path) -> None:
    with sample_pdf.open("rb") as handle:
        client.post(
            "/api/v1/documents",
            files={"file": (sample_pdf.name, handle, "application/pdf")},
        )

    response = client.get("/api/v1/documents")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == len(body["documents"])
    assert any(item["original_filename"] == "sample.pdf" for item in body["documents"])


def test_non_pdf_upload_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )

    assert response.status_code == 415


def test_empty_upload_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400


def test_pdf_without_text_is_reported(client: TestClient, tmp_path: Path) -> None:
    path = tmp_path / "blank.pdf"
    document = pymupdf.open()
    document.new_page()
    document.save(path)
    document.close()

    with path.open("rb") as handle:
        response = client.post(
            "/api/v1/documents",
            files={"file": (path.name, handle, "application/pdf")},
        )

    assert response.status_code == 422
    assert "No selectable text" in response.json()["detail"]


def test_delete_removes_the_document(client: TestClient, sample_pdf: Path) -> None:
    with sample_pdf.open("rb") as handle:
        created = client.post(
            "/api/v1/documents",
            files={"file": (sample_pdf.name, handle, "application/pdf")},
        ).json()

    response = client.delete(f"/api/v1/documents/{created['id']}")
    assert response.status_code == 204

    assert client.get(f"/api/v1/documents/{created['id']}").status_code == 404


def test_missing_document_returns_404(client: TestClient) -> None:
    assert client.get("/api/v1/documents/999999").status_code == 404
    assert client.delete("/api/v1/documents/999999").status_code == 404


def test_timestamps_are_serialised_as_utc(client: TestClient, sample_pdf: Path) -> None:
    """SQLite drops tz info — the API must still emit an explicit UTC offset."""
    with sample_pdf.open("rb") as handle:
        created = client.post(
            "/api/v1/documents",
            files={"file": (sample_pdf.name, handle, "application/pdf")},
        ).json()

    for key in ("created_at", "updated_at"):
        parsed = datetime.fromisoformat(created[key].replace("Z", "+00:00"))
        assert parsed.tzinfo is not None, f"{key} is missing a timezone"
        assert parsed.utcoffset() == timedelta(0), f"{key} is not UTC"
