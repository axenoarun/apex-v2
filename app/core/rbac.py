from enum import StrEnum


class RoleName(StrEnum):
    ARCHITECT = "ARCHITECT"
    ENGINEER = "ENGINEER"
    CLIENT = "CLIENT"
    ADOBE_LAUNCH_ADVISORY = "ADOBE_LAUNCH_ADVISORY"


# Permission matrix from spec Section 3.1
# Maps role_name -> {permission_name: bool}
DEFAULT_ROLE_PERMISSIONS = {
    RoleName.ARCHITECT: {
        "view_all_projects": True,
        "view_assigned_projects": True,
        "create_project": True,
        "assign_roles": True,
        "view_all_tasks": True,
        "complete_task": True,  # own tasks
        "override_gate": True,
        "reassign_task": True,
        "change_trust_level": True,
        "change_classification": True,
        "view_audit_log": True,
        "view_cost_tracking": True,
        "view_all_feedback": True,
        "submit_feedback": True,
        "review_improvements": True,
        "admin_config": True,
        "sign_off_gate": True,
        "review_pilot": True,
        "answer_questions": True,
    },
    RoleName.ENGINEER: {
        "view_all_projects": False,
        "view_assigned_projects": True,
        "create_project": False,
        "assign_roles": False,
        "view_all_tasks": False,
        "complete_task": True,
        "override_gate": False,
        "reassign_task": False,
        "change_trust_level": False,
        "change_classification": False,
        "view_audit_log": False,
        "view_cost_tracking": False,
        "view_all_feedback": False,
        "submit_feedback": True,
        "review_improvements": False,
        "admin_config": False,
        "sign_off_gate": False,
        "review_pilot": False,
        "answer_questions": True,
    },
    RoleName.CLIENT: {
        "view_all_projects": False,
        "view_assigned_projects": True,
        "create_project": False,
        "assign_roles": False,
        "view_all_tasks": False,
        "complete_task": True,
        "override_gate": False,
        "reassign_task": False,
        "change_trust_level": False,
        "change_classification": False,
        "view_audit_log": False,
        "view_cost_tracking": False,
        "view_all_feedback": False,
        "submit_feedback": False,
        "review_improvements": False,
        "admin_config": False,
        "sign_off_gate": True,
        "review_pilot": False,
        "answer_questions": True,
    },
    RoleName.ADOBE_LAUNCH_ADVISORY: {
        "view_all_projects": False,
        "view_assigned_projects": True,
        "create_project": False,
        "assign_roles": False,
        "view_all_tasks": False,
        "complete_task": True,
        "override_gate": False,
        "reassign_task": False,
        "change_trust_level": False,
        "change_classification": False,
        "view_audit_log": False,
        "view_cost_tracking": False,
        "view_all_feedback": False,
        "submit_feedback": True,
        "review_improvements": False,
        "admin_config": False,
        "sign_off_gate": False,
        "review_pilot": False,
        "answer_questions": True,
    },
}
