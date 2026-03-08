"""
Task service — handles task instance lifecycle, assignment, and completion.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import TaskInstance, TaskDefinition
from app.services.audit import log_audit


async def get_task_instance(db: AsyncSession, task_instance_id: uuid.UUID) -> TaskInstance | None:
    result = await db.execute(
        select(TaskInstance).where(TaskInstance.id == task_instance_id)
    )
    return result.scalar_one_or_none()


async def list_task_instances(
    db: AsyncSession,
    *,
    project_id: uuid.UUID | None = None,
    phase_instance_id: uuid.UUID | None = None,
    assigned_to: uuid.UUID | None = None,
    status: str | None = None,
) -> list[TaskInstance]:
    query = select(TaskInstance)
    if project_id:
        query = query.where(TaskInstance.project_id == project_id)
    if phase_instance_id:
        query = query.where(TaskInstance.phase_instance_id == phase_instance_id)
    if assigned_to:
        query = query.where(TaskInstance.assigned_to == assigned_to)
    if status:
        query = query.where(TaskInstance.status == status)
    query = query.order_by(TaskInstance.created_at)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_task_instance(
    db: AsyncSession,
    task_instance_id: uuid.UUID,
    actor_id: uuid.UUID,
    **updates,
) -> TaskInstance:
    task = await get_task_instance(db, task_instance_id)
    if not task:
        raise ValueError("Task instance not found")

    old_values = {}
    new_values = {}
    for field, value in updates.items():
        if value is not None and hasattr(task, field):
            old_values[field] = getattr(task, field)
            setattr(task, field, value)
            new_values[field] = value

    # Auto-set started_at when moving to active status
    if task.status in ("IN_PROGRESS", "AI_PROCESSING") and not task.started_at:
        task.started_at = datetime.now(timezone.utc)

    await db.flush()

    await log_audit(
        db,
        actor_type="USER",
        actor_id=actor_id,
        action="UPDATE_TASK",
        entity_type="task_instance",
        entity_id=task_instance_id,
        project_id=task.project_id,
        old_value=old_values,
        new_value=new_values,
    )

    await db.refresh(task)
    return task


async def complete_task(
    db: AsyncSession,
    task_instance_id: uuid.UUID,
    completed_by: uuid.UUID,
    ai_output: dict | None = None,
    human_feedback: dict | None = None,
) -> TaskInstance:
    task = await get_task_instance(db, task_instance_id)
    if not task:
        raise ValueError("Task instance not found")

    task.status = "COMPLETED"
    task.completed_at = datetime.now(timezone.utc)
    task.completed_by = completed_by
    if ai_output:
        task.ai_output = ai_output
    if human_feedback:
        task.human_feedback = human_feedback

    await db.flush()

    await log_audit(
        db,
        actor_type="USER",
        actor_id=completed_by,
        action="COMPLETE_TASK",
        entity_type="task_instance",
        entity_id=task_instance_id,
        project_id=task.project_id,
    )

    await db.refresh(task)
    return task


async def assign_task(
    db: AsyncSession,
    task_instance_id: uuid.UUID,
    assigned_to: uuid.UUID,
    assigned_by_user: uuid.UUID,
) -> TaskInstance:
    task = await get_task_instance(db, task_instance_id)
    if not task:
        raise ValueError("Task instance not found")

    old_assignee = task.assigned_to
    task.assigned_to = assigned_to
    task.assigned_by = "ARCHITECT"
    await db.flush()

    await log_audit(
        db,
        actor_type="USER",
        actor_id=assigned_by_user,
        action="ASSIGN_TASK",
        entity_type="task_instance",
        entity_id=task_instance_id,
        project_id=task.project_id,
        old_value={"assigned_to": str(old_assignee) if old_assignee else None},
        new_value={"assigned_to": str(assigned_to)},
    )

    await db.refresh(task)
    return task
