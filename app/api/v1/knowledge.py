"""Cross-project knowledge endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.knowledge import KnowledgeCreate, KnowledgeResponse, KnowledgeUpdate
from app.services.knowledge import (
    create_knowledge,
    list_knowledge,
    get_knowledge,
    use_knowledge,
    update_knowledge,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/", response_model=KnowledgeResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_entry(
    body: KnowledgeCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_knowledge(db, **body.model_dump())


@router.get("/", response_model=list[KnowledgeResponse])
async def list_knowledge_entries(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    knowledge_type: str | None = Query(None),
    min_confidence: float | None = Query(None),
):
    return await list_knowledge(db, knowledge_type=knowledge_type, min_confidence=min_confidence)


@router.get("/{knowledge_id}", response_model=KnowledgeResponse)
async def get_knowledge_entry(
    knowledge_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    entry = await get_knowledge(db, knowledge_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return entry


@router.put("/{knowledge_id}", response_model=KnowledgeResponse)
async def update_knowledge_entry(
    knowledge_id: uuid.UUID,
    body: KnowledgeUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await update_knowledge(db, knowledge_id, **body.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


class KnowledgeUseRequest(BaseModel):
    successful: bool


@router.post("/{knowledge_id}/use", response_model=KnowledgeResponse)
async def record_knowledge_use(
    knowledge_id: uuid.UUID,
    body: KnowledgeUseRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await use_knowledge(db, knowledge_id, body.successful)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
