"""Typed DP-05 calendar assignment and primary deadline-source commands."""

from __future__ import annotations

from typing import Any, Final
from uuid import uuid4

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

from contract_accounting.domain.deadline import (
    DeadlineRule,
    DeadlineRuleError,
    DeadlineSnapshot,
    calculate_deadline,
)
from contract_accounting.infrastructure.calendar_registry import (
    ResolvedCalendar,
    resolve_calendar,
)
from contract_accounting.infrastructure.deadline_guard import (
    CALENDAR_ASSIGNMENT_WRITE_FLAG,
    DEADLINE_EVENT_WRITE_FLAG,
    DEADLINE_SOURCE_WRITE_FLAG,
)

_ASSIGN_ROLES: Final[frozenset[str]] = frozenset({"Руководитель проектов", "System Manager"})
_INITIAL_DEADLINE_ROLES: Final[frozenset[str]] = frozenset(
    {"Юрист", "Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_RECALCULATE_ROLES: Final[frozenset[str]] = frozenset({"Руководитель проектов", "System Manager"})


@frappe.whitelist(methods=["POST"])
def assign_calendar(
    *,
    scope_type: str,
    company: str,
    calendar_revision: str,
    reason: str,
    service_project: str | None = None,
    contract_basis: str | None = None,
    evidence_document: str | None = None,
) -> dict[str, Any]:
    """Activate one Company or explicit Contract revision and retain the old assignment."""

    _require_role(_ASSIGN_ROLES, "assign production calendar")
    reason = _required(reason, "reason")
    if scope_type not in {"Company", "Contract"}:
        frappe.throw(_("scope_type должен быть Company или Contract."))
    if not frappe.db.get_value("Company", company, "name", for_update=True):
        frappe.throw(_("Company не найдена."))
    revision = frappe.get_doc("Ferum Calendar Revision", calendar_revision)
    if revision.status != "Published":
        frappe.throw(_("Назначать можно только Published Calendar Revision."))
    if scope_type == "Contract":
        if not service_project:
            frappe.throw(_("Contract Calendar требует service_project."))
        if not frappe.db.get_value(
            "Ferum Service Project", service_project, "name", for_update=True
        ):
            frappe.throw(_("Service Project не найден."))
        contract_basis = _required(contract_basis, "contract_basis")
        if not evidence_document:
            frappe.throw(_("Contract Calendar требует evidence_document."))
    else:
        service_project = None
        contract_basis = None
        evidence_document = None
    filters: dict[str, Any] = {
        "scope_type": scope_type,
        "company": company,
        "calendar_year": revision.calendar_year,
        "status": "Active",
    }
    if scope_type == "Contract":
        filters["service_project"] = service_project
    existing_name = frappe.db.get_value(
        "Ferum Calendar Assignment", filters, "name", for_update=True
    )
    if existing_name:
        existing = frappe.get_doc("Ferum Calendar Assignment", existing_name)
        if (
            existing.calendar_revision == revision.name
            and existing.contract_basis == contract_basis
            and existing.evidence_document == evidence_document
        ):
            return _assignment_result(existing, created=False)

    savepoint = f"calendar_assignment_{uuid4().hex}"
    frappe.db.savepoint(savepoint)
    try:
        assignment = frappe.get_doc(
            {
                "doctype": "Ferum Calendar Assignment",
                "assignment_key": f"{scope_type}:{company}:{service_project or '-'}:{revision.calendar_year}:{uuid4().hex}",
                "scope_type": scope_type,
                "company": company,
                "service_project": service_project,
                "calendar_year": revision.calendar_year,
                "calendar_revision": revision.name,
                "status": "Active",
                "contract_basis": contract_basis,
                "evidence_document": evidence_document,
                "assigned_by": frappe.session.user,
                "assigned_at": now_datetime(),
                "reason": reason,
            }
        )
        _with_flag(
            CALENDAR_ASSIGNMENT_WRITE_FLAG,
            lambda: assignment.insert(ignore_permissions=True),
        )
        if existing_name:
            existing = frappe.get_doc("Ferum Calendar Assignment", existing_name)
            existing.status = "Superseded"
            existing.superseded_by = assignment.name
            _with_flag(
                CALENDAR_ASSIGNMENT_WRITE_FLAG,
                lambda: existing.save(ignore_permissions=True),
            )
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise
    return _assignment_result(assignment, created=True)


@frappe.whitelist(methods=["POST"])
def set_signature_deadline(
    *,
    project_document: str,
    triggered_at: str,
    offset_days: int | str,
    offset_unit: str,
    reason: str,
    warning_days: int | str = 3,
    escalation_days: int | str = 1,
    manual_recalculation: int | str = 0,
) -> dict[str, Any]:
    """Calculate TCA-A-14-09 on its Project Document primary source."""

    manual = bool(cint(manual_recalculation))
    _require_role(
        _RECALCULATE_ROLES if manual else _INITIAL_DEADLINE_ROLES,
        "recalculate signature deadline" if manual else "set signature deadline",
    )
    document = _locked_doc("Ferum Project Document", project_document)
    document.check_permission("write")
    if document.digital_copy_status == "Signed":
        frappe.throw(_("Signed Project Document не принимает новый signature deadline."))
    result = _calculate_and_attach(
        document=document,
        service_project=document.service_project,
        source_field="signature_due_at",
        triggered_at=triggered_at,
        offset_days=cint(offset_days),
        offset_unit=offset_unit,
        warning_days=cint(warning_days),
        escalation_days=cint(escalation_days),
        reason=reason,
        manual_recalculation=manual,
        calculation_field="signature_deadline_calculation",
        field_prefix="signature_",
    )
    return {"project_document": document.name, **result}


@frappe.whitelist(methods=["POST"])
def create_customer_response_deadline(
    *,
    service_project: str,
    source_doctype: str,
    source_name: str,
    contact: str,
    sent_item: str,
    channel: str,
    sent_at: str,
    sent_evidence: str,
    expected_result: str,
    internal_owner: str,
    offset_days: int | str,
    offset_unit: str,
    reason: str,
    timeout_action: str,
    warning_days: int | str = 3,
    escalation_days: int | str = 1,
) -> dict[str, Any]:
    """Create the structured TCA-A-14-13 source without implementing FR-08 delivery."""

    _require_role(_INITIAL_DEADLINE_ROLES, "create customer response deadline")
    project = _locked_doc("Ferum Service Project", service_project)
    project.check_permission("read")
    reason = _required(reason, "reason")
    resolved, snapshot = _calculate(
        service_project=project.name,
        triggered_at=sent_at,
        offset_days=cint(offset_days),
        offset_unit=offset_unit,
        warning_days=cint(warning_days),
        escalation_days=cint(escalation_days),
    )
    savepoint = f"customer_response_{uuid4().hex}"
    frappe.db.savepoint(savepoint)
    try:
        dependency = frappe.get_doc(
            {
                "doctype": "Ferum External Dependency",
                "service_project": project.name,
                "source_doctype": source_doctype,
                "source_name": source_name,
                "customer": project.customer,
                "contact": contact,
                "sent_item": _required(sent_item, "sent_item"),
                "channel": channel,
                "sent_at": get_datetime(sent_at),
                "sent_evidence": sent_evidence,
                "expected_result": _required(expected_result, "expected_result"),
                "internal_owner": internal_owner,
                "triggered_at": snapshot.triggered_at.replace(tzinfo=None),
                "due_at": snapshot.due_at.replace(tzinfo=None),
                "warning_at": snapshot.warning_at.replace(tzinfo=None),
                "escalation_at": snapshot.escalation_at.replace(tzinfo=None),
                "status": "Waiting External",
                "timeout_action": _required(timeout_action, "timeout_action"),
            }
        )
        _with_flag(DEADLINE_SOURCE_WRITE_FLAG, lambda: dependency.insert(ignore_permissions=True))
        calculation = _insert_calculation(
            document=dependency,
            service_project=project.name,
            source_field="due_at",
            resolved=resolved,
            snapshot=snapshot,
            offset_days=cint(offset_days),
            offset_unit=offset_unit,
            warning_days=cint(warning_days),
            escalation_days=cint(escalation_days),
            reason=reason,
            manual_recalculation=False,
            supersedes=None,
        )
        dependency.deadline_calculation = calculation.name
        _with_flag(DEADLINE_SOURCE_WRITE_FLAG, lambda: dependency.save(ignore_permissions=True))
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise
    return {
        "external_dependency": dependency.name,
        "deadline_calculation": calculation.name,
        "due_at": snapshot.due_at.isoformat(),
        "calendar_scope": resolved.scope_type,
        "created": True,
    }


@frappe.whitelist(methods=["POST"])
def recalculate_customer_response_deadline(
    *,
    external_dependency: str,
    offset_days: int | str,
    offset_unit: str,
    reason: str,
    warning_days: int | str = 3,
    escalation_days: int | str = 1,
) -> dict[str, Any]:
    """Manual, reasoned and append-only recalculation of an open response deadline."""

    _require_role(_RECALCULATE_ROLES, "recalculate customer response deadline")
    dependency = _locked_doc("Ferum External Dependency", external_dependency)
    if dependency.status != "Waiting External":
        frappe.throw(_("Только Waiting External deadline можно пересчитать."))
    result = _calculate_and_attach(
        document=dependency,
        service_project=dependency.service_project,
        source_field="due_at",
        triggered_at=dependency.triggered_at,
        offset_days=cint(offset_days),
        offset_unit=offset_unit,
        warning_days=cint(warning_days),
        escalation_days=cint(escalation_days),
        reason=reason,
        manual_recalculation=True,
        calculation_field="deadline_calculation",
        field_prefix="",
    )
    return {"external_dependency": dependency.name, **result}


def _calculate_and_attach(
    *,
    document: Any,
    service_project: str,
    source_field: str,
    triggered_at: str,
    offset_days: int,
    offset_unit: str,
    warning_days: int,
    escalation_days: int,
    reason: str,
    manual_recalculation: bool,
    calculation_field: str,
    field_prefix: str,
) -> dict[str, Any]:
    reason = _required(reason, "reason")
    existing_name = document.get(calculation_field)
    if manual_recalculation and not existing_name:
        frappe.throw(_("Manual recalculation требует existing calculation."))
    resolved, snapshot = _calculate(
        service_project=service_project,
        triggered_at=triggered_at,
        offset_days=offset_days,
        offset_unit=offset_unit,
        warning_days=warning_days,
        escalation_days=escalation_days,
    )
    if existing_name and not manual_recalculation:
        existing_hash = frappe.db.get_value(
            "Ferum Deadline Calculation", existing_name, "calculation_hash"
        )
        if existing_hash == snapshot.snapshot_hash:
            return {
                "deadline_calculation": existing_name,
                "due_at": snapshot.due_at.isoformat(),
                "calendar_scope": resolved.scope_type,
                "created": False,
            }
        frappe.throw(_("Deadline уже рассчитан; изменение требует manual_recalculation и reason."))
    savepoint = f"deadline_attach_{uuid4().hex}"
    frappe.db.savepoint(savepoint)
    try:
        calculation = _insert_calculation(
            document=document,
            service_project=service_project,
            source_field=source_field,
            resolved=resolved,
            snapshot=snapshot,
            offset_days=offset_days,
            offset_unit=offset_unit,
            warning_days=warning_days,
            escalation_days=escalation_days,
            reason=reason,
            manual_recalculation=manual_recalculation,
            supersedes=existing_name,
        )
        document.set(f"{field_prefix}triggered_at", snapshot.triggered_at.replace(tzinfo=None))
        document.set(f"{field_prefix}due_at", snapshot.due_at.replace(tzinfo=None))
        document.set(f"{field_prefix}warning_at", snapshot.warning_at.replace(tzinfo=None))
        document.set(f"{field_prefix}escalation_at", snapshot.escalation_at.replace(tzinfo=None))
        document.set(calculation_field, calculation.name)
        _with_flag(DEADLINE_SOURCE_WRITE_FLAG, lambda: document.save(ignore_permissions=True))
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise
    return {
        "deadline_calculation": calculation.name,
        "due_at": snapshot.due_at.isoformat(),
        "calendar_scope": resolved.scope_type,
        "created": True,
    }


def _calculate(
    *,
    service_project: str,
    triggered_at: str,
    offset_days: int,
    offset_unit: str,
    warning_days: int,
    escalation_days: int,
) -> tuple[ResolvedCalendar, DeadlineSnapshot]:
    resolved = resolve_calendar(service_project, triggered_at)
    try:
        snapshot = calculate_deadline(
            triggered_at=get_datetime(triggered_at),
            rule=DeadlineRule(
                offset_days=offset_days,
                offset_unit=offset_unit,
                warning_days=warning_days,
                escalation_days=escalation_days,
            ),
            calendar=resolved.calendar,
        )
    except DeadlineRuleError as exc:
        frappe.throw(_("Deadline не рассчитан: {0}.").format(str(exc)))
        raise AssertionError from exc
    return resolved, snapshot


def _insert_calculation(
    *,
    document: Any,
    service_project: str,
    source_field: str,
    resolved: ResolvedCalendar,
    snapshot: DeadlineSnapshot,
    offset_days: int,
    offset_unit: str,
    warning_days: int,
    escalation_days: int,
    reason: str,
    manual_recalculation: bool,
    supersedes: str | None,
) -> Any:
    calculation = frappe.get_doc(
        {
            "doctype": "Ferum Deadline Calculation",
            "service_project": service_project,
            "source_doctype": document.doctype,
            "source_name": document.name,
            "source_field": source_field,
            "calculation_kind": "Manual Recalculation" if manual_recalculation else "Initial",
            "triggered_at": snapshot.triggered_at.replace(tzinfo=None),
            "normalized_anchor_at": snapshot.anchor_at.replace(tzinfo=None),
            "offset_days": offset_days,
            "offset_unit": offset_unit,
            "warning_days": warning_days,
            "escalation_days": escalation_days,
            "due_at": snapshot.due_at.replace(tzinfo=None),
            "warning_at": snapshot.warning_at.replace(tzinfo=None),
            "escalation_at": snapshot.escalation_at.replace(tzinfo=None),
            "calendar_assignment": resolved.assignment_name,
            "calendar_revision": resolved.revision_name,
            "calendar_hash": snapshot.calendar_hash,
            "calendar_snapshot_json": snapshot.snapshot_json,
            "algorithm_version": snapshot.algorithm_version,
            "calculation_hash": snapshot.snapshot_hash,
            "supersedes": supersedes,
            "reason": reason,
            "actor": frappe.session.user,
            "occurred_at": now_datetime(),
        }
    )
    _with_flag(DEADLINE_EVENT_WRITE_FLAG, lambda: calculation.insert(ignore_permissions=True))
    return calculation


def _locked_doc(doctype: str, name: str) -> Any:
    if not frappe.db.get_value(doctype, name, "name", for_update=True):
        frappe.throw(_("{0} не найден.").format(doctype), frappe.DoesNotExistError)
    return frappe.get_doc(doctype, name)


def _assignment_result(document: Any, *, created: bool) -> dict[str, Any]:
    return {
        "calendar_assignment": document.name,
        "scope_type": document.scope_type,
        "calendar_revision": document.calendar_revision,
        "calendar_year": document.calendar_year,
        "created": created,
    }


def _required(value: Any, fieldname: str) -> str:
    text = str(value or "").strip()
    if not text:
        frappe.throw(_("{0} обязательно.").format(fieldname))
    return text


def _require_role(roles: frozenset[str], operation: str) -> None:
    if not roles.intersection(frappe.get_roles(frappe.session.user)):
        frappe.throw(
            _("Недостаточно роли для операции: {0}.").format(operation),
            frappe.PermissionError,
        )


def _with_flag(flag: str, operation: Any) -> Any:
    previous = frappe.flags.get(flag)
    frappe.flags[flag] = True
    try:
        return operation()
    finally:
        frappe.flags[flag] = previous
