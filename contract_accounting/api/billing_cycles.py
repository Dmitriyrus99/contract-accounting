"""CA-13 recurring Billing Cycle orchestration over CA-06/07 and CA-11."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Final, TypeVar
from uuid import uuid4

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime

from contract_accounting.api.processes import generate_project_process
from contract_accounting.contract_accounting.doctype.ferum_billing_cycle.ferum_billing_cycle import (
    BILLING_CYCLE_UPDATE_FLAG,
    BILLING_CYCLE_WRITER_FLAG,
)
from contract_accounting.contract_accounting.doctype.ferum_billing_output.ferum_billing_output import (
    ACTIVE_STATUSES,
    snapshot_for_source,
)
from contract_accounting.domain.process import canonical_snapshot
from contract_accounting.setup.billing_cycle_template import (
    ensure_reference_billing_cycle_template,
)

CYCLE_DOCTYPE: Final[str] = "Ferum Billing Cycle"
OUTPUT_DOCTYPE: Final[str] = "Ferum Billing Output"
BACKFILL_CONFIRMATION: Final[str] = "CONFIRM_UNAMBIGUOUS_BILLING_CYCLE_BACKFILL"
_BILLING_ROLES: Final[frozenset[str]] = frozenset(
    {"Бухгалтер", "Руководитель проектов", "System Manager"}
)
_T = TypeVar("_T")


@frappe.whitelist(methods=["POST"])
def create_billing_cycle(
    service_project: str,
    period_start: str,
    period_end: str,
    due_date: str,
    idempotency_key: str,
) -> dict[str, Any]:
    """Create one explicit recurring cycle after accepted work exists."""

    _require_billing_role()
    project = _authorized("Ferum Service Project", service_project, "read")
    if project.execution_status not in {"Active", "Completed"}:
        frappe.throw(_("Billing Cycle требует Active/Completed Service Project."))
    start, end, due = getdate(period_start), getdate(period_end), getdate(due_date)
    if end < start or due < end:
        frappe.throw(_("Некорректные границы или due_date Billing Cycle."))
    key = _required(idempotency_key, "idempotency_key")
    existing = frappe.db.get_value(
        CYCLE_DOCTYPE,
        {"idempotency_key": key},
        ("name", "service_project", "period_start", "period_end"),
        as_dict=True,
    )
    if existing:
        if (
            existing.service_project,
            getdate(existing.period_start),
            getdate(existing.period_end),
        ) != (project.name, start, end):
            frappe.throw(
                _("Billing Cycle idempotency_key принадлежит другому context.")
            )
        return {**get_billing_cycle_projection(existing.name), "created": False}
    period_existing = frappe.db.get_value(
        CYCLE_DOCTYPE,
        {"service_project": project.name, "period_start": start, "period_end": end},
        "name",
    )
    if period_existing:
        frappe.throw(_("Billing Cycle этого проекта/периода уже существует."))
    accepted = _accepted_work(project.name, start, end)
    if not accepted:
        frappe.throw(
            _("Billing Cycle начинается только после выполненных/принятых работ.")
        )
    expected = _expected_work(project.name, start, end)
    expected_payload = {
        "service_project": project.name,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "rows": expected,
    }
    _expected_json, expected_hash = canonical_snapshot(expected_payload)
    expected_payload["source_hash"] = expected_hash
    savepoint = f"ca13_create_{uuid4().hex}"
    frappe.db.savepoint(savepoint)
    try:
        template = ensure_reference_billing_cycle_template()
        process_result = generate_project_process(
            project.name,
            template,
            f"billing-cycle:{key}",
            f"Period closing {start.isoformat()}..{end.isoformat()}",
            f"FERUM-BILLING-CYCLE-v1:{start.isoformat()}..{end.isoformat()}",
        )
        cycle = frappe.get_doc(
            {
                "doctype": CYCLE_DOCTYPE,
                "service_project": project.name,
                "project_process": process_result["project_process"],
                "period_start": start,
                "period_end": end,
                "period_key": _period_key(start, end),
                "due_date": due,
                "status": "Open",
                "expected_work_snapshot": expected_payload,
                "completion_snapshot": {},
                "idempotency_key": key,
                "created_at": now_datetime(),
                "created_by": frappe.session.user,
            }
        )
        _with_flag(
            BILLING_CYCLE_WRITER_FLAG,
            True,
            lambda: cycle.insert(ignore_permissions=True),
        )
        return {**get_billing_cycle_projection(cycle.name), "created": True}
    except BaseException:
        frappe.db.rollback(save_point=savepoint)
        raise


@frappe.whitelist()
def get_billing_cycle_projection(
    billing_cycle: str,
    as_of: str | None = None,
) -> dict[str, Any]:
    cycle = _authorized(CYCLE_DOCTYPE, billing_cycle, "read")
    return _projection(cycle, as_of=as_of)


@frappe.whitelist(methods=["POST"])
def complete_billing_cycle(billing_cycle: str) -> dict[str, Any]:
    """Freeze a cycle only after its BPM gate and ERP payment facts are complete."""

    _require_billing_role()
    cycle = _locked_cycle(billing_cycle)
    if cycle.status == "Completed":
        return get_billing_cycle_projection(cycle.name)
    if cycle.status != "Open":
        frappe.throw(_("Завершить можно только Open Billing Cycle."))
    projection = _projection(cycle)
    blockers: list[str] = []
    if projection["process"]["status"] != "Completed":
        blockers.append("Period Closing Process is not Completed")
    if projection["work"]["accepted_count"] < 1:
        blockers.append("accepted work is empty")
    if projection["work"]["unbilled_count"]:
        blockers.append("accepted work remains unbilled")
    if projection["work"]["claimed_outside_cycle_count"]:
        blockers.append("accepted work is claimed outside this cycle")
    if projection["documents"]["active_output_count"] < 1:
        blockers.append("active Billing Output is missing")
    if not projection["documents"]["all_active_outputs_signed"]:
        blockers.append("active Billing Output is not Signed")
    if not projection["payment"]["all_invoices_paid"]:
        blockers.append("submitted invoice is not fully paid")
    if blockers:
        frappe.throw(_("Billing Cycle gate blocked: {0}.").format("; ".join(blockers)))
    completion_payload = {
        "project_process": cycle.project_process,
        "gate": projection["process"]["gate"],
        "work": projection["work"],
        "documents": projection["documents"],
        "payment": projection["payment"],
    }
    completion_json, completion_hash = canonical_snapshot(completion_payload)
    cycle.status = "Completed"
    cycle.completed_at = now_datetime()
    cycle.completed_by = frappe.session.user
    cycle.completion_snapshot = {
        "payload": json.loads(completion_json),
        "content_hash": completion_hash,
    }
    _save_cycle(cycle)
    return get_billing_cycle_projection(cycle.name)


@frappe.whitelist(methods=["POST"])
def cancel_billing_cycle(billing_cycle: str, reason: str) -> dict[str, Any]:
    _require_billing_role()
    cycle = _locked_cycle(billing_cycle)
    if cycle.status != "Open":
        frappe.throw(_("Отменить можно только Open Billing Cycle."))
    if frappe.db.exists(
        OUTPUT_DOCTYPE,
        {"billing_cycle": cycle.name, "status": ["in", ["Issued", "Signed"]]},
    ):
        frappe.throw(_("Cycle с Issued/Signed Output нельзя отменить."))
    cycle.status = "Cancelled"
    cycle.cancellation_reason = _required(reason, "reason")
    _save_cycle(cycle)
    return get_billing_cycle_projection(cycle.name)


@frappe.whitelist()
def get_billing_cycle_backfill_assessment(
    service_project: str | None = None,
) -> dict[str, Any]:
    """Read-only legacy assessment; no cycle or Output is mutated."""

    _require_billing_role()
    filters: dict[str, Any] = {"billing_cycle": ["is", "not set"]}
    if service_project:
        _authorized("Ferum Service Project", service_project, "read")
        filters["service_project"] = service_project
    outputs = frappe.get_all(
        OUTPUT_DOCTYPE,
        filters=filters,
        fields=["name", "service_project", "period_start", "period_end", "status"],
        order_by="service_project asc, period_start asc, period_end asc, name asc",
    )
    groups: dict[tuple[str, str, str], list[Any]] = defaultdict(list)
    for row in outputs:
        groups[
            (str(row.service_project), str(row.period_start), str(row.period_end))
        ].append(row)
    rows = []
    for (project, start, end), group in groups.items():
        statuses = sorted({str(row.status) for row in group})
        legal = [row.name for row in group if row.status in {"Issued", "Signed"}]
        unsupported = [
            row.name
            for row in group
            if row.status not in {"Draft", "Generated", "Issued", "Signed"}
        ]
        rows.append(
            {
                "service_project": project,
                "period_start": start,
                "period_end": end,
                "outputs": [row.name for row in group],
                "statuses": statuses,
                "decision": "CONFLICT_MANUAL_LEGAL_RECONCILIATION"
                if legal or unsupported
                else "CANDIDATE_EXPLICIT_BACKFILL",
                "immutable_legal_outputs": legal,
                "unsupported_outputs": unsupported,
            }
        )
    return {
        "mode": "READ_ONLY",
        "candidate_count": sum(
            row["decision"] == "CANDIDATE_EXPLICIT_BACKFILL" for row in rows
        ),
        "conflict_count": sum(
            row["decision"] != "CANDIDATE_EXPLICIT_BACKFILL" for row in rows
        ),
        "rows": rows,
    }


@frappe.whitelist(methods=["POST"])
def backfill_billing_cycle_group(
    service_project: str,
    period_start: str,
    period_end: str,
    due_date: str,
    confirmation: str,
) -> dict[str, Any]:
    """Explicitly bind only Draft/Generated outputs with one exact period key."""

    _require_billing_role()
    if confirmation != BACKFILL_CONFIRMATION:
        frappe.throw(_("Требуется exact Billing Cycle backfill confirmation token."))
    rows = frappe.get_all(
        OUTPUT_DOCTYPE,
        filters={
            "service_project": service_project,
            "period_start": getdate(period_start),
            "period_end": getdate(period_end),
            "billing_cycle": ["is", "not set"],
        },
        fields=["name", "status"],
        order_by="name asc",
    )
    if not rows:
        frappe.throw(_("Unlinked Billing Output group не найден."))
    if any(row.status not in {"Draft", "Generated"} for row in rows):
        frappe.throw(
            _(
                "Issued/Signed/terminal Output не изменяется; требуется manual reconciliation."
            )
        )
    savepoint = f"ca13_backfill_{uuid4().hex}"
    frappe.db.savepoint(savepoint)
    try:
        result = create_billing_cycle(
            service_project,
            period_start,
            period_end,
            due_date,
            f"backfill:{service_project}:{_period_key(getdate(period_start), getdate(period_end))}",
        )
        from contract_accounting.api.billing import attach_billing_output_to_cycle

        for row in rows:
            attach_billing_output_to_cycle(row.name, result["billing_cycle"])
        return {
            **get_billing_cycle_projection(result["billing_cycle"]),
            "linked_outputs": [row.name for row in rows],
        }
    except BaseException:
        frappe.db.rollback(save_point=savepoint)
        raise


@frappe.whitelist()
def resolve_billing_cycles_for_source(
    source_doctype: str,
    source_name: str,
) -> dict[str, Any]:
    """Reverse trace from basis/output/invoice/payment to exact cycles."""

    allowed = {
        CYCLE_DOCTYPE,
        OUTPUT_DOCTYPE,
        "Ferum Maintenance Visit",
        "Ferum Service Request",
        "Sales Invoice",
        "Payment Entry",
    }
    if source_doctype not in allowed:
        frappe.throw(_("Source DocType не поддерживается Billing Cycle resolver."))
    _authorized(source_doctype, source_name, "read")
    output_names: set[str] = set()
    cycle_names: set[str] = set()
    if source_doctype == CYCLE_DOCTYPE:
        cycle_names.add(source_name)
    elif source_doctype == OUTPUT_DOCTYPE:
        output_names.add(source_name)
    elif source_doctype == "Sales Invoice":
        output_names.update(
            frappe.get_all(
                OUTPUT_DOCTYPE,
                filters={"sales_invoice": source_name},
                pluck="name",
            )
        )
    elif source_doctype == "Payment Entry":
        invoices = frappe.get_all(
            "Payment Entry Reference",
            filters={
                "parent": source_name,
                "parenttype": "Payment Entry",
                "reference_doctype": "Sales Invoice",
            },
            pluck="reference_name",
        )
        if invoices:
            output_names.update(
                frappe.get_all(
                    OUTPUT_DOCTYPE,
                    filters={"sales_invoice": ["in", invoices]},
                    pluck="name",
                )
            )
    else:
        output_names.update(
            frappe.get_all(
                "Ferum Billing Basis Item",
                filters={
                    "parenttype": OUTPUT_DOCTYPE,
                    "source_doctype": source_doctype,
                    "source_name": source_name,
                },
                pluck="parent",
            )
        )
    if output_names:
        cycle_names.update(
            name
            for name in frappe.get_all(
                OUTPUT_DOCTYPE,
                filters={"name": ["in", sorted(output_names)]},
                pluck="billing_cycle",
            )
            if name
        )
    readable = [
        name
        for name in sorted(cycle_names)
        if frappe.session.user == "Administrator"
        or frappe.has_permission(CYCLE_DOCTYPE, "read", doc=name)
    ]
    return {
        "source_doctype": source_doctype,
        "source_name": source_name,
        "billing_outputs": sorted(output_names),
        "billing_cycles": readable,
    }


def validate_billing_process_evidence(
    step: Any,
    evidence_type: str,
    source_doctype: str | None,
    source_name: str | None,
) -> None:
    """Bind CA-13 evidence to the exact cycle/process/accounting context."""

    cycle_name = frappe.db.get_value(
        CYCLE_DOCTYPE, {"project_process": step.project_process}, "name"
    )
    if not cycle_name:
        return
    cycle = frappe.get_doc(CYCLE_DOCTYPE, cycle_name)
    code = str(step.template_step_code)
    if code in {"WORK_COMPLETED", "EXECUTION_CONFIRMED"}:
        if evidence_type != "Manual Confirmation" or not _accepted_work(
            cycle.service_project,
            getdate(cycle.period_start),
            getdate(cycle.period_end),
        ):
            frappe.throw(
                _("Billing work confirmation требует accepted work exact period.")
            )
        return
    if code == "INVOICE_PREPARED":
        if source_doctype != "Sales Invoice" or not _invoice_in_cycle(
            cycle.name, source_name
        ):
            frappe.throw(_("Invoice evidence не относится к Billing Cycle."))
        return
    if code == "PAYMENT_RECEIVED":
        if source_doctype != "Payment Entry" or not _payment_in_cycle(
            cycle.name, source_name
        ):
            frappe.throw(_("Payment evidence не относится к Billing Cycle."))
        return
    if code == "DOCUMENTS_APPROVED":
        if source_doctype != "User":
            frappe.throw(_("Billing approval evidence требует User."))
        return
    if code in {
        "ACT_PREPARED",
        "UPD_OR_SF_PREPARED",
        "DOCUMENTS_SENT",
        "CUSTOMER_RECEIPT",
    } and (
        source_doctype != "Ferum Project Document"
        or not _document_in_cycle(
            cycle, source_name, require_billing_source=code != "CUSTOMER_RECEIPT"
        )
    ):
        frappe.throw(_("Document evidence не относится к Billing Cycle."))


def _projection(cycle: Any, as_of: str | None = None) -> dict[str, Any]:
    start, end = getdate(cycle.period_start), getdate(cycle.period_end)
    expected_payload = json.loads(cycle.expected_work_snapshot or "{}")
    accepted = _accepted_work(cycle.service_project, start, end)
    accepted_keys = {
        f"{row['source_doctype']}::{row['source_name']}" for row in accepted
    }
    outputs = frappe.get_all(
        OUTPUT_DOCTYPE,
        filters={"billing_cycle": cycle.name},
        fields=[
            "name",
            "status",
            "output_type",
            "sales_invoice",
            "period_start",
            "period_end",
            "supersedes",
            "superseded_by",
        ],
        order_by="creation asc, name asc",
    )
    output_names = [row.name for row in outputs]
    active_outputs = [row for row in outputs if row.status in ACTIVE_STATUSES]
    active_output_names = {row.name for row in active_outputs}
    basis = (
        frappe.get_all(
            "Ferum Billing Basis Item",
            filters={"parenttype": OUTPUT_DOCTYPE, "parent": ["in", output_names]},
            fields=[
                "parent as billing_output",
                "source_doctype",
                "source_name",
                "period_key",
                "amount_snapshot",
                "currency",
                "source_hash",
                "inclusion_state",
                "active_claim_key",
            ],
            order_by="parent asc, idx asc",
        )
        if output_names
        else []
    )
    cycle_claims = {
        str(row.active_claim_key)
        for row in basis
        if row.billing_output in active_output_names and row.active_claim_key
    }
    global_claims = {
        str(row.active_claim_key)
        for row in frappe.get_all(
            "Ferum Billing Basis Item",
            filters={"active_claim_key": ["is", "set"]},
            fields=["active_claim_key"],
        )
    }
    unbilled = sorted(accepted_keys - global_claims)
    claimed_outside = sorted((accepted_keys & global_claims) - cycle_claims)
    invoice_names = sorted(
        {str(row.sales_invoice) for row in outputs if row.sales_invoice}
    )
    invoices = (
        frappe.get_all(
            "Sales Invoice",
            filters={"name": ["in", invoice_names]},
            fields=[
                "name",
                "docstatus",
                "status",
                "posting_date",
                "due_date",
                "currency",
                "grand_total",
                "outstanding_amount",
            ],
            order_by="name asc",
        )
        if invoice_names
        else []
    )
    payments = _payments_for_invoices(invoice_names)
    process = frappe.get_doc("Ferum Project Process", cycle.project_process)
    steps = frappe.get_all(
        "Ferum Project Process Step",
        filters={"project_process": process.name},
        fields=["name", "template_step_code", "title", "status", "due_at"],
        order_by="creation asc, name asc",
    )
    stages = frappe.get_all(
        "Ferum Project Stage",
        filters={"project_process": process.name},
        fields=["name", "status"],
        order_by="sequence asc",
    )
    gate = (
        frappe.db.get_value(
            "Ferum Stage Gate",
            {"project_stage": stages[0].name},
            ("name", "status"),
            as_dict=True,
        )
        if stages
        else None
    )
    milestone_status = {str(row.template_step_code): str(row.status) for row in steps}
    paid_invoices = [
        row.name
        for row in invoices
        if int(row.docstatus) == 1 and flt(row.outstanding_amount) <= 0
    ]
    classification_date = getdate(as_of) if as_of else None
    is_overdue = (
        bool(
            classification_date
            and cycle.status == "Open"
            and getdate(cycle.due_date) < classification_date
        )
        if as_of
        else None
    )
    return {
        "billing_cycle": cycle.name,
        "service_project": cycle.service_project,
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "key": cycle.period_key,
            "due_date": str(cycle.due_date),
        },
        "status": cycle.status,
        "classification": {
            "as_of": str(classification_date) if classification_date else None,
            "is_overdue": is_overdue,
            "display_status": "Overdue" if is_overdue else cycle.status,
        },
        "work": {
            "expected_count": len(expected_payload.get("rows") or []),
            "expected_snapshot": expected_payload,
            "accepted_count": len(accepted),
            "accepted": accepted,
            "unbilled_count": len(unbilled),
            "unbilled_source_keys": unbilled,
            "billed_source_count": len(cycle_claims),
            "claimed_outside_cycle_count": len(claimed_outside),
            "claimed_outside_cycle_source_keys": claimed_outside,
        },
        "documents": {
            "output_count": len(outputs),
            "active_output_count": len(active_outputs),
            "signed_output_count": sum(
                row.status == "Signed" for row in active_outputs
            ),
            "all_active_outputs_signed": bool(active_outputs)
            and all(row.status == "Signed" for row in active_outputs),
            "outputs": [dict(row) for row in outputs],
            "basis": [dict(row) for row in basis],
            "sent_status": milestone_status.get("DOCUMENTS_SENT"),
            "customer_receipt_status": milestone_status.get("CUSTOMER_RECEIPT"),
        },
        "payment": {
            "invoice_count": len(invoices),
            "paid_invoice_count": len(paid_invoices),
            "all_invoices_paid": bool(invoices) and len(paid_invoices) == len(invoices),
            "invoices": [dict(row) for row in invoices],
            "payments": payments,
        },
        "process": {
            "name": process.name,
            "status": process.status,
            "gate": dict(gate) if gate else None,
            "milestones": [dict(row) for row in steps],
        },
    }


def _accepted_work(service_project: str, start: Any, end: Any) -> list[dict[str, Any]]:
    refs: list[tuple[str, str]] = []
    for row in frappe.get_all(
        "Ferum Maintenance Visit",
        filters={
            "service_project": service_project,
            "acceptance_status": "Accepted",
            "billing_eligible": 1,
            "actual_end": ["between", [str(start), f"{end} 23:59:59"]],
        },
        fields=["name"],
        order_by="name asc",
    ):
        refs.append(("Ferum Maintenance Visit", row.name))
    for row in frappe.get_all(
        "Ferum Service Request",
        filters={
            "service_project": service_project,
            "status": ["in", ["Resolved", "Closed"]],
            "actual_end": ["between", [str(start), f"{end} 23:59:59"]],
        },
        fields=["name"],
        order_by="name asc",
    ):
        refs.append(("Ferum Service Request", row.name))
    return [
        snapshot_for_source(doctype, name, service_project) for doctype, name in refs
    ]


def _expected_work(service_project: str, start: Any, end: Any) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in frappe.get_all(
            "Ferum Maintenance Schedule",
            filters={
                "service_project": service_project,
                "status": ["!=", "Cancelled"],
                "planned_date": ["between", [start, end]],
            },
            fields=[
                "name",
                "contract_obligation",
                "project_object",
                "object_system",
                "work_type",
                "period_key",
                "planned_date",
                "due_date",
                "status",
                "generated_visit",
            ],
            order_by="planned_date asc, name asc",
        )
    ]


def _payments_for_invoices(invoice_names: list[str]) -> list[dict[str, Any]]:
    if not invoice_names:
        return []
    references = frappe.get_all(
        "Payment Entry Reference",
        filters={
            "reference_doctype": "Sales Invoice",
            "reference_name": ["in", invoice_names],
        },
        fields=["parent", "reference_name", "allocated_amount"],
        order_by="parent asc, idx asc",
    )
    result = []
    for row in references:
        payment = frappe.db.get_value(
            "Payment Entry",
            row.parent,
            ("docstatus", "posting_date", "payment_type", "party_type", "party"),
            as_dict=True,
        )
        if payment and int(payment.docstatus) == 1:
            result.append(
                {
                    "payment_entry": row.parent,
                    "sales_invoice": row.reference_name,
                    "allocated_amount": flt(row.allocated_amount),
                    "posting_date": payment.posting_date,
                    "payment_type": payment.payment_type,
                    "party_type": payment.party_type,
                    "party": payment.party,
                }
            )
    return result


def _invoice_in_cycle(cycle: str, invoice: str | None) -> bool:
    return bool(
        invoice
        and frappe.db.exists(
            OUTPUT_DOCTYPE, {"billing_cycle": cycle, "sales_invoice": invoice}
        )
    )


def _payment_in_cycle(cycle: str, payment: str | None) -> bool:
    if not payment or frappe.db.get_value("Payment Entry", payment, "docstatus") != 1:
        return False
    invoices = frappe.get_all(
        "Payment Entry Reference",
        filters={
            "parent": payment,
            "parenttype": "Payment Entry",
            "reference_doctype": "Sales Invoice",
        },
        pluck="reference_name",
    )
    return bool(
        invoices
        and frappe.db.exists(
            OUTPUT_DOCTYPE,
            {"billing_cycle": cycle, "sales_invoice": ["in", invoices]},
        )
    )


def _document_in_cycle(
    cycle: Any,
    document: str | None,
    *,
    require_billing_source: bool,
) -> bool:
    if not document:
        return False
    row = frappe.db.get_value(
        "Ferum Project Document",
        document,
        ("service_project", "billing_reference_doctype", "billing_reference_name"),
        as_dict=True,
    )
    if not row or row.service_project != cycle.service_project:
        return False
    if not require_billing_source:
        return True
    if row.billing_reference_doctype != "Ferum Billing Artifact":
        return False
    output = frappe.db.get_value(
        "Ferum Billing Artifact", row.billing_reference_name, "billing_output"
    )
    return bool(
        output
        and frappe.db.get_value(OUTPUT_DOCTYPE, output, "billing_cycle") == cycle.name
    )


def _locked_cycle(name: str) -> Any:
    name = _required(name, "billing_cycle")
    if not frappe.db.get_value(CYCLE_DOCTYPE, name, "name", for_update=True):
        frappe.throw(_("Billing Cycle не найден."), frappe.DoesNotExistError)
    cycle = frappe.get_doc(CYCLE_DOCTYPE, name)
    cycle.check_permission("read")
    return cycle


def _save_cycle(cycle: Any) -> None:
    _with_flag(
        BILLING_CYCLE_UPDATE_FLAG,
        True,
        lambda: cycle.save(ignore_permissions=True),
    )


def _authorized(doctype: str, name: str, permission_type: str) -> Any:
    if not frappe.db.exists(doctype, name):
        frappe.throw(_("{0} не найден.").format(doctype), frappe.DoesNotExistError)
    document = frappe.get_doc(doctype, name)
    document.check_permission(permission_type)
    return document


def _period_key(start: Any, end: Any) -> str:
    return f"{getdate(start).isoformat()}..{getdate(end).isoformat()}"


def _required(value: Any, fieldname: str) -> str:
    text = str(value or "").strip()
    if not text:
        frappe.throw(_("{0} обязателен.").format(fieldname))
    return text


def _require_billing_role() -> None:
    if frappe.session.user == "Administrator":
        return
    if not set(frappe.get_roles(frappe.session.user)).intersection(_BILLING_ROLES):
        frappe.throw(
            _("Роль не разрешает CA-13 Billing Cycle command."), frappe.PermissionError
        )


def _with_flag(flag: str, value: Any, callback: Any) -> _T:
    previous = frappe.flags.get(flag)
    frappe.flags[flag] = value
    try:
        return callback()
    finally:
        frappe.flags[flag] = previous
