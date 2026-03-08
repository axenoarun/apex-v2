"""
Improvement proposal service — manages AI-generated improvement suggestions.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.improvement import ImprovementProposal
from app.services.audit import log_audit


async def create_proposal(
    db: AsyncSession,
    *,
    project_id: uuid.UUID | None,
    generated_by_agent_execution_id: uuid.UUID,
    proposal_type: str,
    title: str,
    description: str,
    evidence: dict | None = None,
) -> ImprovementProposal:
    proposal = ImprovementProposal(
        project_id=project_id,
        generated_by_agent_execution_id=generated_by_agent_execution_id,
        proposal_type=proposal_type,
        title=title,
        description=description,
        evidence=evidence,
        status="PROPOSED",
    )
    db.add(proposal)
    await db.flush()
    await db.refresh(proposal)
    return proposal


async def review_proposal(
    db: AsyncSession,
    proposal_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    new_status: str,
) -> ImprovementProposal:
    result = await db.execute(
        select(ImprovementProposal).where(ImprovementProposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise ValueError("Improvement proposal not found")

    old_status = proposal.status
    proposal.status = new_status
    proposal.reviewed_by = reviewer_id
    proposal.reviewed_at = datetime.now(timezone.utc)
    await db.flush()

    await log_audit(
        db,
        actor_type="USER",
        actor_id=reviewer_id,
        action="REVIEW_IMPROVEMENT",
        entity_type="improvement_proposal",
        entity_id=proposal_id,
        project_id=proposal.project_id,
        old_value={"status": old_status},
        new_value={"status": new_status},
    )

    await db.refresh(proposal)
    return proposal


async def list_proposals(
    db: AsyncSession,
    *,
    project_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[ImprovementProposal]:
    query = select(ImprovementProposal)
    if project_id:
        query = query.where(ImprovementProposal.project_id == project_id)
    if status:
        query = query.where(ImprovementProposal.status == status)
    query = query.order_by(ImprovementProposal.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())
