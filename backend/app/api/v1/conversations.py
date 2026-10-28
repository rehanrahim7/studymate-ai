"""Conversation and message history endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.models.document import Conversation, Message
from app.schemas.chat import (
    ChatSource,
    ConversationCreate,
    ConversationDetail,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
def list_conversations(session: DbSession) -> list[ConversationResponse]:
    conversations = session.scalars(
        select(Conversation).order_by(Conversation.updated_at.desc())
    ).all()
    result = []
    for conv in conversations:
        message_count = session.scalar(
            select(func.count(Message.id)).where(Message.conversation_id == conv.id)
        ) or 0
        result.append(
            ConversationResponse(
                id=conv.id,
                title=conv.title,
                document_ids=conv.get_document_ids(),
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=message_count,
            )
        )
    return result


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, session: DbSession) -> ConversationResponse:
    conversation = Conversation(
        title=payload.title or "New Chat",
        document_ids=json.dumps(payload.document_ids),
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        document_ids=conversation.get_document_ids(),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=0,
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int, session: DbSession) -> ConversationDetail:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    
    messages = []
    for msg in conversation.messages:
        sources = None
        if msg.sources:
            try:
                sources_data = json.loads(msg.sources)
                sources = [ChatSource(**s) for s in sources_data]
            except (json.JSONDecodeError, TypeError, ValueError):
                sources = None
        messages.append(
            MessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                role=msg.role,
                content=msg.content,
                sources=sources,
                model=msg.model,
                llm_used=bool(msg.llm_used),
                created_at=msg.created_at,
            )
        )
    
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        document_ids=conversation.get_document_ids(),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: int, payload: ConversationUpdate, session: DbSession
) -> ConversationResponse:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    
    conversation.title = payload.title
    session.commit()
    session.refresh(conversation)
    
    message_count = session.scalar(
        select(func.count(Message.id)).where(Message.conversation_id == conversation.id)
    ) or 0
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        document_ids=conversation.get_document_ids(),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=message_count,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: int, session: DbSession) -> None:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    session.delete(conversation)
    session.commit()
