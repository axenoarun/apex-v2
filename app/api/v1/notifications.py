"""Notification endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationResponse
from app.services.notification import create_notification, list_notifications, mark_read, mark_all_read

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notif(
    body: NotificationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_notification(
        db,
        user_id=body.user_id,
        project_id=body.project_id,
        type=body.type,
        title=body.title,
        body=body.body,
        action_url=body.action_url,
    )


@router.get("/", response_model=list[NotificationResponse])
async def get_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    unread_only: bool = Query(False),
):
    return await list_notifications(db, current_user.id, unread_only)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def read_notification(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await mark_read(db, notification_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/read-all")
async def read_all_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    count = await mark_all_read(db, current_user.id)
    return {"marked_read": count}
