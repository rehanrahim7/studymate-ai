"""Deterministic, page-aware text chunking.

Chunking needs no models and no network, so the dashboard can show a truthful
`chunk_count` as soon as a PDF is uploaded. The RAG indexer embeds these chunks
lazily on the first question about the document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.pdf.extractor import ExtractedPage


@dataclass(slots=True)
class Chunk:
    """A slice of text that keeps track of the page it came from."""

    ordinal: int
    page_number: int
    text: str
    token_estimate: int
    heading: str | None = None


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 characters per token for English prose)."""
    return max(1, len(text) // 4)


def _extract_heading(paragraph: str) -> str | None:
    stripped = paragraph.strip()
    if not stripped:
        return None
    # Common heading patterns: "Chapter 1: ...", "1. Introduction", "INTRODUCTION"
    if len(stripped) <= 80:
        if re.match(r"^(chapter|section)\s+\d+[:\.\s]+.+$", stripped, re.IGNORECASE):
            return stripped
        if re.match(r"^\d+[\.\)]\s+[A-Z][A-Za-z\s\-]+$", stripped):
            return stripped
        if stripped.isupper() and len(stripped.split()) <= 6 and len(stripped) >= 4:
            return stripped
        # Title-like short line ending with colon
        if stripped.endswith(":") and len(stripped.split()) <= 8:
            return stripped.rstrip(":")
    return None


def _split_on_boundaries(
    text: str, chunk_size: int, chunk_overlap: int
) -> list[tuple[str, str | None]]:
    """Split text into overlapping windows, preferring paragraph boundaries."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[tuple[str, str | None]] = []
    current = ""
    current_heading: str | None = None

    for paragraph in paragraphs:
        heading = _extract_heading(paragraph)
        if heading and not current.strip():
            current_heading = heading
            # Don't start a chunk with just a heading; include next content
            continue
        elif heading and current.strip():
            # New section starts - flush current
            chunks.append((current, current_heading))
            current = paragraph
            current_heading = heading
            continue

        # A single oversized paragraph is hard-split by character budget.
        if len(paragraph) > chunk_size:
            if current:
                chunks.append((current, current_heading))
                current = ""
                current_heading = None
            start = 0
            while start < len(paragraph):
                end = min(start + chunk_size, len(paragraph))
                piece = paragraph[start:end]
                chunks.append((piece, current_heading))
                if end == len(paragraph):
                    break
                start = max(start + 1, end - chunk_overlap)
            continue

        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        chunks.append((current, current_heading))
        # Overlap: carry the tail of the previous chunk into the next one.
        tail = current[-chunk_overlap:] if chunk_overlap > 0 else ""
        current = f"{tail}\n\n{paragraph}".strip() if tail else paragraph
        # Reset heading on new chunk unless we carry context

    if current:
        chunks.append((current, current_heading))

    return chunks


def chunk_pages(
    pages: list[ExtractedPage],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[Chunk]:
    """Turn extracted pages into ordered, page-tagged chunks."""
    chunks: list[Chunk] = []
    ordinal = 0

    for page in pages:
        if not page.text:
            continue
        for piece, heading in _split_on_boundaries(page.text, chunk_size, chunk_overlap):
            text = piece.strip()
            if not text:
                continue
            chunks.append(
                Chunk(
                    ordinal=ordinal,
                    page_number=page.page_number,
                    text=text,
                    token_estimate=_estimate_tokens(text),
                    heading=heading,
                )
            )
            ordinal += 1

    return chunks
