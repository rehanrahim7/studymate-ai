"""Deterministic, page-aware text chunking.

Chunking needs no models and no network, so the dashboard can show a truthful
`chunk_count` as soon as a PDF is uploaded. Embeddings and vector search build
on top of these chunks in the RAG phase.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.pdf.extractor import ExtractedPage


@dataclass(slots=True)
class Chunk:
    """A slice of text that keeps track of the page it came from."""

    ordinal: int
    page_number: int
    text: str
    token_estimate: int


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 characters per token for English prose)."""
    return max(1, len(text) // 4)


def _split_on_boundaries(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text into overlapping windows, preferring paragraph boundaries."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        # A single oversized paragraph is hard-split by character budget.
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            start = 0
            while start < len(paragraph):
                end = min(start + chunk_size, len(paragraph))
                piece = paragraph[start:end]
                chunks.append(piece)
                if end == len(paragraph):
                    break
                start = max(start + 1, end - chunk_overlap)
            continue

        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        chunks.append(current)
        # Overlap: carry the tail of the previous chunk into the next one.
        tail = current[-chunk_overlap:] if chunk_overlap > 0 else ""
        current = f"{tail}\n\n{paragraph}".strip() if tail else paragraph

    if current:
        chunks.append(current)

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
        for piece in _split_on_boundaries(page.text, chunk_size, chunk_overlap):
            text = piece.strip()
            if not text:
                continue
            chunks.append(
                Chunk(
                    ordinal=ordinal,
                    page_number=page.page_number,
                    text=text,
                    token_estimate=_estimate_tokens(text),
                )
            )
            ordinal += 1

    return chunks
