"""AI Improvement Engine — Section 10 from spec.

Analyzes feedback patterns, generates improvement proposals,
extracts cross-project knowledge, and auto-adjusts trust levels.
"""

import json
import logging
import uuid
from decimal import Decimal

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentDefinition
from app.models.improvement import ImprovementProposal
from app.models.knowledge import CrossProjectKnowledge
from app.models.feedback import Feedback
from app.models.document import DocumentInstance, DocumentTemplate
from app.models.task import TaskInstance, TaskDefinition
from app.models.user import User
from app.models.role import Role, UserProjectRole
from app.services.claude_client import call_claude
from app.services.agent import create_execution, complete_execution
from app.services.improvement import create_proposal
from app.services.knowledge import create_knowledge
from app.services.notification import create_notification
from app.services.audit import log_audit

logger = logging.getLogger(__name__)


async def analyze_feedback_and_propose(
    project_id: uuid.UUID,
    db: AsyncSession,
) -> list[ImprovementProposal]:
    """Analyze feedback patterns and generate improvement proposals using AI.
    Per Section 10.2."""
    fb_result = await db.execute(
        select(Feedback).where(Feedback.project_id == project_id)
        .order_by(Feedback.created_at.desc()).limit(100)
    )
    feedbacks = fb_result.scalars().all()

    if len(feedbacks) < 3:
        return []

    # Aggregate feedback stats
    category_counts: dict[str, int] = {}
    total_quality = 0.0
    low_quality_tasks = []

    for fb in feedbacks:
        category_counts[fb.category] = category_counts.get(fb.category, 0) + 1
        total_quality += fb.quality_score
        if fb.quality_score < 0.5:
            low_quality_tasks.append(str(fb.task_instance_id))

    avg_quality = total_quality / len(feedbacks)

    feedback_summary = {
        "total_feedback": len(feedbacks),
        "average_quality": avg_quality,
        "category_breakdown": category_counts,
        "low_quality_task_count": len(low_quality_tasks),
        "sample_descriptions": [fb.description for fb in feedbacks[:10] if fb.description],
    }

    agent_def = await _get_improvement_agent(db)

    execution = await create_execution(
        db,
        agent_definition_id=agent_def.id,
        project_id=project_id,
        triggered_by="SYSTEM",
        input_context=feedback_summary,
    )

    try:
        system_prompt = """You are an AI process improvement analyst for CJA migration projects.
Analyze the feedback data and generate improvement proposals.

Proposal types:
- PROCESS_CHANGE: Changes to workflow or task sequencing
- TEMPLATE_UPDATE: Updates to document templates or prompts
- TRUST_LEVEL_ADJUSTMENT: Recommendations to change AI trust levels
- PROMPT_REFINEMENT: Improvements to AI prompts based on feedback patterns

Return a JSON array of proposals, each with:
- proposal_type: one of the types above
- title: short descriptive title
- description: detailed explanation
- evidence: supporting data from the feedback"""

        user_prompt = f"""Feedback analysis for project:
{json.dumps(feedback_summary, indent=2)}

Based on this feedback data, generate improvement proposals.
Focus on patterns that suggest systematic issues rather than one-off problems."""

        response = await call_claude(system_prompt, user_prompt)

        await complete_execution(
            db, execution.id,
            output={"raw": response.content},
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost_usd=Decimal(str(response.cost_usd)),
            confidence_score=0.75,
        )

        proposals_data = _parse_json_array(response.content)
        created = []

        for p in proposals_data:
            proposal = await create_proposal(
                db,
                project_id=project_id,
                generated_by_agent_execution_id=execution.id,
                proposal_type=p.get("proposal_type", "PROCESS_CHANGE"),
                title=p.get("title", "Untitled Proposal"),
                description=p.get("description", ""),
                evidence=p.get("evidence"),
            )
            created.append(proposal)

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
                type="IMPROVEMENT_PROPOSAL",
                title=f"{len(created)} improvement proposal(s) generated",
                body=f"AI analysis of {len(feedbacks)} feedback items generated {len(created)} proposals for review.",
                action_url=f"/projects/{project_id}/improvements",
            )

        return created

    except Exception as e:
        execution.status = "FAILED"
        execution.output = {"error": str(e)}
        await db.flush()
        logger.error(f"Feedback analysis failed: {e}")
        return []


async def extract_knowledge_from_project(
    project_id: uuid.UUID,
    db: AsyncSession,
) -> list[CrossProjectKnowledge]:
    """Extract reusable knowledge from a completed project using AI. Per Section 10.4."""
    fb_result = await db.execute(
        select(Feedback).where(Feedback.project_id == project_id).limit(50)
    )
    feedbacks = [
        {"category": f.category, "quality_score": f.quality_score, "description": f.description}
        for f in fb_result.scalars().all()
    ]

    doc_result = await db.execute(
        select(DocumentInstance, DocumentTemplate)
        .join(DocumentTemplate, DocumentInstance.document_template_id == DocumentTemplate.id)
        .where(
            DocumentInstance.project_id == project_id,
            DocumentInstance.status.in_(["FINAL", "EXPORTED"]),
        )
    )
    documents = [
        {"name": dt.name, "content_summary": str(di.content)[:300] if di.content else ""}
        for di, dt in doc_result.all()
    ]

    if not feedbacks and not documents:
        return []

    agent_def = await _get_improvement_agent(db)

    execution = await create_execution(
        db,
        agent_definition_id=agent_def.id,
        project_id=project_id,
        triggered_by="SYSTEM",
        input_context={"feedbacks": feedbacks, "documents": documents},
    )

    try:
        system_prompt = """You are an AI knowledge extraction analyst for CJA migration projects.
Extract reusable patterns and knowledge from the completed project data.

Knowledge types:
- FIELD_MAPPING_PATTERN: Common AA-to-XDM field mapping patterns
- SCHEMA_PATTERN: XDM schema design patterns that worked well
- ERROR_RESOLUTION: Common errors and their resolutions
- PROMPT_EFFECTIVENESS: Which AI prompts produced the best results

Return a JSON array of knowledge entries, each with:
- knowledge_type: one of the types above
- content: the reusable knowledge (structured)
- confidence: how confident you are this is transferable (0-1)"""

        user_prompt = f"""Project data:
Feedback ({len(feedbacks)} items): {json.dumps(feedbacks[:20])}
Documents ({len(documents)} items): {json.dumps(documents[:10])}

Extract reusable knowledge patterns from this project."""

        response = await call_claude(system_prompt, user_prompt)

        await complete_execution(
            db, execution.id,
            output={"raw": response.content},
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost_usd=Decimal(str(response.cost_usd)),
            confidence_score=0.7,
        )

        entries = _parse_json_array(response.content)
        created = []

        for entry in entries:
            k = await create_knowledge(
                db,
                source_project_id=project_id,
                knowledge_type=entry.get("knowledge_type", "SCHEMA_PATTERN"),
                content=entry.get("content", {}),
                confidence=entry.get("confidence", 0.5),
            )
            created.append(k)

        return created

    except Exception as e:
        execution.status = "FAILED"
        execution.output = {"error": str(e)}
        await db.flush()
        logger.error(f"Knowledge extraction failed: {e}")
        return []


async def auto_adjust_trust_levels(
    project_id: uuid.UUID,
    db: AsyncSession,
) -> list[dict]:
    """Analyze feedback quality per task definition and recommend trust level changes.
    Per Section 10.3."""
    result = await db.execute(
        select(
            TaskInstance.task_definition_id,
            sa_func.avg(Feedback.quality_score),
            sa_func.count(Feedback.id),
        )
        .join(Feedback, Feedback.task_instance_id == TaskInstance.id)
        .where(TaskInstance.project_id == project_id)
        .group_by(TaskInstance.task_definition_id)
        .having(sa_func.count(Feedback.id) >= 3)
    )

    adjustments = []

    for td_id, avg_quality, count in result.all():
        td_result = await db.execute(
            select(TaskDefinition).where(TaskDefinition.id == td_id)
        )
        td = td_result.scalar_one_or_none()
        if td is None:
            continue

        current_trust = td.default_trust_level
        recommended = current_trust

        if avg_quality >= 0.8 and count >= 5:
            if current_trust == "ASSIST_ONLY":
                recommended = "SUPERVISED"
            elif current_trust == "SUPERVISED":
                recommended = "FULL_AUTO"
        elif avg_quality < 0.4:
            if current_trust == "FULL_AUTO":
                recommended = "SUPERVISED"
            elif current_trust == "SUPERVISED":
                recommended = "ASSIST_ONLY"

        if recommended != current_trust:
            adjustments.append({
                "task_definition_id": str(td_id),
                "task_name": td.name,
                "current_trust_level": current_trust,
                "recommended_trust_level": recommended,
                "avg_quality_score": float(avg_quality),
                "feedback_count": count,
            })

    return adjustments


# --- Helpers ---

async def _get_improvement_agent(db: AsyncSession) -> AgentDefinition:
    """Get or create the improvement agent definition."""
    from app.config import settings

    result = await db.execute(
        select(AgentDefinition).where(AgentDefinition.name == "improvement_agent")
    )
    agent_def = result.scalar_one_or_none()

    if not agent_def:
        agent_def = AgentDefinition(
            name="improvement_agent",
            display_name="Improvement Agent",
            role_description="Analyzes feedback patterns, generates improvement proposals, and extracts cross-project knowledge.",
            model=settings.CLAUDE_MODEL,
            temperature=0.3,
            max_tokens_per_call=settings.CLAUDE_MAX_TOKENS,
            is_active=True,
        )
        db.add(agent_def)
        await db.flush()

    return agent_def


def _parse_json_array(content: str) -> list[dict]:
    """Parse JSON array from Claude response."""
    clean = content.strip()
    if "```json" in clean:
        start = clean.index("```json") + 7
        end = clean.index("```", start)
        clean = clean[start:end].strip()
    elif "```" in clean:
        start = clean.index("```") + 3
        end = clean.index("```", start)
        clean = clean[start:end].strip()

    if "[" in clean:
        start = clean.index("[")
        end = clean.rindex("]") + 1
        clean = clean[start:end]

    try:
        parsed = json.loads(clean)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key in ("proposals", "entries", "knowledge"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]
            return [parsed]
    except json.JSONDecodeError:
        pass

    return []
