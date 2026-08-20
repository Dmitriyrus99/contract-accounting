"""Fail-closed row policy for project-linked DocTypes.

Frappe DocPerm does not inherit the row restriction of a linked Service
Project. Every operational DocType exposed to a scoped role therefore has to
be registered here and in hooks.py. Static tests compare this registry with
the DocType permission inventory so a new unguarded surface fails CI.
"""

from __future__ import annotations

from typing import Any, Final

import frappe

from contract_accounting.infrastructure.operations_permissions import (
    can_access_project,
    project_visibility_condition,
    scoped_project_roles,
)

DIRECT_PROJECT_DOCTYPES: Final[frozenset[str]] = frozenset(
    {
        "Ferum Contract Obligation",
        "Ferum Contractor Assignment",
        "Ferum Finding",
        "Ferum Inspection",
        "Ferum Maintenance Schedule",
        "Ferum Maintenance Visit",
        "Ferum Material Expense",
        "Ferum Photo Evidence",
        "Ferum Project Document",
        "Ferum Project Object",
        "Ferum Project Process",
        "Ferum Project Process Step",
        "Ferum Project Stage",
        "Ferum Service Request",
        "Ferum Stage Gate",
    }
)

INDIRECT_PROJECT_DOCTYPES: Final[frozenset[str]] = frozenset(
    {
        "Ferum Object System",
        "Ferum Process Evidence",
        "Ferum Project Document Event",
        "Ferum Service Object",
    }
)

PROJECT_SCOPED_DOCTYPES: Final[frozenset[str]] = DIRECT_PROJECT_DOCTYPES | INDIRECT_PROJECT_DOCTYPES

# These surfaces have separate, intentionally different policies. The static
# gate requires an explanation for every exemption instead of silently
# skipping it.
PROJECT_SCOPE_EXEMPTIONS: Final[dict[str, str]] = {
    "Ferum Contractor Worker": "privacy_permissions: Worker scope and break-glass",
    "Ferum Party Identity": "global ERPNext master-data linkage for Office Manager",
    "Ferum Personnel Credential": "privacy_permissions: Credential scope and break-glass",
    "Ferum Service Project": "operations_permissions: authoritative parent policy",
}


def has_project_graph_permission(
    doc: Any,
    ptype: str | None = None,
    user: str | None = None,
    debug: bool = False,
) -> bool | None:
    """Deny a scoped user when none of the document projects is visible.

    Returning ``None`` for an allowed project deliberately keeps normal
    DocPerm, permlevel and User Permission checks in force.
    """

    user = user or frappe.session.user
    if not scoped_project_roles(user):
        return None
    projects = _document_projects(doc)
    if not projects:
        return False
    if not any(can_access_project(project, user) for project in projects):
        return False
    return None


def _direct_query(doctype: str, user: str | None) -> str:
    user = user or frappe.session.user
    roles = scoped_project_roles(user)
    if not roles:
        return ""
    return project_visibility_condition(
        f"`tab{doctype}`.`service_project`",
        user=user,
        roles=roles,
    )


def _service_object_query(doctype: str, user: str | None) -> str:
    user = user or frappe.session.user
    roles = scoped_project_roles(user)
    if not roles:
        return ""
    visibility = project_visibility_condition(
        "project_object.service_project", user=user, roles=roles
    )
    return (
        "exists (select 1 from `tabFerum Project Object` project_object "
        f"where project_object.service_object = `tab{doctype}`.`name` "
        f"and {visibility})"
    )


def _object_system_query(user: str | None) -> str:
    user = user or frappe.session.user
    roles = scoped_project_roles(user)
    if not roles:
        return ""
    visibility = project_visibility_condition(
        "project_object.service_project", user=user, roles=roles
    )
    return (
        "exists (select 1 from `tabFerum Project Object` project_object "
        "where project_object.service_object = `tabFerum Object System`.`service_object` "
        f"and {visibility})"
    )


def _process_evidence_query(user: str | None) -> str:
    user = user or frappe.session.user
    roles = scoped_project_roles(user)
    if not roles:
        return ""
    visibility = project_visibility_condition("step.service_project", user=user, roles=roles)
    return (
        "exists (select 1 from `tabFerum Project Process Step` step "
        "where step.name = `tabFerum Process Evidence`.`process_step` "
        f"and {visibility})"
    )


def _document_event_query(user: str | None) -> str:
    user = user or frappe.session.user
    roles = scoped_project_roles(user)
    if not roles:
        return ""
    visibility = project_visibility_condition(
        "project_document.service_project", user=user, roles=roles
    )
    return (
        "exists (select 1 from `tabFerum Project Document` project_document "
        "where project_document.name = `tabFerum Project Document Event`.`project_document` "
        f"and {visibility})"
    )


def _document_projects(doc: Any) -> set[str]:
    doctype = str(doc.doctype)
    if doctype in DIRECT_PROJECT_DOCTYPES:
        return {str(doc.service_project)} if doc.get("service_project") else set()
    if doctype == "Ferum Service Object":
        return _projects_for_service_object(str(doc.name))
    if doctype == "Ferum Object System":
        service_object = doc.get("service_object")
        return _projects_for_service_object(str(service_object)) if service_object else set()
    if doctype == "Ferum Process Evidence":
        project = frappe.db.get_value(
            "Ferum Project Process Step", doc.get("process_step"), "service_project"
        )
        return {str(project)} if project else set()
    if doctype == "Ferum Project Document Event":
        project = frappe.db.get_value(
            "Ferum Project Document", doc.get("project_document"), "service_project"
        )
        return {str(project)} if project else set()
    return set()


def _projects_for_service_object(service_object: str) -> set[str]:
    return {
        str(name)
        for name in frappe.get_all(
            "Ferum Project Object",
            filters={"service_object": service_object},
            pluck="service_project",
            ignore_permissions=True,
        )
        if name
    }


# Explicit query wrappers are intentionally repetitive: hooks.py can be
# audited mechanically and each DocType has one stable callable.
def contract_obligation_query(user: str | None = None) -> str:
    return _direct_query("Ferum Contract Obligation", user)


def contractor_assignment_query(user: str | None = None) -> str:
    return _direct_query("Ferum Contractor Assignment", user)


def finding_query(user: str | None = None) -> str:
    return _direct_query("Ferum Finding", user)


def inspection_query(user: str | None = None) -> str:
    return _direct_query("Ferum Inspection", user)


def maintenance_schedule_query(user: str | None = None) -> str:
    return _direct_query("Ferum Maintenance Schedule", user)


def maintenance_visit_query(user: str | None = None) -> str:
    return _direct_query("Ferum Maintenance Visit", user)


def material_expense_query(user: str | None = None) -> str:
    return _direct_query("Ferum Material Expense", user)


def photo_evidence_query(user: str | None = None) -> str:
    return _direct_query("Ferum Photo Evidence", user)


def project_document_query(user: str | None = None) -> str:
    return _direct_query("Ferum Project Document", user)


def project_object_query(user: str | None = None) -> str:
    return _direct_query("Ferum Project Object", user)


def project_process_query(user: str | None = None) -> str:
    return _direct_query("Ferum Project Process", user)


def project_process_step_query(user: str | None = None) -> str:
    return _direct_query("Ferum Project Process Step", user)


def project_stage_query(user: str | None = None) -> str:
    return _direct_query("Ferum Project Stage", user)


def service_request_query(user: str | None = None) -> str:
    return _direct_query("Ferum Service Request", user)


def stage_gate_query(user: str | None = None) -> str:
    return _direct_query("Ferum Stage Gate", user)


def service_object_query(user: str | None = None) -> str:
    return _service_object_query("Ferum Service Object", user)


def object_system_query(user: str | None = None) -> str:
    return _object_system_query(user)


def process_evidence_query(user: str | None = None) -> str:
    return _process_evidence_query(user)


def project_document_event_query(user: str | None = None) -> str:
    return _document_event_query(user)
