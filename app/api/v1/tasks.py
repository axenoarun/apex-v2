"""Task instance endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models.user import User
from app.models.task import TaskDefinition
from app.schemas.task import (
    TaskDefinitionResponse,
    TaskInstanceResponse,
    TaskInstanceDetail,
    TaskInstanceUpdate,
    TaskCompleteRequest,
)
from app.services.task import (
    get_task_instance,
    list_task_instances,
    update_task_instance,
    complete_task,
    assign_task,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/definitions", response_model=list[TaskDefinitionResponse])
async def list_task_definitions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    phase_definition_id: uuid.UUID | None = Query(None),
):
    query = select(TaskDefinition).order_by(TaskDefinition.sort_order)
    if phase_definition_id:
        query = query.where(TaskDefinition.phase_definition_id == phase_definition_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/", response_model=list[TaskInstanceResponse])
async def list_tasks(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: uuid.UUID | None = Query(None),
    phase_instance_id: uuid.UUID | None = Query(None),
    assigned_to: uuid.UUID | None = Query(None),
    task_status: str | None = Query(None, alias="status"),
):
    return await list_task_instances(
        db,
        project_id=project_id,
        phase_instance_id=phase_instance_id,
        assigned_to=assigned_to,
        status=task_status,
    )


@router.get("/{task_instance_id}", response_model=TaskInstanceDetail)
async def get_task(
    task_instance_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    task = await get_task_instance(db, task_instance_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task instance not found")

    # Load definition for name
    task_def_result = await db.execute(
        select(TaskDefinition).where(TaskDefinition.id == task.task_definition_id)
    )
    task_def = task_def_result.scalar_one()

    return TaskInstanceDetail(
        **{c.key: getattr(task, c.key) for c in task.__table__.columns},
        task_name=task_def.name,
        task_description=task_def.description,
    )


@router.put("/{task_instance_id}", response_model=TaskInstanceResponse)
async def update_task(
    task_instance_id: uuid.UUID,
    body: TaskInstanceUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await update_task_instance(
            db, task_instance_id, current_user.id,
            **body.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{task_instance_id}/complete", response_model=TaskInstanceResponse)
async def complete_task_endpoint(
    task_instance_id: uuid.UUID,
    body: TaskCompleteRequest,
    current_user: Annotated[User, Depends(require_permission("complete_task"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await complete_task(
            db, task_instance_id, current_user.id,
            ai_output=body.ai_output,
            human_feedback=body.human_feedback,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


class TaskAssignRequest(BaseModel):
    assigned_to: uuid.UUID


@router.post("/{task_instance_id}/assign", response_model=TaskInstanceResponse)
async def assign_task_endpoint(
    task_instance_id: uuid.UUID,
    body: TaskAssignRequest,
    current_user: Annotated[User, Depends(require_permission("reassign_task"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await assign_task(db, task_instance_id, body.assigned_to, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
