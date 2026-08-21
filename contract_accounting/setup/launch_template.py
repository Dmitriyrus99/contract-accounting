"""Idempotent CA-12 reference Launch Template installation."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Final

import frappe
from frappe import _

TEMPLATE_CODE: Final[str] = "FERUM-LAUNCH"
TEMPLATE_VERSION: Final[int] = 1
STAGES: Final[tuple[dict[str, Any], ...]] = (
    {
        "code": "INITIATION",
        "title": "Initiation",
        "role": "Менеджер проектов",
        "steps": (
            (
                "INIT_CONTRACT_DRAFT",
                "Receive Contract Draft",
                "Document",
                "Document",
                None,
            ),
            (
                "INIT_TECH_SPEC",
                "Receive Technical Specification",
                "Document",
                "Document",
                None,
            ),
            (
                "INIT_REQUIREMENTS",
                "Record Contract Requirements",
                "Manual Confirmation",
                "Manual",
                None,
            ),
            (
                "INIT_RESPONSIBILITY",
                "Assign Responsible Persons",
                "Manual Confirmation",
                "Manual",
                None,
            ),
        ),
    },
    {
        "code": "CUSTOMER_ONBOARDING",
        "title": "Customer Contact",
        "role": "Менеджер проектов",
        "steps": (
            (
                "CUST_CHANNEL",
                "Establish Official Customer Channel",
                "Email",
                "Communication",
                None,
            ),
            (
                "CUST_CONTACTS",
                "Register Customer and Technical Contacts",
                "Manual Confirmation",
                "Manual",
                None,
            ),
            (
                "CUST_MEETING",
                "Hold Initial Customer Meeting",
                "Meeting Record",
                "Communication",
                None,
            ),
        ),
    },
    {
        "code": "EXECUTION_MODEL",
        "title": "Execution Scheme",
        "role": "Руководитель проектов",
        "steps": (
            ("EXEC_MODEL", "Approve Execution Model", "Approval", "Approval", None),
            (
                "EXEC_SUBCONTRACT",
                "Record Subcontracting Decision",
                "Manual Confirmation",
                "Manual",
                None,
            ),
            (
                "EXEC_CONTRACTOR_DOCS",
                "Collect Contractor Documents or Record N/A",
                "Document",
                "Document",
                None,
            ),
        ),
    },
    {
        "code": "PERSONNEL_READINESS",
        "title": "Personnel Readiness",
        "role": "Руководитель проектов",
        "steps": (
            (
                "PERSONNEL_READY",
                "Verify Personnel and Credential Readiness",
                "None",
                "Gate Preparation",
                None,
            ),
        ),
    },
    {
        "code": "SITE_MOBILIZATION",
        "title": "Mobilization",
        "role": "Менеджер проектов",
        "steps": (
            (
                "MOB_ACCESS_LETTER",
                "Prepare Access Letter",
                "Document",
                "Document",
                None,
            ),
            (
                "MOB_RESP_ORDER",
                "Prepare Responsible Person Order",
                "Document",
                "Document",
                None,
            ),
            (
                "MOB_PROJECT_DOCS",
                "Request Project Documentation",
                "Outgoing Letter",
                "Communication",
                None,
            ),
            (
                "MOB_CONTACT_CARD",
                "Prepare Company Contact Card",
                "Document",
                "Document",
                None,
            ),
            (
                "MOB_WORK_SCHEDULE",
                "Prepare Work Schedule",
                "Document",
                "Document",
                None,
            ),
            (
                "MOB_MAINT_JOURNALS",
                "Prepare Maintenance Journals",
                "Document",
                "Document",
                None,
            ),
            (
                "MOB_INITIAL_PACKAGE",
                "Send Initial Package",
                "Outgoing Letter",
                "Communication",
                "MOB_WORK_SCHEDULE",
            ),
        ),
    },
    {
        "code": "INITIAL_INSPECTION",
        "title": "Initial Inspection",
        "role": "Менеджер проектов",
        "steps": (
            (
                "INSPECT_INITIAL",
                "Conduct Initial Inspection",
                "Inspection",
                "Inspection",
                None,
            ),
            (
                "INSPECT_ACT",
                "Prepare Initial Inspection Act",
                "Document",
                "Document",
                "INSPECT_INITIAL",
            ),
            (
                "INSPECT_DEFECT_STATEMENT",
                "Prepare Defect Statement",
                "Document",
                "Document",
                "INSPECT_INITIAL",
            ),
            (
                "INSPECT_MANAGER_APPROVAL",
                "Approve Inspection Results",
                "Approval",
                "Approval",
                "INSPECT_INITIAL",
            ),
            (
                "INSPECT_CUSTOMER_SEND",
                "Send Approved Inspection to Customer",
                "Outgoing Letter",
                "Communication",
                "INSPECT_MANAGER_APPROVAL",
            ),
        ),
    },
    {
        "code": "HANDOVER_TO_OPERATIONS",
        "title": "Launch Readiness",
        "role": "Руководитель проектов",
        "steps": (
            (
                "HANDOVER_OPERATIONS",
                "Handover Project to Operations",
                "Manual Confirmation",
                "Manual",
                None,
            ),
            (
                "PROJECT_OPERATIONAL",
                "Confirm Project Operational",
                "Approval",
                "Approval",
                "HANDOVER_OPERATIONS",
            ),
        ),
    },
)


def ensure_reference_launch_template() -> str:
    """Install exactly one immutable v1 graph; never create project history."""

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
    for stage_sequence, definition in enumerate(STAGES, start=1):
        stage = frappe.get_doc(
            {
                "doctype": "Ferum Stage Template",
                "process_template": template.name,
                **_expected_stage(definition, stage_sequence),
            }
        ).insert(ignore_permissions=True)
        for step_sequence, (
            code,
            title,
            evidence_type,
            step_type,
            dependency,
        ) in enumerate(definition["steps"], start=1):
            frappe.get_doc(
                {
                    "doctype": "Ferum Step Template",
                    "stage_template": stage.name,
                    **_expected_step(
                        definition,
                        (code, title, evidence_type, step_type, dependency),
                        step_sequence,
                    ),
                }
            ).insert(ignore_permissions=True)
    from contract_accounting.api.processes import publish_process_template

    publish_process_template(template.name)
    return template.name


def _validate_existing(name: str, status: str) -> None:
    if status != "Published":
        frappe.throw(
            _("Existing FERUM-LAUNCH v1 is not Published; manual reconciliation required.")
        )
    _assert_values(
        "FERUM-LAUNCH v1 template",
        frappe.db.get_value(
            "Ferum Process Template",
            name,
            tuple(_expected_template("Published")),
            as_dict=True,
        ),
        _expected_template("Published"),
    )
    stage_rows = frappe.get_all(
        "Ferum Stage Template",
        filters={"process_template": name},
        fields=["name", "stage_code"],
        order_by="sequence asc",
    )
    expected = [str(stage["code"]) for stage in STAGES]
    if [row.stage_code for row in stage_rows] != expected:
        frappe.throw(_("Existing FERUM-LAUNCH v1 graph differs from the approved CA-12 reference."))
    personnel = None
    for stage_sequence, (stage_row, definition) in enumerate(
        zip(stage_rows, STAGES, strict=True), start=1
    ):
        _assert_values(
            f"FERUM-LAUNCH v1 stage {stage_row.stage_code}",
            frappe.db.get_value(
                "Ferum Stage Template",
                stage_row.name,
                tuple(_expected_stage(definition, stage_sequence)),
                as_dict=True,
            ),
            _expected_stage(definition, stage_sequence),
        )
        steps = frappe.get_all(
            "Ferum Step Template",
            filters={"stage_template": stage_row.name},
            fields=["name", "step_code", "action_type", "completion_evidence_type"],
            order_by="sequence asc",
        )
        expected_steps = [str(row[0]) for row in definition["steps"]]
        if [row.step_code for row in steps] != expected_steps:
            frappe.throw(
                _("Existing FERUM-LAUNCH v1 steps differ in stage {0}.").format(
                    stage_row.stage_code
                )
            )
        for step_sequence, (step, step_definition) in enumerate(
            zip(steps, definition["steps"], strict=True), start=1
        ):
            _assert_values(
                f"FERUM-LAUNCH v1 step {step.step_code}",
                frappe.db.get_value(
                    "Ferum Step Template",
                    step.name,
                    tuple(_expected_step(definition, step_definition, step_sequence)),
                    as_dict=True,
                ),
                _expected_step(definition, step_definition, step_sequence),
            )
        if stage_row.stage_code == "PERSONNEL_READINESS":
            personnel = steps[0] if steps else None
    if not personnel or (personnel.action_type, personnel.completion_evidence_type) != (
        "Personnel Readiness",
        "None",
    ):
        frappe.throw(_("Existing FERUM-LAUNCH v1 PERSONNEL_READY contract differs."))


def _expected_template(status: str) -> dict[str, Any]:
    return {
        "code": TEMPLATE_CODE,
        "title": "Ferum Seven-Stage Project Launch",
        "version": TEMPLATE_VERSION,
        "process_type": "Launch",
        "scope_rule": {
            "and": [
                {
                    "in": [
                        {"var": "project.legal_status"},
                        ["Approved", "Signing", "Signed", "In Force"],
                    ]
                },
                {
                    "in": [
                        {"var": "project.execution_status"},
                        ["Not Started", "Launching"],
                    ]
                },
            ]
        },
        "effective_from": "2026-08-18",
        "status": status,
        "change_note": "CA-12 reference v1; PERSONNEL_READY remains fail-closed pending MG-CA-015.",
    }


def _expected_stage(definition: dict[str, Any], sequence: int) -> dict[str, Any]:
    return {
        "stage_code": definition["code"],
        "title": definition["title"],
        "description": f"CA-12 reference stage {sequence}/7.",
        "sequence": sequence,
        "purpose": definition["title"],
        "entry_rule": {},
        "exit_rule": {},
        "default_owner_role": definition["role"],
        "gate_policy": {"mode": "All Blocking Steps", "override": "Role Controlled"},
        "parallelism": "Sequential",
        "active": 1,
    }


def _expected_step(
    stage: dict[str, Any],
    definition: tuple[str, str, str, str, str | None],
    sequence: int,
) -> dict[str, Any]:
    code, title, evidence_type, step_type, dependency = definition
    return {
        "step_code": code,
        "title": title,
        "description": "CA-12 reference step; completion evidence remains source-linked and validated.",
        "sequence": sequence,
        "action_type": "Personnel Readiness" if code == "PERSONNEL_READY" else title,
        "step_type": step_type,
        "requirement_source_policy": "None",
        "requirement_match_rule": {},
        "responsible_role": stage["role"],
        "approver_role": "Руководитель проектов" if step_type == "Approval" else None,
        "depends_on_step_codes": dependency,
        "deadline_type": "None",
        "condition_rule": {},
        "activation_rule": {},
        "criticality": "Mandatory",
        "blocking": 1,
        "completion_evidence_type": evidence_type,
        "failure_action": "Block stage and expose the failed criterion.",
        "timeout_action": "Expose overdue action; automatic delivery remains CA-11 OPEN.",
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
