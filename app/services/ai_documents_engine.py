"""AI Document Generation Engine — generates documents from templates using Claude.

Lifecycle: NOT_STARTED → AI_DRAFTING → DRAFT → IN_REVIEW → FINAL → EXPORTED
"""

import json
import logging
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentDefinition
from app.models.document import DocumentTemplate, DocumentInstance
from app.models.phase import PhaseInstance, PhaseDefinition
from app.models.project import Project
from app.models.ai_question import AIQuestion
from app.models.user import User
from app.models.role import Role, UserProjectRole
from app.services.claude_client import call_claude
from app.services.agent import create_execution, complete_execution
from app.services.notification import create_notification
from app.services.audit import log_audit

logger = logging.getLogger(__name__)


async def generate_document(
    project_id: uuid.UUID,
    template_id: uuid.UUID,
    phase_instance_id: uuid.UUID,
    db: AsyncSession,
    *,
    task_instance_id: uuid.UUID | None = None,
) -> DocumentInstance:
    """Generate a document using AI based on a template."""
    template = await db.execute(
        select(DocumentTemplate).where(DocumentTemplate.id == template_id)
    )
    template = template.scalar_one_or_none()
    if not template:
        raise ValueError("Document template not found")

    # Find or create document instance
    result = await db.execute(
        select(DocumentInstance).where(
            DocumentInstance.project_id == project_id,
            DocumentInstance.document_template_id == template_id,
            DocumentInstance.phase_instance_id == phase_instance_id,
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        doc = DocumentInstance(
            document_template_id=template_id,
            project_id=project_id,
            phase_instance_id=phase_instance_id,
            task_instance_id=task_instance_id,
            status="NOT_STARTED",
            generated_by="AI",
            version=1,
        )
        db.add(doc)
        await db.flush()

    doc.status = "AI_DRAFTING"
    doc.generated_by = "AI"
    await db.flush()

    # Build context
    context = await _build_document_context(project_id, phase_instance_id, template, db)

    # Get document agent
    agent_def = await _get_document_agent(db)

    # Create execution
    execution = await create_execution(
        db,
        agent_definition_id=agent_def.id,
        project_id=project_id,
        task_instance_id=task_instance_id,
        triggered_by="SYSTEM",
        input_context=context,
    )

    try:
        system_prompt = f"""You are an expert Adobe Analytics to CJA migration consultant.
You are generating the document: {template.name}
Output format: {template.output_format}

Template structure:
{json.dumps(template.template_structure, indent=2) if template.template_structure else 'Standard document format'}

{template.ai_generation_prompt or ''}

Use the project context to generate a complete, professional document.
Return structured JSON with sections matching the template structure.
Each section should have a "title" and "content" field."""

        user_prompt = f"""Project context:
- Project: {context.get('project_name', '')} for client {context.get('client_name', '')}
- Phase: {context.get('phase_name', '')}
- Answered questions: {json.dumps(context.get('answered_questions', [])[:15])}
- Prior documents: {json.dumps(context.get('prior_documents', [])[:5])}

Generate the complete document: {template.name}"""

        response = await call_claude(system_prompt, user_prompt)

        content = _parse_document_content(response.content, template)

        await complete_execution(
            db, execution.id,
            output=content,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost_usd=Decimal(str(response.cost_usd)),
            confidence_score=0.8,
        )

        doc.content = content
        doc.status = "DRAFT"
        await db.flush()

        await log_audit(
            db, actor_type="AI", actor_id=None,
            action="DOCUMENT_AI_GENERATED", entity_type="document_instance",
            entity_id=doc.id, project_id=project_id,
            new_value={"template_name": template.name, "version": doc.version},
        )

        # Notify architects
        arch_result = await db.execute(
            select(User)
            .join(UserProjectRole, UserProjectRole.user_id == User.id)
            .join(Role, UserProjectRole.role_id == Role.id)
            .where(UserProjectRole.project_id == project_id, Role.name == "ARCHITECT")
        )
        for arch in arch_result.scalars().all():
            await create_notification(
                db, user_id=arch.id, project_id=project_id,
                type="DOCUMENT_REVIEW",
                title=f"AI-generated document: {template.name}",
                body=f"'{template.name}' draft generated by AI and ready for review.",
                action_url=f"/projects/{project_id}/documents/{doc.id}",
            )

    except Exception as e:
        execution.status = "FAILED"
        execution.output = {"error": str(e)}
        doc.status = "NOT_STARTED"
        await db.flush()
        logger.error(f"Document generation failed: {e}")
        raise

    return doc


# --- Helpers ---

async def _get_document_agent(db: AsyncSession) -> AgentDefinition:
    """Get or create the document agent definition."""
    from app.config import settings

    result = await db.execute(
        select(AgentDefinition).where(AgentDefinition.name == "document_agent")
    )
    agent_def = result.scalar_one_or_none()

    if not agent_def:
        agent_def = AgentDefinition(
            name="document_agent",
            display_name="Document Agent",
            role_description="Generates and maintains migration documents from templates using project context.",
            model=settings.CLAUDE_MODEL,
            temperature=0.3,
            max_tokens_per_call=settings.CLAUDE_MAX_TOKENS,
            is_active=True,
        )
        db.add(agent_def)
        await db.flush()

    return agent_def


async def _build_document_context(
    project_id: uuid.UUID,
    phase_instance_id: uuid.UUID,
    template: DocumentTemplate,
    db: AsyncSession,
) -> dict:
    """Build context for AI document generation."""
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()

    pi_result = await db.execute(
        select(PhaseInstance, PhaseDefinition)
        .join(PhaseDefinition, PhaseInstance.phase_definition_id == PhaseDefinition.id)
        .where(PhaseInstance.id == phase_instance_id)
    )
    pi_row = pi_result.one_or_none()
    phase_name = pi_row[1].name if pi_row else ""

    # Answered questions
    q_result = await db.execute(
        select(AIQuestion).where(
            AIQuestion.project_id == project_id,
            AIQuestion.status == "ANSWERED",
        ).limit(50)
    )
    answers = [
        {"question": q.question_text, "answer": q.answer, "role": q.target_role}
        for q in q_result.scalars().all()
    ]

    # Prior documents
    prior_docs_result = await db.execute(
        select(DocumentInstance, DocumentTemplate)
        .join(DocumentTemplate, DocumentInstance.document_template_id == DocumentTemplate.id)
        .where(
            DocumentInstance.project_id == project_id,
            DocumentInstance.status.in_(["FINAL", "EXPORTED"]),
        )
    )
    prior_docs = [
        {"name": dt.name, "content_summary": str(di.content)[:500] if di.content else ""}
        for di, dt in prior_docs_result.all()
    ]

    return {
        "project_name": project.name if project else "",
        "client_name": project.client_name if project else "",
        "phase_name": phase_name,
        "template_name": template.name,
        "answered_questions": answers,
        "prior_documents": prior_docs,
    }


def _parse_document_content(content: str, template: DocumentTemplate) -> dict:
    """Parse AI response into structured document content."""
    clean = content.strip()
    if "```json" in clean:
        start = clean.index("```json") + 7
        end = clean.index("```", start)
        clean = clean[start:end].strip()
    elif "```" in clean:
        start = clean.index("```") + 3
        end = clean.index("```", start)
        clean = clean[start:end].strip()

    try:
        parsed = json.loads(clean)
        return {"sections": parsed, "raw": content, "format": template.output_format}
    except json.JSONDecodeError:
        return {"raw": content, "format": template.output_format}
