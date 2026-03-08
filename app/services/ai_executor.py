"""AI Task Execution — Rule 5.3 (AI task execution) + Rule 5.4 (confidence & pause logic).

Handles FULL_AUTO, SUPERVISED, and ASSIST_ONLY trust levels.
Integrates with agent execution tracking, cost tracking, notifications, and evals.
"""

import json
import time
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent import AgentDefinition, AgentExecution
from app.models.task import TaskInstance, TaskDefinition
from app.models.project import Project
from app.models.ai_question import AIQuestion
from app.models.document import DocumentInstance
from app.models.feedback import Feedback
from app.models.knowledge import CrossProjectKnowledge
from app.services.claude_client import call_claude, ClaudeResponse
from app.services.agent import create_execution, complete_execution, pause_execution
from app.services.notification import create_notification
from app.services.audit import log_audit


async def execute_ai_task(
    task_instance: TaskInstance,
    task_def: TaskDefinition,
    db: AsyncSession,
    *,
    triggered_by: str = "SYSTEM",
) -> AgentExecution:
    """Execute an AI or HYBRID task based on trust level. Per Rule 5.3."""
    project_id = task_instance.project_id
    start_time = time.monotonic()

    # Resolve agent definition
    agent_def = await _resolve_agent(task_def, db)

    # Gather context per Rule 5.3
    context = await _build_task_context(project_id, task_instance, task_def, db)

    # Create execution record
    execution = await create_execution(
        db,
        agent_definition_id=agent_def.id,
        project_id=project_id,
        task_instance_id=task_instance.id,
        triggered_by=triggered_by,
        input_context=context,
    )

    execution.status = "IN_PROGRESS"
    task_instance.status = "AI_PROCESSING"
    await db.flush()

    try:
        response = await _call_claude_for_task(task_def, agent_def, context)
    except RuntimeError as e:
        # All retries failed
        execution.status = "FAILED"
        execution.output = {"error": str(e)}
        task_instance.status = "BLOCKED"
        await db.flush()

        await _notify_architects(
            db, project_id,
            title=f"AI action failed: {task_def.name}",
            body=f"AI could not complete '{task_def.name}'. Manual intervention required.",
            action_url=f"/projects/{project_id}/tasks/{task_instance.id}",
        )

        await log_audit(
            db, actor_type="AI", actor_id=None,
            action="AI_ACTION_FAILED", entity_type="task_instance",
            entity_id=task_instance.id, project_id=project_id,
            new_value={"error": str(e)[:500]},
        )
        return execution

    duration_ms = int((time.monotonic() - start_time) * 1000)

    # Evaluate confidence (Rule 5.4)
    confidence = _evaluate_confidence(response, task_def, context)

    # Confidence below threshold — pause (Rule 5.4)
    if confidence < settings.AI_CONFIDENCE_THRESHOLD:
        await pause_execution(db, execution.id, reason={
            "type": "LOW_CONFIDENCE",
            "confidence": confidence,
            "message": f"AI confidence is low ({confidence:.2f}). Additional context needed.",
        })

        # Update execution metrics
        execution.tokens_input = response.tokens_input
        execution.tokens_output = response.tokens_output
        execution.cost_usd = Decimal(str(response.cost_usd))
        execution.confidence_score = confidence
        execution.duration_ms = duration_ms

        task_instance.status = "AI_PAUSED_NEEDS_INPUT"
        task_instance.ai_confidence = confidence
        await db.flush()

        if task_instance.assigned_to:
            await create_notification(
                db, user_id=task_instance.assigned_to, project_id=project_id,
                type="AI_NEEDS_INPUT",
                title=f"AI needs input: {task_def.name}",
                body=f"AI needs additional input for '{task_def.name}' (confidence: {confidence:.0%}).",
                action_url=f"/projects/{project_id}/tasks/{task_instance.id}",
            )

        return execution

    # Parse output
    output = _parse_ai_output(response.content, task_def)

    # Complete execution
    await complete_execution(
        db, execution.id,
        output=output,
        tokens_input=response.tokens_input,
        tokens_output=response.tokens_output,
        cost_usd=Decimal(str(response.cost_usd)),
        confidence_score=confidence,
        duration_ms=duration_ms,
    )

    task_instance.ai_output = output
    task_instance.ai_confidence = confidence

    # Apply trust level logic (Rule 5.3)
    trust = task_instance.trust_level
    notification_body = ""

    if trust == "FULL_AUTO":
        if confidence >= settings.AI_CONFIDENCE_AUTO_THRESHOLD:
            task_instance.status = "IN_REVIEW"
            notification_body = f"AI has completed '{task_def.name}' — review ready (confidence: {confidence:.0%})."
        else:
            task_instance.status = "AI_PAUSED_NEEDS_INPUT"
            notification_body = f"AI needs your input on '{task_def.name}' (confidence: {confidence:.0%})."
    elif trust == "SUPERVISED":
        task_instance.status = "IN_REVIEW"
        notification_body = f"AI draft ready for '{task_def.name}' — approval needed (confidence: {confidence:.0%})."
    elif trust == "ASSIST_ONLY":
        task_instance.ai_output = {"suggestions": output, "note": "AI suggestions only — complete the task manually"}
        task_instance.status = "IN_PROGRESS"
        notification_body = f"AI suggestions available for '{task_def.name}'."
    else:
        task_instance.status = "IN_REVIEW"
        notification_body = f"AI output ready for '{task_def.name}'."

    await db.flush()

    if task_instance.assigned_to and notification_body:
        await create_notification(
            db, user_id=task_instance.assigned_to, project_id=project_id,
            type="TASK_ASSIGNED",
            title=f"AI output: {task_def.name}",
            body=notification_body,
            action_url=f"/projects/{project_id}/tasks/{task_instance.id}",
        )

    await log_audit(
        db, actor_type="AI", actor_id=None,
        action="AI_TASK_EXECUTED", entity_type="task_instance",
        entity_id=task_instance.id, project_id=project_id,
        new_value={"trust_level": trust, "confidence": confidence, "status": task_instance.status},
    )

    # Run automated evals
    await _run_evals(db, execution, task_instance, output)

    return execution


async def resume_paused_execution(
    execution_id: uuid.UUID,
    additional_input: dict,
    db: AsyncSession,
) -> AgentExecution:
    """Resume a paused AI execution with new input. Per Rule 5.4."""
    result = await db.execute(
        select(AgentExecution).where(AgentExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise ValueError("Agent execution not found")
    if execution.status != "PAUSED":
        raise ValueError("Execution is not paused")

    # Get task context
    task_result = await db.execute(
        select(TaskInstance, TaskDefinition)
        .join(TaskDefinition, TaskInstance.task_definition_id == TaskDefinition.id)
        .where(TaskInstance.id == execution.task_instance_id)
    )
    row = task_result.one_or_none()
    if not row:
        raise ValueError("Associated task not found")
    task_instance, task_def = row

    # Rebuild context with additional input
    context = execution.input_context or {}
    context["additional_input"] = additional_input

    execution.status = "IN_PROGRESS"
    execution.paused = False
    execution.input_context = context
    task_instance.status = "AI_PROCESSING"
    await db.flush()

    agent_def = await _resolve_agent(task_def, db)
    start_time = time.monotonic()

    try:
        response = await _call_claude_for_task(task_def, agent_def, context)
    except RuntimeError as e:
        execution.status = "FAILED"
        execution.output = {"error": str(e)}
        task_instance.status = "BLOCKED"
        await db.flush()
        return execution

    duration_ms = int((time.monotonic() - start_time) * 1000)
    confidence = _evaluate_confidence(response, task_def, context)

    if confidence < settings.AI_CONFIDENCE_THRESHOLD:
        await pause_execution(db, execution.id, reason={
            "type": "LOW_CONFIDENCE",
            "confidence": confidence,
            "message": "AI confidence still low after additional input.",
        })
        execution.tokens_input = (execution.tokens_input or 0) + response.tokens_input
        execution.tokens_output = (execution.tokens_output or 0) + response.tokens_output
        execution.cost_usd = Decimal(str(float(execution.cost_usd or 0) + response.cost_usd))
        task_instance.status = "AI_PAUSED_NEEDS_INPUT"
        await db.flush()
        return execution

    output = _parse_ai_output(response.content, task_def)
    total_input = (execution.tokens_input or 0) + response.tokens_input
    total_output = (execution.tokens_output or 0) + response.tokens_output
    total_cost = Decimal(str(float(execution.cost_usd or 0) + response.cost_usd))

    await complete_execution(
        db, execution.id,
        output=output,
        tokens_input=total_input,
        tokens_output=total_output,
        cost_usd=total_cost,
        confidence_score=confidence,
        duration_ms=duration_ms,
    )

    task_instance.ai_output = output
    task_instance.ai_confidence = confidence
    task_instance.status = "IN_REVIEW"
    await db.flush()

    return execution


# --- Internal helpers ---

async def _resolve_agent(task_def: TaskDefinition, db: AsyncSession) -> AgentDefinition:
    """Map task definition to the appropriate agent."""
    name_lower = task_def.name.lower()

    if "question" in name_lower or "questionnaire" in name_lower:
        agent_name = "discovery_agent"
    elif "schema" in name_lower:
        agent_name = "schema_agent"
    elif "document" in name_lower or "sdr" in name_lower or "intent" in name_lower or "runbook" in name_lower or "report" in name_lower:
        agent_name = "document_agent"
    elif "field mapping" in name_lower or "mapping" in name_lower:
        agent_name = "solution_agent"
    elif "gate" in name_lower or "validation" in name_lower:
        agent_name = "validation_agent"
    elif "error" in name_lower or "pipeline" in name_lower:
        agent_name = "solution_agent"
    else:
        agent_name = "orchestrator_agent"

    result = await db.execute(
        select(AgentDefinition).where(AgentDefinition.name == agent_name)
    )
    agent_def = result.scalar_one_or_none()

    if not agent_def:
        # Fallback to orchestrator
        result = await db.execute(
            select(AgentDefinition).where(AgentDefinition.name == "orchestrator_agent")
        )
        agent_def = result.scalar_one_or_none()

    if not agent_def:
        # Create a default agent on the fly
        agent_def = AgentDefinition(
            name=agent_name,
            display_name=agent_name.replace("_", " ").title(),
            role_description=f"Agent for {task_def.name}",
            system_prompt=None,
            model=settings.CLAUDE_MODEL,
            temperature=0.3,
            max_tokens_per_call=settings.CLAUDE_MAX_TOKENS,
            is_active=True,
        )
        db.add(agent_def)
        await db.flush()

    return agent_def


async def _build_task_context(
    project_id: uuid.UUID,
    task_instance: TaskInstance,
    task_def: TaskDefinition,
    db: AsyncSession,
) -> dict:
    """Build context for AI call per Rule 5.3."""
    proj = await db.execute(select(Project).where(Project.id == project_id))
    project = proj.scalar_one_or_none()

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

    # Prior finalized documents
    doc_result = await db.execute(
        select(DocumentInstance).where(
            DocumentInstance.project_id == project_id,
            DocumentInstance.status.in_(["FINAL", "EXPORTED", "DRAFT"]),
        )
    )
    docs = [
        {"template_id": str(d.document_template_id), "content_summary": str(d.content)[:500] if d.content else ""}
        for d in doc_result.scalars().all()
    ]

    # Feedback from this project
    fb_result = await db.execute(
        select(Feedback).where(Feedback.project_id == project_id).limit(20)
    )
    feedback = [
        {"category": f.category, "description": f.description, "quality_score": f.quality_score}
        for f in fb_result.scalars().all()
    ]

    # Cross-project knowledge
    kn_result = await db.execute(
        select(CrossProjectKnowledge)
        .where(CrossProjectKnowledge.confidence >= 0.5)
        .order_by(CrossProjectKnowledge.times_successful.desc())
        .limit(10)
    )
    knowledge = [
        {"type": k.knowledge_type, "content": k.content}
        for k in kn_result.scalars().all()
    ]

    return {
        "project_name": project.name if project else "",
        "client_name": project.client_name if project else "",
        "task_name": task_def.name,
        "task_classification": task_def.classification,
        "task_hybrid_pattern": task_def.hybrid_pattern,
        "source_type": task_def.source_type,
        "answered_questions": answers,
        "prior_documents": docs,
        "prior_feedback": feedback,
        "cross_project_knowledge": knowledge,
    }


async def _call_claude_for_task(
    task_def: TaskDefinition,
    agent_def: AgentDefinition,
    context: dict,
) -> ClaudeResponse:
    """Build prompts and call Claude for a specific task."""
    # Use agent's system prompt if available, otherwise build one
    if agent_def.system_prompt:
        system_prompt = agent_def.system_prompt
    else:
        system_prompt = f"""You are an expert Adobe Analytics to CJA migration consultant.
You are completing the task: {task_def.name}
Classification: {task_def.classification}
{f'Hybrid pattern: {task_def.hybrid_pattern}' if task_def.hybrid_pattern else ''}

Project: {context.get('project_name', '')} for client {context.get('client_name', '')}

Use the context provided to generate high-quality, specific output for this task.
If the task is HYBRID with AI_DRAFTS_HUMAN_REVIEWS, produce a complete draft.
If the task is HYBRID with AI_OPTIONS_HUMAN_PICKS, produce 2-3 options with pros/cons.
If the task is AI, produce the final output.

Return structured JSON output."""

    user_prompt = f"""Context:
- Answered questions: {json.dumps(context.get('answered_questions', [])[:10])}
- Prior documents: {json.dumps(context.get('prior_documents', [])[:5])}
- Cross-project knowledge: {json.dumps(context.get('cross_project_knowledge', [])[:5])}
{f"- Additional input: {json.dumps(context.get('additional_input', {}))}" if context.get('additional_input') else ""}

Generate the output for: {task_def.name}
{f'Source type: {task_def.source_type}' if task_def.source_type else ''}"""

    return await call_claude(
        system_prompt, user_prompt,
        temperature=agent_def.temperature,
        max_tokens=agent_def.max_tokens_per_call,
        model=agent_def.model,
    )


def _evaluate_confidence(
    response: ClaudeResponse,
    task_def: TaskDefinition,
    context: dict,
) -> float:
    """Evaluate confidence based on Rule 5.4 criteria."""
    score = 0.7  # Base confidence

    # Boost if we have answered questions
    answered = context.get("answered_questions", [])
    if len(answered) >= 5:
        score += 0.1
    elif len(answered) == 0:
        score -= 0.15

    # Boost if prior documents exist
    docs = context.get("prior_documents", [])
    if len(docs) >= 2:
        score += 0.05

    # Boost if prior feedback is positive
    feedback = context.get("prior_feedback", [])
    if feedback:
        avg_quality = sum(f.get("quality_score", 0.5) for f in feedback) / len(feedback)
        if avg_quality > 0.7:
            score += 0.05
        elif avg_quality < 0.4:
            score -= 0.1

    # Cross-project knowledge boost
    knowledge = context.get("cross_project_knowledge", [])
    if len(knowledge) >= 3:
        score += 0.05

    # Additional input boosts confidence
    if context.get("additional_input"):
        score += 0.1

    # Response length heuristic — very short responses may indicate low quality
    if len(response.content) < 100:
        score -= 0.15

    return max(0.0, min(1.0, round(score, 3)))


def _parse_ai_output(content: str, task_def: TaskDefinition) -> dict:
    """Parse AI response into structured output."""
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
        return {"structured": parsed, "raw": content}
    except json.JSONDecodeError:
        return {"raw": content}


async def _run_evals(
    db: AsyncSession,
    execution: AgentExecution,
    task_instance: TaskInstance,
    output: dict,
) -> None:
    """Run automated evals against agent output."""
    from app.services.ai_eval_engine import run_evals_for_execution

    try:
        await run_evals_for_execution(db, execution, task_instance, output)
    except Exception as e:
        logger.warning(f"Eval execution failed: {e}")


async def _notify_architects(
    db: AsyncSession,
    project_id: uuid.UUID,
    title: str,
    body: str,
    action_url: str,
) -> None:
    """Notify all architects on a project."""
    from app.models.role import Role, UserProjectRole
    from app.models.user import User

    result = await db.execute(
        select(User)
        .join(UserProjectRole, UserProjectRole.user_id == User.id)
        .join(Role, UserProjectRole.role_id == Role.id)
        .where(UserProjectRole.project_id == project_id, Role.name == "ARCHITECT")
    )
    for arch in result.scalars().all():
        await create_notification(
            db, user_id=arch.id, project_id=project_id,
            type="ESCALATION", title=title, body=body, action_url=action_url,
        )


import logging
logger = logging.getLogger(__name__)
