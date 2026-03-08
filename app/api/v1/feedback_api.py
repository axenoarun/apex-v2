"""Feedback endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models.user import User
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.services.feedback import create_feedback, list_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    body: FeedbackCreate,
    current_user: Annotated[User, Depends(require_permission("submit_feedback"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_feedback(
        db,
        submitted_by=current_user.id,
        **body.model_dump(),
    )


@router.get("/", response_model=list[FeedbackResponse])
async def get_feedback(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: uuid.UUID | None = Query(None),
    agent_execution_id: uuid.UUID | None = Query(None),
    category: str | None = Query(None),
):
    return await list_feedback(
        db,
        project_id=project_id,
        agent_execution_id=agent_execution_id,
        category=category,
    )
