"""
Notification service — manages user notifications.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def create_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    type: str,
    title: str,
    body: str,
    action_url: str | None = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        project_id=project_id,
        type=type,
        title=title,
        body=body,
        action_url=action_url,
    )
    db.add(notif)
    await db.flush()
    await db.refresh(notif)
    return notif


async def list_notifications(
    db: AsyncSession,
    user_id: uuid.UUID,
    unread_only: bool = False,
) -> list[Notification]:
    query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(Notification.read == False)  # noqa: E712
    query = query.order_by(Notification.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def mark_read(db: AsyncSession, notification_id: uuid.UUID) -> Notification:
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise ValueError("Notification not found")
    notif.read = True
    notif.read_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(notif)
    return notif


async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.read == False,  # noqa: E712
        )
    )
    notifications = result.scalars().all()
    now = datetime.now(timezone.utc)
    for n in notifications:
        n.read = True
        n.read_at = now
    await db.flush()
    return len(notifications)
