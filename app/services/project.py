"""
Project service — handles project creation with automatic phase/task instance scaffolding.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.phase import PhaseDefinition, PhaseInstance
from app.models.task import TaskDefinition, TaskInstance
from app.models.role import Role, UserProjectRole
from app.services.audit import log_audit


async def create_project(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    name: str,
    client_name: str,
    description: str | None,
    created_by: uuid.UUID,
) -> Project:
    """Create a project and scaffold all phase + task instances from definitions."""
    project = Project(
        organization_id=organization_id,
        name=name,
        client_name=client_name,
        description=description,
        created_by=created_by,
    )
    db.add(project)
    await db.flush()

    # Load all active phase definitions ordered by phase_number
    result = await db.execute(
        select(PhaseDefinition)
        .where(PhaseDefinition.is_active == True)  # noqa: E712
        .order_by(PhaseDefinition.phase_number)
    )
    phase_defs = result.scalars().all()

    first_phase_instance = None
    for phase_def in phase_defs:
        phase_instance = PhaseInstance(
            project_id=project.id,
            phase_definition_id=phase_def.id,
            status="NOT_STARTED",
        )
        db.add(phase_instance)
        await db.flush()

        if first_phase_instance is None:
            first_phase_instance = phase_instance

        # Load task definitions for this phase
        task_result = await db.execute(
            select(TaskDefinition)
            .where(
                TaskDefinition.phase_definition_id == phase_def.id,
                TaskDefinition.is_active == True,  # noqa: E712
            )
            .order_by(TaskDefinition.sort_order)
        )
        task_defs = task_result.scalars().all()

        for task_def in task_defs:
            task_instance = TaskInstance(
                task_definition_id=task_def.id,
                phase_instance_id=phase_instance.id,
                project_id=project.id,
                assigned_by="AI",
                status="NOT_STARTED",
                trust_level=task_def.default_trust_level,
                classification=task_def.classification,
                priority="MEDIUM",
            )
            db.add(task_instance)

    # Set current phase to Phase 1
    if first_phase_instance:
        project.current_phase_id = first_phase_instance.id
        first_phase_instance.status = "IN_PROGRESS"
        first_phase_instance.started_at = datetime.now(timezone.utc)

    await db.flush()

    # Auto-assign creator as ARCHITECT on this project
    architect_role = await db.execute(select(Role).where(Role.name == "ARCHITECT"))
    role = architect_role.scalar_one_or_none()
    if role:
        assignment = UserProjectRole(
            user_id=created_by,
            project_id=project.id,
            role_id=role.id,
            assigned_by=created_by,
        )
        db.add(assignment)
        await db.flush()

    await log_audit(
        db,
        actor_type="USER",
        actor_id=created_by,
        action="CREATE",
        entity_type="project",
        entity_id=project.id,
        new_value={"name": name, "client_name": client_name},
    )

    await db.refresh(project)
    return project


async def get_project_detail(db: AsyncSession, project_id: uuid.UUID) -> Project | None:
    """Get project with phase instances eagerly loaded."""
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.phase_instances))
        .where(Project.id == project_id)
    )
    return result.scalar_one_or_none()


async def list_projects(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> list[Project]:
    """List projects, optionally filtered by org or user assignment."""
    query = select(Project)
    if organization_id:
        query = query.where(Project.organization_id == organization_id)
    if user_id:
        query = query.join(UserProjectRole, UserProjectRole.project_id == Project.id).where(
            UserProjectRole.user_id == user_id
        )
    query = query.order_by(Project.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())
