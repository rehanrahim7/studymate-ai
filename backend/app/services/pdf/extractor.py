"""PDF text extraction built on PyMuPDF.

Only text that actually exists in the file is returned — nothing is generated
or inferred. Scanned/image-only PDFs legitimately yield empty pages, which the
API surfaces as a processing error rather than inventing content.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pymupdf

logger = logging.getLogger(__name__)


class PDFExtractionError(RuntimeError):
    """Raised when a PDF cannot be opened or contains no extractable text."""


@dataclass(slots=True)
class ExtractedPage:
    """Text of a single PDF page (1-indexed page numbers)."""

    page_number: int
    text: str
    character_count: int


@dataclass(slots=True)
class ExtractedDocument:
    """Result of extracting a whole PDF."""

    pages: list[ExtractedPage]

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def character_count(self) -> int:
        return sum(page.character_count for page in self.pages)

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages if page.text)


def _normalise(text: str) -> str:
    """Collapse runaway whitespace while keeping paragraph breaks."""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    collapsed: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip():
            blank_run = 0
            collapsed.append(line)
        else:
            blank_run += 1
            if blank_run <= 2:  # keep at most one blank line between paragraphs
                collapsed.append("")
    return "\n".join(collapsed).strip()


def extract_pdf_text(path: Path) -> ExtractedDocument:
    """Extract per-page text from the PDF at `path`.

    Raises:
        PDFExtractionError: if the file is not a readable PDF or has no text.
    """
    if not path.exists():
        raise PDFExtractionError(f"File not found: {path}")

    try:
        document = pymupdf.open(path)  # type: ignore[no-untyped-call]
    except Exception as exc:
        # pragma: no cover - depends on malformed input
        raise PDFExtractionError(f"Could not open PDF: {exc}") from exc

    with document:
        if document.needs_pass:
            raise PDFExtractionError("This PDF is password protected.")

        pages: list[ExtractedPage] = []
        for index in range(document.page_count):
            try:
                raw = document.load_page(index).get_text("text")  # type: ignore[no-untyped-call]
            except Exception as exc:  # noqa: BLE001 - PyMuPDF raises backend-specific errors
                # pragma: no cover - corrupt page
                logger.warning("Failed to read page %s of %s: %s", index + 1, path.name, exc)
                raw = ""
            text = _normalise(raw)
            pages.append(
                ExtractedPage(
                    page_number=index + 1,
                    text=text,
                    character_count=len(text),
                )
            )

    if not any(page.text for page in pages):
        raise PDFExtractionError(
            "No selectable text found. The PDF may be a scanned image; OCR is not enabled yet."
        )

    return ExtractedDocument(pages=pages)


def get_pdf_metadata(path: Path) -> dict[str, str | int | None]:
    """Return a small subset of PDF metadata (title, author, page count)."""
    try:
        with pymupdf.open(path) as document:  # type: ignore[no-untyped-call]
            meta = document.metadata or {}
            return {
                "title": meta.get("title") or None,
                "author": meta.get("author") or None,
                "page_count": document.page_count,
            }
    except Exception:  # noqa: BLE001 - metadata is best-effort
        # pragma: no cover - metadata is best-effort
        return {"title": None, "author": None, "page_count": 0}
