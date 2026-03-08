"""
Source service — handles source instance lifecycle for a project.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import SourceDefinition, SourceInstance
from app.services.audit import log_audit


async def list_source_definitions(db: AsyncSession) -> list[SourceDefinition]:
    result = await db.execute(select(SourceDefinition).order_by(SourceDefinition.name))
    return list(result.scalars().all())


async def select_sources_for_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    source_definition_ids: list[uuid.UUID],
    actor_id: uuid.UUID,
) -> list[SourceInstance]:
    """Create source instances for selected source definitions."""
    instances = []
    for sd_id in source_definition_ids:
        # Check not already added
        existing = await db.execute(
            select(SourceInstance).where(
                SourceInstance.project_id == project_id,
                SourceInstance.source_definition_id == sd_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        instance = SourceInstance(
            project_id=project_id,
            source_definition_id=sd_id,
            status="NOT_STARTED",
        )
        db.add(instance)
        instances.append(instance)

    await db.flush()

    await log_audit(
        db,
        actor_type="USER",
        actor_id=actor_id,
        action="SELECT_SOURCES",
        entity_type="project",
        entity_id=project_id,
        project_id=project_id,
        new_value={"source_definition_ids": [str(s) for s in source_definition_ids]},
    )

    return instances


async def list_source_instances(db: AsyncSession, project_id: uuid.UUID) -> list[SourceInstance]:
    result = await db.execute(
        select(SourceInstance)
        .where(SourceInstance.project_id == project_id)
        .order_by(SourceInstance.created_at)
    )
    return list(result.scalars().all())


async def update_source_instance(
    db: AsyncSession,
    source_instance_id: uuid.UUID,
    actor_id: uuid.UUID,
    **updates,
) -> SourceInstance:
    result = await db.execute(
        select(SourceInstance).where(SourceInstance.id == source_instance_id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise ValueError("Source instance not found")

    for field, value in updates.items():
        if value is not None and hasattr(instance, field):
            setattr(instance, field, value)

    await db.flush()

    await log_audit(
        db,
        actor_type="USER",
        actor_id=actor_id,
        action="UPDATE_SOURCE",
        entity_type="source_instance",
        entity_id=source_instance_id,
        project_id=instance.project_id,
        new_value={k: v for k, v in updates.items() if v is not None},
    )

    await db.refresh(instance)
    return instance
