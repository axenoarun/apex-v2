"""
Phase service — handles phase lifecycle, gate evaluation, and advancement.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.phase import PhaseDefinition, PhaseInstance
from app.models.task import TaskInstance
from app.models.project import Project
from app.services.audit import log_audit


async def get_phase_instances(db: AsyncSession, project_id: uuid.UUID) -> list[PhaseInstance]:
    """Get all phase instances for a project, ordered by phase number."""
    result = await db.execute(
        select(PhaseInstance)
        .join(PhaseDefinition, PhaseInstance.phase_definition_id == PhaseDefinition.id)
        .where(PhaseInstance.project_id == project_id)
        .order_by(PhaseDefinition.phase_number)
    )
    return list(result.scalars().all())


async def get_phase_instance_detail(db: AsyncSession, phase_instance_id: uuid.UUID) -> PhaseInstance | None:
    """Get a phase instance with its task instances."""
    result = await db.execute(
        select(PhaseInstance).where(PhaseInstance.id == phase_instance_id)
    )
    return result.scalar_one_or_none()


async def get_phase_task_instances(db: AsyncSession, phase_instance_id: uuid.UUID) -> list[TaskInstance]:
    """Get all task instances for a phase."""
    result = await db.execute(
        select(TaskInstance)
        .where(TaskInstance.phase_instance_id == phase_instance_id)
        .order_by(TaskInstance.created_at)
    )
    return list(result.scalars().all())


async def evaluate_gate(db: AsyncSession, phase_instance_id: uuid.UUID) -> dict:
    """Evaluate gate criteria for a phase. Returns gate status."""
    phase = await db.execute(
        select(PhaseInstance).where(PhaseInstance.id == phase_instance_id)
    )
    phase_instance = phase.scalar_one_or_none()
    if not phase_instance:
        raise ValueError("Phase instance not found")

    # Load phase definition for gate criteria
    phase_def_result = await db.execute(
        select(PhaseDefinition).where(PhaseDefinition.id == phase_instance.phase_definition_id)
    )
    phase_def = phase_def_result.scalar_one()

    # Check all task instances are completed
    tasks_result = await db.execute(
        select(TaskInstance).where(TaskInstance.phase_instance_id == phase_instance_id)
    )
    tasks = tasks_result.scalars().all()
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == "COMPLETED")

    gate_criteria = phase_def.gate_criteria or {}
    gate_results = {}
    all_passed = True

    for criterion, _ in gate_criteria.items():
        # Check if there's a task that maps to this gate item
        mapped_tasks = [t for t in tasks if t.status == "COMPLETED"]
        # Simple check: mark as passed if associated tasks are done
        passed = completed_tasks == total_tasks and total_tasks > 0
        gate_results[criterion] = passed
        if not passed:
            all_passed = False

    phase_instance.gate_results = gate_results

    return {
        "phase_instance_id": str(phase_instance_id),
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "gate_criteria": gate_criteria,
        "gate_results": gate_results,
        "gate_passed": all_passed,
    }


async def advance_phase(
    db: AsyncSession,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    override: bool = False,
    override_reason: str | None = None,
) -> dict:
    """Advance project to the next phase."""
    # Get project
    project_result = await db.execute(select(Project).where(Project.id == project_id))
    project = project_result.scalar_one_or_none()
    if not project:
        raise ValueError("Project not found")

    if not project.current_phase_id:
        raise ValueError("No current phase set")

    # Get current phase instance
    current_result = await db.execute(
        select(PhaseInstance).where(PhaseInstance.id == project.current_phase_id)
    )
    current_phase = current_result.scalar_one()

    # Evaluate gate unless overriding
    if not override:
        gate_result = await evaluate_gate(db, current_phase.id)
        if not gate_result["gate_passed"]:
            raise ValueError(f"Gate not passed. Results: {gate_result['gate_results']}")

    # Complete current phase
    current_phase.status = "COMPLETED"
    current_phase.completed_at = datetime.now(timezone.utc)

    if override:
        current_phase.gate_override_by = actor_id
        current_phase.gate_override_reason = override_reason

    # Find next phase
    current_def_result = await db.execute(
        select(PhaseDefinition).where(PhaseDefinition.id == current_phase.phase_definition_id)
    )
    current_def = current_def_result.scalar_one()

    next_def_result = await db.execute(
        select(PhaseDefinition)
        .where(
            PhaseDefinition.phase_number == current_def.phase_number + 1,
            PhaseDefinition.is_active == True,  # noqa: E712
        )
    )
    next_def = next_def_result.scalar_one_or_none()

    next_phase_instance = None
    if next_def:
        # Find the corresponding phase instance
        next_instance_result = await db.execute(
            select(PhaseInstance).where(
                PhaseInstance.project_id == project_id,
                PhaseInstance.phase_definition_id == next_def.id,
            )
        )
        next_phase_instance = next_instance_result.scalar_one_or_none()
        if next_phase_instance:
            next_phase_instance.status = "IN_PROGRESS"
            next_phase_instance.started_at = datetime.now(timezone.utc)
            project.current_phase_id = next_phase_instance.id

    await db.flush()

    await log_audit(
        db,
        actor_type="USER",
        actor_id=actor_id,
        action="ADVANCE_PHASE",
        entity_type="project",
        entity_id=project_id,
        project_id=project_id,
        old_value={"phase": current_def.name},
        new_value={"phase": next_def.name if next_def else "COMPLETED"},
    )

    return {
        "current_phase": current_phase,
        "next_phase": next_phase_instance,
        "message": f"Advanced from {current_def.name}" + (f" to {next_def.name}" if next_def else " — project complete"),
    }


async def rollback_phase(
    db: AsyncSession,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> PhaseInstance:
    """Rollback current phase to NOT_STARTED, reset all its tasks."""
    project_result = await db.execute(select(Project).where(Project.id == project_id))
    project = project_result.scalar_one_or_none()
    if not project or not project.current_phase_id:
        raise ValueError("Project not found or no current phase")

    current_result = await db.execute(
        select(PhaseInstance).where(PhaseInstance.id == project.current_phase_id)
    )
    current_phase = current_result.scalar_one()

    # Reset phase
    current_phase.status = "NOT_STARTED"
    current_phase.started_at = None
    current_phase.completed_at = None
    current_phase.gate_results = None
    current_phase.gate_override_by = None
    current_phase.gate_override_reason = None

    # Reset all task instances
    tasks_result = await db.execute(
        select(TaskInstance).where(TaskInstance.phase_instance_id == current_phase.id)
    )
    for task in tasks_result.scalars().all():
        task.status = "NOT_STARTED"
        task.started_at = None
        task.completed_at = None
        task.completed_by = None
        task.ai_confidence = None
        task.ai_output = None
        task.human_feedback = None
        task.reminder_count = 0
        task.escalated = False

    await db.flush()

    await log_audit(
        db,
        actor_type="USER",
        actor_id=actor_id,
        action="ROLLBACK_PHASE",
        entity_type="phase_instance",
        entity_id=current_phase.id,
        project_id=project_id,
    )

    return current_phase
