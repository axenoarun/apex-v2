"""Agent definition + execution endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.agent import (
    AgentDefinitionResponse,
    AgentExecutionCreate,
    AgentExecutionResponse,
    AgentExecutionUpdate,
)
from app.services.agent import (
    list_agent_definitions,
    create_execution,
    complete_execution,
    pause_execution,
    list_executions,
    get_execution,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/definitions", response_model=list[AgentDefinitionResponse])
async def get_agent_definitions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_agent_definitions(db)


@router.post("/executions", response_model=AgentExecutionResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_execution(
    body: AgentExecutionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_execution(
        db,
        agent_definition_id=body.agent_definition_id,
        project_id=body.project_id,
        task_instance_id=body.task_instance_id,
        triggered_by=body.triggered_by,
        input_context=body.input_context,
    )


@router.get("/executions", response_model=list[AgentExecutionResponse])
async def list_agent_executions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: uuid.UUID | None = Query(None),
    task_instance_id: uuid.UUID | None = Query(None),
    agent_definition_id: uuid.UUID | None = Query(None),
    exec_status: str | None = Query(None, alias="status"),
):
    return await list_executions(
        db,
        project_id=project_id,
        task_instance_id=task_instance_id,
        agent_definition_id=agent_definition_id,
        status=exec_status,
    )


@router.get("/executions/{execution_id}", response_model=AgentExecutionResponse)
async def get_agent_execution(
    execution_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    execution = await get_execution(db, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Agent execution not found")
    return execution


@router.post("/executions/{execution_id}/pause", response_model=AgentExecutionResponse)
async def pause_agent_execution(
    execution_id: uuid.UUID,
    body: AgentExecutionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await pause_execution(db, execution_id, body.pause_reason or {})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
