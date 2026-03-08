"""
Seed data for APEX v2 — Enhanced CJA Migration Automation.

Seeds: roles (with RBAC permissions), phase definitions, task definitions (70-task matrix),
source definitions, document templates, agent definitions (with system prompts),
eval definitions.
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
# Phase Definitions — 7 phases with rich gate criteria
# ---------------------------------------------------------------------------
PHASE_DEFINITIONS = [
    {
        "phase_number": 1,
        "name": "Discovery & BRD",
        "description": "Stakeholder interviews, current-state audit, BRD generation",
        "gate_criteria": {
            "all_questions_answered": False,
            "sdr_first_draft_complete": False,
            "intent_document_approved": False,
            "current_state_documented": False,
            "stakeholders_identified": False,
            "workshop_completed": False,
            "workshop_notes_captured": False,
            "sources_identified": False,
        },
    },
    {
        "phase_number": 2,
        "name": "Solution Design",
        "description": "SDR creation, schema design, identity resolution, data layer mapping",
        "gate_criteria": {
            "schema_design_approved": False,
            "xdm_field_groups_selected": False,
            "identity_strategy_approved": False,
            "data_sources_inventoried": False,
            "connection_strategy_defined": False,
            "dataview_strategy_defined": False,
            "migration_approach_documented": False,
            "solution_design_document_approved": False,
            "client_review_complete": False,
        },
    },
    {
        "phase_number": 3,
        "name": "Build — Pilot Layer",
        "description": "Pilot environment setup, initial schemas, XDM validation, test ingestion",
        "gate_criteria": {
            "field_mapping_complete": False,
            "data_dictionary_generated": False,
            "schema_json_created": False,
            "pilot_schemas_validated": False,
            "pilot_data_flowing": False,
            "error_analysis_complete": False,
            "schema_grooming_done": False,
            "pilot_review_passed": False,
            "data_governance_plan_approved": False,
        },
    },
    {
        "phase_number": 4,
        "name": "Build — Dev Layer",
        "description": "Dev environment replication, source-specific connectors, data layer implementation",
        "gate_criteria": {
            "dev_promotion_complete": False,
            "dev_validation_passed": False,
            "source_connectors_configured": False,
            "client_credentials_provided": False,
            "dev_to_prod_signoff": False,
        },
    },
    {
        "phase_number": 5,
        "name": "Build — Prod Layer",
        "description": "CJA connection/dataview creation, production deployment, client sign-off",
        "gate_criteria": {
            "cja_connection_created": False,
            "cja_dataview_created": False,
            "workspace_templates_generated": False,
            "data_verified_in_dataview": False,
            "prod_data_flowing": False,
            "client_signoff": False,
            "architect_signoff": False,
        },
    },
    {
        "phase_number": 6,
        "name": "Validation & QA",
        "description": "Data validation, calculated metrics verification, report reconciliation, UAT",
        "gate_criteria": {
            "test_cases_generated": False,
            "data_validation_passed": False,
            "aa_cja_comparison_complete": False,
            "identity_resolution_validated": False,
            "workspace_reports_validated": False,
            "client_uat_complete": False,
            "bugs_resolved": False,
            "validation_report_approved": False,
        },
    },
    {
        "phase_number": 7,
        "name": "Go-Live & Hypercare",
        "description": "Production cutover, monitoring, hypercare support, knowledge transfer",
        "gate_criteria": {
            "go_live_runbook_approved": False,
            "go_live_checklist_complete": False,
            "production_cutover_done": False,
            "client_training_complete": False,
            "monitoring_active": False,
            "hypercare_issues_triaged": False,
            "hypercare_report_generated": False,
            "knowledge_transfer_complete": False,
            "project_closure_signoff": False,
        },
    },
]

# ---------------------------------------------------------------------------
# Task Definitions — 70-task automation matrix mapped to 7 phases
#
# Format per tuple:
#   (sort_order, name, classification, hybrid_pattern, default_owner_role,
#    secondary_owner_role, default_trust_level, source_type, depends_on_sort_orders)
# ---------------------------------------------------------------------------
TASK_DEFINITIONS_BY_PHASE = {
    # -----------------------------------------------------------------------
    # Phase 1: Discovery & BRD (10 tasks)
    # -----------------------------------------------------------------------
    1: [
        (1, "Client questionnaire generation", "AI", None, "ENGINEER", None, "SUPERVISED", None, []),
        (2, "Client questionnaire collection", "MANUAL", None, "CLIENT", None, "SUPERVISED", None, [1]),
        (3, "AA report suite analysis", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", None, []),
        (4, "SDR first draft", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", None, [2, 3]),
        (5, "Intent Document draft", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ARCHITECT", None, "SUPERVISED", None, [2]),
        (6, "Current state documentation", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ARCHITECT", None, "SUPERVISED", None, [2, 3]),
        (7, "Stakeholder identification", "MANUAL", None, "CLIENT", None, "SUPERVISED", None, []),
        (8, "Adobe Planning Workshop", "MANUAL", None, "ARCHITECT", None, "SUPERVISED", None, [5]),
        (9, "Workshop notes capture", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ARCHITECT", None, "SUPERVISED", None, [8]),
        (10, "Phase 1 gate check", "AI", None, "ARCHITECT", None, "FULL_AUTO", None, [4, 5, 6, 7, 8, 9]),
    ],
    # -----------------------------------------------------------------------
    # Phase 2: Solution Design (10 tasks)
    # -----------------------------------------------------------------------
    2: [
        (1, "Schema design proposal", "HYBRID", "AI_OPTIONS_HUMAN_PICKS", "ARCHITECT", None, "SUPERVISED", None, []),
        (2, "XDM field group selection", "HYBRID", "AI_OPTIONS_HUMAN_PICKS", "ARCHITECT", None, "SUPERVISED", None, [1]),
        (3, "Identity resolution strategy", "HYBRID", "AI_OPTIONS_HUMAN_PICKS", "ARCHITECT", None, "SUPERVISED", None, []),
        (4, "Data source inventory", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", None, []),
        (5, "Connection strategy design", "MANUAL", None, "ARCHITECT", None, "SUPERVISED", None, [1, 4]),
        (6, "Dataview strategy design", "MANUAL", None, "ARCHITECT", None, "SUPERVISED", None, [1, 4]),
        (7, "Migration approach documentation", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ARCHITECT", None, "SUPERVISED", None, [1, 3, 4]),
        (8, "Solution design document", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ARCHITECT", None, "SUPERVISED", None, [1, 2, 3, 5, 6, 7]),
        (9, "Client review of solution design", "MANUAL", None, "CLIENT", None, "SUPERVISED", None, [8]),
        (10, "Phase 2 gate check", "AI", None, "ARCHITECT", None, "FULL_AUTO", None, [8, 9]),
    ],
    # -----------------------------------------------------------------------
    # Phase 3: Build — Pilot Layer (14 tasks)
    # -----------------------------------------------------------------------
    3: [
        (1, "Field mapping (AA vars to XDM)", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", None, []),
        (2, "Custom field group design", "HYBRID", "AI_OPTIONS_HUMAN_PICKS", "ARCHITECT", None, "SUPERVISED", None, [1]),
        (3, "Data dictionary generation", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", None, [1, 2]),
        (4, "Schema JSON/definition creation", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", None, [1, 2]),
        (5, "Dataset configuration design", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", None, [4]),
        (6, "Lookup/Profile dataset design", "HYBRID", "AI_OPTIONS_HUMAN_PICKS", "ARCHITECT", None, "SUPERVISED", None, [4]),
        (7, "Data governance/labeling plan", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ARCHITECT", None, "SUPERVISED", None, [3, 4]),
        (8, "Schema creation (pilot)", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", "ALL", [4]),
        (9, "Ingestion pipeline config", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", "ALL", [8]),
        (10, "Test data ingestion trigger", "MANUAL", None, "ENGINEER", None, "SUPERVISED", "ALL", [9]),
        (11, "Error analysis", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", "ALL", [10]),
        (12, "Schema grooming", "HYBRID", "AI_OPTIONS_HUMAN_PICKS", "ENGINEER", None, "SUPERVISED", "ALL", [11]),
        (13, "Pilot review", "MANUAL", None, "ARCHITECT", None, "SUPERVISED", "ALL", [12]),
        (14, "Phase 3 gate check", "AI", None, "ARCHITECT", None, "FULL_AUTO", None, [7, 13]),
    ],
    # -----------------------------------------------------------------------
    # Phase 4: Build — Dev Layer (13 tasks)
    # -----------------------------------------------------------------------
    4: [
        (1, "Dev promotion", "MANUAL", None, "ENGINEER", None, "SUPERVISED", "ALL", []),
        (2, "Dev validation", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", "ALL", [1]),
        (3, "SDK + datastream config", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", "WEB_MOBILE", [1]),
        (4, "Historical backfill pipeline", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", "WEB_MOBILE", [3]),
        (5, "Connector setup (Salesforce)", "MANUAL", None, "ENGINEER", "CLIENT", "SUPERVISED", "SALESFORCE", [1]),
        (6, "SF field mapping", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", "SALESFORCE", [5]),
        (7, "Client-side ETL", "MANUAL", None, "CLIENT", None, "SUPERVISED", None, []),
        (8, "Connector config + mapping (RainFocus)", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", "RAINFOCUS", [1]),
        (9, "Custom field mapping (Marketo)", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", "MARKETO", [1]),
        (10, "Pipeline config (6sense)", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", "SIXSENSE", [1]),
        (11, "Client credential provisioning", "MANUAL", None, "CLIENT", None, "SUPERVISED", "ALL", []),
        (12, "Dev to Prod sign-off", "MANUAL", None, "ARCHITECT", "CLIENT", "SUPERVISED", "ALL", [2]),
        (13, "Phase 4 gate check", "AI", None, "ARCHITECT", None, "FULL_AUTO", None, [2, 12]),
    ],
    # -----------------------------------------------------------------------
    # Phase 5: Build — Prod Layer (8 tasks)
    # -----------------------------------------------------------------------
    5: [
        (1, "CJA connection creation", "MANUAL", None, "ARCHITECT", "ENGINEER", "SUPERVISED", "CJA_SETUP", []),
        (2, "CJA dataview creation", "MANUAL", None, "ARCHITECT", "ENGINEER", "SUPERVISED", "CJA_SETUP", [1]),
        (3, "CJA workspace template generation", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ARCHITECT", None, "SUPERVISED", "CJA_SETUP", [2]),
        (4, "Data verification in dataview", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", "CJA_SETUP", [2]),
        (5, "Production data flow activation", "HYBRID", "HUMAN_INITIATES_AI_COMPLETES", "ARCHITECT", None, "SUPERVISED", None, [1, 2]),
        (6, "Client production sign-off", "MANUAL", None, "CLIENT", None, "SUPERVISED", None, [4, 5]),
        (7, "Architect production sign-off", "MANUAL", None, "ARCHITECT", None, "SUPERVISED", None, [4, 5]),
        (8, "Phase 5 gate check", "AI", None, "ARCHITECT", None, "FULL_AUTO", None, [6, 7]),
    ],
    # -----------------------------------------------------------------------
    # Phase 6: Validation & QA (9 tasks)
    # -----------------------------------------------------------------------
    6: [
        (1, "Test case generation", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", None, []),
        (2, "Data validation execution", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", None, [1]),
        (3, "AA vs CJA data comparison", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", None, [2]),
        (4, "Identity resolution validation", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ARCHITECT", None, "SUPERVISED", None, [2]),
        (5, "Workspace report validation", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ARCHITECT", None, "SUPERVISED", None, [3]),
        (6, "Client UAT coordination", "MANUAL", None, "CLIENT", None, "SUPERVISED", None, [3, 5]),
        (7, "Bug/issue tracking", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", None, [6]),
        (8, "Validation report generation", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ARCHITECT", None, "SUPERVISED", None, [2, 3, 4, 5, 6, 7]),
        (9, "Phase 6 gate check", "AI", None, "ARCHITECT", None, "FULL_AUTO", None, [8]),
    ],
    # -----------------------------------------------------------------------
    # Phase 7: Go-Live & Hypercare (10 tasks)
    # -----------------------------------------------------------------------
    7: [
        (1, "Go-live runbook creation", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ARCHITECT", None, "SUPERVISED", None, []),
        (2, "Go-live checklist validation", "AI", None, "ARCHITECT", None, "FULL_AUTO", None, [1]),
        (3, "Production cutover execution", "MANUAL", None, "ENGINEER", None, "SUPERVISED", None, [2]),
        (4, "Client communication/training", "MANUAL", None, "ARCHITECT", None, "SUPERVISED", None, [3]),
        (5, "Hypercare monitoring setup", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", None, "SUPERVISED", None, [3]),
        (6, "Issue triage during hypercare", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ENGINEER", "ARCHITECT", "SUPERVISED", None, [5]),
        (7, "Hypercare report generation", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ARCHITECT", None, "SUPERVISED", None, [6]),
        (8, "Knowledge transfer documentation", "HYBRID", "AI_DRAFTS_HUMAN_REVIEWS", "ARCHITECT", None, "SUPERVISED", None, [7]),
        (9, "Project closure sign-off", "MANUAL", None, "ARCHITECT", "CLIENT", "SUPERVISED", None, [8]),
        (10, "Phase 7 gate check", "AI", None, "ARCHITECT", None, "FULL_AUTO", None, [9]),
    ],
}

# ---------------------------------------------------------------------------
# Source Definitions — with artifacts, layers, and client_dependencies
# ---------------------------------------------------------------------------
SOURCE_DEFINITIONS = [
    {
        "name": "Web & Mobile (AA)",
        "source_type": "WEB_MOBILE",
        "is_mandatory": True,
        "business_type": "ALL",
        "requires_client_admin": False,
        "description": "Primary Adobe Analytics web/mobile data source — eVars, props, events, page views, visits, visitors",
        "implementation_owner_role": "ENGINEER",
        "client_dependencies": [],
        "ai_scope": "Full schema design, dataset creation, connection setup across all layers. AI handles field mapping from AA variables (eVars, props, events) to XDM schema fields, generates SDK/datastream configurations, and automates historical backfill pipelines.",
        "artifacts": ["SCHEMA", "DATASET", "CONNECTION", "DATASTREAM", "SDK_CONFIG"],
        "layers": ["PILOT", "DEV", "PROD"],
    },
    {
        "name": "Salesforce CRM",
        "source_type": "SALESFORCE",
        "is_mandatory": False,
        "business_type": "B2B",
        "requires_client_admin": True,
        "description": "Salesforce CRM integration for B2B clients — accounts, contacts, opportunities, campaigns",
        "implementation_owner_role": "ENGINEER",
        "client_dependencies": ["api_credentials", "field_mapping_approval", "connected_app_setup", "ip_whitelisting"],
        "ai_scope": "Schema design and field mapping from Salesforce objects to XDM. AI generates connector configuration and validates field type compatibility. Client must provide Connected App credentials and approve field-level access.",
        "artifacts": ["SCHEMA", "DATASET", "CONNECTION", "SOURCE_CONNECTOR"],
        "layers": ["DEV", "PROD"],
    },
    {
        "name": "RainFocus Events",
        "source_type": "RAINFOCUS",
        "is_mandatory": False,
        "business_type": "BUSINESS_SPECIFIC",
        "requires_client_admin": True,
        "description": "RainFocus event data integration — attendee registrations, session attendance, engagement scores",
        "implementation_owner_role": "ENGINEER",
        "client_dependencies": ["api_credentials", "event_catalog", "webhook_endpoint_approval", "data_retention_policy"],
        "ai_scope": "Schema design for event-based XDM. AI maps RainFocus event attributes to ExperienceEvent fields, configures webhook-based ingestion, and validates event deduplication logic.",
        "artifacts": ["SCHEMA", "DATASET", "CONNECTION", "WEBHOOK_CONFIG"],
        "layers": ["DEV", "PROD"],
    },
    {
        "name": "Marketo MAP",
        "source_type": "MARKETO",
        "is_mandatory": False,
        "business_type": "B2B",
        "requires_client_admin": True,
        "description": "Marketo marketing automation integration — leads, programs, email engagement, scoring",
        "implementation_owner_role": "ENGINEER",
        "client_dependencies": ["api_credentials", "program_mapping", "custom_object_definitions", "lead_partition_access"],
        "ai_scope": "Schema design and lead/contact mapping from Marketo to XDM Profile. AI generates program-to-campaign mapping, email interaction event schemas, and lead scoring field configurations.",
        "artifacts": ["SCHEMA", "DATASET", "CONNECTION", "SOURCE_CONNECTOR"],
        "layers": ["DEV", "PROD"],
    },
    {
        "name": "6sense ABM",
        "source_type": "SIXSENSE",
        "is_mandatory": False,
        "business_type": "B2B",
        "requires_client_admin": True,
        "description": "6sense account-based marketing integration — account intent signals, buying stages, segment membership",
        "implementation_owner_role": "ENGINEER",
        "client_dependencies": ["api_credentials", "segment_definitions", "intent_topic_taxonomy", "account_matching_rules"],
        "ai_scope": "Schema design for account-level XDM fields. AI maps 6sense intent signals and buying stage data to B2B account schema, configures batch ingestion pipeline, and validates account-to-profile stitching.",
        "artifacts": ["SCHEMA", "DATASET", "CONNECTION", "BATCH_PIPELINE"],
        "layers": ["DEV", "PROD"],
    },
]

# ---------------------------------------------------------------------------
# Document Templates — with full section structures from v1
# ---------------------------------------------------------------------------
DOCUMENT_TEMPLATES = [
    {
        "name": "SDR",
        "phase_number": 1,
        "output_format": "XLSX",
        "template_structure": {
            "sections": [
                {
                    "id": "sdr_overview",
                    "title": "Schema Overview",
                    "required": True,
                    "fields": ["schema_name", "schema_class", "xdm_version", "tenant_namespace"],
                },
                {
                    "id": "sdr_field_mappings",
                    "title": "Field Mappings",
                    "required": True,
                    "fields": ["aa_variable", "aa_variable_type", "xdm_path", "xdm_data_type", "transformation_rule", "notes"],
                },
                {
                    "id": "sdr_calculated_metrics",
                    "title": "Calculated Metrics",
                    "required": True,
                    "fields": ["metric_name", "aa_formula", "cja_formula", "validation_method"],
                },
                {
                    "id": "sdr_segments",
                    "title": "Segments / Filters",
                    "required": True,
                    "fields": ["segment_name", "aa_definition", "cja_filter_definition", "migration_notes"],
                },
                {
                    "id": "sdr_data_views",
                    "title": "Data Views",
                    "required": True,
                    "fields": ["dataview_name", "included_datasets", "dimension_config", "metric_config", "attribution_settings"],
                },
                {
                    "id": "sdr_connections",
                    "title": "Connections",
                    "required": True,
                    "fields": ["connection_name", "datasets", "backfill_config", "streaming_config"],
                },
            ],
        },
        "ai_generation_prompt": (
            "Generate a comprehensive Solution Design Reference (SDR) for the Adobe Analytics to CJA migration. "
            "Map all AA variables (eVars, props, events, classifications) to XDM schema fields. "
            "Include calculated metric translations, segment-to-filter mappings, and dataview configurations. "
            "Use the client's AA report suite data and questionnaire responses as input. "
            "Ensure every AA variable has a corresponding XDM mapping or is explicitly marked as deprecated."
        ),
    },
    {
        "name": "Intent Document",
        "phase_number": 1,
        "output_format": "DOCX",
        "template_structure": {
            "sections": [
                {
                    "id": "intent_executive_summary",
                    "title": "Executive Summary",
                    "required": True,
                    "fields": ["project_overview", "business_drivers", "expected_outcomes"],
                },
                {
                    "id": "intent_current_state",
                    "title": "Current State Analysis",
                    "required": True,
                    "fields": ["aa_implementation_overview", "report_suites", "data_sources", "known_issues"],
                },
                {
                    "id": "intent_future_state",
                    "title": "Future State Vision",
                    "required": True,
                    "fields": ["cja_target_architecture", "cross_channel_goals", "identity_requirements"],
                },
                {
                    "id": "intent_business_requirements",
                    "title": "Business Requirements",
                    "required": True,
                    "fields": ["functional_requirements", "non_functional_requirements", "data_retention", "compliance"],
                },
                {
                    "id": "intent_stakeholders",
                    "title": "Stakeholders & RACI",
                    "required": True,
                    "fields": ["stakeholder_list", "raci_matrix", "escalation_path"],
                },
                {
                    "id": "intent_success_metrics",
                    "title": "Success Metrics",
                    "required": True,
                    "fields": ["kpis", "acceptance_criteria", "go_live_criteria"],
                },
                {
                    "id": "intent_timeline",
                    "title": "Timeline & Milestones",
                    "required": True,
                    "fields": ["phase_timeline", "key_milestones", "dependencies"],
                },
                {
                    "id": "intent_risks",
                    "title": "Risks & Dependencies",
                    "required": True,
                    "fields": ["risk_register", "mitigation_strategies", "external_dependencies"],
                },
            ],
        },
        "ai_generation_prompt": (
            "Generate an Intent Document for the CJA migration project. "
            "Summarize the current Adobe Analytics implementation, define the future state CJA architecture, "
            "list business requirements gathered from stakeholder interviews, and outline the project timeline. "
            "Include a stakeholder RACI matrix, success metrics, and a risk register."
        ),
    },
    {
        "name": "Solution Design Document",
        "phase_number": 2,
        "output_format": "DOCX",
        "template_structure": {
            "sections": [
                {
                    "id": "sdd_architecture",
                    "title": "Solution Architecture",
                    "required": True,
                    "fields": ["architecture_diagram", "component_inventory", "integration_points"],
                },
                {
                    "id": "sdd_schema_design",
                    "title": "Schema Design",
                    "required": True,
                    "fields": ["schema_list", "field_groups", "class_hierarchy", "tenant_namespace_config"],
                },
                {
                    "id": "sdd_identity",
                    "title": "Identity Resolution",
                    "required": True,
                    "fields": ["identity_namespaces", "stitching_strategy", "identity_graph_config", "fallback_rules"],
                },
                {
                    "id": "sdd_data_sources",
                    "title": "Data Source Design",
                    "required": True,
                    "fields": ["source_inventory", "connector_config", "ingestion_patterns", "data_quality_rules"],
                },
                {
                    "id": "sdd_connections",
                    "title": "Connection Design",
                    "required": True,
                    "fields": ["connection_topology", "dataset_assignments", "backfill_strategy", "streaming_latency_targets"],
                },
                {
                    "id": "sdd_dataviews",
                    "title": "Dataview Design",
                    "required": True,
                    "fields": ["dataview_inventory", "dimension_config", "metric_definitions", "attribution_models", "session_config"],
                },
                {
                    "id": "sdd_migration",
                    "title": "Migration Approach",
                    "required": True,
                    "fields": ["migration_phases", "parallel_run_strategy", "cutover_plan", "rollback_plan"],
                },
                {
                    "id": "sdd_governance",
                    "title": "Data Governance",
                    "required": True,
                    "fields": ["dule_labels", "access_policies", "consent_management", "data_lifecycle"],
                },
            ],
        },
        "ai_generation_prompt": (
            "Generate a comprehensive Solution Design Document for the CJA migration. "
            "Include detailed schema designs with field groups, identity resolution strategy, "
            "data source configurations, connection topology, dataview definitions, and migration approach. "
            "Reference the approved SDR for field mappings and the Intent Document for business requirements."
        ),
    },
    {
        "name": "Data Dictionary",
        "phase_number": 3,
        "output_format": "XLSX",
        "template_structure": {
            "sections": [
                {
                    "id": "dd_field_inventory",
                    "title": "Field Inventory",
                    "required": True,
                    "fields": ["field_path", "display_name", "data_type", "description", "source_system", "aa_origin"],
                },
                {
                    "id": "dd_field_groups",
                    "title": "Field Group Mapping",
                    "required": True,
                    "fields": ["field_group_name", "field_group_type", "fields_included", "schema_assignment"],
                },
                {
                    "id": "dd_enumerations",
                    "title": "Enumerations & Lookups",
                    "required": True,
                    "fields": ["field_path", "enum_values", "display_labels", "default_value"],
                },
                {
                    "id": "dd_transformations",
                    "title": "Transformation Rules",
                    "required": True,
                    "fields": ["source_field", "target_field", "transformation_type", "transformation_logic", "validation_rule"],
                },
                {
                    "id": "dd_governance",
                    "title": "Governance Labels",
                    "required": True,
                    "fields": ["field_path", "dule_label", "sensitivity_level", "retention_policy"],
                },
            ],
        },
        "ai_generation_prompt": (
            "Generate a Data Dictionary for all XDM fields in this CJA migration. "
            "Include every field from the approved schema design with its path, data type, description, "
            "and source system origin. Map field groups, enumerate allowed values, "
            "document transformation rules, and assign data governance labels."
        ),
    },
    {
        "name": "Validation Report",
        "phase_number": 6,
        "output_format": "XLSX",
        "template_structure": {
            "sections": [
                {
                    "id": "vr_data_completeness",
                    "title": "Data Completeness",
                    "required": True,
                    "fields": ["dataset_name", "expected_record_count", "actual_record_count", "completeness_pct", "missing_fields"],
                },
                {
                    "id": "vr_field_accuracy",
                    "title": "Field Accuracy",
                    "required": True,
                    "fields": ["field_path", "sample_aa_value", "sample_cja_value", "match_status", "discrepancy_notes"],
                },
                {
                    "id": "vr_metric_reconciliation",
                    "title": "Metric Reconciliation",
                    "required": True,
                    "fields": ["metric_name", "aa_value", "cja_value", "variance_pct", "acceptable_threshold", "pass_fail"],
                },
                {
                    "id": "vr_identity_validation",
                    "title": "Identity Resolution Validation",
                    "required": True,
                    "fields": ["namespace", "match_rate", "cross_device_rate", "orphan_rate", "stitching_quality_score"],
                },
                {
                    "id": "vr_anomalies",
                    "title": "Anomalies & Issues",
                    "required": True,
                    "fields": ["anomaly_id", "description", "severity", "affected_data", "root_cause", "resolution"],
                },
                {
                    "id": "vr_recommendations",
                    "title": "Recommendations",
                    "required": True,
                    "fields": ["recommendation_id", "category", "description", "priority", "effort_estimate"],
                },
            ],
        },
        "ai_generation_prompt": (
            "Generate a Validation Report comparing Adobe Analytics data with CJA data. "
            "Check data completeness across all datasets, validate field-level accuracy with sampling, "
            "reconcile key metrics (page views, visits, visitors, revenue, events) between AA and CJA, "
            "validate identity resolution quality, and flag anomalies with severity ratings."
        ),
    },
    {
        "name": "Go-Live Runbook",
        "phase_number": 7,
        "output_format": "DOCX",
        "template_structure": {
            "sections": [
                {
                    "id": "glr_pre_golive",
                    "title": "Pre-Go-Live Checklist",
                    "required": True,
                    "fields": ["checklist_item", "owner", "status", "due_date", "verification_method"],
                },
                {
                    "id": "glr_golive_day",
                    "title": "Go-Live Day Procedures",
                    "required": True,
                    "fields": ["step_number", "action", "responsible_party", "expected_duration", "verification", "rollback_step"],
                },
                {
                    "id": "glr_post_golive",
                    "title": "Post-Go-Live Validation",
                    "required": True,
                    "fields": ["validation_item", "method", "expected_result", "actual_result", "status"],
                },
                {
                    "id": "glr_rollback",
                    "title": "Rollback Plan",
                    "required": True,
                    "fields": ["trigger_condition", "rollback_steps", "data_recovery_plan", "communication_plan"],
                },
                {
                    "id": "glr_communication",
                    "title": "Communication Plan",
                    "required": True,
                    "fields": ["audience", "message", "channel", "timing", "sender"],
                },
                {
                    "id": "glr_monitoring",
                    "title": "Monitoring Setup",
                    "required": True,
                    "fields": ["metric", "threshold", "alert_channel", "escalation_path", "dashboard_link"],
                },
            ],
        },
        "ai_generation_prompt": (
            "Generate a Go-Live Runbook for the CJA migration cutover. "
            "Include a pre-go-live checklist with owners and due dates, step-by-step go-live day procedures, "
            "post-go-live validation steps, a detailed rollback plan with trigger conditions, "
            "a stakeholder communication plan, and production monitoring configuration."
        ),
    },
    {
        "name": "Knowledge Transfer Document",
        "phase_number": 7,
        "output_format": "DOCX",
        "template_structure": {
            "sections": [
                {
                    "id": "kt_architecture",
                    "title": "Architecture Overview",
                    "required": True,
                    "fields": ["system_diagram", "component_descriptions", "data_flow_diagram"],
                },
                {
                    "id": "kt_schemas",
                    "title": "Schema Documentation",
                    "required": True,
                    "fields": ["schema_inventory", "field_group_details", "custom_fields", "schema_evolution_guide"],
                },
                {
                    "id": "kt_operations",
                    "title": "Operational Procedures",
                    "required": True,
                    "fields": ["daily_monitoring", "weekly_maintenance", "monthly_reviews", "incident_response"],
                },
                {
                    "id": "kt_troubleshooting",
                    "title": "Troubleshooting Guide",
                    "required": True,
                    "fields": ["common_issues", "diagnostic_steps", "resolution_procedures", "escalation_contacts"],
                },
                {
                    "id": "kt_admin",
                    "title": "Administration Guide",
                    "required": True,
                    "fields": ["user_management", "permission_config", "connection_management", "dataview_management"],
                },
                {
                    "id": "kt_faq",
                    "title": "FAQ & Best Practices",
                    "required": True,
                    "fields": ["frequently_asked_questions", "best_practices", "anti_patterns", "useful_resources"],
                },
            ],
        },
        "ai_generation_prompt": (
            "Generate a Knowledge Transfer Document for the completed CJA migration. "
            "Include the full architecture overview with diagrams, detailed schema documentation, "
            "operational procedures for daily/weekly/monthly tasks, a troubleshooting guide with common issues, "
            "an administration guide for CJA management, and FAQ with best practices."
        ),
    },
]

# ---------------------------------------------------------------------------
# Agent Definitions — 8 agents with detailed system prompts
# ---------------------------------------------------------------------------
AGENT_DEFINITIONS = [
    {
        "name": "orchestrator",
        "display_name": "Orchestrator Agent",
        "role_description": "Coordinates all other agents, manages workflow sequencing, and handles task routing",
        "system_prompt": (
            "You are the Orchestrator Agent for the APEX CJA Migration Accelerator. "
            "Your primary responsibility is coordinating the entire migration workflow across all 7 phases.\n\n"
            "RESPONSIBILITIES:\n"
            "1. Route incoming tasks to the appropriate specialized agent based on task classification and phase context.\n"
            "2. Manage task dependency chains — never dispatch a task until all its dependencies are satisfied.\n"
            "3. Monitor agent execution status and handle failures with retry logic or escalation.\n"
            "4. Maintain the project-level execution context so downstream agents have access to prior outputs.\n"
            "5. Coordinate parallel task execution where dependencies allow.\n"
            "6. Enforce trust level policies — SUPERVISED tasks require human review, FULL_AUTO tasks can auto-complete.\n"
            "7. Trigger gate checks when all phase tasks are complete.\n\n"
            "ROUTING RULES:\n"
            "- Phase 1 discovery tasks -> discovery_agent\n"
            "- Schema design/creation tasks -> schema_agent\n"
            "- Document generation tasks -> document_agent\n"
            "- Solution design tasks -> solution_agent\n"
            "- Validation/QA tasks -> validation_agent\n"
            "- Gate check tasks -> gate_agent\n"
            "- MANUAL tasks -> create human action items, do not invoke AI agents\n\n"
            "OUTPUT: Return a structured routing decision with agent_name, task_context, and priority."
        ),
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.2,
        "tools": ["task_router", "agent_invoker", "dependency_checker", "context_aggregator"],
    },
    {
        "name": "discovery",
        "display_name": "Discovery Agent",
        "role_description": "Generates stakeholder interview questions, analyzes current AA implementation, identifies gaps",
        "system_prompt": (
            "You are the Discovery Agent for the APEX CJA Migration Accelerator. "
            "Your purpose is to drive the Discovery & BRD phase by generating targeted questions, "
            "analyzing existing Adobe Analytics implementations, and documenting the current state.\n\n"
            "RESPONSIBILITIES:\n"
            "1. Generate client questionnaires tailored to the specific AA implementation:\n"
            "   - Report suite configuration questions (eVars, props, events, classifications)\n"
            "   - Data collection methodology questions (AppMeasurement, Web SDK, Launch rules)\n"
            "   - Business requirement questions (KPIs, reporting cadence, stakeholder needs)\n"
            "   - Cross-channel and identity questions (ECID, CRM ID stitching, device graph)\n"
            "   - Compliance and governance questions (data retention, consent, DULE labels)\n"
            "2. Analyze AA report suite exports to identify:\n"
            "   - Active vs. inactive variables\n"
            "   - Custom events and their business context\n"
            "   - Processing rules and VISTA rules impact\n"
            "   - Classification hierarchies\n"
            "   - Calculated metrics and segment definitions\n"
            "3. Generate the first draft of the SDR from AA analysis.\n"
            "4. Draft the Intent Document from stakeholder responses.\n"
            "5. Document the current state architecture.\n\n"
            "INPUT: Client questionnaire responses, AA report suite JSON exports, stakeholder interview notes.\n"
            "OUTPUT: Structured analysis with findings, gaps, recommendations, and draft documents."
        ),
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.3,
        "tools": ["question_generator", "aa_analyzer", "gap_identifier", "report_suite_parser"],
        "input_sources": {"questionnaire_responses": True, "aa_report_suites": True, "stakeholder_notes": True},
    },
    {
        "name": "solution",
        "display_name": "Solution Design Agent",
        "role_description": "Creates SDR, designs XDM schemas, maps AA variables to CJA fields, defines identity strategy",
        "system_prompt": (
            "You are the Solution Design Agent for the APEX CJA Migration Accelerator. "
            "Your purpose is to create the technical solution design that bridges Adobe Analytics and CJA.\n\n"
            "RESPONSIBILITIES:\n"
            "1. SDR Creation:\n"
            "   - Map every AA variable (eVar, prop, event, classification) to an XDM field path\n"
            "   - Define data type transformations (e.g., AA string eVar -> XDM string with enum)\n"
            "   - Translate calculated metrics from AA formulas to CJA metric definitions\n"
            "   - Convert AA segments to CJA filter definitions\n"
            "   - Design dataview configurations with proper attribution models\n\n"
            "2. Schema Design:\n"
            "   - Propose XDM schema class (ExperienceEvent, Profile, Record)\n"
            "   - Select appropriate Adobe field groups (Web Details, Commerce, etc.)\n"
            "   - Design custom field groups for client-specific data\n"
            "   - Define tenant namespace structure\n"
            "   - Plan schema evolution strategy\n\n"
            "3. Identity Resolution:\n"
            "   - Define identity namespaces (ECID, CRM ID, email, phone)\n"
            "   - Design cross-device stitching strategy\n"
            "   - Configure identity graph settings\n"
            "   - Plan fallback identity resolution\n\n"
            "4. Connection & Dataview Strategy:\n"
            "   - Design connection topology (which datasets in which connections)\n"
            "   - Define backfill and streaming configurations\n"
            "   - Plan dataview dimension/metric configurations\n"
            "   - Configure session settings and attribution models\n\n"
            "INPUT: Discovery outputs (SDR first draft, Intent Document, AA analysis), source inventory.\n"
            "OUTPUT: Complete Solution Design Document, refined SDR, schema proposals."
        ),
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.2,
        "tools": ["schema_designer", "field_mapper", "sdr_generator", "identity_planner", "dataview_designer"],
        "input_sources": {"brd": True, "source_definitions": True, "aa_analysis": True},
    },
    {
        "name": "schema",
        "display_name": "Schema Agent",
        "role_description": "Generates and validates XDM schemas, manages schema lifecycle across pilot/dev/prod layers",
        "system_prompt": (
            "You are the Schema Agent for the APEX CJA Migration Accelerator. "
            "Your purpose is to generate valid XDM schemas, validate them against Adobe standards, "
            "and manage schema deployment across pilot, dev, and production layers.\n\n"
            "RESPONSIBILITIES:\n"
            "1. Schema Generation:\n"
            "   - Generate XDM-compliant JSON schema definitions from the solution design\n"
            "   - Include proper $id, meta:class, meta:extends references\n"
            "   - Define field groups with correct allOf composition\n"
            "   - Set required fields, enum constraints, and default values\n"
            "   - Generate tenant-specific custom field group definitions\n\n"
            "2. Schema Validation:\n"
            "   - Validate schema JSON against XDM meta-schema rules\n"
            "   - Check field type compatibility with AEP supported types\n"
            "   - Verify identity descriptor configurations\n"
            "   - Ensure backward compatibility when evolving schemas\n"
            "   - Validate lookup and profile dataset relationship keys\n\n"
            "3. Schema Lifecycle Management:\n"
            "   - Pilot layer: Create initial schemas with test data validation\n"
            "   - Dev layer: Promote pilot schemas, apply grooming changes\n"
            "   - Prod layer: Deploy production-ready schemas with immutability checks\n"
            "   - Track schema versions across layers\n\n"
            "4. Dataset Configuration:\n"
            "   - Generate dataset configurations from schemas\n"
            "   - Configure batch vs. streaming ingestion settings\n"
            "   - Set up lookup and profile dataset relationships\n"
            "   - Define data governance labels at field level\n\n"
            "INPUT: Solution design schema proposals, field mapping spreadsheets, grooming feedback.\n"
            "OUTPUT: Valid XDM JSON schemas, dataset configs, validation reports, promotion manifests."
        ),
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.1,
        "tools": ["schema_generator", "schema_validator", "layer_manager", "dataset_configurator"],
    },
    {
        "name": "document",
        "display_name": "Document Agent",
        "role_description": "Generates project documents (SDR, Intent Doc, reports) from templates and project data",
        "system_prompt": (
            "You are the Document Agent for the APEX CJA Migration Accelerator. "
            "Your purpose is to generate high-quality migration documents from predefined templates, "
            "populated with project-specific data and AI-generated analysis.\n\n"
            "RESPONSIBILITIES:\n"
            "1. Template-Based Generation:\n"
            "   - Load the appropriate DocumentTemplate for the requested document type\n"
            "   - Populate every required section with project-specific content\n"
            "   - Ensure all required fields within each section are filled\n"
            "   - Apply consistent formatting and terminology across documents\n\n"
            "2. Document Types:\n"
            "   - SDR (XLSX): Field-level mapping spreadsheet with AA-to-XDM translations\n"
            "   - Intent Document (DOCX): Executive-level project intent and requirements\n"
            "   - Solution Design Document (DOCX): Technical architecture and design decisions\n"
            "   - Data Dictionary (XLSX): Complete field inventory with governance labels\n"
            "   - Validation Report (XLSX): Data quality and reconciliation results\n"
            "   - Go-Live Runbook (DOCX): Step-by-step cutover procedures\n"
            "   - Knowledge Transfer Document (DOCX): Post-migration operational guide\n\n"
            "3. Quality Standards:\n"
            "   - Every section must have substantive content (no placeholder text)\n"
            "   - Cross-reference related documents for consistency\n"
            "   - Include version tracking and change history\n"
            "   - Flag sections requiring human review or client input\n\n"
            "INPUT: Document template, project context (prior outputs, source data, agent results).\n"
            "OUTPUT: Fully populated document content in structured JSON, ready for export."
        ),
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.4,
        "tools": ["document_generator", "template_filler", "export_formatter", "cross_reference_checker"],
    },
    {
        "name": "validation",
        "display_name": "Validation Agent",
        "role_description": "Validates data accuracy, reconciles metrics between AA and CJA, detects anomalies",
        "system_prompt": (
            "You are the Validation Agent for the APEX CJA Migration Accelerator. "
            "Your purpose is to ensure data integrity and accuracy throughout the migration process "
            "by comparing AA and CJA data at every layer.\n\n"
            "RESPONSIBILITIES:\n"
            "1. Test Case Generation:\n"
            "   - Generate data validation test cases based on schema and mapping definitions\n"
            "   - Create metric reconciliation test cases for all calculated metrics\n"
            "   - Design identity resolution validation scenarios\n"
            "   - Produce edge case tests (null handling, special characters, large values)\n\n"
            "2. Data Validation:\n"
            "   - Compare record counts between AA exports and CJA datasets\n"
            "   - Validate field-level data accuracy with statistical sampling\n"
            "   - Check data type preservation across transformation pipeline\n"
            "   - Verify timestamp accuracy and timezone handling\n"
            "   - Validate lookup and profile dataset joins\n\n"
            "3. Metric Reconciliation:\n"
            "   - Compare key metrics: page views, visits, unique visitors, revenue, events\n"
            "   - Calculate variance percentages and flag out-of-threshold values\n"
            "   - Analyze calculated metric formula translations for correctness\n"
            "   - Validate segment-to-filter population equivalence\n\n"
            "4. Identity Validation:\n"
            "   - Verify identity namespace match rates\n"
            "   - Check cross-device stitching accuracy\n"
            "   - Validate profile merge behavior\n"
            "   - Measure orphan record rates\n\n"
            "5. Anomaly Detection:\n"
            "   - Detect data volume anomalies (sudden drops/spikes)\n"
            "   - Identify field value distribution changes\n"
            "   - Flag unexpected null rates or cardinality changes\n\n"
            "INPUT: AA data exports, CJA query results, schema definitions, mapping rules.\n"
            "OUTPUT: Validation report with pass/fail per test case, variance analysis, anomaly flags."
        ),
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.1,
        "tools": ["data_validator", "metric_reconciler", "anomaly_detector", "identity_validator", "test_case_generator"],
    },
    {
        "name": "gate",
        "display_name": "Gate Agent",
        "role_description": "Evaluates gate criteria, determines phase readiness, generates gate reports",
        "system_prompt": (
            "You are the Gate Agent for the APEX CJA Migration Accelerator. "
            "Your purpose is to evaluate whether all criteria for a phase gate have been met "
            "and provide a go/no-go recommendation.\n\n"
            "RESPONSIBILITIES:\n"
            "1. Gate Criteria Evaluation:\n"
            "   - Check each gate criterion for the current phase against project state\n"
            "   - Verify all required tasks are completed (status = COMPLETED)\n"
            "   - Confirm all required documents are in FINAL status\n"
            "   - Validate all required sign-offs have been obtained\n"
            "   - Check data quality thresholds are met (for build/validation phases)\n\n"
            "2. Phase-Specific Checks:\n"
            "   - Phase 1: All questionnaires answered, SDR first draft exists, intent document approved\n"
            "   - Phase 2: Solution design approved, schemas designed, client review complete\n"
            "   - Phase 3: Pilot schemas validated, data flowing, pilot review passed\n"
            "   - Phase 4: Dev validation passed, all source connectors configured, sign-off obtained\n"
            "   - Phase 5: CJA connection/dataview created, prod data flowing, client + architect sign-off\n"
            "   - Phase 6: All validations passed, metrics reconciled, UAT complete, report approved\n"
            "   - Phase 7: Go-live complete, monitoring active, knowledge transfer done, project closed\n\n"
            "3. Gate Report Generation:\n"
            "   - Produce a structured gate report with status per criterion\n"
            "   - List blocking items that prevent gate passage\n"
            "   - Provide recommendations for resolving blockers\n"
            "   - Calculate overall readiness score (0-100%)\n\n"
            "INPUT: Phase definition gate_criteria, task instance statuses, document statuses, sign-off records.\n"
            "OUTPUT: Gate evaluation result (PASS/FAIL), readiness score, blocker list, gate report."
        ),
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.1,
        "tools": ["gate_evaluator", "readiness_checker", "gate_reporter", "blocker_analyzer"],
    },
    {
        "name": "improvement",
        "display_name": "Improvement Agent",
        "role_description": "Analyzes feedback patterns, proposes prompt improvements, learns from corrections",
        "system_prompt": (
            "You are the Improvement Agent for the APEX CJA Migration Accelerator. "
            "Your purpose is to continuously improve the quality of AI outputs by analyzing human feedback, "
            "identifying patterns in corrections, and proposing prompt and workflow optimizations.\n\n"
            "RESPONSIBILITIES:\n"
            "1. Feedback Analysis:\n"
            "   - Analyze human feedback on AI-generated outputs (approvals, rejections, edits)\n"
            "   - Identify recurring correction patterns across projects\n"
            "   - Categorize feedback by agent, task type, and severity\n"
            "   - Track improvement trends over time\n\n"
            "2. Prompt Optimization:\n"
            "   - Propose system prompt refinements based on feedback patterns\n"
            "   - A/B test prompt variations and measure quality improvements\n"
            "   - Optimize temperature and model parameters per agent\n"
            "   - Identify where additional context in prompts would reduce errors\n\n"
            "3. Knowledge Extraction:\n"
            "   - Extract reusable patterns from successful outputs\n"
            "   - Build a knowledge base of client-specific customizations\n"
            "   - Identify best practices across migration projects\n"
            "   - Document anti-patterns that lead to poor outputs\n\n"
            "4. Quality Metrics:\n"
            "   - Track first-pass approval rates per agent and task type\n"
            "   - Measure average revision cycles before approval\n"
            "   - Monitor confidence score calibration (predicted vs. actual quality)\n"
            "   - Generate periodic improvement reports\n\n"
            "INPUT: Feedback records, eval results, agent execution history, correction diffs.\n"
            "OUTPUT: Improvement proposals with expected impact, knowledge base entries, quality reports."
        ),
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.5,
        "tools": ["feedback_analyzer", "prompt_optimizer", "knowledge_extractor", "quality_tracker"],
    },
]

# ---------------------------------------------------------------------------
# Eval Definitions — base evals + agent-specific evals
# ---------------------------------------------------------------------------
EVAL_DEFINITIONS = [
    # Base evals
    {
        "name": "Completeness Check",
        "eval_type": "COMPLETENESS",
        "description": "Checks if AI output covers all required sections/fields",
        "threshold": 0.8,
        "applies_to": {"agents": ["discovery_agent", "solution_agent", "document_agent"]},
        "eval_prompt": "Evaluate whether the output covers all required sections. Score 1.0 if complete, reduce proportionally for missing sections.",
    },
    {
        "name": "Accuracy Check",
        "eval_type": "ACCURACY",
        "description": "Validates factual accuracy of AI output against source data",
        "threshold": 0.9,
        "applies_to": {"agents": ["solution_agent", "schema_agent", "validation_agent"]},
        "eval_prompt": "Evaluate the factual accuracy of the output against the provided source data. Flag any discrepancies.",
    },
    {
        "name": "Schema Validity",
        "eval_type": "SCHEMA_VALIDITY",
        "description": "Validates XDM schema compliance and field type correctness",
        "threshold": 0.95,
        "applies_to": {"agents": ["schema_agent"]},
        "eval_prompt": "Validate that the generated schema complies with XDM standards. Check field types, required fields, and naming conventions.",
    },
    {
        "name": "Consistency Check",
        "eval_type": "CONSISTENCY",
        "description": "Checks output consistency with previous project outputs",
        "threshold": 0.7,
        "applies_to": {"agents": ["solution_agent", "document_agent"]},
        "eval_prompt": "Compare the output against previous outputs for this project to ensure consistency in terminology, field names, and design decisions.",
    },
    {
        "name": "Quality Score",
        "eval_type": "QUALITY",
        "description": "Overall quality assessment of AI output",
        "threshold": 0.7,
        "applies_to": {"agents": ["discovery_agent", "solution_agent", "document_agent", "validation_agent"]},
        "eval_prompt": "Rate the overall quality of the output considering clarity, completeness, accuracy, and actionability.",
    },
    # Agent-specific evals
    {
        "name": "XDM Schema Compliance",
        "eval_type": "XDM_COMPLIANCE",
        "description": "Validates XDM schema structure, field group composition, and AEP compatibility",
        "threshold": 0.95,
        "applies_to": {"agents": ["schema_agent"]},
        "eval_prompt": (
            "Evaluate the generated XDM schema for full compliance with Adobe Experience Platform standards. "
            "Check: 1) Valid $id and meta:class references, 2) Correct allOf field group composition, "
            "3) Supported data types (string, integer, number, boolean, array, object, date-time), "
            "4) Proper identity descriptor configuration, 5) Required field declarations, "
            "6) Tenant namespace usage for custom fields, 7) Backward compatibility with existing schemas. "
            "Score 1.0 for full compliance, deduct 0.1 for each violation category."
        ),
    },
    {
        "name": "Question Relevance",
        "eval_type": "RELEVANCE",
        "description": "Evaluates whether generated questions are relevant and actionable for CJA migration discovery",
        "threshold": 0.8,
        "applies_to": {"agents": ["discovery_agent"]},
        "eval_prompt": (
            "Evaluate the generated discovery questions for relevance to a CJA migration project. "
            "Check: 1) Questions target information needed for schema design, field mapping, or identity resolution, "
            "2) Questions are specific enough to get actionable answers (not overly generic), "
            "3) Questions cover all critical areas: data sources, business KPIs, identity strategy, governance, "
            "4) Questions are appropriate for the stakeholder role (technical vs. business), "
            "5) No redundant or overlapping questions. "
            "Score 1.0 for a fully relevant and well-structured questionnaire, deduct proportionally for gaps."
        ),
    },
    {
        "name": "Document Section Coverage",
        "eval_type": "SECTION_COVERAGE",
        "description": "Validates that generated documents populate all required template sections with substantive content",
        "threshold": 0.85,
        "applies_to": {"agents": ["document_agent"]},
        "eval_prompt": (
            "Evaluate the generated document against its template structure. "
            "Check: 1) Every required section from the template is present in the output, "
            "2) Each section contains substantive content (not placeholder or boilerplate text), "
            "3) All required fields within each section are populated, "
            "4) Cross-references to other documents are valid, "
            "5) Consistent terminology and formatting throughout. "
            "Score = (sections_with_substantive_content / total_required_sections). "
            "Deduct 0.05 for each section with thin or placeholder content."
        ),
    },
    {
        "name": "Gate Criteria Completeness",
        "eval_type": "GATE_COMPLETENESS",
        "description": "Validates that gate evaluations check every defined criterion and provide accurate status",
        "threshold": 0.9,
        "applies_to": {"agents": ["gate_agent"]},
        "eval_prompt": (
            "Evaluate the gate check output for completeness and accuracy. "
            "Check: 1) Every gate criterion defined for the phase is evaluated (none skipped), "
            "2) Each criterion status accurately reflects the actual project state, "
            "3) Blocking items are correctly identified with actionable resolution steps, "
            "4) The readiness score calculation is mathematically correct, "
            "5) The go/no-go recommendation is consistent with the criterion statuses. "
            "Score 1.0 for a complete and accurate gate evaluation. "
            "Deduct 0.15 for each missed criterion, 0.1 for each inaccurate status."
        ),
    },
    {
        "name": "Metric Reconciliation Accuracy",
        "eval_type": "RECONCILIATION_ACCURACY",
        "description": "Validates that AA vs CJA metric comparisons are mathematically correct and variance thresholds are properly applied",
        "threshold": 0.9,
        "applies_to": {"agents": ["validation_agent"]},
        "eval_prompt": (
            "Evaluate the metric reconciliation output for mathematical accuracy and completeness. "
            "Check: 1) All key metrics are compared (page views, visits, unique visitors, revenue, custom events), "
            "2) Variance percentages are calculated correctly: abs(aa_value - cja_value) / aa_value * 100, "
            "3) Pass/fail thresholds are applied correctly per metric type "
            "(typically <=2% for page views, <=5% for unique visitors, <=1% for revenue), "
            "4) Root cause analysis is provided for failing metrics, "
            "5) Sampling methodology is statistically sound (date range, segment coverage). "
            "Score 1.0 for fully accurate reconciliation. Deduct 0.1 per miscalculated metric, "
            "0.05 per missing metric, 0.1 for incorrect threshold application."
        ),
    },
]


# ===========================================================================
# Seeding functions
# ===========================================================================


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
    """Seed task definitions linked to phase definitions.

    Two-pass approach:
      1. Create/update all tasks, building a {(phase_number, sort_order): task_def_id} map.
      2. Resolve depends_on sort orders to UUIDs and update.
    """
    # First pass: create or update tasks, collect ID mapping
    task_id_map: dict[tuple[int, int], uuid.UUID] = {}  # (phase_number, sort_order) -> uuid

    for phase_number, tasks in TASK_DEFINITIONS_BY_PHASE.items():
        phase_def_id = phase_ids[phase_number]
        for task_tuple in tasks:
            (
                sort_order, name, classification, hybrid_pattern,
                default_owner_role, secondary_owner_role, default_trust_level,
                source_type, _depends_on_sort_orders,
            ) = task_tuple

            existing = await db.execute(
                select(TaskDefinition).where(
                    TaskDefinition.phase_definition_id == phase_def_id,
                    TaskDefinition.sort_order == sort_order,
                )
            )
            task = existing.scalar_one_or_none()
            if task:
                # Upsert: update existing record
                task.name = name
                task.classification = classification
                task.hybrid_pattern = hybrid_pattern
                task.default_owner_role = default_owner_role
                task.secondary_owner_role = secondary_owner_role
                task.default_trust_level = default_trust_level
                task.source_type = source_type
            else:
                task = TaskDefinition(
                    phase_definition_id=phase_def_id,
                    name=name,
                    classification=classification,
                    hybrid_pattern=hybrid_pattern,
                    default_owner_role=default_owner_role,
                    secondary_owner_role=secondary_owner_role,
                    default_trust_level=default_trust_level,
                    source_type=source_type,
                    sort_order=sort_order,
                )
                db.add(task)
                await db.flush()

            task_id_map[(phase_number, sort_order)] = task.id

    await db.flush()

    # Second pass: resolve depends_on sort orders to UUIDs
    for phase_number, tasks in TASK_DEFINITIONS_BY_PHASE.items():
        for task_tuple in tasks:
            sort_order = task_tuple[0]
            depends_on_sort_orders = task_tuple[8]

            if not depends_on_sort_orders:
                continue

            task_id = task_id_map[(phase_number, sort_order)]
            depends_on_ids = [
                str(task_id_map[(phase_number, dep_sort)])
                for dep_sort in depends_on_sort_orders
                if (phase_number, dep_sort) in task_id_map
            ]

            # Update the task's depends_on field
            result = await db.execute(
                select(TaskDefinition).where(TaskDefinition.id == task_id)
            )
            task = result.scalar_one()
            task.depends_on = depends_on_ids

    await db.flush()


async def seed_source_definitions(db: AsyncSession) -> None:
    """Seed source definitions with upsert logic."""
    for sd in SOURCE_DEFINITIONS:
        existing = await db.execute(select(SourceDefinition).where(SourceDefinition.source_type == sd["source_type"]))
        source = existing.scalar_one_or_none()
        if source:
            # Upsert: update existing record
            source.name = sd["name"]
            source.is_mandatory = sd["is_mandatory"]
            source.business_type = sd["business_type"]
            source.requires_client_admin = sd["requires_client_admin"]
            source.description = sd.get("description")
            source.implementation_owner_role = sd.get("implementation_owner_role")
            source.client_dependencies = sd.get("client_dependencies")
            source.ai_scope = sd.get("ai_scope")
            source.artifacts = sd.get("artifacts", ["SCHEMA", "DATASET", "CONNECTION"])
            source.layers = sd.get("layers", ["PILOT", "DEV", "PROD"])
        else:
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
                artifacts=sd.get("artifacts", ["SCHEMA", "DATASET", "CONNECTION"]),
                layers=sd.get("layers", ["PILOT", "DEV", "PROD"]),
            )
            db.add(source)
    await db.flush()


async def seed_document_templates(db: AsyncSession, phase_ids: dict[int, uuid.UUID]) -> None:
    """Seed document templates linked to phases with upsert logic."""
    for dt in DOCUMENT_TEMPLATES:
        phase_def_id = phase_ids[dt["phase_number"]]
        existing = await db.execute(select(DocumentTemplate).where(DocumentTemplate.name == dt["name"]))
        template = existing.scalar_one_or_none()
        if template:
            # Upsert: update existing record
            template.phase_definition_id = phase_def_id
            template.output_format = dt["output_format"]
            template.template_structure = dt.get("template_structure")
            template.ai_generation_prompt = dt.get("ai_generation_prompt")
        else:
            template = DocumentTemplate(
                name=dt["name"],
                phase_definition_id=phase_def_id,
                output_format=dt["output_format"],
                template_structure=dt.get("template_structure"),
                ai_generation_prompt=dt.get("ai_generation_prompt"),
            )
            db.add(template)
    await db.flush()


async def seed_agent_definitions(db: AsyncSession) -> None:
    """Seed agent definitions with upsert logic."""
    for ad in AGENT_DEFINITIONS:
        existing = await db.execute(select(AgentDefinition).where(AgentDefinition.name == ad["name"]))
        agent = existing.scalar_one_or_none()
        if agent:
            # Upsert: update existing record
            agent.display_name = ad.get("display_name")
            agent.role_description = ad.get("role_description")
            agent.system_prompt = ad.get("system_prompt")
            agent.model = ad.get("model")
            agent.temperature = ad.get("temperature", 0.3)
            agent.tools = ad.get("tools")
            agent.input_sources = ad.get("input_sources")
        else:
            agent = AgentDefinition(
                name=ad["name"],
                display_name=ad.get("display_name"),
                role_description=ad.get("role_description"),
                system_prompt=ad.get("system_prompt"),
                model=ad.get("model"),
                temperature=ad.get("temperature", 0.3),
                tools=ad.get("tools"),
                input_sources=ad.get("input_sources"),
            )
            db.add(agent)
    await db.flush()


async def seed_eval_definitions(db: AsyncSession) -> None:
    """Seed eval definitions with upsert logic."""
    for ed in EVAL_DEFINITIONS:
        existing = await db.execute(select(EvalDefinition).where(EvalDefinition.name == ed["name"]))
        eval_def = existing.scalar_one_or_none()
        if eval_def:
            # Upsert: update existing record
            eval_def.eval_type = ed["eval_type"]
            eval_def.description = ed.get("description")
            eval_def.eval_prompt = ed.get("eval_prompt")
            eval_def.threshold = ed.get("threshold", 0.7)
            eval_def.applies_to = ed.get("applies_to")
        else:
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
