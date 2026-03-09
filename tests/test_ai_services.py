"""Tests for AI service internals: confidence evaluation, output parsing,
heuristic eval, question parsing, cost recording, and error categorization.

All Claude API calls are mocked so no API key is required.
"""

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.claude_client import ClaudeResponse


# ---------------------------------------------------------------------------
# _evaluate_confidence (from ai_executor)
# ---------------------------------------------------------------------------


class TestEvaluateConfidence:
    def test_evaluate_confidence_base(self):
        """Base confidence is 0.7 with moderate context."""
        from app.services.ai_executor import _evaluate_confidence

        response = ClaudeResponse(
            content="A" * 200,
            tokens_input=100,
            tokens_output=200,
            cost_usd=0.001,
            model_used="claude-sonnet-4-20250514",
        )
        task_def = MagicMock()
        task_def.name = "Test Task"
        context = {
            "answered_questions": [{"q": "a"}] * 3,
            "prior_documents": [],
            "prior_feedback": [],
            "cross_project_knowledge": [],
        }

        score = _evaluate_confidence(response, task_def, context)
        assert 0.0 <= score <= 1.0
        # With 3 answered questions (not >=5, not 0), no other boosts
        assert score == pytest.approx(0.7, abs=0.01)

    def test_evaluate_confidence_high_context(self):
        """Score increases with rich context."""
        from app.services.ai_executor import _evaluate_confidence

        response = ClaudeResponse(
            content="A" * 500,
            tokens_input=200,
            tokens_output=400,
            cost_usd=0.002,
            model_used="claude-sonnet-4-20250514",
        )
        task_def = MagicMock()
        task_def.name = "Test"
        context = {
            "answered_questions": [{"q": "a"}] * 6,  # +0.1
            "prior_documents": [{"d": "x"}] * 3,  # +0.05
            "prior_feedback": [{"quality_score": 0.9}] * 2,  # +0.05
            "cross_project_knowledge": [{"k": "v"}] * 4,  # +0.05
            "additional_input": {"extra": "data"},  # +0.1
        }

        score = _evaluate_confidence(response, task_def, context)
        # 0.7 + 0.1 + 0.05 + 0.05 + 0.05 + 0.1 = 1.05 -> clamped to 1.0
        assert score == pytest.approx(1.0, abs=0.01)

    def test_evaluate_confidence_low_with_short_response(self):
        """Very short response lowers confidence."""
        from app.services.ai_executor import _evaluate_confidence

        response = ClaudeResponse(
            content="short",
            tokens_input=10,
            tokens_output=5,
            cost_usd=0.0001,
            model_used="claude-sonnet-4-20250514",
        )
        task_def = MagicMock()
        task_def.name = "Test"
        context = {"answered_questions": [], "prior_documents": []}

        score = _evaluate_confidence(response, task_def, context)
        # 0.7 - 0.15 (no questions) - 0.15 (short response) = 0.4
        assert score == pytest.approx(0.4, abs=0.01)


# ---------------------------------------------------------------------------
# _parse_ai_output (from ai_executor)
# ---------------------------------------------------------------------------


class TestParseAIOutput:
    def test_parse_ai_output_json_block(self):
        """Parses JSON wrapped in code fences."""
        from app.services.ai_executor import _parse_ai_output

        task_def = MagicMock()
        task_def.hybrid_pattern = "AI_DRAFTS_HUMAN_REVIEWS"
        task_def.classification = "HYBRID"

        content = '```json\n{"result": "success", "items": [1, 2]}\n```'
        output = _parse_ai_output(content, task_def)

        assert "raw" in output
        assert "structured" in output
        assert output["structured"]["result"] == "success"
        assert output["output_type"] == "draft"

    def test_parse_ai_output_options_pattern(self):
        """AI_OPTIONS_HUMAN_PICKS produces options format."""
        from app.services.ai_executor import _parse_ai_output

        task_def = MagicMock()
        task_def.hybrid_pattern = "AI_OPTIONS_HUMAN_PICKS"
        task_def.classification = "HYBRID"

        content = '```json\n[{"option": "A"}, {"option": "B"}]\n```'
        output = _parse_ai_output(content, task_def)

        assert output["output_type"] == "options"
        assert "options" in output
        assert len(output["options"]) == 2

    def test_parse_ai_output_plain_text(self):
        """Non-JSON content is captured in raw field."""
        from app.services.ai_executor import _parse_ai_output

        task_def = MagicMock()
        task_def.hybrid_pattern = None
        task_def.classification = "AI"

        content = "This is plain text output with no JSON."
        output = _parse_ai_output(content, task_def)

        assert output["raw"] == content
        assert "structured" not in output
        assert output["output_type"] == "final"

    def test_parse_ai_output_ai_classification(self):
        """AI classification produces 'final' output type."""
        from app.services.ai_executor import _parse_ai_output

        task_def = MagicMock()
        task_def.hybrid_pattern = None
        task_def.classification = "AI"

        content = '{"data": "value"}'
        output = _parse_ai_output(content, task_def)
        assert output["output_type"] == "final"
        assert output["structured"]["data"] == "value"


# ---------------------------------------------------------------------------
# _run_heuristic_eval (from ai_eval_engine)
# ---------------------------------------------------------------------------


class TestHeuristicEval:
    def test_heuristic_eval_with_structured_output(self):
        """Heuristic eval awards points for structured content."""
        from app.services.ai_eval_engine import _run_heuristic_eval

        eval_def = MagicMock()
        eval_def.name = "test_eval"
        eval_def.threshold = 0.5
        eval_def.applies_to = {"domain": "general"}

        output = {
            "raw": "This is a long enough output with substantial content " * 20,
            "structured": {"key1": "v1", "key2": "v2", "key3": "v3"},
        }

        result = _run_heuristic_eval(eval_def, output)
        assert result["eval_type"] == "HEURISTIC"
        assert result["eval_name"] == "test_eval"
        assert 0.0 <= result["score"] <= 1.0
        assert isinstance(result["passed"], bool)

    def test_heuristic_eval_schema_domain(self):
        """Schema domain eval checks for XDM content."""
        from app.services.ai_eval_engine import _run_heuristic_eval

        eval_def = MagicMock()
        eval_def.name = "schema_eval"
        eval_def.threshold = 0.3
        eval_def.applies_to = {"domain": "schema"}

        output = {
            "raw": "xdm schema with /path/to/field definitions and fieldgroup mappings",
            "structured": {"xdm_fields": ["/path/to/field1", "/path/to/field2"]},
        }

        result = _run_heuristic_eval(eval_def, output)
        assert result["score"] > 0.5
        assert result["passed"] is True

    def test_heuristic_eval_error_penalty(self):
        """Error language in output reduces score."""
        from app.services.ai_eval_engine import _run_heuristic_eval

        eval_def = MagicMock()
        eval_def.name = "error_test"
        eval_def.threshold = 0.7
        eval_def.applies_to = {"domain": "general"}

        output = {
            "raw": "sorry, I was unable to complete this task due to an error",
            "structured": {},
        }

        result = _run_heuristic_eval(eval_def, output)
        assert result["score"] < 0.5
        assert result["passed"] is False


# ---------------------------------------------------------------------------
# _parse_questions (from ai_questions_engine)
# ---------------------------------------------------------------------------


class TestParseQuestions:
    def test_parse_questions_json_array(self):
        """Parses a JSON array of question objects from code fences."""
        from app.services.ai_questions_engine import _parse_questions

        content = """```json
[
    {"question_text": "What analytics tools are in use?", "question_type": "STRUCTURED"},
    {"question_text": "How many report suites?", "question_type": "STRUCTURED"}
]
```"""
        questions = _parse_questions(content)
        assert len(questions) == 2
        assert questions[0]["question_text"] == "What analytics tools are in use?"

    def test_parse_questions_bare_json(self):
        """Parses a bare JSON array without code fences."""
        from app.services.ai_questions_engine import _parse_questions

        content = '[{"question_text": "Q1", "question_type": "FREE_TEXT"}]'
        questions = _parse_questions(content)
        assert len(questions) == 1

    def test_parse_questions_invalid_json(self):
        """Returns empty list on invalid JSON."""
        from app.services.ai_questions_engine import _parse_questions

        content = "This is not JSON at all"
        questions = _parse_questions(content)
        assert questions == []

    def test_parse_questions_embedded_array(self):
        """Extracts JSON array even when surrounded by text."""
        from app.services.ai_questions_engine import _parse_questions

        content = 'Here are the questions:\n[{"question_text": "Test?", "question_type": "STRUCTURED"}]\nEnd.'
        questions = _parse_questions(content)
        assert len(questions) == 1
        assert questions[0]["question_text"] == "Test?"


# ---------------------------------------------------------------------------
# cost recording (from services.cost)
# ---------------------------------------------------------------------------


class TestCostRecording:
    async def test_cost_recording(
        self,
        db_session: AsyncSession,
        sample_project,
        sample_agent_def,
    ):
        """record_cost creates a CostTracking record in the database."""
        from app.models.agent import AgentExecution
        from app.services.cost import record_cost

        execution = AgentExecution(
            id=uuid.uuid4(),
            agent_definition_id=sample_agent_def.id,
            project_id=sample_project.id,
            triggered_by="SYSTEM",
            status="COMPLETED",
            tokens_input=100,
            tokens_output=50,
            cost_usd=Decimal("0.001"),
        )
        db_session.add(execution)
        await db_session.flush()

        record = await record_cost(
            db_session,
            project_id=sample_project.id,
            agent_execution_id=execution.id,
            tokens_input=100,
            tokens_output=50,
            cost_usd=Decimal("0.001050"),
            is_rework=False,
            is_eval=False,
        )

        assert record.id is not None
        assert record.project_id == sample_project.id
        assert record.tokens_input == 100
        assert record.tokens_output == 50
        assert float(record.cost_usd) == pytest.approx(0.001050, abs=1e-6)

    async def test_cost_recording_rework(
        self,
        db_session: AsyncSession,
        sample_project,
        sample_agent_def,
    ):
        """record_cost marks rework entries correctly."""
        from app.models.agent import AgentExecution
        from app.services.cost import record_cost

        execution = AgentExecution(
            id=uuid.uuid4(),
            agent_definition_id=sample_agent_def.id,
            project_id=sample_project.id,
            triggered_by="SYSTEM",
            status="COMPLETED",
            tokens_input=200,
            tokens_output=100,
            cost_usd=Decimal("0.002"),
        )
        db_session.add(execution)
        await db_session.flush()

        record = await record_cost(
            db_session,
            project_id=sample_project.id,
            agent_execution_id=execution.id,
            tokens_input=200,
            tokens_output=100,
            cost_usd=Decimal("0.002100"),
            is_rework=True,
            rework_reason="Task re-execution",
        )

        assert record.is_rework is True
        assert record.rework_reason == "Task re-execution"


# ---------------------------------------------------------------------------
# _categorize_error (from ai_executor)
# ---------------------------------------------------------------------------


class TestErrorCategorization:
    def test_categorize_api_error(self):
        """Rate limit / timeout errors are classified as API_ERROR."""
        from app.services.ai_executor import _categorize_error

        assert _categorize_error(RuntimeError("rate limit exceeded")) == "API_ERROR"
        assert _categorize_error(RuntimeError("timeout waiting for response")) == "API_ERROR"
        assert _categorize_error(RuntimeError("Claude API failed after 3 retries")) == "API_ERROR"

    def test_categorize_context_error(self):
        """Missing context errors are classified as CONTEXT_ERROR."""
        from app.services.ai_executor import _categorize_error

        assert _categorize_error(KeyError("missing_field")) == "CONTEXT_ERROR"
        assert _categorize_error(AttributeError("NoneType has no attribute")) == "CONTEXT_ERROR"
        assert _categorize_error(RuntimeError("required field not found")) == "CONTEXT_ERROR"

    def test_categorize_parsing_error(self):
        """JSON parse errors are classified as PARSING_ERROR."""
        from app.services.ai_executor import _categorize_error

        assert _categorize_error(json.JSONDecodeError("msg", "doc", 0)) == "PARSING_ERROR"
        assert _categorize_error(ValueError("invalid literal")) == "PARSING_ERROR"

    def test_categorize_unknown_error(self):
        """Unrecognized errors are classified as UNKNOWN."""
        from app.services.ai_executor import _categorize_error

        assert _categorize_error(TypeError("something weird")) == "UNKNOWN"
        assert _categorize_error(RuntimeError("completely unexpected")) == "UNKNOWN"


# ---------------------------------------------------------------------------
# get_project_costs (from services.cost)
# ---------------------------------------------------------------------------


class TestGetProjectCosts:
    async def test_get_project_costs(
        self,
        db_session: AsyncSession,
        sample_project,
        sample_agent_def,
    ):
        """record_cost + get_project_costs aggregates correctly."""
        from app.models.agent import AgentExecution
        from app.services.cost import record_cost, get_project_costs

        execution = AgentExecution(
            id=uuid.uuid4(),
            agent_definition_id=sample_agent_def.id,
            project_id=sample_project.id,
            triggered_by="SYSTEM",
            status="COMPLETED",
            tokens_input=100,
            tokens_output=50,
            cost_usd=Decimal("0.001"),
        )
        db_session.add(execution)
        await db_session.flush()

        await record_cost(
            db_session,
            project_id=sample_project.id,
            agent_execution_id=execution.id,
            tokens_input=100,
            tokens_output=50,
            cost_usd=Decimal("0.002"),
        )
        await record_cost(
            db_session,
            project_id=sample_project.id,
            agent_execution_id=execution.id,
            tokens_input=200,
            tokens_output=100,
            cost_usd=Decimal("0.003"),
            is_rework=True,
            rework_reason="Re-execution",
        )

        costs = await get_project_costs(db_session, sample_project.id)
        assert costs["total_calls"] == 2
        assert costs["total_tokens_input"] == 300
        assert costs["total_tokens_output"] == 150
        assert costs["total_cost_usd"] == pytest.approx(0.005, abs=1e-6)
        assert costs["rework_calls"] == 1
        assert costs["rework_cost_usd"] == pytest.approx(0.003, abs=1e-6)
        assert costs["rework_percentage"] == pytest.approx(60.0, abs=0.1)

    async def test_get_project_costs_empty(
        self,
        db_session: AsyncSession,
        sample_project,
    ):
        """get_project_costs returns zeros when no costs exist."""
        from app.services.cost import get_project_costs

        costs = await get_project_costs(db_session, sample_project.id)
        assert costs["total_calls"] == 0
        assert costs["total_cost_usd"] == 0.0
        assert costs["rework_percentage"] == 0.0


# ---------------------------------------------------------------------------
# task dependency engine (from services.task)
# ---------------------------------------------------------------------------


class TestTaskDependencyEngine:
    async def test_check_dependencies_all_met(
        self,
        db_session: AsyncSession,
        sample_project,
        sample_phase_instance,
        sample_task_def,
        sample_user,
    ):
        """check_dependencies returns all_met=True when all deps are COMPLETED."""
        from app.models.task import TaskInstance
        from app.services.task import check_dependencies

        dep1 = TaskInstance(
            id=uuid.uuid4(),
            task_definition_id=sample_task_def.id,
            phase_instance_id=sample_phase_instance.id,
            project_id=sample_project.id,
            assigned_by="AI",
            status="COMPLETED",
            trust_level="SUPERVISED",
            classification="AI",
            priority="MEDIUM",
            completed_at=datetime.now(timezone.utc),
            completed_by=sample_user.id,
        )
        dep2 = TaskInstance(
            id=uuid.uuid4(),
            task_definition_id=sample_task_def.id,
            phase_instance_id=sample_phase_instance.id,
            project_id=sample_project.id,
            assigned_by="AI",
            status="COMPLETED",
            trust_level="SUPERVISED",
            classification="AI",
            priority="MEDIUM",
            completed_at=datetime.now(timezone.utc),
            completed_by=sample_user.id,
        )
        db_session.add_all([dep1, dep2])
        await db_session.flush()

        task = TaskInstance(
            id=uuid.uuid4(),
            task_definition_id=sample_task_def.id,
            phase_instance_id=sample_phase_instance.id,
            project_id=sample_project.id,
            assigned_by="AI",
            status="NOT_STARTED",
            trust_level="SUPERVISED",
            classification="AI",
            priority="MEDIUM",
            depends_on=[str(dep1.id), str(dep2.id)],
        )
        db_session.add(task)
        await db_session.flush()

        result = await check_dependencies(db_session, task)
        assert result["all_met"] is True
        assert result["total"] == 2
        assert result["completed"] == 2
        assert result["blocking"] == []

    async def test_check_dependencies_partially_met(
        self,
        db_session: AsyncSession,
        sample_project,
        sample_phase_instance,
        sample_task_def,
        sample_user,
    ):
        """check_dependencies returns blocking tasks when not all deps are done."""
        from app.models.task import TaskInstance
        from app.services.task import check_dependencies

        dep_done = TaskInstance(
            id=uuid.uuid4(),
            task_definition_id=sample_task_def.id,
            phase_instance_id=sample_phase_instance.id,
            project_id=sample_project.id,
            assigned_by="AI",
            status="COMPLETED",
            trust_level="SUPERVISED",
            classification="AI",
            priority="MEDIUM",
            completed_at=datetime.now(timezone.utc),
            completed_by=sample_user.id,
        )
        dep_pending = TaskInstance(
            id=uuid.uuid4(),
            task_definition_id=sample_task_def.id,
            phase_instance_id=sample_phase_instance.id,
            project_id=sample_project.id,
            assigned_by="AI",
            status="IN_PROGRESS",
            trust_level="SUPERVISED",
            classification="AI",
            priority="MEDIUM",
        )
        db_session.add_all([dep_done, dep_pending])
        await db_session.flush()

        task = TaskInstance(
            id=uuid.uuid4(),
            task_definition_id=sample_task_def.id,
            phase_instance_id=sample_phase_instance.id,
            project_id=sample_project.id,
            assigned_by="AI",
            status="NOT_STARTED",
            trust_level="SUPERVISED",
            classification="AI",
            priority="MEDIUM",
            depends_on=[str(dep_done.id), str(dep_pending.id)],
        )
        db_session.add(task)
        await db_session.flush()

        result = await check_dependencies(db_session, task)
        assert result["all_met"] is False
        assert result["total"] == 2
        assert result["completed"] == 1
        assert str(dep_pending.id) in result["blocking"]


# ---------------------------------------------------------------------------
# gate criterion validators (from services.phase)
# ---------------------------------------------------------------------------


class TestGateCriterionValidators:
    async def test_all_tasks_completed_criterion(
        self,
        db_session: AsyncSession,
        sample_phase_instance,
        sample_task_instance,
        sample_user,
    ):
        """evaluate_gate checks 'all_tasks_completed' criterion."""
        from app.services.phase import evaluate_gate

        # Task not completed yet
        result = await evaluate_gate(db_session, sample_phase_instance.id)
        assert result["gate_passed"] is False
        assert result["gate_results"]["all_tasks_completed"]["passed"] is False

        # Complete the task
        sample_task_instance.status = "COMPLETED"
        sample_task_instance.completed_at = datetime.now(timezone.utc)
        sample_task_instance.completed_by = sample_user.id
        await db_session.flush()

        result = await evaluate_gate(db_session, sample_phase_instance.id)
        assert result["gate_results"]["all_tasks_completed"]["passed"] is True
        assert result["gate_passed"] is True

    async def test_gate_with_no_tasks(
        self,
        db_session: AsyncSession,
        sample_project,
        sample_phase_def,
    ):
        """evaluate_gate fails when phase has no tasks at all."""
        from app.models.phase import PhaseInstance
        from app.services.phase import evaluate_gate

        empty_phase = PhaseInstance(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            phase_definition_id=sample_phase_def.id,
            status="IN_PROGRESS",
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(empty_phase)
        await db_session.flush()

        result = await evaluate_gate(db_session, empty_phase.id)
        assert result["total_tasks"] == 0
        assert result["gate_passed"] is False


# ---------------------------------------------------------------------------
# document template validation (from ai_documents_engine)
# ---------------------------------------------------------------------------


class TestDocumentTemplateValidation:
    def test_validate_against_template_all_present(self):
        """_validate_against_template reports valid when all sections present."""
        from app.services.ai_documents_engine import _validate_against_template

        template = MagicMock()
        template.template_structure = {"sections": ["overview", "architecture"]}

        content = {"sections": {"overview": "...", "architecture": "..."}}
        result = _validate_against_template(content, template)
        assert result["valid"] is True
        assert result["missing_sections"] == []
        assert result["coverage_ratio"] == 1.0

    def test_validate_against_template_missing_section(self):
        """_validate_against_template detects missing sections."""
        from app.services.ai_documents_engine import _validate_against_template

        template = MagicMock()
        template.template_structure = {"sections": ["overview", "architecture", "timeline"]}

        content = {"sections": {"overview": "..."}}
        result = _validate_against_template(content, template)
        assert result["valid"] is False
        assert "architecture" in result["missing_sections"]
        assert "timeline" in result["missing_sections"]
        assert result["coverage_ratio"] == pytest.approx(1 / 3, abs=0.01)

    def test_validate_against_template_no_structure(self):
        """_validate_against_template skips validation when template has no structure."""
        from app.services.ai_documents_engine import _validate_against_template

        template = MagicMock()
        template.template_structure = None

        content = {"sections": {"anything": "..."}}
        result = _validate_against_template(content, template)
        assert result["valid"] is True
        assert result["coverage_ratio"] == 1.0

    def test_fill_missing_sections(self):
        """_fill_missing_sections adds placeholders for missing sections."""
        from app.services.ai_documents_engine import _fill_missing_sections

        content = {"sections": {"overview": "Content here"}}
        result = _fill_missing_sections(content, ["architecture", "timeline"])
        assert "architecture" in result["sections"]
        assert "timeline" in result["sections"]
        assert "pending" in result["sections"]["architecture"]["content"].lower()

    def test_get_expected_section_keys_list_format(self):
        """_get_expected_section_keys handles list-of-strings format."""
        from app.services.ai_documents_engine import _get_expected_section_keys

        template = MagicMock()
        template.template_structure = {"sections": ["overview", "architecture"]}
        keys = _get_expected_section_keys(template)
        assert keys == ["overview", "architecture"]

    def test_get_expected_section_keys_dict_format(self):
        """_get_expected_section_keys handles dict format."""
        from app.services.ai_documents_engine import _get_expected_section_keys

        template = MagicMock()
        template.template_structure = {
            "sections": {"overview": {"required": True}, "details": {"required": False}}
        }
        keys = _get_expected_section_keys(template)
        assert "overview" in keys
        assert "details" in keys


# ---------------------------------------------------------------------------
# _detect_missing_context (from ai_executor)
# ---------------------------------------------------------------------------


class TestDetectMissingContext:
    def test_detect_missing_context_all_missing(self):
        """Reports missing fields when context is empty."""
        from app.services.ai_executor import _detect_missing_context

        context = {}
        missing = _detect_missing_context(context)
        assert any("project_name" in m for m in missing)
        assert any("client_name" in m for m in missing)
        assert any("answered_questions" in m for m in missing)

    def test_detect_missing_context_all_present(self):
        """Returns fallback message when all required fields are present."""
        from app.services.ai_executor import _detect_missing_context

        context = {
            "project_name": "Test",
            "client_name": "Acme",
            "answered_questions": [{"q": "a"}],
            "prior_documents": [{"d": "x"}],
            "task_name": "Task 1",
        }
        missing = _detect_missing_context(context)
        assert any("Unable to determine" in m for m in missing)
