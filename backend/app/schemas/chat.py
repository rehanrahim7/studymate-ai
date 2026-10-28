"""Schemas for document question answering."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator


class ChatRequest(BaseModel):
    """A question scoped to one or more uploaded documents."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(
        min_length=1,
        max_length=2000,
        description="Question to answer from the selected documents.",
    )
    document_ids: list[PositiveInt] = Field(
        min_length=1,
        max_length=10,
        description="Documents the answer must be grounded in.",
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of chunks to retrieve. Defaults to RETRIEVAL_TOP_K.",
    )
    conversation_id: int | None = Field(
        default=None,
        description="Conversation ID for persisting history.",
    )

    @field_validator("question")
    @classmethod
    def _strip_question(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must not be blank")
        return stripped

    @field_validator("document_ids")
    @classmethod
    def _deduplicate_documents(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


class ChatSource(BaseModel):
    """A retrieved passage. These are real chunks, never model-invented citations."""

    document_id: int
    document_name: str
    chunk_id: int
    page_number: int = Field(ge=1)
    ordinal: int = Field(ge=0)
    score: float = Field(ge=-1.0, le=1.0)
    text: str


class ChatResponse(BaseModel):
    """A grounded answer with the passages that were supplied to the model."""

    answer: str
    sources: list[ChatSource]
    model: str | None = Field(
        default=None,
        description="Chat model used, or null when no LLM call was necessary.",
    )
    llm_used: bool
    prompt_tokens: int = 0
    completion_tokens: int = 0
    conversation_id: int | None = None
    message_id: int | None = None


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    document_ids: list[int] = Field(default_factory=list)


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: str
    content: str
    sources: list[ChatSource] | None = None
    model: str | None = None
    llm_used: bool = False
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    document_ids: list[int] = []
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    document_ids: list[int] = []
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []
