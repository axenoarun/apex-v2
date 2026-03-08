from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user
from app.models.role import Role
from app.models.user import User
from app.schemas.role import RoleResponse

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/", response_model=list[RoleResponse])
async def list_roles(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Role).order_by(Role.name))
    return result.scalars().all()
