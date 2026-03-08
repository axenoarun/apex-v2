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
from app.models.ai_question import AIQuestion
from app.models.document import DocumentInstance, DocumentTemplate
from app.models.eval import EvalResult
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


async def _check_all_questions_answered(
    db: AsyncSession, project_id: uuid.UUID, phase_instance_id: uuid.UUID,
) -> dict:
    """Check that all AI questions for this project/phase have been answered."""
    result = await db.execute(
        select(AIQuestion).where(
            AIQuestion.project_id == project_id,
            AIQuestion.phase_instance_id == phase_instance_id,
        )
    )
    questions = list(result.scalars().all())
    total = len(questions)
    pending = sum(1 for q in questions if q.status == "PENDING")
    passed = total > 0 and pending == 0
    return {
        "passed": passed,
        "detail": f"{total - pending}/{total} answered" if total else "No questions found",
    }


async def _check_document_complete_or_generated(
    db: AsyncSession,
    project_id: uuid.UUID,
    phase_instance_id: uuid.UUID,
    criterion_key: str,
) -> dict:
    """Check that a document matching the criterion exists and is at least in DRAFT status."""
    # Derive a template name pattern from the criterion key, e.g. "sdr_first_draft_complete" -> "sdr_first_draft"
    pattern = criterion_key.removesuffix("_complete").removesuffix("_generated")
    template_name_like = f"%{pattern.replace('_', '%')}%"

    result = await db.execute(
        select(DocumentInstance)
        .join(DocumentTemplate, DocumentInstance.document_template_id == DocumentTemplate.id)
        .where(
            DocumentInstance.project_id == project_id,
            DocumentInstance.phase_instance_id == phase_instance_id,
            DocumentTemplate.name.ilike(template_name_like),
        )
    )
    docs = list(result.scalars().all())
    if not docs:
        return {"passed": False, "detail": f"No document found matching '{pattern}'"}
    # At least one document must be beyond NOT_STARTED / AI_DRAFTING
    valid_statuses = {"DRAFT", "IN_REVIEW", "REVISION_REQUESTED", "FINAL", "EXPORTED"}
    completed_docs = [d for d in docs if d.status in valid_statuses]
    passed = len(completed_docs) > 0
    return {
        "passed": passed,
        "detail": f"{len(completed_docs)}/{len(docs)} documents at DRAFT or beyond",
    }


async def _check_document_approved_or_reviewed(
    db: AsyncSession,
    project_id: uuid.UUID,
    phase_instance_id: uuid.UUID,
    criterion_key: str,
) -> dict:
    """Check that a document matching the criterion has reached FINAL status."""
    pattern = criterion_key.removesuffix("_approved").removesuffix("_reviewed")
    template_name_like = f"%{pattern.replace('_', '%')}%"

    result = await db.execute(
        select(DocumentInstance)
        .join(DocumentTemplate, DocumentInstance.document_template_id == DocumentTemplate.id)
        .where(
            DocumentInstance.project_id == project_id,
            DocumentInstance.phase_instance_id == phase_instance_id,
            DocumentTemplate.name.ilike(template_name_like),
        )
    )
    docs = list(result.scalars().all())
    if not docs:
        return {"passed": False, "detail": f"No document found matching '{pattern}'"}
    final_docs = [d for d in docs if d.status in ("FINAL", "EXPORTED")]
    passed = len(final_docs) > 0
    return {
        "passed": passed,
        "detail": f"{len(final_docs)}/{len(docs)} documents at FINAL/EXPORTED",
    }


async def _check_sign_off(
    db: AsyncSession,
    project_id: uuid.UUID,
    phase_instance_id: uuid.UUID,
    criterion_key: str,
) -> dict:
    """Check for sign-off via a FINAL document or answered approval question."""
    pattern = criterion_key.removesuffix("_sign_off")
    template_name_like = f"%{pattern.replace('_', '%')}%"

    # Check for a FINAL/EXPORTED document
    doc_result = await db.execute(
        select(DocumentInstance)
        .join(DocumentTemplate, DocumentInstance.document_template_id == DocumentTemplate.id)
        .where(
            DocumentInstance.project_id == project_id,
            DocumentInstance.phase_instance_id == phase_instance_id,
            DocumentTemplate.name.ilike(template_name_like),
            DocumentInstance.status.in_(("FINAL", "EXPORTED")),
        )
    )
    if doc_result.scalars().first():
        return {"passed": True, "detail": "Signed off via approved document"}

    # Fallback: check for an answered approval question mapped to this gate item
    q_result = await db.execute(
        select(AIQuestion).where(
            AIQuestion.project_id == project_id,
            AIQuestion.phase_instance_id == phase_instance_id,
            AIQuestion.maps_to_gate_item == criterion_key,
            AIQuestion.status == "ANSWERED",
        )
    )
    if q_result.scalars().first():
        return {"passed": True, "detail": "Signed off via answered approval question"}

    return {"passed": False, "detail": "No sign-off found"}


async def _check_validation_passed(
    db: AsyncSession,
    project_id: uuid.UUID,
    phase_instance_id: uuid.UUID,
    criterion_key: str,
) -> dict:
    """Check that eval results for this project/phase have passing scores."""
    # Get task instances in this phase to narrow eval results
    tasks_result = await db.execute(
        select(TaskInstance.id).where(
            TaskInstance.phase_instance_id == phase_instance_id,
        )
    )
    task_ids = [row[0] for row in tasks_result.all()]

    if not task_ids:
        return {"passed": False, "detail": "No tasks found for validation check"}

    eval_result = await db.execute(
        select(EvalResult).where(
            EvalResult.project_id == project_id,
            EvalResult.task_instance_id.in_(task_ids),
        )
    )
    evals = list(eval_result.scalars().all())
    if not evals:
        return {"passed": False, "detail": "No eval results found"}

    all_passed = all(e.passed for e in evals)
    passing = sum(1 for e in evals if e.passed)
    return {
        "passed": all_passed,
        "detail": f"{passing}/{len(evals)} evaluations passed",
    }


async def evaluate_gate(db: AsyncSession, phase_instance_id: uuid.UUID) -> dict:
    """Evaluate gate criteria for a phase. Returns per-criterion results and overall status."""
    phase = await db.execute(
        select(PhaseInstance).where(PhaseInstance.id == phase_instance_id)
    )
    phase_instance = phase.scalar_one_or_none()
    if not phase_instance:
        raise ValueError("Phase instance not found")

    project_id = phase_instance.project_id

    # Load phase definition for gate criteria
    phase_def_result = await db.execute(
        select(PhaseDefinition).where(PhaseDefinition.id == phase_instance.phase_definition_id)
    )
    phase_def = phase_def_result.scalar_one()

    # Base check: task completion
    tasks_result = await db.execute(
        select(TaskInstance).where(TaskInstance.phase_instance_id == phase_instance_id)
    )
    tasks = list(tasks_result.scalars().all())
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == "COMPLETED")

    gate_criteria = phase_def.gate_criteria or {}
    gate_results: dict[str, dict] = {}
    all_passed = True

    for criterion_key, criterion_meta in gate_criteria.items():
        is_required = criterion_meta.get("required", True) if isinstance(criterion_meta, dict) else True
        description = criterion_meta.get("description", "") if isinstance(criterion_meta, dict) else str(criterion_meta)

        # Route to the appropriate validator based on the criterion key
        if criterion_key == "all_questions_answered":
            result = await _check_all_questions_answered(db, project_id, phase_instance_id)

        elif criterion_key == "all_tasks_completed":
            passed = completed_tasks == total_tasks and total_tasks > 0
            result = {
                "passed": passed,
                "detail": f"{completed_tasks}/{total_tasks} tasks completed",
            }

        elif criterion_key.endswith("_complete") or criterion_key.endswith("_generated"):
            result = await _check_document_complete_or_generated(
                db, project_id, phase_instance_id, criterion_key,
            )

        elif criterion_key.endswith("_approved") or criterion_key.endswith("_reviewed"):
            result = await _check_document_approved_or_reviewed(
                db, project_id, phase_instance_id, criterion_key,
            )

        elif criterion_key.endswith("_sign_off"):
            result = await _check_sign_off(
                db, project_id, phase_instance_id, criterion_key,
            )

        elif criterion_key.endswith("_validation_passed"):
            result = await _check_validation_passed(
                db, project_id, phase_instance_id, criterion_key,
            )

        else:
            # No specific validator — mark as not evaluated
            result = {"passed": False, "detail": "NOT_EVALUATED — no validator for this criterion"}

        gate_results[criterion_key] = {
            "passed": result["passed"],
            "required": is_required,
            "description": description,
            "detail": result["detail"],
        }

        if is_required and not result["passed"]:
            all_passed = False

    # Base criterion: all tasks must also be completed for the gate to pass
    if completed_tasks < total_tasks or total_tasks == 0:
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
