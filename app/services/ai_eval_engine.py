"""AI Eval Engine — runs automated evaluations against agent outputs using Claude.

Per spec: EvalDefinition/EvalResult score every agent output.
"""

import json
import logging
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentExecution
from app.models.eval import EvalDefinition
from app.models.task import TaskInstance
from app.services.claude_client import call_claude
from app.services.eval import get_applicable_evals, record_eval_result

logger = logging.getLogger(__name__)


async def run_evals_for_execution(
    db: AsyncSession,
    execution: AgentExecution,
    task_instance: TaskInstance | None,
    output: dict,
) -> list[dict]:
    """Run all applicable evals for an agent execution."""
    # Get the agent name
    from app.models.agent import AgentDefinition
    agent_result = await db.execute(
        select(AgentDefinition).where(AgentDefinition.id == execution.agent_definition_id)
    )
    agent_def = agent_result.scalar_one_or_none()
    if not agent_def:
        return []

    applicable_evals = await get_applicable_evals(db, agent_def.name)
    if not applicable_evals:
        return []

    results = []
    for eval_def in applicable_evals:
        try:
            result = await _run_single_eval(
                db, eval_def, execution, task_instance, output
            )
            results.append(result)
        except Exception as e:
            logger.warning(f"Eval '{eval_def.name}' failed for execution {execution.id}: {e}")

    # Update execution with eval scores
    if results:
        execution.eval_scores = {
            r["eval_name"]: {"score": r["score"], "passed": r["passed"]}
            for r in results
        }
        await db.flush()

    return results


async def _run_single_eval(
    db: AsyncSession,
    eval_def: EvalDefinition,
    execution: AgentExecution,
    task_instance: TaskInstance | None,
    output: dict,
) -> dict:
    """Run a single eval against an agent output."""
    if eval_def.eval_type == "AI_JUDGE":
        return await _run_ai_judge_eval(db, eval_def, execution, task_instance, output)
    elif eval_def.eval_type == "HEURISTIC":
        return _run_heuristic_eval(eval_def, output)
    else:
        return _run_heuristic_eval(eval_def, output)


async def _run_ai_judge_eval(
    db: AsyncSession,
    eval_def: EvalDefinition,
    execution: AgentExecution,
    task_instance: TaskInstance | None,
    output: dict,
) -> dict:
    """Use Claude as a judge to evaluate agent output."""
    system_prompt = eval_def.eval_prompt or f"""You are an AI quality evaluator.
Evaluate the following output on a scale of 0.0 to 1.0.
Criteria: {eval_def.description or eval_def.name}

Return JSON: {{"score": 0.0-1.0, "reasoning": "...", "issues": ["..."]}}"""

    output_str = json.dumps(output)[:3000]
    user_prompt = f"Evaluate this agent output:\n{output_str}"

    response = await call_claude(system_prompt, user_prompt, temperature=0.1)

    # Parse eval result
    score = 0.5
    details = {"raw": response.content}
    try:
        clean = response.content.strip()
        if "```json" in clean:
            start = clean.index("```json") + 7
            end = clean.index("```", start)
            clean = clean[start:end].strip()
        parsed = json.loads(clean)
        score = float(parsed.get("score", 0.5))
        details = parsed
    except (json.JSONDecodeError, ValueError):
        pass

    passed = score >= eval_def.threshold

    await record_eval_result(
        db,
        eval_definition_id=eval_def.id,
        agent_execution_id=execution.id,
        task_instance_id=task_instance.id if task_instance else None,
        project_id=execution.project_id,
        score=score,
        passed=passed,
        details=details,
        eval_tokens_used=response.tokens_input + response.tokens_output,
        eval_cost_usd=Decimal(str(response.cost_usd)),
    )

    return {
        "eval_name": eval_def.name,
        "eval_type": "AI_JUDGE",
        "score": score,
        "passed": passed,
        "details": details,
    }


def _run_heuristic_eval(eval_def: EvalDefinition, output: dict) -> dict:
    """Run a simple heuristic eval (no AI call needed)."""
    score = 0.5

    # Check if output has structured content
    if "structured" in output:
        score += 0.2
    if "raw" in output and len(output.get("raw", "")) > 200:
        score += 0.1
    if output.get("raw", "") and len(output.get("raw", "")) > 500:
        score += 0.1

    # Check for common quality indicators
    raw = output.get("raw", "")
    if isinstance(raw, str):
        if len(raw) < 50:
            score -= 0.3
        if "error" in raw.lower() or "sorry" in raw.lower():
            score -= 0.2

    score = max(0.0, min(1.0, score))
    passed = score >= eval_def.threshold

    return {
        "eval_name": eval_def.name,
        "eval_type": "HEURISTIC",
        "score": score,
        "passed": passed,
        "details": {"method": "heuristic", "output_length": len(raw) if isinstance(raw, str) else 0},
    }
