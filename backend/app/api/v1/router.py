"""API v1 router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import chat, conversations, documents, health, study, study_history

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(conversations.router)
api_router.include_router(study.router)
api_router.include_router(study_history.router)
