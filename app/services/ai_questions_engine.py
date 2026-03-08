"""AI Question Generation Engine — Rule 5.8 from spec.

Generates questions per role when a phase starts.
Detects inconsistencies when answers are provided.
"""

import json
import logging
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentDefinition
from app.models.ai_question import AIQuestion
from app.models.phase import PhaseDefinition, PhaseInstance
from app.models.task import TaskDefinition
from app.models.project import Project
from app.models.document import DocumentInstance
from app.models.user import User
from app.models.role import Role, UserProjectRole
from app.services.claude_client import call_claude
from app.services.agent import create_execution, complete_execution
from app.services.ai_question import create_question
from app.services.notification import create_notification
from app.services.audit import log_audit

logger = logging.getLogger(__name__)


async def generate_questions_for_phase(
    project_id: uuid.UUID,
    phase_instance_id: uuid.UUID,
    db: AsyncSession,
) -> list[AIQuestion]:
    """Generate questions for all roles when a phase starts. Per Rule 5.8."""
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        return []

    pi_result = await db.execute(
        select(PhaseInstance, PhaseDefinition)
        .join(PhaseDefinition, PhaseInstance.phase_definition_id == PhaseDefinition.id)
        .where(PhaseInstance.id == phase_instance_id)
    )
    row = pi_result.one_or_none()
    if not row:
        return []
    phase_instance, phase_def = row

    # Prior answers
    prior_q = await db.execute(
        select(AIQuestion).where(
            AIQuestion.project_id == project_id,
            AIQuestion.status == "ANSWERED",
        )
    )
    prior_answers = [
        {"question": q.question_text, "answer": q.answer, "role": q.target_role}
        for q in prior_q.scalars().all()
    ]

    # Task definitions for this phase
    td_result = await db.execute(
        select(TaskDefinition).where(
            TaskDefinition.phase_definition_id == phase_def.id,
            TaskDefinition.is_active == True,  # noqa: E712
        )
    )
    task_defs = td_result.scalars().all()

    # Resolve discovery agent
    agent_def = await _get_discovery_agent(db)

    all_questions: list[AIQuestion] = []
    roles = ["ARCHITECT", "ENGINEER", "CLIENT", "ADOBE_LAUNCH_ADVISORY"]

    for role in roles:
        role_tasks = [td for td in task_defs if td.default_owner_role == role]
        if not role_tasks:
            continue

        execution = await create_execution(
            db,
            agent_definition_id=agent_def.id,
            project_id=project_id,
            triggered_by="SYSTEM",
            input_context={
                "phase": phase_def.name,
                "phase_number": phase_def.phase_number,
                "role": role,
                "task_count": len(role_tasks),
            },
        )

        # Use agent's system_prompt as base if available
        base_prompt = agent_def.system_prompt or ""
        system_prompt = f"""{base_prompt}

CURRENT CONTEXT:
- Role being questioned: {role}
- Phase {phase_def.phase_number}: {phase_def.name}
- Project: {project.name} for client {project.client_name}
- Phase description: {phase_def.description or 'N/A'}

INSTRUCTIONS:
Generate focused questions that will help the {role} complete their tasks in this phase.
Each question should map to a specific task or document field where possible.
Avoid asking questions already answered in prior responses.

Previous answers from this project: {json.dumps(prior_answers[:20]) if prior_answers else 'None yet'}

Return a JSON array of question objects:
[{{"question_text": "...", "question_type": "STRUCTURED", "maps_to_document_field": "field_name or null", "maps_to_gate_item": "gate_item or null", "context": "why this question matters"}}]

Generate 3-8 questions. Be specific to CJA migration and {role} responsibilities."""

        user_prompt = f"""Tasks for {role} in Phase {phase_def.phase_number}:
{chr(10).join(f'- {td.name} ({td.classification})' for td in role_tasks)}

Generate questions that {role} needs to answer to complete these tasks effectively."""

        try:
            response = await call_claude(system_prompt, user_prompt, temperature=0.7)
            questions_data = _parse_questions(response.content)

            await complete_execution(
                db, execution.id,
                output={"questions": questions_data},
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                cost_usd=Decimal(str(response.cost_usd)),
                confidence_score=0.9,
            )

            # Create question records
            batch_id = uuid.uuid4()
            for qd in questions_data:
                q = await create_question(
                    db,
                    project_id=project_id,
                    phase_instance_id=phase_instance_id,
                    target_role=role,
                    question_text=qd.get("question_text", ""),
                    question_type=qd.get("question_type", "STRUCTURED"),
                    question_context={"context": qd.get("context", "")},
                    maps_to_document_field=qd.get("maps_to_document_field"),
                    maps_to_gate_item=qd.get("maps_to_gate_item"),
                    batch_id=batch_id,
                )
                all_questions.append(q)

            # Notify users with this role
            user_result = await db.execute(
                select(User)
                .join(UserProjectRole, UserProjectRole.user_id == User.id)
                .join(Role, UserProjectRole.role_id == Role.id)
                .where(
                    UserProjectRole.project_id == project_id,
                    Role.name == role,
                )
            )
            for user in user_result.scalars().all():
                await create_notification(
                    db,
                    user_id=user.id,
                    project_id=project_id,
                    type="AI_NEEDS_INPUT",
                    title=f"New questions for Phase {phase_def.phase_number}",
                    body=f"{len(questions_data)} questions ready for your input in Phase {phase_def.phase_number}: {phase_def.name}.",
                    action_url=f"/projects/{project_id}/questions?phase={phase_instance_id}&role={role}",
                )

        except RuntimeError as e:
            execution.status = "FAILED"
            execution.output = {"error": str(e)}
            await db.flush()
            logger.error(f"Question generation failed for role {role}: {e}")

    return all_questions


async def check_answer_inconsistency(
    question: AIQuestion,
    db: AsyncSession,
) -> None:
    """Check answer against prior answers for consistency. Per Rule 5.8."""
    prior_result = await db.execute(
        select(AIQuestion).where(
            AIQuestion.project_id == question.project_id,
            AIQuestion.status == "ANSWERED",
            AIQuestion.id != question.id,
        )
    )
    prior_answers = list(prior_result.scalars().all())

    if len(prior_answers) < 2:
        return

    answer_lower = question.answer.lower() if question.answer else ""
    question_lower = question.question_text.lower()

    for prior in prior_answers:
        prior_answer_lower = prior.answer.lower() if prior.answer else ""
        prior_question_lower = prior.question_text.lower()

        if _is_contradiction(answer_lower, prior_answer_lower, question_lower, prior_question_lower):
            # Notify architect only (per spec: do NOT notify the answerer)
            arch_result = await db.execute(
                select(User)
                .join(UserProjectRole, UserProjectRole.user_id == User.id)
                .join(Role, UserProjectRole.role_id == Role.id)
                .where(
                    UserProjectRole.project_id == question.project_id,
                    Role.name == "ARCHITECT",
                )
            )
            for arch in arch_result.scalars().all():
                await create_notification(
                    db,
                    user_id=arch.id,
                    project_id=question.project_id,
                    type="AI_NEEDS_INPUT",
                    title="Potential inconsistency detected",
                    body=f"Answer to '{question.question_text[:80]}...' may conflict with prior answer to '{prior.question_text[:80]}...'",
                    action_url=f"/projects/{question.project_id}/questions",
                )

            await log_audit(
                db, actor_type="AI", actor_id=None,
                action="INCONSISTENCY_DETECTED",
                entity_type="ai_question",
                entity_id=question.id,
                project_id=question.project_id,
                new_value={
                    "current_question": question.question_text[:200],
                    "current_answer": (question.answer or "")[:200],
                    "conflicting_question": prior.question_text[:200],
                    "conflicting_answer": (prior.answer or "")[:200],
                },
            )
            break


# --- Helpers ---

async def _get_discovery_agent(db: AsyncSession) -> AgentDefinition:
    """Get or create the discovery agent definition."""
    from app.config import settings

    result = await db.execute(
        select(AgentDefinition).where(AgentDefinition.name == "discovery")
    )
    agent_def = result.scalar_one_or_none()

    if not agent_def:
        agent_def = AgentDefinition(
            name="discovery",
            display_name="Discovery Agent",
            role_description="Generates targeted questions for stakeholders based on phase context and prior answers.",
            model=settings.CLAUDE_MODEL,
            temperature=0.7,
            max_tokens_per_call=settings.CLAUDE_MAX_TOKENS,
            is_active=True,
        )
        db.add(agent_def)
        await db.flush()

    return agent_def


def _parse_questions(content: str) -> list[dict]:
    """Parse JSON array of questions from Claude response."""
    content = content.strip()

    if "```json" in content:
        start = content.index("```json") + 7
        end = content.index("```", start)
        content = content[start:end].strip()
    elif "```" in content:
        start = content.index("```") + 3
        end = content.index("```", start)
        content = content[start:end].strip()

    if "[" in content:
        start = content.index("[")
        end = content.rindex("]") + 1
        content = content[start:end]

    try:
        questions = json.loads(content)
        if isinstance(questions, list):
            return questions
    except json.JSONDecodeError:
        pass

    return []


def _is_contradiction(answer1: str, answer2: str, q1: str, q2: str) -> bool:
    """Simple heuristic to detect contradictions between yes/no style answers on similar topics."""
    words1 = set(q1.split()) - {"the", "a", "an", "is", "are", "do", "does", "will", "what", "how"}
    words2 = set(q2.split()) - {"the", "a", "an", "is", "are", "do", "does", "will", "what", "how"}
    overlap = words1 & words2

    if len(overlap) < 3:
        return False

    yes_words = {"yes", "true", "correct", "confirmed", "affirmative"}
    no_words = {"no", "false", "incorrect", "denied", "negative", "not"}

    a1_yes = any(w in answer1.split() for w in yes_words)
    a1_no = any(w in answer1.split() for w in no_words)
    a2_yes = any(w in answer2.split() for w in yes_words)
    a2_no = any(w in answer2.split() for w in no_words)

    return (a1_yes and a2_no) or (a1_no and a2_yes)
