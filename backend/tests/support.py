"""Deterministic test doubles and helpers for the RAG pipeline.

No network, no Ollama and no model downloads are involved: the fake embedder
maps tokens to collision-free slots so unrelated text is exactly orthogonal,
and the fake LLM records the prompts it receives.
"""

from __future__ import annotations

import hashlib
import re
import textwrap
from pathlib import Path
from typing import Any

import pymupdf
from fastapi.testclient import TestClient

from app.services.llm.base import (
    LLMResponse,
    LLMService,
    LLMUnavailableError,
    Message,
    MessageRole,
)
from app.services.rag.embeddings import EmbeddingError, EmbeddingService

_TOKEN = re.compile(r"[a-z0-9]+")
_VECTOR_DIMENSION = 256
_STOPWORDS = frozenset(
    {
        "a",
        "about",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "being",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "each",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "his",
        "how",
        "i",
        "in",
        "into",
        "is",
        "it",
        "its",
        "may",
        "me",
        "might",
        "must",
        "my",
        "no",
        "not",
        "of",
        "on",
        "or",
        "our",
        "should",
        "she",
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
        "to",
        "use",
        "used",
        "using",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
    }
)


def significant_tokens(text: str) -> list[str]:
    """Lower-case content words, suitable for a fake bag-of-words embedding."""
    return [
        token
        for token in _TOKEN.findall(text.lower())
        if len(token) > 2 and token not in _STOPWORDS
    ]


class FakeEmbeddingService(EmbeddingService):
    """Bag-of-words embeddings with collision-free slots and call counters."""

    def __init__(
        self,
        model_name: str = "fake-embedding",
        dimension: int = _VECTOR_DIMENSION,
    ) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self.document_batch_calls = 0
        self.query_calls = 0
        self.embedded_texts: list[str] = []
        self.raise_on_embed = False
        self._slots: dict[str, int] = {}

    def _slot(self, token: str) -> int:
        existing = self._slots.get(token)
        if existing is not None:
            return existing
        if len(self._slots) >= self.dimension:
            raise EmbeddingError("Fake embedding vocabulary is full.")
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        slot = int.from_bytes(digest, "big") % self.dimension
        while slot in self._slots.values():
            slot = (slot + 1) % self.dimension
        self._slots[token] = slot
        return slot

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in significant_tokens(text):
            vector[self._slot(token)] += 1.0
        norm = sum(value * value for value in vector) ** 0.5
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.raise_on_embed:
            raise EmbeddingError("Fake embedding failure.")
        self.document_batch_calls += 1
        self.embedded_texts.extend(texts)
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        if self.raise_on_embed:
            raise EmbeddingError("Fake embedding failure.")
        self.query_calls += 1
        return self._vector(text)


class FakeLLM(LLMService):
    """Configurable LLM double that records prompts and call counts."""

    name = "fake"

    def __init__(
        self,
        *,
        available: bool = True,
        installed_models: list[str] | None = None,
        response_text: str = "Grounded answer based on [Source 1].",
        model_name: str = "fake-model",
    ) -> None:
        self.available = available
        self.installed_models = installed_models
        self.response_text = response_text
        self.response_texts: list[str] | None = None
        self.error: Exception | None = None
        self.errors: list[Exception | None] | None = None
        self._model_name = model_name

        self.generate_calls = 0
        self.last_prompt = ""
        self.last_system: str | None = None
        self.last_messages: list[Message] = []

    @property
    def model_name(self) -> str:
        return self._model_name

    def check_ready(self) -> None:
        if not self.available:
            raise LLMUnavailableError("Fake LLM is unavailable. Start it with `fake serve`.")
        if self.installed_models is not None and self._model_name not in self.installed_models:
            raise LLMUnavailableError(
                f"Model '{self._model_name}' is not installed. "
                f"Run `fake pull {self._model_name}`."
            )

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        top_p: float | None = None,
        num_predict: int | None = None,
    ) -> LLMResponse:
        call_index = self.generate_calls
        self.generate_calls += 1
        self.last_prompt = prompt
        self.last_system = system
        self.last_messages = []
        if system:
            self.last_messages.append(Message(role=MessageRole.SYSTEM, content=system))
        self.last_messages.append(Message(role=MessageRole.USER, content=prompt))

        if self.error is not None:
            raise self.error
        if self.errors is not None and call_index < len(self.errors):
            error = self.errors[call_index]
            if error is not None:
                raise error
        text = self.response_text
        if self.response_texts is not None and call_index < len(self.response_texts):
            text = self.response_texts[call_index]
        return LLMResponse(
            text=text,
            model=self._model_name,
            prompt_tokens=12,
            completion_tokens=34,
        )

    def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        top_p: float | None = None,
        num_predict: int | None = None,
    ) -> LLMResponse:
        self.last_messages = list(messages)
        if self.error is not None:
            raise self.error
        return LLMResponse(text=self.response_text, model=self._model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Retrieval uses the embedding service, not the LLM.")

    def is_available(self) -> bool:
        return self.available


def make_pdf(directory: Path, name: str, pages: list[str]) -> Path:
    """Create a real PDF with one paragraph per page."""
    document = pymupdf.open()
    for text in pages:
        page = document.new_page()
        for line_number, line in enumerate(textwrap.wrap(text, width=90)):
            page.insert_text((72, 72 + line_number * 14), line, fontsize=10)
    path = directory / name
    document.save(path)
    document.close()
    return path


def upload_pdf(client: TestClient, path: Path) -> dict[str, Any]:
    """Upload a PDF and return the created document payload."""
    with path.open("rb") as handle:
        response = client.post(
            "/api/v1/documents",
            files={"file": (path.name, handle, "application/pdf")},
        )
    assert response.status_code == 201, response.text
    return dict(response.json())
