"""Eval definition + result endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.eval import EvalDefinitionResponse, EvalResultResponse
from app.services.eval import (
    list_eval_definitions,
    list_eval_results,
    get_project_eval_summary,
)

router = APIRouter(prefix="/evals", tags=["evals"])


@router.get("/definitions", response_model=list[EvalDefinitionResponse])
async def get_eval_definitions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_eval_definitions(db)


@router.get("/results", response_model=list[EvalResultResponse])
async def get_eval_results(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: uuid.UUID | None = Query(None),
    agent_execution_id: uuid.UUID | None = Query(None),
):
    return await list_eval_results(
        db,
        project_id=project_id,
        agent_execution_id=agent_execution_id,
    )


@router.get("/summary/{project_id}")
async def get_eval_summary(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_project_eval_summary(db, project_id)
