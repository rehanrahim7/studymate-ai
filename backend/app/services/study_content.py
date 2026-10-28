"""Document context selection and content checks for study-tool generation."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.models.document import DocumentChunk

_MAX_CONTEXT_CHUNKS = 12
_MAX_CONTEXT_CHARS = 9_000

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.ASCII)
_STOPWORDS = frozenset(
    {
        "about",
        "after",
        "again",
        "against",
        "also",
        "among",
        "and",
        "are",
        "because",
        "been",
        "before",
        "being",
        "between",
        "both",
        "but",
        "can",
        "could",
        "did",
        "does",
        "doing",
        "during",
        "each",
        "from",
        "further",
        "had",
        "has",
        "have",
        "having",
        "here",
        "how",
        "into",
        "its",
        "itself",
        "more",
        "most",
        "not",
        "only",
        "other",
        "our",
        "out",
        "over",
        "own",
        "same",
        "should",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "under",
        "until",
        "very",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "why",
        "will",
        "with",
        "would",
        "your",
    }
)


class InsufficientStudyContentError(ValueError):
    """The document does not contain enough usable text for the request."""


@dataclass(frozen=True)
class StudyContext:
    chunks: tuple[DocumentChunk, ...]
    text: str
    source_hash: str
    source_tokens: frozenset[str]
    usable_character_count: int


def usable_chunks(chunks: Sequence[DocumentChunk]) -> list[DocumentChunk]:
    return [chunk for chunk in chunks if chunk.text and chunk.text.strip()]


def document_content_hash(chunks: Sequence[DocumentChunk]) -> str:
    """Hash document text so a deck can detect later source changes."""
    digest = hashlib.sha256()
    for chunk in sorted(chunks, key=lambda item: (item.ordinal, item.id or 0)):
        text = chunk.text.strip()
        digest.update(str(len(text)).encode("ascii"))
        digest.update(b":")
        digest.update(text.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def content_tokens(text: str) -> frozenset[str]:
    """Return meaningful lowercase tokens for a cheap grounding check."""
    tokens = {
        token
        for token in _TOKEN_PATTERN.findall(text.casefold())
        if token not in _STOPWORDS and (len(token) > 2 or any(char.isdigit() for char in token))
    }
    return frozenset(tokens)


def has_source_overlap(text: str, source_tokens: frozenset[str], minimum: int = 2) -> bool:
    return len(content_tokens(text) & source_tokens) >= minimum


def build_study_context(
    chunks: Sequence[DocumentChunk],
    *,
    required_chars: int,
) -> StudyContext:
    """Select a bounded, spread-out sample and validate available content.

    The page-level chunks are used directly because they are already extracted
    and persisted with the document. Study outputs remain scoped to one document.
    """
    usable = usable_chunks(chunks)
    total_chars = sum(len(chunk.text.strip()) for chunk in usable)
    if not usable or total_chars < required_chars:
        raise InsufficientStudyContentError(
            "This document does not contain enough usable text for that study set. "
            "Try a longer, clearer PDF or request fewer items."
        )

    if len(usable) <= _MAX_CONTEXT_CHUNKS:
        selected = usable
    else:
        last_index = len(usable) - 1
        indexes = {
            round(position * last_index / (_MAX_CONTEXT_CHUNKS - 1))
            for position in range(_MAX_CONTEXT_CHUNKS)
        }
        selected = [usable[index] for index in sorted(indexes)]

    blocks: list[str] = []
    used_chars = 0
    for chunk in selected:
        block = f"[Page {chunk.page_number}] {chunk.text.strip()}"
        if blocks and used_chars + len(block) > _MAX_CONTEXT_CHARS:
            break
        blocks.append(block)
        used_chars += len(block)

    context_text = "\n\n".join(blocks)
    return StudyContext(
        chunks=tuple(selected),
        text=context_text,
        source_hash=document_content_hash(usable),
        source_tokens=content_tokens(context_text),
        usable_character_count=total_chars,
    )
