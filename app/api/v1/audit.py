"""Audit log endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import require_permission
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/", response_model=list[AuditLogResponse])
async def list_audit_logs(
    current_user: Annotated[User, Depends(require_permission("view_audit_log"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: uuid.UUID | None = Query(None),
    entity_type: str | None = Query(None),
    action: str | None = Query(None),
    actor_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    query = select(AuditLog)
    if project_id:
        query = query.where(AuditLog.project_id == project_id)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if action:
        query = query.where(AuditLog.action == action)
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/project/{project_id}/summary")
async def get_audit_summary(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("view_audit_log"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from sqlalchemy import func
    result = await db.execute(
        select(
            AuditLog.action,
            func.count(AuditLog.id),
        )
        .where(AuditLog.project_id == project_id)
        .group_by(AuditLog.action)
    )
    actions = {row[0]: row[1] for row in result.all()}

    total_result = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.project_id == project_id)
    )
    total = total_result.scalar() or 0

    return {
        "project_id": str(project_id),
        "total_entries": total,
        "actions": actions,
    }
