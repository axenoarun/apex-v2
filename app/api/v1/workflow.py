"""Workflow I/O (task_io) endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.workflow import (
    TaskIODefinitionResponse,
    TaskIODefinitionCreate,
    TaskIOInstanceResponse,
    TaskIOInstanceCreate,
    TaskIOInstanceUpdate,
)
from app.services.workflow import (
    create_io_definition,
    list_io_definitions,
    create_io_instance,
    update_io_instance,
    list_io_instances,
    get_task_inputs,
    get_task_outputs,
)

router = APIRouter(prefix="/workflow", tags=["workflow"])


# --- IO Definitions ---

@router.post("/definitions", response_model=TaskIODefinitionResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow_definition(
    body: TaskIODefinitionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_io_definition(db, **body.model_dump())


@router.get("/definitions", response_model=list[TaskIODefinitionResponse])
async def list_workflow_definitions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    task_definition_id: uuid.UUID | None = Query(None),
    io_type: str | None = Query(None),
):
    return await list_io_definitions(db, task_definition_id, io_type)


# --- IO Instances ---

@router.post("/instances", response_model=TaskIOInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow_instance(
    body: TaskIOInstanceCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_io_instance(db, **body.model_dump())


@router.get("/instances", response_model=list[TaskIOInstanceResponse])
async def list_workflow_instances(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    task_instance_id: uuid.UUID | None = Query(None),
    project_id: uuid.UUID | None = Query(None),
    io_status: str | None = Query(None, alias="status"),
):
    return await list_io_instances(
        db, task_instance_id=task_instance_id, project_id=project_id, status=io_status
    )


@router.put("/instances/{io_instance_id}", response_model=TaskIOInstanceResponse)
async def update_workflow_instance(
    io_instance_id: uuid.UUID,
    body: TaskIOInstanceUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await update_io_instance(db, io_instance_id, **body.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/task/{task_instance_id}/inputs", response_model=list[TaskIOInstanceResponse])
async def get_task_input_data(
    task_instance_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_task_inputs(db, task_instance_id)


@router.get("/task/{task_instance_id}/outputs", response_model=list[TaskIOInstanceResponse])
async def get_task_output_data(
    task_instance_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_task_outputs(db, task_instance_id)
