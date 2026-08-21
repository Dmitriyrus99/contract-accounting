"""Assigned-project read boundary for operational Desk roles."""

from __future__ import annotations

from typing import Any, Final

import frappe

DOCTYPE: Final[str] = "Ferum Service Project"
SCOPED_ROLES: Final[frozenset[str]] = frozenset({"Инженер", "Офис-менеджер"})
UNRESTRICTED_ROLES: Final[frozenset[str]] = frozenset(
    {
        "System Manager",
        "Генеральный директор",
        "Руководитель проектов",
        "Менеджер проектов",
        "Юрист",
        "Бухгалтер",
    }
)
ACTIVE_STEP_STATUSES: Final[tuple[str, ...]] = (
    "Planned",
    "Ready",
    "In Progress",
    "Waiting External",
    "Waiting Approval",
    "Blocked",
)
ACTIVE_REQUEST_STATUSES: Final[tuple[str, ...]] = (
    "Open",
    "Assigned",
    "In Progress",
    "Resolved",
)
ACTIVE_VISIT_STATUSES: Final[tuple[str, ...]] = ("Planned", "In Progress")
ACTIVE_DOCUMENT_STATUSES: Final[tuple[str, ...]] = ("Draft", "Active")


def get_permission_query_conditions(user: str | None = None, doctype: str | None = None) -> str:
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if user == "Administrator" or roles.intersection(UNRESTRICTED_ROLES):
        return ""
    scoped_roles = roles.intersection(SCOPED_ROLES)
    if not scoped_roles:
        return "1=0"
    return _project_condition(user, scoped_roles)


def has_permission(
    doc: Any,
    ptype: str | None = None,
    user: str | None = None,
    debug: bool = False,
) -> bool | None:
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if user == "Administrator" or roles.intersection(UNRESTRICTED_ROLES):
        return None
    if not roles.intersection(SCOPED_ROLES):
        return False
    if ptype not in {None, "read", "select", "report"}:
        return False
    return _is_assigned_project(str(doc.name), user, roles)


def _project_condition(user: str, roles: set[str]) -> str:
    return project_visibility_condition(
        f"`tab{DOCTYPE}`.`name`",
        user=user,
        roles=roles,
    )


def project_visibility_condition(
    project_expression: str,
    *,
    user: str,
    roles: set[str] | None = None,
) -> str:
    """Return one SQL predicate for the projects visible to a scoped Desk user.

    ``project_expression`` is supplied only from the versioned ACL registry. It
    must never contain request data or another user-controlled value.
    """

    roles = roles or set(frappe.get_roles(user))
    escaped_user = frappe.db.escape(user)
    step_statuses = _sql_values(ACTIVE_STEP_STATUSES)
    request_statuses = _sql_values(ACTIVE_REQUEST_STATUSES)
    visit_statuses = _sql_values(ACTIVE_VISIT_STATUSES)
    document_statuses = _sql_values(ACTIVE_DOCUMENT_STATUSES)
    conditions = [
        f"exists (select 1 from `tabFerum Project Process Step` step where step.service_project = {project_expression} and step.responsible_user = {escaped_user} and step.status in ({step_statuses}))"
    ]
    if "Инженер" in roles:
        conditions.extend(
            [
                f"exists (select 1 from `tabFerum Project Object` obj where obj.service_project = {project_expression} and obj.responsible_engineer = {escaped_user} and obj.status = 'Active')",
                f"exists (select 1 from `tabFerum Service Request` req where req.service_project = {project_expression} and req.assigned_engineer = {escaped_user} and req.status in ({request_statuses}))",
                f"exists (select 1 from `tabFerum Maintenance Visit` visit where visit.service_project = {project_expression} and visit.assigned_engineer = {escaped_user} and visit.status in ({visit_statuses}))",
            ]
        )
    if "Офис-менеджер" in roles:
        conditions.extend(
            [
                f"exists (select 1 from `tabFerum Project Document` doc where doc.service_project = {project_expression} and doc.owner_user = {escaped_user} and doc.status in ({document_statuses}))",
            ]
        )
    return "(" + " or ".join(conditions) + ")"


def scoped_project_roles(user: str) -> set[str]:
    """Return active project-scoped roles, unless an explicit broad role wins."""

    roles = set(frappe.get_roles(user))
    if user == "Administrator" or roles.intersection(UNRESTRICTED_ROLES):
        return set()
    return roles.intersection(SCOPED_ROLES)


def can_access_project(project: str, user: str) -> bool:
    """Evaluate the same assignment policy used by list-query conditions."""

    roles = scoped_project_roles(user)
    if not roles:
        return True
    return _is_assigned_project(project, user, roles)


def _is_assigned_project(project: str, user: str, roles: set[str]) -> bool:
    if frappe.db.exists(
        "Ferum Project Process Step",
        {
            "service_project": project,
            "responsible_user": user,
            "status": ["in", ACTIVE_STEP_STATUSES],
        },
    ):
        return True
    if "Инженер" in roles:
        for doctype, fieldname, status_filter in (
            ("Ferum Project Object", "responsible_engineer", "Active"),
            ("Ferum Service Request", "assigned_engineer", ["in", ACTIVE_REQUEST_STATUSES]),
            ("Ferum Maintenance Visit", "assigned_engineer", ["in", ACTIVE_VISIT_STATUSES]),
        ):
            if frappe.db.exists(
                doctype,
                {"service_project": project, fieldname: user, "status": status_filter},
            ):
                return True
    if "Офис-менеджер" in roles:
        if frappe.db.exists(
            "Ferum Project Document",
            {
                "service_project": project,
                "owner_user": user,
                "status": ["in", ACTIVE_DOCUMENT_STATUSES],
            },
        ):
            return True
    return False


def _sql_values(values: tuple[str, ...]) -> str:
    return ", ".join(frappe.db.escape(value) for value in values)
