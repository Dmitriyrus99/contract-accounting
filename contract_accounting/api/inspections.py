"""Typed CA-12 Inspection lifecycle and derived-result commands."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Final, TypeVar

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime

from contract_accounting.contract_accounting.doctype.ferum_inspection.ferum_inspection import (
    INSPECTION_WRITE_FLAG,
)
from contract_accounting.domain.process import canonical_snapshot

_T = TypeVar("_T")
INSPECTION_DOCTYPE: Final[str] = "Ferum Inspection"
_EXECUTION_ROLES: Final[frozenset[str]] = frozenset(
    {"Инженер", "Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_MANAGER_ROLES: Final[frozenset[str]] = frozenset(
    {"Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_APPROVAL_ROLES: Final[frozenset[str]] = frozenset(
    {"Руководитель проектов", "System Manager"}
)


@frappe.whitelist(methods=["POST"])
def create_inspection_from_step(
    process_step: str,
    project_object: str,
    planned_date: str,
    idempotency_key: str,
    inspection_type: str = "Initial",
    object_system: str | None = None,
    lead_inspector: str | None = None,
    contractor: str | None = None,
    checklist_template_reference: str | None = None,
    template_version_snapshot: str | dict[str, Any] | None = None,
    items: str | list[dict[str, Any]] | None = None,
    team: str | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create one planned Inspection from an active typed process step."""

    _require_role(_EXECUTION_ROLES, "create Inspection")
    key = _required(idempotency_key, "idempotency_key")
    step = _authorized("Ferum Project Process Step", process_step, "read")
    if step.status not in {"Ready", "In Progress"}:
        frappe.throw(
            _("Inspection создаётся только из Ready/In Progress Process Step.")
        )
    if "inspection" not in str(step.action_type or "").lower():
        frappe.throw(_("Process Step не является Inspection step."))
    existing = frappe.db.get_value(
        INSPECTION_DOCTYPE,
        {"idempotency_key": key},
        ("name", "process_step", "project_object", "inspection_type"),
        as_dict=True,
    )
    if existing:
        if (
            existing.process_step,
            existing.project_object,
            existing.inspection_type,
        ) != (
            step.name,
            project_object,
            inspection_type,
        ):
            frappe.throw(_("Inspection idempotency_key принадлежит другому context."))
        return _result(existing.name, created=False)
    if inspection_type == "Initial" and frappe.db.exists(
        INSPECTION_DOCTYPE,
        {
            "project_object": project_object,
            "inspection_type": "Initial",
            "status": ["in", ["Planned", "In Progress", "Completed"]],
        },
    ):
        frappe.throw(_("Project Object уже имеет active Initial Inspection."))
    template_snapshot = _json_object(
        template_version_snapshot, "template_version_snapshot"
    )
    if not template_snapshot:
        frappe.throw(_("template_version_snapshot не может быть пустым."))
    document = frappe.get_doc(
        {
            "doctype": INSPECTION_DOCTYPE,
            "service_project": step.service_project,
            "project_process": step.project_process,
            "process_step": step.name,
            "project_object": project_object,
            "object_system": object_system,
            "inspection_type": inspection_type,
            "status": "Planned",
            "planned_date": getdate(planned_date),
            "lead_inspector": lead_inspector or frappe.session.user,
            "contractor": contractor,
            "checklist_template_reference": checklist_template_reference,
            "template_version_snapshot": template_snapshot,
            "system_inventory_snapshot": {},
            "report_snapshot": {},
            "items": _json_list(items, "items"),
            "team": _json_list(team, "team"),
            "idempotency_key": key,
        }
    )
    document.insert()
    return _result(document.name, created=True)


@frappe.whitelist(methods=["POST"])
def start_inspection(
    inspection: str,
    system_inventory_snapshot: str | dict[str, Any],
) -> dict[str, Any]:
    """Freeze the object/system inventory at the server start timestamp."""

    _require_role(_EXECUTION_ROLES, "start Inspection")
    document = _locked_inspection(inspection)
    if document.status != "Planned":
        frappe.throw(_("Только Planned Inspection можно начать."))
    inventory = _json_object(system_inventory_snapshot, "system_inventory_snapshot")
    if not inventory:
        frappe.throw(_("system_inventory_snapshot не может быть пустым."))
    document.system_inventory_snapshot = inventory
    document.status = "In Progress"
    document.actual_start = now_datetime()
    document.snapshot_at = document.actual_start
    _save(document)
    return _result(document.name)


@frappe.whitelist(methods=["POST"])
def complete_inspection(
    inspection: str,
    outcome: str,
    summary: str,
    results: str | list[dict[str, Any]],
    evidence: str | list[dict[str, Any]],
) -> dict[str, Any]:
    """Complete once, then derive report, Findings and Photo Evidence transactionally."""

    _require_role(_EXECUTION_ROLES, "complete Inspection")
    document = _locked_inspection(inspection)
    if document.status in {"Completed", "Approved"}:
        return _result(document.name, created=False)
    if document.status != "In Progress":
        frappe.throw(_("Только In Progress Inspection можно завершить."))
    if outcome not in {"Ready", "Ready With Findings", "Not Ready"}:
        frappe.throw(_("Некорректный Inspection outcome."))
    _apply_results(document, _json_list(results, "results"))
    _apply_evidence(document, _json_list(evidence, "evidence"))
    document.outcome = outcome
    document.summary = _required(summary, "summary")
    document.actual_end = now_datetime()
    report_payload = _report_payload(document)
    report_snapshot, _report_hash = canonical_snapshot(report_payload)
    document.report_snapshot = report_snapshot
    document.report_document = _get_or_create_report(document, report_payload)
    document.status = "Completed"
    _save(document)
    outputs = _derive_outputs(document)
    document = frappe.get_doc(INSPECTION_DOCTYPE, document.name)
    return {**_result(document.name), **outputs}


@frappe.whitelist(methods=["POST"])
def approve_inspection(inspection: str) -> dict[str, Any]:
    """Manager approval freezes the completed Inspection fact."""

    _require_role(_APPROVAL_ROLES, "approve Inspection")
    document = _locked_inspection(inspection)
    if document.status == "Approved":
        return _result(document.name, created=False)
    if document.status != "Completed":
        frappe.throw(_("Только Completed Inspection можно утвердить."))
    missing = [
        row.item_code
        for row in document.items
        if row.result in {"Defect", "Observation"} and not row.finding
    ]
    if missing:
        frappe.throw(
            _("Inspection results не имеют Findings: {0}.").format(", ".join(missing))
        )
    document.status = "Approved"
    document.manager_approved_at = now_datetime()
    document.manager_approved_by = frappe.session.user
    _save(document)
    return _result(document.name)


@frappe.whitelist(methods=["POST"])
def record_customer_inspection_status(
    inspection: str,
    target_status: str,
) -> dict[str, Any]:
    """Record send/decision without conflating manager and customer approval."""

    _require_role(_MANAGER_ROLES, "record customer Inspection status")
    document = _locked_inspection(inspection)
    if document.status != "Approved":
        frappe.throw(_("Customer flow требует Approved Inspection."))
    allowed = {
        "Pending": {"Sent"},
        "Sent": {"Approved", "Rejected"},
        "Approved": set(),
        "Rejected": set(),
    }
    if target_status not in allowed.get(document.customer_approval, set()):
        frappe.throw(_("Недопустимый customer Inspection transition."))
    document.customer_approval = target_status
    if target_status == "Sent":
        document.customer_sent_at = now_datetime()
        document.customer_sent_by = frappe.session.user
    else:
        document.customer_decided_at = now_datetime()
        document.customer_decided_by = frappe.session.user
    _save(document)
    return _result(document.name)


@frappe.whitelist(methods=["POST"])
def cancel_inspection(inspection: str, reason: str) -> dict[str, Any]:
    _require_role(_MANAGER_ROLES, "cancel Inspection")
    document = _locked_inspection(inspection)
    if document.status not in {"Planned", "In Progress"}:
        frappe.throw(_("Отменить можно только Planned/In Progress Inspection."))
    document.status = "Cancelled"
    document.cancellation_reason = _required(reason, "reason")
    _save(document)
    return _result(document.name)


@frappe.whitelist()
def get_inspection_trace(inspection: str) -> dict[str, Any]:
    document = _authorized(INSPECTION_DOCTYPE, inspection, "read")
    return {
        **_result(document.name),
        "findings": frappe.get_all(
            "Ferum Finding",
            filters={
                "source_doctype": INSPECTION_DOCTYPE,
                "source_name": document.name,
            },
            fields=["name", "category", "severity", "status", "decision"],
            order_by="name asc",
        ),
        "photo_evidence": frappe.get_all(
            "Ferum Photo Evidence",
            filters={
                "source_doctype": INSPECTION_DOCTYPE,
                "source_name": document.name,
            },
            fields=["name", "file", "review_status", "content_hash"],
            order_by="name asc",
        ),
    }


def _apply_results(document: Any, results: list[dict[str, Any]]) -> None:
    by_code = {str(row.item_code).upper(): row for row in document.items}
    seen: set[str] = set()
    for payload in results:
        code = str(payload.get("item_code") or "").strip().upper()
        if code not in by_code or code in seen:
            frappe.throw(
                _(
                    "Inspection result item_code неизвестен или продублирован: {0}."
                ).format(code)
            )
        seen.add(code)
        row = by_code[code]
        for fieldname in (
            "result",
            "severity",
            "finding_title",
            "observation",
            "photo_file",
        ):
            if fieldname in payload:
                row.set(fieldname, payload[fieldname])
    if seen != set(by_code):
        frappe.throw(_("Completion требует результат для каждого checklist item."))


def _apply_evidence(document: Any, rows: list[dict[str, Any]]) -> None:
    if not rows:
        frappe.throw(_("Inspection completion evidence обязателен."))
    document.set("completion_evidence", [])
    for payload in rows:
        file_name = _required(str(payload.get("file") or ""), "evidence.file")
        content_hash = frappe.db.get_value("File", file_name, "content_hash")
        if not content_hash:
            frappe.throw(_("Inspection evidence File требует content_hash."))
        document.append(
            "completion_evidence",
            {
                "evidence_type": payload.get("evidence_type") or "Other",
                "file": file_name,
                "captured_at": payload.get("captured_at") or now_datetime(),
                "captured_by": payload.get("captured_by") or frappe.session.user,
                "content_hash": content_hash,
                "note": payload.get("note"),
            },
        )


def _report_payload(document: Any) -> dict[str, Any]:
    return {
        "inspection": document.name,
        "service_project": document.service_project,
        "project_object": document.project_object,
        "inspection_type": document.inspection_type,
        "snapshot_at": document.snapshot_at,
        "actual_start": document.actual_start,
        "actual_end": document.actual_end,
        "outcome": document.outcome,
        "summary": document.summary,
        "inventory": json.loads(document.system_inventory_snapshot),
        "items": [
            {
                "item_code": row.item_code,
                "object_system": row.object_system,
                "component_code": row.component_code,
                "component_name": row.component_name,
                "question": row.question,
                "result": row.result,
                "severity": row.severity,
                "finding_title": row.finding_title,
                "observation": row.observation,
                "photo_file": row.photo_file,
            }
            for row in document.items
        ],
    }


def _get_or_create_report(document: Any, payload: dict[str, Any]) -> str:
    existing = frappe.db.get_value(
        "Ferum Project Document",
        {
            "source_doctype": INSPECTION_DOCTYPE,
            "source_name": document.name,
            "document_number": f"{document.name}-REPORT",
        },
        "name",
    )
    if existing:
        return str(existing)
    report = frappe.get_doc(
        {
            "doctype": "Ferum Project Document",
            "document_type": "Other",
            "document_number": f"{document.name}-REPORT",
            "document_date": getdate(document.actual_end),
            "version": "1",
            "source_doctype": INSPECTION_DOCTYPE,
            "source_name": document.name,
            "owner_user": frappe.session.user,
            "confidentiality": "Internal",
            "comment": "Initial Inspection Report; structured source snapshot is stored on Inspection.",
        }
    ).insert()
    return report.name


def _derive_outputs(document: Any) -> dict[str, Any]:
    finding_count = 0
    photo_count = 0
    for row in document.items:
        if row.result in {"Observation", "Defect"} and not row.finding:
            finding = frappe.get_doc(
                {
                    "doctype": "Ferum Finding",
                    "source_doctype": INSPECTION_DOCTYPE,
                    "source_name": document.name,
                    "category": row.result,
                    "severity": row.severity,
                    "title": row.finding_title,
                    "description": json.dumps(
                        {
                            "inspection_item_code": row.item_code,
                            "object_system": row.object_system,
                            "component_code": row.component_code,
                            "component_name": row.component_name,
                            "question": row.question,
                            "result_detail": row.observation,
                        },
                        ensure_ascii=False,
                    ),
                }
            ).insert()
            row.finding = finding.name
            finding_count += 1
        if row.photo_file and not frappe.db.exists(
            "Ferum Photo Evidence",
            {
                "source_doctype": INSPECTION_DOCTYPE,
                "source_name": document.name,
                "file": row.photo_file,
            },
        ):
            frappe.get_doc(
                {
                    "doctype": "Ferum Photo Evidence",
                    "source_doctype": INSPECTION_DOCTYPE,
                    "source_name": document.name,
                    "category": "Defect" if row.result == "Defect" else "General",
                    "file": row.photo_file,
                    "comment": f"Inspection item {row.item_code}",
                }
            ).insert()
            photo_count += 1
    _save(document)
    return {"finding_count": finding_count, "photo_evidence_count": photo_count}


def _locked_inspection(name: str) -> Any:
    if not frappe.db.get_value(INSPECTION_DOCTYPE, name, "name", for_update=True):
        frappe.throw(_("Inspection не найден."), frappe.DoesNotExistError)
    return _authorized(INSPECTION_DOCTYPE, name, "write")


def _authorized(doctype: str, name: str, permission_type: str) -> Any:
    if not frappe.db.exists(doctype, name):
        frappe.throw(
            _("{0} не найден: {1}.").format(doctype, name), frappe.DoesNotExistError
        )
    document = frappe.get_doc(doctype, name)
    document.check_permission(permission_type)
    return document


def _save(document: Any) -> None:
    _with_flag(
        INSPECTION_WRITE_FLAG, True, lambda: document.save(ignore_permissions=True)
    )


def _result(name: str, *, created: bool | None = None) -> dict[str, Any]:
    document = frappe.get_doc(INSPECTION_DOCTYPE, name)
    result = {
        "inspection": document.name,
        "status": document.status,
        "outcome": document.outcome,
        "report_document": document.report_document,
        "customer_approval": document.customer_approval,
    }
    if created is not None:
        result["created"] = created
    return result


def _json_object(value: str | dict[str, Any] | None, fieldname: str) -> dict[str, Any]:
    parsed = frappe.parse_json(value) if isinstance(value, str) else value
    parsed = {} if parsed is None else parsed
    if not isinstance(parsed, dict):
        frappe.throw(_("{0} должен быть JSON object.").format(fieldname))
    return parsed


def _json_list(
    value: str | list[dict[str, Any]] | None, fieldname: str
) -> list[dict[str, Any]]:
    parsed = frappe.parse_json(value) if isinstance(value, str) else value
    parsed = [] if parsed is None else parsed
    if not isinstance(parsed, list) or any(
        not isinstance(item, dict) for item in parsed
    ):
        frappe.throw(_("{0} должен быть JSON array of objects.").format(fieldname))
    return parsed


def _required(value: str | None, fieldname: str) -> str:
    text = (value or "").strip()
    if not text:
        frappe.throw(_("{0} обязателен.").format(fieldname))
    return text


def _require_role(roles: frozenset[str], operation: str) -> None:
    if frappe.session.user == "Administrator":
        return
    if not set(frappe.get_roles()).intersection(roles):
        frappe.throw(
            _("Недостаточно прав: {0}.").format(operation), frappe.PermissionError
        )


def _with_flag(flag: str, value: Any, callback: Callable[[], _T]) -> _T:
    previous = frappe.flags.get(flag)
    frappe.flags[flag] = value
    try:
        return callback()
    finally:
        frappe.flags[flag] = previous
