"""Ollama implementation of `LLMService`."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

import httpx

from app.core.config import Settings, get_settings
from app.services.llm.base import (
    LLMResponse,
    LLMService,
    LLMServiceError,
    Message,
    MessageRole,
)

logger = logging.getLogger(__name__)


class OllamaLLMService(LLMService):
    """Talks to a local (or remote) Ollama server over its HTTP API."""

    name = "ollama"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self._settings = settings or get_settings()
        self._client = client or httpx.Client(
            base_url=self._settings.ollama_base_url.rstrip("/"),
            timeout=self._settings.ollama_timeout_seconds,
        )

    # -- internals --------------------------------------------------------

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.post(path, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise LLMServiceError(f"Ollama returned {exc.response.status_code}: {detail}") from exc
        except httpx.HTTPError as exc:
            raise LLMServiceError(f"Could not reach Ollama at {self._base}: {exc}") from exc

        try:
            return cast("dict[str, Any]", response.json())
        except json.JSONDecodeError as exc:
            raise LLMServiceError("Ollama returned a non-JSON response") from exc

    @property
    def _base(self) -> str:
        return self._settings.ollama_base_url.rstrip("/")

    # -- LLMService -------------------------------------------------------

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        messages: list[Message] = []
        if system:
            messages.append(Message(role=MessageRole.SYSTEM, content=system))
        messages.append(Message(role=MessageRole.USER, content=prompt))
        return self.chat(messages, temperature=temperature, max_tokens=max_tokens)

    def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._settings.ollama_chat_model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        data = self._post("/api/chat", payload)
        return LLMResponse(
            text=(data.get("message") or {}).get("content", "").strip(),
            model=data.get("model", self._settings.ollama_chat_model),
            prompt_tokens=int(data.get("prompt_eval_count") or 0),
            completion_tokens=int(data.get("eval_count") or 0),
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        payload = {"model": self._settings.ollama_embed_model, "input": texts}
        data = self._post("/api/embed", payload)

        embeddings = data.get("embeddings")
        if embeddings is None and "embedding" in data:
            embeddings = [data["embedding"]]
        if not embeddings:
            raise LLMServiceError("Ollama returned no embeddings")

        return [[float(value) for value in vector] for vector in embeddings]

    def is_available(self) -> bool:
        try:
            response = self._client.get("/api/tags", timeout=3.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def list_models(self) -> list[str]:
        try:
            response = self._client.get("/api/tags", timeout=3.0)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return []
        return [str(model.get("name", "")) for model in data.get("models", [])]
