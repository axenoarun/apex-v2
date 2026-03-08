"""Source definition + instance endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.source import (
    SourceDefinitionResponse,
    SourceInstanceResponse,
    SourceInstanceUpdate,
    SourceSelectRequest,
)
from app.services.source import (
    list_source_definitions,
    select_sources_for_project,
    list_source_instances,
    update_source_instance,
)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/definitions", response_model=list[SourceDefinitionResponse])
async def get_source_definitions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_source_definitions(db)


@router.post("/project/{project_id}/select", response_model=list[SourceInstanceResponse], status_code=status.HTTP_201_CREATED)
async def select_project_sources(
    project_id: uuid.UUID,
    body: SourceSelectRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await select_sources_for_project(
        db, project_id, body.source_definition_ids, current_user.id
    )


@router.get("/project/{project_id}", response_model=list[SourceInstanceResponse])
async def get_project_sources(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_source_instances(db, project_id)


@router.put("/{source_instance_id}", response_model=SourceInstanceResponse)
async def update_source(
    source_instance_id: uuid.UUID,
    body: SourceInstanceUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await update_source_instance(
            db, source_instance_id, current_user.id,
            **body.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
