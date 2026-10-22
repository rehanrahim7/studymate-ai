"""Abstract LLM interface.

The rest of the application only ever talks to `LLMService`, so swapping
Ollama for another provider (or a test double) never touches feature code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(slots=True)
class Message:
    """A single chat message."""

    role: MessageRole
    content: str


@dataclass(slots=True)
class LLMResponse:
    """A completion returned by an LLM provider."""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMServiceError(RuntimeError):
    """Raised when the LLM backend cannot fulfil a request."""


class LLMService(ABC):
    """Contract every LLM backend must satisfy."""

    name: str = "unknown"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Run a single-turn completion."""

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Run a multi-turn completion."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when the backend is reachable and usable."""
