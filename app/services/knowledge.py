"""
Cross-project knowledge service — manages reusable patterns across projects.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import CrossProjectKnowledge


async def create_knowledge(
    db: AsyncSession,
    *,
    knowledge_type: str,
    source_project_id: uuid.UUID,
    content: dict | None = None,
    confidence: float,
) -> CrossProjectKnowledge:
    entry = CrossProjectKnowledge(
        knowledge_type=knowledge_type,
        source_project_id=source_project_id,
        content=content,
        confidence=confidence,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


async def list_knowledge(
    db: AsyncSession,
    *,
    knowledge_type: str | None = None,
    min_confidence: float | None = None,
) -> list[CrossProjectKnowledge]:
    query = select(CrossProjectKnowledge)
    if knowledge_type:
        query = query.where(CrossProjectKnowledge.knowledge_type == knowledge_type)
    if min_confidence is not None:
        query = query.where(CrossProjectKnowledge.confidence >= min_confidence)
    query = query.order_by(CrossProjectKnowledge.confidence.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_knowledge(db: AsyncSession, knowledge_id: uuid.UUID) -> CrossProjectKnowledge | None:
    result = await db.execute(
        select(CrossProjectKnowledge).where(CrossProjectKnowledge.id == knowledge_id)
    )
    return result.scalar_one_or_none()


async def use_knowledge(
    db: AsyncSession,
    knowledge_id: uuid.UUID,
    successful: bool,
) -> CrossProjectKnowledge:
    """Record that a knowledge entry was used, and whether it was successful."""
    entry = await get_knowledge(db, knowledge_id)
    if not entry:
        raise ValueError("Knowledge entry not found")

    entry.times_used += 1
    if successful:
        entry.times_successful += 1
    # Adjust confidence based on success rate
    if entry.times_used > 0:
        entry.confidence = round(entry.times_successful / entry.times_used, 3)

    await db.flush()
    await db.refresh(entry)
    return entry


async def update_knowledge(
    db: AsyncSession,
    knowledge_id: uuid.UUID,
    **updates,
) -> CrossProjectKnowledge:
    entry = await get_knowledge(db, knowledge_id)
    if not entry:
        raise ValueError("Knowledge entry not found")

    for field, value in updates.items():
        if value is not None and hasattr(entry, field):
            setattr(entry, field, value)

    await db.flush()
    await db.refresh(entry)
    return entry
