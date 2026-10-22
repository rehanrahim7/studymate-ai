"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.llm.base import LLMService
from app.services.llm.factory import get_llm_service

DbSession = Annotated[Session, Depends(get_db)]
LLMServiceDep = Annotated[LLMService, Depends(get_llm_service)]
