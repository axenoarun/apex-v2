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


async def check_dependencies(db: AsyncSession, task_instance: TaskInstance) -> dict:
    """
    Check whether all dependencies for a task instance are satisfied.

    Returns:
        {
            "all_met": bool,
            "blocking": [list of blocking task instance UUIDs as strings],
            "total": int,
            "completed": int,
        }
    """
    depends_on = task_instance.depends_on
    if not depends_on:
        return {"all_met": True, "blocking": [], "total": 0, "completed": 0}

    dep_ids = [uuid.UUID(str(dep_id)) for dep_id in depends_on]

    result = await db.execute(
        select(TaskInstance).where(TaskInstance.id.in_(dep_ids))
    )
    dep_tasks = list(result.scalars().all())

    completed = [t for t in dep_tasks if t.status == "COMPLETED"]
    blocking = [str(t.id) for t in dep_tasks if t.status != "COMPLETED"]

    return {
        "all_met": len(blocking) == 0,
        "blocking": blocking,
        "total": len(dep_ids),
        "completed": len(completed),
    }


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

    # When transitioning to IN_PROGRESS, enforce dependency checks
    new_status = updates.get("status")
    if new_status == "IN_PROGRESS":
        dep_check = await check_dependencies(db, task)
        if not dep_check["all_met"]:
            blocking_ids = dep_check["blocking"]
            raise ValueError(
                f"Cannot start task: {len(blocking_ids)} blocking dependencies not completed. "
                f"Blocking task IDs: {blocking_ids}"
            )

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


async def _unblock_dependent_tasks(db: AsyncSession, completed_task: TaskInstance) -> list[TaskInstance]:
    """
    Find tasks that depend on the completed task and unblock them if all
    their dependencies are now satisfied.

    Returns a list of tasks that were unblocked.
    """
    completed_task_id_str = str(completed_task.id)

    # Find all BLOCKED tasks in the same project that might depend on this task.
    # We query all BLOCKED tasks and filter in Python because JSONB array
    # containment queries vary across dialects.
    result = await db.execute(
        select(TaskInstance).where(
            TaskInstance.project_id == completed_task.project_id,
            TaskInstance.status == "BLOCKED",
            TaskInstance.depends_on.isnot(None),
        )
    )
    blocked_tasks = list(result.scalars().all())

    unblocked: list[TaskInstance] = []
    for candidate in blocked_tasks:
        deps = candidate.depends_on or []
        # Check if the completed task is actually one of this task's dependencies
        dep_strs = [str(d) for d in deps]
        if completed_task_id_str not in dep_strs:
            continue

        # Check if ALL dependencies are now completed
        dep_check = await check_dependencies(db, candidate)
        if dep_check["all_met"]:
            candidate.status = "NOT_STARTED"
            unblocked.append(candidate)

    if unblocked:
        await db.flush()

    return unblocked


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

    # Unblock downstream tasks whose dependencies are now fully satisfied
    await _unblock_dependent_tasks(db, task)

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
