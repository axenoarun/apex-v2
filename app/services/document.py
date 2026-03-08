"""
Document service — handles document instance lifecycle and generation.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentTemplate, DocumentInstance
from app.services.audit import log_audit


async def list_templates(db: AsyncSession, phase_definition_id: uuid.UUID | None = None) -> list[DocumentTemplate]:
    query = select(DocumentTemplate)
    if phase_definition_id:
        query = query.where(DocumentTemplate.phase_definition_id == phase_definition_id)
    query = query.order_by(DocumentTemplate.name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_document_instance(
    db: AsyncSession,
    *,
    document_template_id: uuid.UUID,
    project_id: uuid.UUID,
    phase_instance_id: uuid.UUID,
    task_instance_id: uuid.UUID | None = None,
    generated_by: str = "AI",
) -> DocumentInstance:
    doc = DocumentInstance(
        document_template_id=document_template_id,
        project_id=project_id,
        phase_instance_id=phase_instance_id,
        task_instance_id=task_instance_id,
        status="NOT_STARTED",
        generated_by=generated_by,
        version=1,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


async def update_document_instance(
    db: AsyncSession,
    doc_id: uuid.UUID,
    actor_id: uuid.UUID,
    **updates,
) -> DocumentInstance:
    result = await db.execute(
        select(DocumentInstance).where(DocumentInstance.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError("Document instance not found")

    for field, value in updates.items():
        if value is not None and hasattr(doc, field):
            setattr(doc, field, value)

    await db.flush()

    await log_audit(
        db,
        actor_type="USER",
        actor_id=actor_id,
        action="UPDATE_DOCUMENT",
        entity_type="document_instance",
        entity_id=doc_id,
        project_id=doc.project_id,
        new_value={k: v for k, v in updates.items() if v is not None},
    )

    await db.refresh(doc)
    return doc


async def review_document(
    db: AsyncSession,
    doc_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    approved: bool,
) -> DocumentInstance:
    result = await db.execute(
        select(DocumentInstance).where(DocumentInstance.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError("Document instance not found")

    doc.reviewed_by = reviewer_id
    doc.status = "FINAL" if approved else "REVISION_REQUESTED"
    if approved:
        doc.version += 1

    await db.flush()

    await log_audit(
        db,
        actor_type="USER",
        actor_id=reviewer_id,
        action="REVIEW_DOCUMENT",
        entity_type="document_instance",
        entity_id=doc_id,
        project_id=doc.project_id,
        new_value={"approved": approved, "status": doc.status},
    )

    await db.refresh(doc)
    return doc


async def list_document_instances(
    db: AsyncSession,
    project_id: uuid.UUID,
    phase_instance_id: uuid.UUID | None = None,
) -> list[DocumentInstance]:
    query = select(DocumentInstance).where(DocumentInstance.project_id == project_id)
    if phase_instance_id:
        query = query.where(DocumentInstance.phase_instance_id == phase_instance_id)
    query = query.order_by(DocumentInstance.created_at)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_document_instance(db: AsyncSession, doc_id: uuid.UUID) -> DocumentInstance | None:
    result = await db.execute(
        select(DocumentInstance).where(DocumentInstance.id == doc_id)
    )
    return result.scalar_one_or_none()
