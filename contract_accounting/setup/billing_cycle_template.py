"""Idempotent CA-13 recurring Billing Cycle Process Template installation."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Final

import frappe
from frappe import _

TEMPLATE_CODE: Final[str] = "FERUM-BILLING-CYCLE"
TEMPLATE_VERSION: Final[int] = 1
STAGE_CODE: Final[str] = "PERIOD_CLOSING"
STEPS: Final[tuple[tuple[str, str, str, str, str | None], ...]] = (
    (
        "WORK_COMPLETED",
        "Confirm Work Completed for Period",
        "Manual Confirmation",
        "ERP Check",
        None,
    ),
    (
        "EXECUTION_CONFIRMED",
        "Confirm Execution Evidence",
        "Manual Confirmation",
        "ERP Check",
        "WORK_COMPLETED",
    ),
    (
        "ACT_PREPARED",
        "Prepare Act",
        "Document",
        "Document",
        "EXECUTION_CONFIRMED",
    ),
    (
        "INVOICE_PREPARED",
        "Prepare Invoice",
        "ERP Document",
        "ERP Check",
        "ACT_PREPARED",
    ),
    (
        "UPD_OR_SF_PREPARED",
        "Prepare UPD or Invoice Factura",
        "Document",
        "Document",
        "INVOICE_PREPARED",
    ),
    (
        "DOCUMENTS_APPROVED",
        "Approve Closing Documents",
        "Approval",
        "Approval",
        "UPD_OR_SF_PREPARED",
    ),
    (
        "DOCUMENTS_SENT",
        "Send Closing Documents",
        "Outgoing Letter",
        "Communication",
        "DOCUMENTS_APPROVED",
    ),
    (
        "CUSTOMER_RECEIPT",
        "Record Customer Receipt",
        "Incoming Letter",
        "Communication",
        "DOCUMENTS_SENT",
    ),
    (
        "PAYMENT_RECEIVED",
        "Control Payment",
        "Payment",
        "Payment Check",
        "CUSTOMER_RECEIPT",
    ),
)


def ensure_reference_billing_cycle_template() -> str:
    """Install one immutable recurring process graph; never create cycle history."""

    existing = frappe.db.get_value(
        "Ferum Process Template",
        {"code": TEMPLATE_CODE, "version": TEMPLATE_VERSION},
        ("name", "status"),
        as_dict=True,
    )
    if existing:
        _validate_existing(existing.name, existing.status)
        return str(existing.name)
    template = frappe.get_doc(
        {"doctype": "Ferum Process Template", **_expected_template("Draft")}
    ).insert(ignore_permissions=True)
    stage = frappe.get_doc(
        {
            "doctype": "Ferum Stage Template",
            "process_template": template.name,
            **_expected_stage(),
        }
    ).insert(ignore_permissions=True)
    for sequence, (code, title, evidence, step_type, dependency) in enumerate(STEPS, start=1):
        frappe.get_doc(
            {
                "doctype": "Ferum Step Template",
                "stage_template": stage.name,
                **_expected_step((code, title, evidence, step_type, dependency), sequence),
            }
        ).insert(ignore_permissions=True)
    from contract_accounting.api.processes import publish_process_template

    publish_process_template(template.name)
    return template.name


def _validate_existing(name: str, status: str) -> None:
    if status != "Published":
        frappe.throw(
            _("Existing FERUM-BILLING-CYCLE v1 is not Published; manual reconciliation required.")
        )
    _assert_values(
        "FERUM-BILLING-CYCLE v1 template",
        frappe.db.get_value(
            "Ferum Process Template",
            name,
            tuple(_expected_template("Published")),
            as_dict=True,
        ),
        _expected_template("Published"),
    )
    stages = frappe.get_all(
        "Ferum Stage Template",
        filters={"process_template": name},
        fields=["name", "stage_code"],
        order_by="sequence asc",
    )
    if len(stages) != 1 or stages[0].stage_code != STAGE_CODE:
        frappe.throw(_("Existing FERUM-BILLING-CYCLE v1 stage graph differs."))
    _assert_values(
        "FERUM-BILLING-CYCLE v1 stage",
        frappe.db.get_value(
            "Ferum Stage Template",
            stages[0].name,
            tuple(_expected_stage()),
            as_dict=True,
        ),
        _expected_stage(),
    )
    steps = frappe.get_all(
        "Ferum Step Template",
        filters={"stage_template": stages[0].name},
        fields=[
            "name",
            "step_code",
            "completion_evidence_type",
            "depends_on_step_codes",
            "blocking",
        ],
        order_by="sequence asc",
    )
    if [row.step_code for row in steps] != [definition[0] for definition in STEPS]:
        frappe.throw(_("Existing FERUM-BILLING-CYCLE v1 step graph differs."))
    for sequence, (row, definition) in enumerate(zip(steps, STEPS, strict=True), start=1):
        _assert_values(
            f"FERUM-BILLING-CYCLE v1 step {row.step_code}",
            frappe.db.get_value(
                "Ferum Step Template",
                row.name,
                tuple(_expected_step(definition, sequence)),
                as_dict=True,
            ),
            _expected_step(definition, sequence),
        )


def _expected_template(status: str) -> dict[str, Any]:
    return {
        "code": TEMPLATE_CODE,
        "title": "Ferum Recurring Billing Cycle",
        "version": TEMPLATE_VERSION,
        "process_type": "Period Closing",
        "scope_rule": {
            "and": [
                {"in": [{"var": "project.legal_status"}, ["Signed", "In Force"]]},
                {
                    "in": [
                        {"var": "project.execution_status"},
                        ["Active", "Completed"],
                    ]
                },
            ]
        },
        "effective_from": "2026-08-18",
        "status": status,
        "change_note": "CA-13 recurring period closing v1; no automatic history backfill.",
    }


def _expected_stage() -> dict[str, Any]:
    return {
        "stage_code": STAGE_CODE,
        "title": "Billing Cycle",
        "description": "One evidence-backed closing cycle for one exact period.",
        "sequence": 1,
        "purpose": "Close applicable document and payment milestones for the period.",
        "entry_rule": {},
        "exit_rule": {},
        "default_owner_role": "Бухгалтер",
        "gate_policy": {
            "mode": "All Blocking Steps",
            "not_applicable": "Explicit reason required",
            "override": "Role Controlled",
        },
        "parallelism": "Sequential",
        "active": 1,
    }


def _expected_step(
    definition: tuple[str, str, str, str, str | None], sequence: int
) -> dict[str, Any]:
    code, title, evidence, step_type, dependency = definition
    return {
        "step_code": code,
        "title": title,
        "description": "CA-13 source-linked period-closing milestone.",
        "sequence": sequence,
        "action_type": title,
        "step_type": step_type,
        "requirement_source_policy": "None",
        "requirement_match_rule": {},
        "responsible_role": "Бухгалтер",
        "approver_role": "Руководитель проектов" if step_type == "Approval" else None,
        "depends_on_step_codes": dependency,
        "deadline_type": "None",
        "condition_rule": {},
        "activation_rule": {},
        "criticality": (
            "Conditional Mandatory"
            if code in {"ACT_PREPARED", "UPD_OR_SF_PREPARED"}
            else "Mandatory"
        ),
        "blocking": 1,
        "completion_evidence_type": evidence,
        "failure_action": "Block the Billing Cycle gate and expose exact source.",
        "timeout_action": "Expose overdue cycle action; no automatic completion.",
        "active": 1,
    }


def _assert_values(label: str, actual: Any, expected: dict[str, Any]) -> None:
    if not actual:
        frappe.throw(_("{0} is missing.").format(label))
    changed = [
        fieldname
        for fieldname, value in expected.items()
        if _canonical(actual.get(fieldname)) != _canonical(value)
    ]
    if changed:
        frappe.throw(_("{0} differs in fields: {1}.").format(label, ", ".join(changed)))


def _canonical(value: Any) -> Any:
    if value == "":
        return None
    if isinstance(value, str) and value[:1] in {"{", "["}:
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, (date, datetime)):
        return str(value)
    return value
