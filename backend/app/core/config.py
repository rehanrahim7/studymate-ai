"""Application settings, loaded from environment variables / .env files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration.

    Every value can be overridden with an environment variable of the same
    (case-insensitive) name. Secrets are never committed: only names and
    non-sensitive defaults live in `.env.example`.
    """

    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application -----------------------------------------------------
    app_name: str = "StudyMate AI API"
    app_version: str = "0.1.0"
    environment: str = Field(default="development")
    debug: bool = True
    api_prefix: str = "/api/v1"

    # --- Server ----------------------------------------------------------
    host: str = "127.0.0.1"
    port: int = 8000

    # --- CORS ------------------------------------------------------------
    # Origins that may call this API from a browser during local development.
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    # --- Database --------------------------------------------------------
    database_url: str = f"sqlite:///{BACKEND_DIR / 'storage' / 'studymate.db'}"

    # --- Storage ---------------------------------------------------------
    storage_dir: Path = BACKEND_DIR / "storage"
    upload_dir: Path = BACKEND_DIR / "storage" / "uploads"
    max_upload_size_mb: int = 25

    # --- LLM (Ollama) ----------------------------------------------------
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = "llama3.1:8b"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_timeout_seconds: float = 120.0

    # --- Retrieval -------------------------------------------------------
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_top_k: int = 5

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Allow `CORS_ORIGINS="http://a,http://b"` in addition to a JSON list."""
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                return value
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance (cheap to call from anywhere)."""
    return Settings()
