"""AI Question endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models.user import User
from app.schemas.ai_question import (
    AIQuestionCreate,
    AIQuestionResponse,
    AIQuestionAnswer,
    AIQuestionBatchCreate,
)
from app.services.ai_question import (
    create_question,
    create_batch,
    answer_question,
    list_questions,
    get_question_stats,
)

router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("/", response_model=AIQuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_question(
    body: AIQuestionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_question(db, **body.model_dump())


@router.post("/batch", response_model=list[AIQuestionResponse], status_code=status.HTTP_201_CREATED)
async def create_question_batch(
    body: AIQuestionBatchCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_batch(db, **body.model_dump())


@router.get("/", response_model=list[AIQuestionResponse])
async def list_ai_questions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: uuid.UUID | None = Query(None),
    phase_instance_id: uuid.UUID | None = Query(None),
    target_role: str | None = Query(None),
    q_status: str | None = Query(None, alias="status"),
    batch_id: uuid.UUID | None = Query(None),
):
    return await list_questions(
        db,
        project_id=project_id,
        phase_instance_id=phase_instance_id,
        target_role=target_role,
        status=q_status,
        batch_id=batch_id,
    )


@router.post("/{question_id}/answer", response_model=AIQuestionResponse)
async def answer_ai_question(
    question_id: uuid.UUID,
    body: AIQuestionAnswer,
    current_user: Annotated[User, Depends(require_permission("answer_questions"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await answer_question(db, question_id, body.answer, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/stats/{project_id}")
async def get_question_statistics(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_question_stats(db, project_id)
