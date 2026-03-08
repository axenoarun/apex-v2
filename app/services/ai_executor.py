"""AI Task Execution — Rule 5.3 (AI task execution) + Rule 5.4 (confidence & pause logic).

Handles FULL_AUTO, SUPERVISED, and ASSIST_ONLY trust levels.
Integrates with agent execution tracking, cost tracking, notifications, and evals.
"""

import json
import time
import uuid
from decimal import Decimal

from sqlalchemy import select, func as sa_func
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
from app.services.cost import record_cost
from app.services.notification import create_notification
from app.services.audit import log_audit

import logging
logger = logging.getLogger(__name__)


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

    # Determine if this is rework (task was previously COMPLETED or has prior executions)
    is_rework = await _check_is_rework(db, task_instance)

    try:
        response = await _call_claude_for_task(task_def, agent_def, context)
    except Exception as e:
        error_type = _categorize_error(e)
        error_details = {
            "error": str(e)[:500],
            "error_type": error_type,
            "task_name": task_def.name,
        }

        if error_type == "PARSING_ERROR":
            # Attempt one automatic retry with a more explicit prompt format instruction
            try:
                response = await _call_claude_for_task_with_format_hint(
                    task_def, agent_def, context
                )
            except Exception as retry_err:
                error_details["retry_attempted"] = True
                error_details["retry_error"] = str(retry_err)[:500]
                execution.status = "FAILED"
                execution.output = error_details
                task_instance.status = "BLOCKED"
                await db.flush()
                await _notify_and_audit_failure(
                    db, project_id, task_instance, task_def, error_details
                )
                return execution
        elif error_type == "API_ERROR":
            # Rate limit / timeout — set to WAITING_INPUT with retry note
            execution.status = "FAILED"
            execution.output = error_details
            task_instance.status = "WAITING_INPUT"
            task_instance.ai_output = {
                "retry_note": (
                    "AI service temporarily unavailable due to rate limiting or timeout. "
                    "The task will be automatically retried. No action required unless "
                    "this persists for more than 15 minutes."
                ),
                "error_type": error_type,
            }
            await db.flush()
            await _notify_and_audit_failure(
                db, project_id, task_instance, task_def, error_details
            )
            return execution
        elif error_type == "CONTEXT_ERROR":
            # Missing inputs — set to BLOCKED with details about what's missing
            missing_info = _detect_missing_context(context)
            error_details["missing_context"] = missing_info
            execution.status = "FAILED"
            execution.output = error_details
            task_instance.status = "BLOCKED"
            task_instance.ai_output = {
                "blocked_reason": (
                    "AI could not proceed because required context is missing."
                ),
                "missing_context": missing_info,
                "error_type": error_type,
            }
            await db.flush()
            await _notify_and_audit_failure(
                db, project_id, task_instance, task_def, error_details
            )
            return execution
        else:
            # UNKNOWN error
            execution.status = "FAILED"
            execution.output = error_details
            task_instance.status = "BLOCKED"
            await db.flush()
            await _notify_and_audit_failure(
                db, project_id, task_instance, task_def, error_details
            )
            return execution

    duration_ms = int((time.monotonic() - start_time) * 1000)

    # Record cost tracking for the Claude call
    await record_cost(
        db,
        project_id=project_id,
        agent_execution_id=execution.id,
        tokens_input=response.tokens_input,
        tokens_output=response.tokens_output,
        cost_usd=Decimal(str(response.cost_usd)),
        is_rework=is_rework,
        rework_reason="Task re-execution or previously completed" if is_rework else None,
        is_eval=False,
        phase_instance_id=task_instance.phase_instance_id,
        task_instance_id=task_instance.id,
    )

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

    # Record cost for the resumed call (always rework since this is a retry)
    await record_cost(
        db,
        project_id=execution.project_id,
        agent_execution_id=execution.id,
        tokens_input=response.tokens_input,
        tokens_output=response.tokens_output,
        cost_usd=Decimal(str(response.cost_usd)),
        is_rework=True,
        rework_reason="Resumed after pause for additional input",
        is_eval=False,
        phase_instance_id=task_instance.phase_instance_id,
        task_instance_id=task_instance.id,
    )

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
        agent_name = "discovery"
    elif "schema" in name_lower:
        agent_name = "schema"
    elif "document" in name_lower or "sdr" in name_lower or "intent" in name_lower or "runbook" in name_lower or "report" in name_lower:
        agent_name = "document"
    elif "field mapping" in name_lower or "mapping" in name_lower:
        agent_name = "solution"
    elif "gate" in name_lower or "validation" in name_lower:
        agent_name = "validation"
    elif "error" in name_lower or "pipeline" in name_lower:
        agent_name = "solution"
    else:
        agent_name = "orchestrator"

    result = await db.execute(
        select(AgentDefinition).where(AgentDefinition.name == agent_name)
    )
    agent_def = result.scalar_one_or_none()

    if not agent_def:
        # Fallback to orchestrator
        result = await db.execute(
            select(AgentDefinition).where(AgentDefinition.name == "orchestrator")
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

    # Cross-project knowledge — filter by PATTERN and BEST_PRACTICE with confidence >= 0.6
    kn_result = await db.execute(
        select(CrossProjectKnowledge)
        .where(
            CrossProjectKnowledge.knowledge_type.in_(["PATTERN", "BEST_PRACTICE"]),
            CrossProjectKnowledge.confidence >= 0.6,
        )
        .order_by(CrossProjectKnowledge.times_successful.desc())
        .limit(10)
    )
    knowledge = [
        {
            "type": k.knowledge_type,
            "content": k.content,
            "confidence": k.confidence,
            "times_successful": k.times_successful,
        }
        for k in kn_result.scalars().all()
    ]

    return {
        "project_name": project.name if project else "",
        "client_name": project.client_name if project else "",
        "current_phase_id": str(project.current_phase_id) if project and project.current_phase_id else None,
        "project_status": project.status if project else "",
        "task_name": task_def.name,
        "task_description": task_def.description or "",
        "task_classification": task_def.classification,
        "task_hybrid_pattern": task_def.hybrid_pattern,
        "source_type": task_def.source_type,
        "answered_questions": answers,
        "prior_documents": docs,
        "prior_feedback": feedback,
        "cross_project_knowledge": knowledge,
    }


async def _check_is_rework(db: AsyncSession, task_instance: TaskInstance) -> bool:
    """Check if this execution is rework (task was previously COMPLETED or has prior executions)."""
    if task_instance.completed_at is not None:
        return True

    # Check for prior executions on this task instance
    prior_count = await db.execute(
        select(sa_func.count(AgentExecution.id)).where(
            AgentExecution.task_instance_id == task_instance.id,
            AgentExecution.status.in_(["COMPLETED", "FAILED"]),
        )
    )
    count = prior_count.scalar() or 0
    return count > 0


async def _call_claude_for_task(
    task_def: TaskDefinition,
    agent_def: AgentDefinition,
    context: dict,
) -> ClaudeResponse:
    """Build prompts and call Claude for a specific task."""
    # Build system prompt: ALWAYS use agent_def.system_prompt as the base if it exists
    if agent_def.system_prompt:
        # Use the agent's seeded system prompt as the primary base
        system_prompt = agent_def.system_prompt

        # Append project context
        project_context_lines = []
        if context.get("client_name"):
            project_context_lines.append(f"Client: {context['client_name']}")
        if context.get("project_name"):
            project_context_lines.append(f"Project: {context['project_name']}")
        if context.get("current_phase_id"):
            project_context_lines.append(f"Current phase ID: {context['current_phase_id']}")
        if context.get("project_status"):
            project_context_lines.append(f"Project status: {context['project_status']}")

        if project_context_lines:
            system_prompt += f"\n\n--- Project Context ---\n" + "\n".join(project_context_lines)

        # Append task-specific instructions from the task definition
        task_lines = ["\n--- Current Task ---", f"Task: {task_def.name}"]
        if task_def.description:
            task_lines.append(f"Description: {task_def.description}")
        task_lines.append(f"Classification: {task_def.classification}")
        if task_def.hybrid_pattern:
            task_lines.append(f"Hybrid pattern: {task_def.hybrid_pattern}")
        if task_def.source_type:
            task_lines.append(f"Source type: {task_def.source_type}")

        # Add hybrid pattern instructions
        if task_def.hybrid_pattern == "AI_DRAFTS_HUMAN_REVIEWS":
            task_lines.append("Instruction: Produce a complete, publication-ready draft for human review.")
        elif task_def.hybrid_pattern == "AI_OPTIONS_HUMAN_PICKS":
            task_lines.append("Instruction: Produce 2-3 distinct options with pros/cons for each.")
        elif task_def.hybrid_pattern == "HUMAN_INITIATES_AI_COMPLETES":
            task_lines.append("Instruction: Complete the task based on the human-provided initial input.")

        system_prompt += "\n" + "\n".join(task_lines)
    else:
        # Fallback: build a complete system prompt when agent has no seeded prompt
        system_prompt = f"""You are an expert Adobe Analytics to CJA migration consultant.
You are completing the task: {task_def.name}
{f'Description: {task_def.description}' if task_def.description else ''}
Classification: {task_def.classification}
{f'Hybrid pattern: {task_def.hybrid_pattern}' if task_def.hybrid_pattern else ''}
{f'Source type: {task_def.source_type}' if task_def.source_type else ''}

Project: {context.get('project_name', '')} for client {context.get('client_name', '')}
{f"Project status: {context.get('project_status', '')}" if context.get('project_status') else ''}

Use the context provided to generate high-quality, specific output for this task.
If the task is HYBRID with AI_DRAFTS_HUMAN_REVIEWS, produce a complete draft.
If the task is HYBRID with AI_OPTIONS_HUMAN_PICKS, produce 2-3 options with pros/cons.
If the task is AI, produce the final output.

Return structured JSON output."""

    # Build user prompt with all context
    user_prompt_parts = ["Context:"]

    if context.get("answered_questions"):
        user_prompt_parts.append(f"- Answered questions: {json.dumps(context['answered_questions'][:10])}")
    if context.get("prior_documents"):
        user_prompt_parts.append(f"- Prior documents: {json.dumps(context['prior_documents'][:5])}")
    if context.get("prior_feedback"):
        user_prompt_parts.append(f"- Prior feedback: {json.dumps(context['prior_feedback'][:5])}")
    if context.get("cross_project_knowledge"):
        user_prompt_parts.append(f"- Cross-project knowledge (patterns & best practices): {json.dumps(context['cross_project_knowledge'][:5])}")
    if context.get("additional_input"):
        user_prompt_parts.append(f"- Additional input: {json.dumps(context['additional_input'])}")

    user_prompt_parts.append(f"\nGenerate the output for: {task_def.name}")
    if task_def.source_type:
        user_prompt_parts.append(f"Source type: {task_def.source_type}")

    user_prompt = "\n".join(user_prompt_parts)

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
    """Parse AI response into structured output based on task type."""
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
    except json.JSONDecodeError:
        parsed = None

    # Structure output based on task classification and hybrid pattern
    base = {"raw": content}

    if parsed is not None:
        base["structured"] = parsed

    if task_def.hybrid_pattern == "AI_OPTIONS_HUMAN_PICKS":
        # Expect options format; wrap if needed
        if parsed and isinstance(parsed, list):
            base["options"] = parsed
        elif parsed and isinstance(parsed, dict) and "options" in parsed:
            base["options"] = parsed["options"]
        base["output_type"] = "options"
    elif task_def.hybrid_pattern == "AI_DRAFTS_HUMAN_REVIEWS":
        base["output_type"] = "draft"
    elif task_def.hybrid_pattern == "HUMAN_INITIATES_AI_COMPLETES":
        base["output_type"] = "completion"
    elif task_def.classification == "AI":
        base["output_type"] = "final"
    else:
        base["output_type"] = "general"

    return base


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


# --- Error categorization and recovery helpers ---

def _categorize_error(error: Exception) -> str:
    """Categorize an exception into one of: API_ERROR, CONTEXT_ERROR, PARSING_ERROR, UNKNOWN.

    - API_ERROR: rate limits, timeouts, network failures, Anthropic API errors
    - CONTEXT_ERROR: missing required inputs, empty context
    - PARSING_ERROR: malformed AI output, JSON decode failures
    - UNKNOWN: everything else
    """
    error_str = str(error).lower()

    # API_ERROR — rate limit, timeout, connection, Anthropic SDK errors
    api_indicators = [
        "rate limit", "rate_limit", "429", "timeout", "timed out",
        "connection", "api error", "api failed", "retries",
        "overloaded", "503", "502", "500", "service unavailable",
    ]
    if any(indicator in error_str for indicator in api_indicators):
        return "API_ERROR"

    # Check by exception type for Anthropic SDK errors
    error_type_name = type(error).__name__.lower()
    if any(t in error_type_name for t in ["api", "rate", "timeout", "connection", "http"]):
        return "API_ERROR"

    # CONTEXT_ERROR — missing inputs, empty prompts, key errors from context building
    context_indicators = [
        "missing", "not found", "required", "empty", "none",
        "no context", "key error", "keyerror", "not configured",
    ]
    if isinstance(error, (KeyError, AttributeError)):
        return "CONTEXT_ERROR"
    if any(indicator in error_str for indicator in context_indicators):
        return "CONTEXT_ERROR"

    # PARSING_ERROR — JSON decode, value errors from parsing
    parsing_indicators = [
        "json", "decode", "parse", "unexpected token", "invalid literal",
        "unterminated string", "expecting value",
    ]
    if isinstance(error, (json.JSONDecodeError, ValueError)):
        return "PARSING_ERROR"
    if any(indicator in error_str for indicator in parsing_indicators):
        return "PARSING_ERROR"

    return "UNKNOWN"


def _detect_missing_context(context: dict) -> list[str]:
    """Inspect the context dict and report what critical pieces are missing or empty."""
    missing = []

    if not context.get("project_name"):
        missing.append("project_name: Project information is not available.")
    if not context.get("client_name"):
        missing.append("client_name: Client name is not set on the project.")
    if not context.get("answered_questions"):
        missing.append(
            "answered_questions: No answered discovery questions found. "
            "Complete the questionnaire phase before running this task."
        )
    if not context.get("prior_documents"):
        missing.append(
            "prior_documents: No prior documents (DRAFT/FINAL/EXPORTED) exist. "
            "Earlier phase documents may need to be generated first."
        )
    if not context.get("task_name"):
        missing.append("task_name: Task definition name is missing.")

    if not missing:
        missing.append(
            "Unable to determine specific missing context. "
            "Review the task's input requirements and ensure all prerequisites are met."
        )

    return missing


async def _call_claude_for_task_with_format_hint(
    task_def: TaskDefinition,
    agent_def: AgentDefinition,
    context: dict,
) -> ClaudeResponse:
    """Retry a Claude call with an explicit JSON format instruction appended.

    Used as a recovery mechanism when the first call produced a PARSING_ERROR.
    """
    if agent_def.system_prompt:
        system_prompt = agent_def.system_prompt
    else:
        system_prompt = f"""You are an expert Adobe Analytics to CJA migration consultant.
You are completing the task: {task_def.name}
Classification: {task_def.classification}
{f'Hybrid pattern: {task_def.hybrid_pattern}' if task_def.hybrid_pattern else ''}

Project: {context.get('project_name', '')} for client {context.get('client_name', '')}

Use the context provided to generate high-quality, specific output for this task.
Return structured JSON output."""

    # Add explicit format instruction
    system_prompt += """

IMPORTANT: Your response MUST be valid JSON and nothing else.
Do NOT wrap the JSON in markdown code fences.
Do NOT include any text before or after the JSON object.
The response must start with { and end with }.
Example format: {"result": "...", "sections": [...], "metadata": {...}}"""

    # Build user prompt with all context
    user_prompt_parts = ["Context:"]

    if context.get("answered_questions"):
        user_prompt_parts.append(f"- Answered questions: {json.dumps(context['answered_questions'][:10])}")
    if context.get("prior_documents"):
        user_prompt_parts.append(f"- Prior documents: {json.dumps(context['prior_documents'][:5])}")
    if context.get("cross_project_knowledge"):
        user_prompt_parts.append(f"- Cross-project knowledge: {json.dumps(context['cross_project_knowledge'][:5])}")
    if context.get("additional_input"):
        user_prompt_parts.append(f"- Additional input: {json.dumps(context['additional_input'])}")

    user_prompt_parts.append(f"\nGenerate the output for: {task_def.name}")
    if task_def.source_type:
        user_prompt_parts.append(f"Source type: {task_def.source_type}")
    user_prompt_parts.append("\nRemember: respond with ONLY a valid JSON object.")

    user_prompt = "\n".join(user_prompt_parts)

    return await call_claude(
        system_prompt, user_prompt,
        temperature=max(agent_def.temperature - 0.1, 0.0),
        max_tokens=agent_def.max_tokens_per_call,
        model=agent_def.model,
    )


async def _notify_and_audit_failure(
    db: AsyncSession,
    project_id: uuid.UUID,
    task_instance: TaskInstance,
    task_def: TaskDefinition,
    error_details: dict,
) -> None:
    """Send architect notification and log audit entry for a task failure."""
    error_type = error_details.get("error_type", "UNKNOWN")
    status = task_instance.status

    if error_type == "API_ERROR":
        body = (
            f"AI service error while processing '{task_def.name}'. "
            f"Task set to {status}. Will auto-retry."
        )
    elif error_type == "CONTEXT_ERROR":
        missing = error_details.get("missing_context", [])
        missing_summary = "; ".join(missing[:3]) if missing else "unknown"
        body = (
            f"AI could not complete '{task_def.name}' due to missing context: "
            f"{missing_summary}"
        )
    elif error_type == "PARSING_ERROR":
        body = (
            f"AI output for '{task_def.name}' could not be parsed. "
            f"Automatic retry {'succeeded' if status != 'BLOCKED' else 'also failed'}."
        )
    else:
        body = (
            f"AI could not complete '{task_def.name}'. "
            f"Manual intervention required. Error type: {error_type}"
        )

    await _notify_architects(
        db, project_id,
        title=f"AI action failed: {task_def.name}",
        body=body,
        action_url=f"/projects/{project_id}/tasks/{task_instance.id}",
    )

    await log_audit(
        db, actor_type="AI", actor_id=None,
        action="AI_ACTION_FAILED", entity_type="task_instance",
        entity_id=task_instance.id, project_id=project_id,
        new_value={
            "error": error_details.get("error", "")[:500],
            "error_type": error_type,
            "task_status": status,
        },
    )
