"""Chunking tests — the deterministic part of the retrieval pipeline."""

from __future__ import annotations

from app.services.pdf.extractor import ExtractedPage
from app.services.rag.chunking import chunk_pages


def _page(text: str, number: int = 1) -> ExtractedPage:
    return ExtractedPage(page_number=number, text=text, character_count=len(text))


def test_short_text_produces_a_single_chunk() -> None:
    chunks = chunk_pages([_page("Short and sweet.")], chunk_size=1000, chunk_overlap=50)

    assert len(chunks) == 1
    assert chunks[0].text == "Short and sweet."
    assert chunks[0].page_number == 1


def test_long_text_is_split_into_several_chunks() -> None:
    text = "word " * 900
    chunks = chunk_pages([_page(text)], chunk_size=300, chunk_overlap=30)

    assert len(chunks) > 1
    assert all(chunk.text for chunk in chunks)


def test_chunk_ordinals_are_sequential_and_pages_are_preserved() -> None:
    pages = [_page("alpha " * 400, number=1), _page("beta " * 400, number=2)]
    chunks = chunk_pages(pages, chunk_size=300, chunk_overlap=30)

    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))
    assert {chunk.page_number for chunk in chunks} == {1, 2}
    assert all(chunk.token_estimate > 0 for chunk in chunks)


def test_empty_pages_are_skipped() -> None:
    chunks = chunk_pages([_page("", number=1), _page("content", number=2)])

    assert len(chunks) == 1
    assert chunks[0].page_number == 2
