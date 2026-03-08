"""
Feedback service — captures human feedback on agent outputs.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback


async def create_feedback(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    agent_execution_id: uuid.UUID,
    task_instance_id: uuid.UUID | None = None,
    submitted_by: uuid.UUID,
    category: str,
    severity: str,
    description: str,
    original_output: dict | None = None,
    corrected_output: dict | None = None,
    quality_score: float,
) -> Feedback:
    fb = Feedback(
        project_id=project_id,
        agent_execution_id=agent_execution_id,
        task_instance_id=task_instance_id,
        submitted_by=submitted_by,
        category=category,
        severity=severity,
        description=description,
        original_output=original_output,
        corrected_output=corrected_output,
        quality_score=quality_score,
    )
    db.add(fb)
    await db.flush()
    await db.refresh(fb)
    return fb


async def list_feedback(
    db: AsyncSession,
    *,
    project_id: uuid.UUID | None = None,
    agent_execution_id: uuid.UUID | None = None,
    category: str | None = None,
) -> list[Feedback]:
    query = select(Feedback)
    if project_id:
        query = query.where(Feedback.project_id == project_id)
    if agent_execution_id:
        query = query.where(Feedback.agent_execution_id == agent_execution_id)
    if category:
        query = query.where(Feedback.category == category)
    query = query.order_by(Feedback.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())
