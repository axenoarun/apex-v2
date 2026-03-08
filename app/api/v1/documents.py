"""Document template + instance endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.document import (
    DocumentTemplateResponse,
    DocumentInstanceCreate,
    DocumentInstanceResponse,
    DocumentInstanceUpdate,
    DocumentReviewRequest,
)
from app.services.document import (
    list_templates,
    create_document_instance,
    update_document_instance,
    review_document,
    list_document_instances,
    get_document_instance,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/templates", response_model=list[DocumentTemplateResponse])
async def get_templates(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    phase_definition_id: uuid.UUID | None = Query(None),
):
    return await list_templates(db, phase_definition_id)


@router.post("/", response_model=DocumentInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    body: DocumentInstanceCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_document_instance(
        db,
        document_template_id=body.document_template_id,
        project_id=body.project_id,
        phase_instance_id=body.phase_instance_id,
        task_instance_id=body.task_instance_id,
    )


@router.get("/project/{project_id}", response_model=list[DocumentInstanceResponse])
async def get_project_documents(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    phase_instance_id: uuid.UUID | None = Query(None),
):
    return await list_document_instances(db, project_id, phase_instance_id)


@router.get("/{doc_id}", response_model=DocumentInstanceResponse)
async def get_document(
    doc_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    doc = await get_document_instance(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.put("/{doc_id}", response_model=DocumentInstanceResponse)
async def update_document(
    doc_id: uuid.UUID,
    body: DocumentInstanceUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await update_document_instance(
            db, doc_id, current_user.id,
            **body.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{doc_id}/review", response_model=DocumentInstanceResponse)
async def review_document_endpoint(
    doc_id: uuid.UUID,
    body: DocumentReviewRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await review_document(db, doc_id, current_user.id, body.approved)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
