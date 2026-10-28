"""Document upload and management endpoints."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select, update

from app.api.deps import DbSession
from app.core.config import get_settings
from app.models.document import Document, DocumentChunk, DocumentPage, DocumentStatus
from app.models.study import FlashcardDeck, Quiz
from app.schemas.document import DocumentDetail, DocumentListResponse, DocumentSummary
from app.services.pdf.extractor import PDFExtractionError, extract_pdf_text
from app.services.rag.chunking import chunk_pages
from app.services.rag.indexer import delete_document_index

router = APIRouter(prefix="/documents", tags=["documents"])

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")

# Numeric aliases: Starlette renamed these constants in newer releases.
HTTP_CONTENT_TOO_LARGE = 413
HTTP_UNPROCESSABLE_CONTENT = 422


def _sanitize_filename(name: str) -> str:
    """Reduce a user-supplied filename to a safe basename."""
    base = Path(name).name
    cleaned = _SAFE_NAME.sub("_", base).strip("._")
    return cleaned or "document.pdf"


def _unique_stored_name(original_name: str) -> str:
    stem = Path(_sanitize_filename(original_name)).stem or "document"
    suffix = Path(original_name).suffix.lower() or ".pdf"
    return f"{uuid.uuid4().hex[:12]}_{stem}{suffix}"


@router.get("", response_model=DocumentListResponse, summary="List documents")
def list_documents(session: DbSession) -> DocumentListResponse:
    """Return every uploaded document, newest first."""
    documents = session.scalars(
        select(Document).order_by(Document.created_at.desc())
    ).all()
    return DocumentListResponse(
        documents=[DocumentSummary.model_validate(doc) for doc in documents],
        total=len(documents),
    )


@router.post(
    "",
    response_model=DocumentDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF",
)
async def upload_document(
    session: DbSession, file: Annotated[UploadFile, File(...)]
) -> DocumentDetail:
    """Accept a PDF, extract its text and index it for retrieval.

    Text is extracted with PyMuPDF; pages and chunks are persisted so the
    document can be cited with page numbers later.
    """
    settings = get_settings()

    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A filename is required.")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF files are supported."
        )

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    payload = await file.read()
    if not payload:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded file is empty.")
    if len(payload) > max_bytes:
        raise HTTPException(
            HTTP_CONTENT_TOO_LARGE,
            f"File is larger than the {settings.max_upload_size_mb} MB limit.",
        )

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = _unique_stored_name(file.filename)
    stored_path = settings.upload_dir / stored_name
    stored_path.write_bytes(payload)

    document = Document(
        filename=stored_name,
        original_filename=Path(file.filename).name,
        stored_path=str(stored_path),
        content_type=file.content_type or "application/pdf",
        file_size=len(payload),
        status=DocumentStatus.PROCESSING.value,
    )
    session.add(document)
    session.flush()

    try:
        extracted = extract_pdf_text(stored_path)
    except PDFExtractionError as exc:
        document.status = DocumentStatus.FAILED.value
        document.error_message = str(exc)
        stored_path.unlink(missing_ok=True)
        session.commit()
        raise HTTPException(HTTP_UNPROCESSABLE_CONTENT, str(exc)) from exc

    for page in extracted.pages:
        session.add(
            DocumentPage(
                document_id=document.id,
                page_number=page.page_number,
                text=page.text,
                character_count=page.character_count,
            )
        )

    chunks = chunk_pages(
        extracted.pages,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    for chunk in chunks:
        session.add(
            DocumentChunk(
                document_id=document.id,
                page_number=chunk.page_number,
                ordinal=chunk.ordinal,
                text=chunk.text,
                token_estimate=chunk.token_estimate,
            )
        )

    document.page_count = extracted.page_count
    document.character_count = extracted.character_count
    document.chunk_count = len(chunks)
    document.status = DocumentStatus.READY.value
    session.commit()
    session.refresh(document)

    return DocumentDetail.model_validate(document)


@router.get("/{document_id}", response_model=DocumentDetail, summary="Get a document")
def get_document(document_id: int, session: DbSession) -> DocumentDetail:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return DocumentDetail.model_validate(document)


@router.delete(
    "/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a document"
)
def delete_document(document_id: int, session: DbSession) -> None:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")

    Path(document.stored_path).unlink(missing_ok=True)
    session.execute(
        update(FlashcardDeck)
        .where(FlashcardDeck.source_document_id == document_id)
        .values(source_document_id=None)
    )
    session.execute(
        update(Quiz).where(Quiz.source_document_id == document_id).values(source_document_id=None)
    )
    session.delete(document)
    session.commit()
    delete_document_index(document_id, get_settings())
