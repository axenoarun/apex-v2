"""Project CRUD + lifecycle endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models.user import User
from app.models.project import Project
from app.models.role import UserProjectRole, Role
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectDetail
from app.schemas.role import RoleAssign, RoleAssignResponse
from app.services.project import create_project, get_project_detail, list_projects

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_new_project(
    body: ProjectCreate,
    current_user: Annotated[User, Depends(require_permission("create_project"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    project = await create_project(
        db,
        organization_id=body.organization_id,
        name=body.name,
        client_name=body.client_name,
        description=body.description,
        created_by=current_user.id,
    )
    return project


@router.get("/", response_model=list[ProjectResponse])
async def get_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    organization_id: uuid.UUID | None = Query(None),
):
    projects = await list_projects(db, organization_id=organization_id)
    return projects


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    project = await get_project_detail(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.flush()
    return project


@router.post("/{project_id}/roles", response_model=RoleAssignResponse, status_code=status.HTTP_201_CREATED)
async def assign_role_to_project(
    project_id: uuid.UUID,
    body: RoleAssign,
    current_user: Annotated[User, Depends(require_permission("assign_roles"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Assign a user+role to a project."""
    assignment = UserProjectRole(
        user_id=body.user_id,
        project_id=project_id,
        role_id=body.role_id,
        assigned_by=current_user.id,
    )
    db.add(assignment)
    await db.flush()
    return assignment


@router.get("/{project_id}/roles", response_model=list[RoleAssignResponse])
async def list_project_roles(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(UserProjectRole).where(UserProjectRole.project_id == project_id)
    )
    return list(result.scalars().all())
