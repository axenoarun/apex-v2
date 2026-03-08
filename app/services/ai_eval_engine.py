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
from app.services.cost import record_cost

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

    eval_cost = Decimal(str(response.cost_usd))
    eval_tokens = response.tokens_input + response.tokens_output

    await record_eval_result(
        db,
        eval_definition_id=eval_def.id,
        agent_execution_id=execution.id,
        task_instance_id=task_instance.id if task_instance else None,
        project_id=execution.project_id,
        score=score,
        passed=passed,
        details=details,
        eval_tokens_used=eval_tokens,
        eval_cost_usd=eval_cost,
    )

    # Record cost via CostTracking for AI_JUDGE evals
    await record_cost(
        db,
        project_id=execution.project_id,
        agent_execution_id=execution.id,
        tokens_input=response.tokens_input,
        tokens_output=response.tokens_output,
        cost_usd=eval_cost,
        task_instance_id=task_instance.id if task_instance else None,
        is_eval=True,
        eval_definition_id=eval_def.id,
    )

    return {
        "eval_name": eval_def.name,
        "eval_type": "AI_JUDGE",
        "score": score,
        "passed": passed,
        "details": details,
    }


def _run_heuristic_eval(eval_def: EvalDefinition, output: dict) -> dict:
    """Run a domain-aware heuristic eval (no AI call needed).

    Scoring is based on the eval_def.applies_to metadata which indicates
    the domain: schema, document, validation, or general.
    """
    applies_to = eval_def.applies_to or {}
    domain = applies_to.get("domain", "general")
    raw = output.get("raw", "")
    structured = output.get("structured", {})
    sections = output.get("sections", {})
    breakdown: dict = {"method": "heuristic", "domain": domain, "checks": {}}

    score = 0.5  # Base score

    # ------------------------------------------------------------------
    # 1. Universal checks — expected keys present?
    # ------------------------------------------------------------------
    expected_keys = applies_to.get("expected_keys", [])
    if expected_keys:
        present_keys = set(structured.keys()) if isinstance(structured, dict) else set()
        # Also check top-level output keys
        present_keys |= set(output.keys())
        matched = [k for k in expected_keys if k in present_keys]
        key_ratio = len(matched) / len(expected_keys) if expected_keys else 1.0
        score += 0.2 * key_ratio
        breakdown["checks"]["expected_keys"] = {
            "expected": expected_keys,
            "matched": matched,
            "ratio": round(key_ratio, 3),
        }
    else:
        # Fallback: reward having structured content at all
        if structured:
            score += 0.15
            breakdown["checks"]["has_structured"] = True
        else:
            breakdown["checks"]["has_structured"] = False

    # ------------------------------------------------------------------
    # 2. Domain-specific checks
    # ------------------------------------------------------------------
    if domain == "schema":
        score, breakdown = _heuristic_schema(score, breakdown, raw, structured, output)
    elif domain == "document":
        score, breakdown = _heuristic_document(score, breakdown, raw, sections, output)
    elif domain == "validation":
        score, breakdown = _heuristic_validation(score, breakdown, raw, structured, output)
    else:
        # General quality signals
        score, breakdown = _heuristic_general(score, breakdown, raw, structured)

    # ------------------------------------------------------------------
    # 3. Penalty for error-like outputs
    # ------------------------------------------------------------------
    raw_lower = raw.lower() if isinstance(raw, str) else ""
    if "error" in raw_lower or "sorry" in raw_lower or "unable to" in raw_lower:
        score -= 0.2
        breakdown["checks"]["error_language_detected"] = True

    score = max(0.0, min(1.0, round(score, 3)))
    passed = score >= eval_def.threshold

    breakdown["final_score"] = score
    breakdown["threshold"] = eval_def.threshold
    breakdown["passed"] = passed

    return {
        "eval_name": eval_def.name,
        "eval_type": "HEURISTIC",
        "score": score,
        "passed": passed,
        "details": breakdown,
    }


# --- Domain-specific heuristic helpers ---

def _heuristic_schema(
    score: float, breakdown: dict, raw: str, structured: dict, output: dict
) -> tuple[float, dict]:
    """Schema-related eval: check for XDM-like field paths."""
    content_str = json.dumps(output) if output else raw

    # Check for XDM-like field paths (keys with "/" separators or "xdm" content)
    has_xdm = "xdm" in content_str.lower()
    has_path_separators = "/" in content_str and content_str.count("/") >= 3
    has_field_definitions = any(
        k in content_str.lower()
        for k in ["datatype", "data_type", "fieldgroup", "field_group", "schema"]
    )

    xdm_score = 0.0
    if has_xdm:
        xdm_score += 0.1
    if has_path_separators:
        xdm_score += 0.1
    if has_field_definitions:
        xdm_score += 0.1

    score += xdm_score
    breakdown["checks"]["schema"] = {
        "has_xdm_references": has_xdm,
        "has_path_separators": has_path_separators,
        "has_field_definitions": has_field_definitions,
        "schema_score_contribution": round(xdm_score, 3),
    }
    return score, breakdown


def _heuristic_document(
    score: float, breakdown: dict, raw: str, sections: dict | list, output: dict
) -> tuple[float, dict]:
    """Document-related eval: check section coverage and word counts."""
    # Determine section list
    section_items: list[dict] = []
    if isinstance(sections, dict):
        section_items = [{"key": k, "content": v} for k, v in sections.items()]
    elif isinstance(sections, list):
        section_items = sections if sections else []

    section_count = len(section_items)
    min_word_count = 30  # minimum words per section to be considered substantive

    sections_with_content = 0
    section_word_counts = {}
    for item in section_items:
        content_text = ""
        if isinstance(item, dict):
            content_text = str(item.get("content", ""))
        elif isinstance(item, str):
            content_text = item
        wc = len(content_text.split())
        key = item.get("key", item.get("title", f"section_{sections_with_content}")) if isinstance(item, dict) else str(sections_with_content)
        section_word_counts[key] = wc
        if wc >= min_word_count:
            sections_with_content += 1

    if section_count > 0:
        coverage = sections_with_content / section_count
        score += 0.2 * coverage
    else:
        coverage = 0.0
        # Check raw content as fallback
        if isinstance(raw, str) and len(raw.split()) > 100:
            score += 0.1
            coverage = 0.5

    breakdown["checks"]["document"] = {
        "total_sections": section_count,
        "sections_with_sufficient_content": sections_with_content,
        "min_word_count_threshold": min_word_count,
        "section_word_counts": section_word_counts,
        "coverage_ratio": round(coverage, 3),
    }
    return score, breakdown


def _heuristic_validation(
    score: float, breakdown: dict, raw: str, structured: dict, output: dict
) -> tuple[float, dict]:
    """Validation-related eval: check for metric comparisons, variance calculations."""
    content_str = json.dumps(output) if output else raw
    content_lower = content_str.lower()

    has_metrics = any(
        k in content_lower
        for k in ["metric", "kpi", "measure", "count", "total", "average", "sum"]
    )
    has_comparisons = any(
        k in content_lower
        for k in ["comparison", "delta", "difference", "before", "after", "baseline"]
    )
    has_variance = any(
        k in content_lower
        for k in ["variance", "deviation", "tolerance", "threshold", "margin", "percent"]
    )
    has_pass_fail = any(
        k in content_lower
        for k in ["pass", "fail", "valid", "invalid", "status", "result"]
    )

    validation_score = 0.0
    if has_metrics:
        validation_score += 0.08
    if has_comparisons:
        validation_score += 0.08
    if has_variance:
        validation_score += 0.08
    if has_pass_fail:
        validation_score += 0.06

    score += validation_score
    breakdown["checks"]["validation"] = {
        "has_metrics": has_metrics,
        "has_comparisons": has_comparisons,
        "has_variance_calculations": has_variance,
        "has_pass_fail_indicators": has_pass_fail,
        "validation_score_contribution": round(validation_score, 3),
    }
    return score, breakdown


def _heuristic_general(
    score: float, breakdown: dict, raw: str, structured: dict
) -> tuple[float, dict]:
    """General quality heuristics for untyped evals."""
    raw_len = len(raw) if isinstance(raw, str) else 0

    if raw_len < 50:
        score -= 0.2
    elif raw_len > 500:
        score += 0.1

    if structured and isinstance(structured, dict) and len(structured) >= 3:
        score += 0.1

    breakdown["checks"]["general"] = {
        "raw_length": raw_len,
        "structured_key_count": len(structured) if isinstance(structured, dict) else 0,
    }
    return score, breakdown
