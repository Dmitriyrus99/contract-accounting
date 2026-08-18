"""CA-12 launch assessment and explicitly confirmed generation commands."""

from __future__ import annotations

from typing import Any, Final

import frappe
from frappe import _

from contract_accounting.api.processes import generate_project_process
from contract_accounting.setup.launch_template import TEMPLATE_CODE, TEMPLATE_VERSION

CONFIRMATION_TOKEN: Final[str] = "CONFIRM_NO_HISTORY_BACKFILL"
_ROLES: Final[frozenset[str]] = frozenset(
    {
        "Владелец процесса",
        "Менеджер проектов",
        "Руководитель проектов",
        "System Manager",
    }
)


@frappe.whitelist()
def get_launch_assessment(service_project: str) -> dict[str, Any]:
    """Assess current state without creating stages or claiming historical completion."""

    project = _project(service_project, "read")
    template = frappe.db.get_value(
        "Ferum Process Template",
        {"code": TEMPLATE_CODE, "version": TEMPLATE_VERSION, "status": "Published"},
        "name",
    )
    processes = frappe.get_all(
        "Ferum Project Process",
        filters={"service_project": project.name, "process_type": "Launch"},
        fields=["name", "status", "template_version", "generated_at"],
        order_by="generated_at desc",
    )
    eligible = project.legal_status in {
        "Approved",
        "Signing",
        "Signed",
        "In Force",
    } and project.execution_status in {"Not Started", "Launching"}
    return {
        "service_project": project.name,
        "legal_status": project.legal_status,
        "execution_status": project.execution_status,
        "reference_template": template,
        "reference_version": TEMPLATE_VERSION,
        "eligible_for_generation": eligible and bool(template),
        "existing_launch_processes": processes,
        "history_policy": "NO_AUTOMATIC_COMPLETED_OR_NOT_APPLICABLE_BACKFILL",
        "requires_manual_evidence_mapping": bool(
            project.execution_status in {"Active", "Suspended", "Completed", "Stopped"}
            and not processes
        ),
        "personnel_readiness": "BLOCKED_PENDING_MG-CA-015",
    }


@frappe.whitelist(methods=["POST"])
def generate_reference_launch_process(
    service_project: str,
    generation_key: str,
    requirement_revision: str,
    owner_confirmation: str,
) -> dict[str, Any]:
    """Generate v1 only after an explicit no-history-backfill acknowledgement."""

    _require_role()
    if owner_confirmation != CONFIRMATION_TOKEN:
        frappe.throw(_("Generation требует exact owner confirmation token."))
    assessment = get_launch_assessment(service_project)
    if not assessment["eligible_for_generation"]:
        frappe.throw(_("Service Project не подходит для reference Launch generation."))
    active = frappe.db.get_value(
        "Ferum Project Process",
        {
            "service_project": service_project,
            "process_type": "Launch",
            "status": ["in", ["Planned", "Active"]],
        },
        "name",
    )
    if active:
        return {
            "project_process": active,
            "created": False,
            "history_backfilled": False,
            "personnel_readiness": "BLOCKED_PENDING_MG-CA-015",
        }
    result = generate_project_process(
        service_project,
        str(assessment["reference_template"]),
        generation_key,
        "CA-12 owner-confirmed reference Launch; no historical completion backfill",
        requirement_revision,
    )
    return {
        **result,
        "history_backfilled": False,
        "personnel_readiness": "BLOCKED_PENDING_MG-CA-015",
    }


def _project(name: str, permission_type: str) -> Any:
    if not frappe.db.exists("Ferum Service Project", name):
        frappe.throw(_("Ferum Service Project не найден."), frappe.DoesNotExistError)
    document = frappe.get_doc("Ferum Service Project", name)
    document.check_permission(permission_type)
    return document


def _require_role() -> None:
    if frappe.session.user == "Administrator":
        return
    if not set(frappe.get_roles()).intersection(_ROLES):
        frappe.throw(
            _("Недостаточно прав для Launch generation."), frappe.PermissionError
        )
