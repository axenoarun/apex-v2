import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog


async def log_audit(
    db: AsyncSession,
    *,
    actor_type: str,
    actor_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    extra_data: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        project_id=project_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        extra_data=extra_data,
    )
    db.add(entry)
    await db.flush()
    return entry
