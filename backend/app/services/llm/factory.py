"""Factory that resolves the configured LLM backend."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.services.llm.base import LLMService
from app.services.llm.ollama import OllamaLLMService


@lru_cache
def get_llm_service() -> LLMService:
    """Return the process-wide LLM service instance."""
    settings: Settings = get_settings()
    return OllamaLLMService(settings)
