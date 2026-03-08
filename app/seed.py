"""
Seed data for APEX v2 — Phase 1: Foundation.

Seeds: roles (with RBAC permissions), phase definitions, task definitions,
source definitions, document templates, agent definitions, eval definitions.
"""
import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, engine, Base
from app.core.rbac import RoleName, DEFAULT_ROLE_PERMISSIONS
from app.core.security import hash_password
from app.models.role import Role
from app.models.organization import Organization
from app.models.user import User
from app.models.phase import PhaseDefinition
from app.models.task import TaskDefinition
from app.models.source import SourceDefinition
from app.models.document import DocumentTemplate
from app.models.agent import AgentDefinition
from app.models.eval import EvalDefinition


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
ROLES = [
    {"name": RoleName.ARCHITECT, "description": "Solution Architect — full project authority", "is_system_role": True},
    {"name": RoleName.ENGINEER, "description": "Implementation Engineer — task execution", "is_system_role": True},
    {"name": RoleName.CLIENT, "description": "Client stakeholder — approvals and answers", "is_system_role": True},
    {"name": RoleName.ADOBE_LAUNCH_ADVISORY, "description": "Adobe Launch Advisory — Launch/Tags guidance", "is_system_role": True},
]

# ---------------------------------------------------------------------------
# Phase Definitions (Section 4.2)
# ---------------------------------------------------------------------------
PHASE_DEFINITIONS = [
    {"phase_number": 1, "name": "Discovery & BRD", "description": "Stakeholder interviews, current-state audit, BRD generation", "gate_criteria": {"brd_approved": False, "all_questions_answered": False, "sources_identified": False}},
    {"phase_number": 2, "name": "Solution Design", "description": "SDR creation, schema design, data layer mapping", "gate_criteria": {"sdr_approved": False, "schemas_designed": False, "implementation_plan_approved": False}},
    {"phase_number": 3, "name": "Build — Pilot Layer", "description": "Pilot environment setup, initial schemas, XDM validation", "gate_criteria": {"pilot_schemas_validated": False, "pilot_data_flowing": False, "pilot_review_passed": False}},
    {"phase_number": 4, "name": "Build — Dev Layer", "description": "Dev environment replication, data layer implementation", "gate_criteria": {"dev_schemas_validated": False, "dev_data_flowing": False, "dev_review_passed": False}},
    {"phase_number": 5, "name": "Build — Prod Layer", "description": "Production deployment, client sign-off", "gate_criteria": {"prod_schemas_validated": False, "prod_data_flowing": False, "client_signoff": False, "architect_signoff": False}},
    {"phase_number": 6, "name": "Validation & QA", "description": "Data validation, calculated metrics verification, report reconciliation", "gate_criteria": {"data_validation_passed": False, "metrics_reconciled": False, "qa_report_approved": False}},
    {"phase_number": 7, "name": "Go-Live & Hypercare", "description": "Production cutover, monitoring, hypercare support", "gate_criteria": {"go_live_checklist_complete": False, "monitoring_active": False, "hypercare_plan_approved": False}},
]

# ---------------------------------------------------------------------------
# Task Definitions (Section 4.3 – key tasks per phase)
# ---------------------------------------------------------------------------
TASK_DEFINITIONS = [
    # Phase 1: Discovery & BRD
    {"phase_number": 1, "name": "Stakeholder Interview Orchestration", "classification": "HYBRID", "hybrid_pattern": "AI_DRAFTS_HUMAN_REVIEWS", "default_owner_role": "ARCHITECT", "sort_order": 1, "description": "AI generates interview questions, architect conducts interviews"},
    {"phase_number": 1, "name": "Current-State Analytics Audit", "classification": "HYBRID", "hybrid_pattern": "AI_DRAFTS_HUMAN_REVIEWS", "default_owner_role": "ARCHITECT", "sort_order": 2, "description": "AI audits existing AA implementation, architect validates"},
    {"phase_number": 1, "name": "BRD Generation", "classification": "HYBRID", "hybrid_pattern": "AI_DRAFTS_HUMAN_REVIEWS", "default_owner_role": "ARCHITECT", "sort_order": 3, "maps_to_document": "BRD", "description": "AI generates BRD from discovery inputs, architect reviews"},
    {"phase_number": 1, "name": "Source Identification", "classification": "HYBRID", "hybrid_pattern": "AI_OPTIONS_HUMAN_PICKS", "default_owner_role": "ARCHITECT", "sort_order": 4, "description": "AI identifies data sources, architect confirms"},
    {"phase_number": 1, "name": "Client Questionnaire Distribution", "classification": "HYBRID", "hybrid_pattern": "AI_DRAFTS_HUMAN_REVIEWS", "default_owner_role": "ARCHITECT", "secondary_owner_role": "CLIENT", "sort_order": 5, "description": "AI generates questions, sends to client for answers"},
    # Phase 2: Solution Design
    {"phase_number": 2, "name": "SDR Creation", "classification": "HYBRID", "hybrid_pattern": "AI_DRAFTS_HUMAN_REVIEWS", "default_owner_role": "ARCHITECT", "sort_order": 1, "maps_to_document": "SDR", "description": "AI generates Solution Design Reference"},
    {"phase_number": 2, "name": "XDM Schema Design", "classification": "AI", "default_owner_role": "ARCHITECT", "sort_order": 2, "description": "AI designs XDM schemas based on BRD and source analysis"},
    {"phase_number": 2, "name": "Data Layer Mapping", "classification": "AI", "default_owner_role": "ENGINEER", "sort_order": 3, "description": "AI maps AA variables to CJA schema fields"},
    {"phase_number": 2, "name": "Implementation Plan", "classification": "HYBRID", "hybrid_pattern": "AI_DRAFTS_HUMAN_REVIEWS", "default_owner_role": "ARCHITECT", "sort_order": 4, "maps_to_document": "Implementation Plan", "description": "AI drafts implementation timeline and plan"},
    # Phase 3: Build — Pilot
    {"phase_number": 3, "name": "Pilot Schema Deployment", "classification": "AI", "default_owner_role": "ENGINEER", "sort_order": 1, "source_type": "WEB_MOBILE", "description": "AI deploys schemas to pilot environment"},
    {"phase_number": 3, "name": "Pilot Dataset Creation", "classification": "AI", "default_owner_role": "ENGINEER", "sort_order": 2, "description": "AI creates datasets in pilot"},
    {"phase_number": 3, "name": "Pilot Connection Setup", "classification": "AI", "default_owner_role": "ENGINEER", "sort_order": 3, "description": "AI configures connections in pilot"},
    {"phase_number": 3, "name": "Pilot Data Validation", "classification": "HYBRID", "hybrid_pattern": "AI_DRAFTS_HUMAN_REVIEWS", "default_owner_role": "ARCHITECT", "sort_order": 4, "description": "AI validates pilot data, architect reviews"},
    # Phase 4: Build — Dev
    {"phase_number": 4, "name": "Dev Schema Deployment", "classification": "AI", "default_owner_role": "ENGINEER", "sort_order": 1, "description": "Replicate pilot schemas to dev"},
    {"phase_number": 4, "name": "Dev Data Layer Implementation", "classification": "HYBRID", "hybrid_pattern": "AI_DRAFTS_HUMAN_REVIEWS", "default_owner_role": "ENGINEER", "sort_order": 2, "description": "Implement data layer changes"},
    {"phase_number": 4, "name": "Dev Validation", "classification": "HYBRID", "hybrid_pattern": "AI_DRAFTS_HUMAN_REVIEWS", "default_owner_role": "ARCHITECT", "sort_order": 3, "description": "Validate dev environment"},
    # Phase 5: Build — Prod
    {"phase_number": 5, "name": "Prod Schema Deployment", "classification": "AI", "default_owner_role": "ENGINEER", "sort_order": 1, "description": "Deploy schemas to production"},
    {"phase_number": 5, "name": "Prod Data Flow Activation", "classification": "HYBRID", "hybrid_pattern": "HUMAN_INITIATES_AI_COMPLETES", "default_owner_role": "ARCHITECT", "sort_order": 2, "description": "Activate production data flows"},
    {"phase_number": 5, "name": "Client Production Sign-off", "classification": "MANUAL", "default_owner_role": "CLIENT", "sort_order": 3, "maps_to_gate_item": "client_signoff", "description": "Client reviews and signs off on production"},
    {"phase_number": 5, "name": "Architect Production Sign-off", "classification": "MANUAL", "default_owner_role": "ARCHITECT", "sort_order": 4, "maps_to_gate_item": "architect_signoff", "description": "Architect reviews and signs off on production"},
    # Phase 6: Validation & QA
    {"phase_number": 6, "name": "Data Validation Report", "classification": "AI", "default_owner_role": "ENGINEER", "sort_order": 1, "maps_to_document": "Validation Report", "description": "AI generates data validation report"},
    {"phase_number": 6, "name": "Calculated Metrics Reconciliation", "classification": "HYBRID", "hybrid_pattern": "AI_DRAFTS_HUMAN_REVIEWS", "default_owner_role": "ARCHITECT", "sort_order": 2, "description": "Reconcile calculated metrics between AA and CJA"},
    {"phase_number": 6, "name": "QA Report Generation", "classification": "AI", "default_owner_role": "ENGINEER", "sort_order": 3, "maps_to_document": "QA Report", "description": "AI generates QA report"},
    # Phase 7: Go-Live
    {"phase_number": 7, "name": "Go-Live Checklist", "classification": "HYBRID", "hybrid_pattern": "AI_DRAFTS_HUMAN_REVIEWS", "default_owner_role": "ARCHITECT", "sort_order": 1, "maps_to_document": "Go-Live Checklist", "description": "AI generates go-live checklist"},
    {"phase_number": 7, "name": "Monitoring Setup", "classification": "AI", "default_owner_role": "ENGINEER", "sort_order": 2, "description": "Configure monitoring dashboards"},
    {"phase_number": 7, "name": "Hypercare Plan", "classification": "HYBRID", "hybrid_pattern": "AI_DRAFTS_HUMAN_REVIEWS", "default_owner_role": "ARCHITECT", "sort_order": 3, "maps_to_document": "Hypercare Plan", "description": "AI generates hypercare support plan"},
]

# ---------------------------------------------------------------------------
# Source Definitions (Section 5)
# ---------------------------------------------------------------------------
SOURCE_DEFINITIONS = [
    {"name": "Web & Mobile (AA)", "source_type": "WEB_MOBILE", "is_mandatory": True, "business_type": "ALL", "requires_client_admin": False, "description": "Primary Adobe Analytics web/mobile data source", "implementation_owner_role": "ENGINEER", "ai_scope": "Full schema design, dataset creation, connection setup across all layers"},
    {"name": "Salesforce CRM", "source_type": "SALESFORCE", "is_mandatory": False, "business_type": "B2B", "requires_client_admin": True, "description": "Salesforce CRM integration for B2B clients", "implementation_owner_role": "ENGINEER", "client_dependencies": ["api_credentials", "field_mapping_approval"], "ai_scope": "Schema design and field mapping; client provides credentials"},
    {"name": "RainFocus Events", "source_type": "RAINFOCUS", "is_mandatory": False, "business_type": "BUSINESS_SPECIFIC", "requires_client_admin": True, "description": "RainFocus event data integration", "implementation_owner_role": "ENGINEER", "client_dependencies": ["api_credentials", "event_catalog"], "ai_scope": "Schema design; client provides API access"},
    {"name": "Marketo MAP", "source_type": "MARKETO", "is_mandatory": False, "business_type": "B2B", "requires_client_admin": True, "description": "Marketo marketing automation integration", "implementation_owner_role": "ENGINEER", "client_dependencies": ["api_credentials", "program_mapping"], "ai_scope": "Schema design and lead mapping; client provides credentials"},
    {"name": "6sense ABM", "source_type": "SIXSENSE", "is_mandatory": False, "business_type": "B2B", "requires_client_admin": True, "description": "6sense account-based marketing integration", "implementation_owner_role": "ENGINEER", "client_dependencies": ["api_credentials", "segment_definitions"], "ai_scope": "Schema design and account mapping; client provides access"},
]

# ---------------------------------------------------------------------------
# Document Templates (Section 4.5)
# ---------------------------------------------------------------------------
DOCUMENT_TEMPLATES = [
    {"name": "BRD", "phase_number": 1, "output_format": "DOCX", "template_structure": {"sections": ["Executive Summary", "Current State Analysis", "Business Requirements", "Data Sources", "Success Metrics", "Timeline", "Risks & Dependencies"]}, "ai_generation_prompt": "Generate a comprehensive BRD for Adobe Analytics to CJA migration based on discovery inputs and stakeholder interviews."},
    {"name": "SDR", "phase_number": 2, "output_format": "XLSX", "template_structure": {"sections": ["Schema Overview", "Field Mappings", "Calculated Metrics", "Segments", "Data Views", "Connections"]}, "ai_generation_prompt": "Generate a Solution Design Reference mapping all AA variables, events, and segments to CJA XDM schema fields."},
    {"name": "Implementation Plan", "phase_number": 2, "output_format": "DOCX", "template_structure": {"sections": ["Timeline", "Resource Allocation", "Phase Dependencies", "Risk Mitigation", "Testing Strategy"]}, "ai_generation_prompt": "Generate an implementation plan based on the SDR and project requirements."},
    {"name": "Validation Report", "phase_number": 6, "output_format": "XLSX", "template_structure": {"sections": ["Data Completeness", "Field Accuracy", "Metric Reconciliation", "Anomalies", "Recommendations"]}, "ai_generation_prompt": "Generate a data validation report comparing AA and CJA data."},
    {"name": "QA Report", "phase_number": 6, "output_format": "DOCX", "template_structure": {"sections": ["Test Cases", "Results", "Defects", "Resolution Status", "Sign-off"]}, "ai_generation_prompt": "Generate a QA report covering all validation test cases."},
    {"name": "Go-Live Checklist", "phase_number": 7, "output_format": "DOCX", "template_structure": {"sections": ["Pre-Go-Live", "Go-Live Day", "Post-Go-Live", "Rollback Plan"]}, "ai_generation_prompt": "Generate a go-live readiness checklist."},
    {"name": "Hypercare Plan", "phase_number": 7, "output_format": "DOCX", "template_structure": {"sections": ["Support Model", "Escalation Path", "Monitoring", "Knowledge Transfer", "Timeline"]}, "ai_generation_prompt": "Generate a hypercare support plan for post-migration."},
]

# ---------------------------------------------------------------------------
# Agent Definitions (Section 6 – 8 agents)
# ---------------------------------------------------------------------------
AGENT_DEFINITIONS = [
    {"name": "orchestrator", "display_name": "Orchestrator Agent", "role_description": "Coordinates all other agents, manages workflow sequencing, and handles task routing", "model": "claude-sonnet-4-20250514", "temperature": 0.2, "tools": ["task_router", "agent_invoker", "dependency_checker"]},
    {"name": "discovery", "display_name": "Discovery Agent", "role_description": "Generates stakeholder interview questions, analyzes current AA implementation, identifies gaps", "model": "claude-sonnet-4-20250514", "temperature": 0.3, "tools": ["question_generator", "aa_analyzer", "gap_identifier"], "input_sources": {"questionnaire_responses": True, "aa_report_suites": True}},
    {"name": "solution", "display_name": "Solution Design Agent", "role_description": "Creates SDR, designs XDM schemas, maps AA variables to CJA fields", "model": "claude-sonnet-4-20250514", "temperature": 0.2, "tools": ["schema_designer", "field_mapper", "sdr_generator"], "input_sources": {"brd": True, "source_definitions": True}},
    {"name": "schema", "display_name": "Schema Agent", "role_description": "Generates and validates XDM schemas, manages schema lifecycle across layers", "model": "claude-sonnet-4-20250514", "temperature": 0.1, "tools": ["schema_generator", "schema_validator", "layer_manager"]},
    {"name": "document", "display_name": "Document Agent", "role_description": "Generates project documents (BRD, SDR, reports) from templates and project data", "model": "claude-sonnet-4-20250514", "temperature": 0.4, "tools": ["document_generator", "template_filler", "export_formatter"]},
    {"name": "validation", "display_name": "Validation Agent", "role_description": "Validates data accuracy, reconciles metrics between AA and CJA", "model": "claude-sonnet-4-20250514", "temperature": 0.1, "tools": ["data_validator", "metric_reconciler", "anomaly_detector"]},
    {"name": "gate", "display_name": "Gate Agent", "role_description": "Evaluates gate criteria, determines phase readiness, generates gate reports", "model": "claude-sonnet-4-20250514", "temperature": 0.1, "tools": ["gate_evaluator", "readiness_checker", "gate_reporter"]},
    {"name": "improvement", "display_name": "Improvement Agent", "role_description": "Analyzes feedback patterns, proposes prompt improvements, learns from corrections", "model": "claude-sonnet-4-20250514", "temperature": 0.5, "tools": ["feedback_analyzer", "prompt_optimizer", "knowledge_extractor"]},
]

# ---------------------------------------------------------------------------
# Eval Definitions (Section 7)
# ---------------------------------------------------------------------------
EVAL_DEFINITIONS = [
    {"name": "Completeness Check", "eval_type": "COMPLETENESS", "description": "Checks if AI output covers all required sections/fields", "threshold": 0.8, "applies_to": {"agents": ["discovery", "solution", "document"]}, "eval_prompt": "Evaluate whether the output covers all required sections. Score 1.0 if complete, reduce proportionally for missing sections."},
    {"name": "Accuracy Check", "eval_type": "ACCURACY", "description": "Validates factual accuracy of AI output against source data", "threshold": 0.9, "applies_to": {"agents": ["solution", "schema", "validation"]}, "eval_prompt": "Evaluate the factual accuracy of the output against the provided source data. Flag any discrepancies."},
    {"name": "Schema Validity", "eval_type": "SCHEMA_VALIDITY", "description": "Validates XDM schema compliance and field type correctness", "threshold": 0.95, "applies_to": {"agents": ["schema"]}, "eval_prompt": "Validate that the generated schema complies with XDM standards. Check field types, required fields, and naming conventions."},
    {"name": "Consistency Check", "eval_type": "CONSISTENCY", "description": "Checks output consistency with previous project outputs", "threshold": 0.7, "applies_to": {"agents": ["solution", "document"]}, "eval_prompt": "Compare the output against previous outputs for this project to ensure consistency in terminology, field names, and design decisions."},
    {"name": "Quality Score", "eval_type": "QUALITY", "description": "Overall quality assessment of AI output", "threshold": 0.7, "applies_to": {"agents": ["discovery", "solution", "document", "validation"]}, "eval_prompt": "Rate the overall quality of the output considering clarity, completeness, accuracy, and actionability."},
]


async def seed_roles(db: AsyncSession) -> dict[str, uuid.UUID]:
    """Seed system roles with RBAC permissions. Returns {role_name: role_id}."""
    role_ids = {}
    for role_data in ROLES:
        existing = await db.execute(select(Role).where(Role.name == role_data["name"]))
        role = existing.scalar_one_or_none()
        if role:
            role.permissions = DEFAULT_ROLE_PERMISSIONS[role_data["name"]]
            role.description = role_data["description"]
            role_ids[role_data["name"]] = role.id
        else:
            role = Role(
                name=role_data["name"],
                description=role_data["description"],
                permissions=DEFAULT_ROLE_PERMISSIONS[role_data["name"]],
                is_system_role=role_data["is_system_role"],
            )
            db.add(role)
            await db.flush()
            role_ids[role_data["name"]] = role.id
    return role_ids


async def seed_default_org_and_admin(db: AsyncSession, role_ids: dict[str, uuid.UUID]) -> None:
    """Seed default organization and admin user."""
    existing = await db.execute(select(Organization).where(Organization.name == "APEX Default"))
    org = existing.scalar_one_or_none()
    if not org:
        org = Organization(name="APEX Default")
        db.add(org)
        await db.flush()

    existing_user = await db.execute(select(User).where(User.email == "admin@apex.dev"))
    admin = existing_user.scalar_one_or_none()
    if not admin:
        admin = User(
            organization_id=org.id,
            email="admin@apex.dev",
            name="APEX Admin",
            hashed_password=hash_password("admin123"),
        )
        db.add(admin)
        await db.flush()


async def seed_phase_definitions(db: AsyncSession) -> dict[int, uuid.UUID]:
    """Seed phase definitions. Returns {phase_number: phase_def_id}."""
    phase_ids = {}
    for pd in PHASE_DEFINITIONS:
        existing = await db.execute(select(PhaseDefinition).where(PhaseDefinition.phase_number == pd["phase_number"]))
        phase = existing.scalar_one_or_none()
        if phase:
            phase.name = pd["name"]
            phase.description = pd["description"]
            phase.gate_criteria = pd["gate_criteria"]
            phase_ids[pd["phase_number"]] = phase.id
        else:
            phase = PhaseDefinition(
                name=pd["name"],
                phase_number=pd["phase_number"],
                description=pd["description"],
                gate_criteria=pd["gate_criteria"],
            )
            db.add(phase)
            await db.flush()
            phase_ids[pd["phase_number"]] = phase.id
    return phase_ids


async def seed_task_definitions(db: AsyncSession, phase_ids: dict[int, uuid.UUID]) -> None:
    """Seed task definitions linked to phase definitions."""
    for td in TASK_DEFINITIONS:
        phase_def_id = phase_ids[td["phase_number"]]
        existing = await db.execute(
            select(TaskDefinition).where(
                TaskDefinition.phase_definition_id == phase_def_id,
                TaskDefinition.name == td["name"],
            )
        )
        if existing.scalar_one_or_none():
            continue
        task = TaskDefinition(
            phase_definition_id=phase_def_id,
            name=td["name"],
            description=td.get("description"),
            classification=td["classification"],
            hybrid_pattern=td.get("hybrid_pattern"),
            default_owner_role=td["default_owner_role"],
            secondary_owner_role=td.get("secondary_owner_role"),
            source_type=td.get("source_type"),
            sort_order=td["sort_order"],
            maps_to_document=td.get("maps_to_document"),
            maps_to_gate_item=td.get("maps_to_gate_item"),
        )
        db.add(task)
    await db.flush()


async def seed_source_definitions(db: AsyncSession) -> None:
    """Seed source definitions."""
    for sd in SOURCE_DEFINITIONS:
        existing = await db.execute(select(SourceDefinition).where(SourceDefinition.name == sd["name"]))
        if existing.scalar_one_or_none():
            continue
        source = SourceDefinition(
            name=sd["name"],
            source_type=sd["source_type"],
            is_mandatory=sd["is_mandatory"],
            business_type=sd["business_type"],
            requires_client_admin=sd["requires_client_admin"],
            description=sd.get("description"),
            implementation_owner_role=sd.get("implementation_owner_role"),
            client_dependencies=sd.get("client_dependencies"),
            ai_scope=sd.get("ai_scope"),
        )
        db.add(source)
    await db.flush()


async def seed_document_templates(db: AsyncSession, phase_ids: dict[int, uuid.UUID]) -> None:
    """Seed document templates linked to phases."""
    for dt in DOCUMENT_TEMPLATES:
        existing = await db.execute(select(DocumentTemplate).where(DocumentTemplate.name == dt["name"]))
        if existing.scalar_one_or_none():
            continue
        template = DocumentTemplate(
            name=dt["name"],
            phase_definition_id=phase_ids[dt["phase_number"]],
            output_format=dt["output_format"],
            template_structure=dt.get("template_structure"),
            ai_generation_prompt=dt.get("ai_generation_prompt"),
        )
        db.add(template)
    await db.flush()


async def seed_agent_definitions(db: AsyncSession) -> None:
    """Seed agent definitions."""
    for ad in AGENT_DEFINITIONS:
        existing = await db.execute(select(AgentDefinition).where(AgentDefinition.name == ad["name"]))
        if existing.scalar_one_or_none():
            continue
        agent = AgentDefinition(
            name=ad["name"],
            display_name=ad.get("display_name"),
            role_description=ad.get("role_description"),
            model=ad.get("model"),
            temperature=ad.get("temperature", 0.3),
            tools=ad.get("tools"),
            input_sources=ad.get("input_sources"),
        )
        db.add(agent)
    await db.flush()


async def seed_eval_definitions(db: AsyncSession) -> None:
    """Seed eval definitions."""
    for ed in EVAL_DEFINITIONS:
        existing = await db.execute(select(EvalDefinition).where(EvalDefinition.name == ed["name"]))
        if existing.scalar_one_or_none():
            continue
        eval_def = EvalDefinition(
            name=ed["name"],
            eval_type=ed["eval_type"],
            description=ed.get("description"),
            eval_prompt=ed.get("eval_prompt"),
            threshold=ed.get("threshold", 0.7),
            applies_to=ed.get("applies_to"),
        )
        db.add(eval_def)
    await db.flush()


async def run_seed():
    """Run all seed functions."""
    async with async_session() as db:
        try:
            print("Seeding roles...")
            role_ids = await seed_roles(db)

            print("Seeding default org and admin...")
            await seed_default_org_and_admin(db, role_ids)

            print("Seeding phase definitions...")
            phase_ids = await seed_phase_definitions(db)

            print("Seeding task definitions...")
            await seed_task_definitions(db, phase_ids)

            print("Seeding source definitions...")
            await seed_source_definitions(db)

            print("Seeding document templates...")
            await seed_document_templates(db, phase_ids)

            print("Seeding agent definitions...")
            await seed_agent_definitions(db)

            print("Seeding eval definitions...")
            await seed_eval_definitions(db)

            await db.commit()
            print("Seed complete!")
        except Exception:
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(run_seed())
