"""
AI Question service — manages AI-generated questions and stakeholder answers.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_question import AIQuestion
from app.services.audit import log_audit


async def create_question(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    phase_instance_id: uuid.UUID,
    task_instance_id: uuid.UUID | None = None,
    target_role: str,
    question_text: str,
    question_type: str,
    question_context: dict | None = None,
    maps_to_document_field: str | None = None,
    maps_to_gate_item: str | None = None,
    batch_id: uuid.UUID | None = None,
) -> AIQuestion:
    question = AIQuestion(
        project_id=project_id,
        phase_instance_id=phase_instance_id,
        task_instance_id=task_instance_id,
        target_role=target_role,
        question_text=question_text,
        question_type=question_type,
        question_context=question_context,
        maps_to_document_field=maps_to_document_field,
        maps_to_gate_item=maps_to_gate_item,
        batch_id=batch_id,
        status="PENDING",
    )
    db.add(question)
    await db.flush()
    await db.refresh(question)
    return question


async def create_batch(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    phase_instance_id: uuid.UUID,
    task_instance_id: uuid.UUID | None = None,
    target_role: str,
    questions: list[dict],
) -> list[AIQuestion]:
    """Create a batch of questions with a shared batch_id."""
    batch_id = uuid.uuid4()
    created = []
    for q in questions:
        question = await create_question(
            db,
            project_id=project_id,
            phase_instance_id=phase_instance_id,
            task_instance_id=task_instance_id,
            target_role=target_role,
            question_text=q["question_text"],
            question_type=q.get("question_type", "TEXT"),
            question_context=q.get("question_context"),
            maps_to_document_field=q.get("maps_to_document_field"),
            maps_to_gate_item=q.get("maps_to_gate_item"),
            batch_id=batch_id,
        )
        created.append(question)
    return created


async def answer_question(
    db: AsyncSession,
    question_id: uuid.UUID,
    answer: str,
    answered_by: uuid.UUID,
) -> AIQuestion:
    result = await db.execute(
        select(AIQuestion).where(AIQuestion.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise ValueError("Question not found")

    question.answer = answer
    question.answered_by = answered_by
    question.answered_at = datetime.now(timezone.utc)
    question.status = "ANSWERED"

    await db.flush()

    await log_audit(
        db,
        actor_type="USER",
        actor_id=answered_by,
        action="ANSWER_QUESTION",
        entity_type="ai_question",
        entity_id=question_id,
        project_id=question.project_id,
    )

    await db.refresh(question)
    return question


async def list_questions(
    db: AsyncSession,
    *,
    project_id: uuid.UUID | None = None,
    phase_instance_id: uuid.UUID | None = None,
    target_role: str | None = None,
    status: str | None = None,
    batch_id: uuid.UUID | None = None,
) -> list[AIQuestion]:
    query = select(AIQuestion)
    if project_id:
        query = query.where(AIQuestion.project_id == project_id)
    if phase_instance_id:
        query = query.where(AIQuestion.phase_instance_id == phase_instance_id)
    if target_role:
        query = query.where(AIQuestion.target_role == target_role)
    if status:
        query = query.where(AIQuestion.status == status)
    if batch_id:
        query = query.where(AIQuestion.batch_id == batch_id)
    query = query.order_by(AIQuestion.created_at)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_question_stats(db: AsyncSession, project_id: uuid.UUID) -> dict:
    """Get question statistics for a project."""
    result = await db.execute(
        select(
            AIQuestion.status,
            func.count(AIQuestion.id),
        )
        .where(AIQuestion.project_id == project_id)
        .group_by(AIQuestion.status)
    )
    stats = {row[0]: row[1] for row in result.all()}
    return {
        "total": sum(stats.values()),
        "pending": stats.get("PENDING", 0),
        "answered": stats.get("ANSWERED", 0),
        "skipped": stats.get("SKIPPED", 0),
    }
