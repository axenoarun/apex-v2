from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.role import Role, UserProjectRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_permission(permission: str):
    """Check permission across ALL project roles for the user.

    Use for non-project-scoped actions (e.g. create_project).
    For project-scoped actions, use require_project_permission instead.
    """
    async def _check(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> User:
        result = await db.execute(
            select(Role)
            .join(UserProjectRole, UserProjectRole.role_id == Role.id)
            .where(UserProjectRole.user_id == current_user.id)
            .distinct()
        )
        roles = result.scalars().all()

        for role in roles:
            perms = role.permissions or {}
            if perms.get(permission, False):
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission}",
        )

    return _check


import uuid as _uuid


async def check_project_permission(
    db: AsyncSession, user_id: _uuid.UUID, project_id: _uuid.UUID, permission: str
) -> bool:
    """Check if user has a permission on a specific project."""
    result = await db.execute(
        select(Role)
        .join(UserProjectRole, UserProjectRole.role_id == Role.id)
        .where(
            UserProjectRole.user_id == user_id,
            UserProjectRole.project_id == project_id,
        )
    )
    roles = result.scalars().all()
    for role in roles:
        perms = role.permissions or {}
        if perms.get(permission, False):
            return True
    return False
