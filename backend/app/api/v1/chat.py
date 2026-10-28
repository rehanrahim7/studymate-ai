"""Document question-answering endpoint."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, EmbeddingServiceDep, LLMServiceDep
from app.models.document import Conversation, Message
from app.schemas.chat import ChatRequest, ChatResponse, ChatSource
from app.services.llm.base import LLMServiceError, LLMUnavailableError
from app.services.rag.dependencies import RagDependencyError
from app.services.rag.embeddings import EmbeddingError
from app.services.rag.indexer import DocumentIndexError, EmptyDocumentError, IndexBuildError
from app.services.rag.qa import DocumentQAService
from app.services.rag.retriever import (
    DocumentNotReadyError,
    DocumentsNotFoundError,
    RetrievalError,
    TooManyDocumentsError,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask a question about uploaded documents",
    description=(
        "Retrieves the most relevant chunks from the selected documents and asks the "
        "configured LLM to answer using only that context. `sources` always contains "
        "the real retrieved passages, never generated citations."
    ),
)
def ask_question(
    payload: ChatRequest,
    session: DbSession,
    llm: LLMServiceDep,
    embedder: EmbeddingServiceDep,
) -> ChatResponse:
    service = DocumentQAService(session=session, llm=llm, embedder=embedder)

    # Get or create conversation
    conversation = None
    if payload.conversation_id:
        conversation = session.get(Conversation, payload.conversation_id)
    if not conversation:
        conversation = Conversation(
            title=payload.question[:50] + ("..." if len(payload.question) > 50 else ""),
            document_ids=json.dumps(list(payload.document_ids)),
        )
        session.add(conversation)
        session.flush()
    else:
        conversation.document_ids = json.dumps(list(payload.document_ids))
        conversation.updated_at = datetime.now(UTC)

    try:
        result = service.answer(
            document_ids=list(payload.document_ids),
            question=payload.question,
            top_k=payload.top_k,
            conversation_id=conversation.id,
            session=session,
        )
    except DocumentsNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except DocumentNotReadyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except TooManyDocumentsError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except IndexBuildError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except DocumentIndexError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except RetrievalError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except (EmbeddingError, RagDependencyError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Could not prepare document embeddings. {exc}",
        ) from exc
    except LLMUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except LLMServiceError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"The language model failed to answer: {exc}",
        ) from exc

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.question,
    )
    session.add(user_msg)
    
    # Save assistant message
    sources_data = [
        {
            "document_id": source.document_id,
            "document_name": source.document_name,
            "chunk_id": source.chunk_id,
            "page_number": source.page_number,
            "ordinal": source.ordinal,
            "score": round(source.score, 6),
            "text": source.text,
        }
        for source in result.sources
    ]
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=result.answer,
        sources=json.dumps(sources_data) if sources_data else None,
        model=result.model,
        llm_used=1 if result.llm_used else 0,
    )
    session.add(assistant_msg)
    conversation.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(assistant_msg)

    return ChatResponse(
        answer=result.answer,
        sources=[
            ChatSource(
                document_id=source.document_id,
                document_name=source.document_name,
                chunk_id=source.chunk_id,
                page_number=source.page_number,
                ordinal=source.ordinal,
                score=round(source.score, 6),
                text=source.text,
            )
            for source in result.sources
        ],
        model=result.model,
        llm_used=result.llm_used,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        conversation_id=conversation.id,
        message_id=assistant_msg.id,
    )
