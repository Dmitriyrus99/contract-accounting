"""Recurring period-closing fact linked to BPM and ERPNext accounting sources."""

from __future__ import annotations

import json
from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

DOCTYPE: Final[str] = "Ferum Billing Cycle"
BILLING_CYCLE_WRITER_FLAG: Final[str] = "contract_accounting_billing_cycle_writer"
BILLING_CYCLE_UPDATE_FLAG: Final[str] = "contract_accounting_billing_cycle_update"
_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "service_project",
    "project_process",
    "period_start",
    "period_end",
    "period_key",
    "due_date",
    "expected_work_snapshot",
    "idempotency_key",
    "created_at",
    "created_by",
)
_CONTROLLED_FIELDS: Final[tuple[str, ...]] = (
    "status",
    "completion_snapshot",
    "completed_at",
    "completed_by",
    "cancellation_reason",
)


class FerumBillingCycle(Document):
    def before_insert(self) -> None:
        if not frappe.flags.get(BILLING_CYCLE_WRITER_FLAG):
            frappe.throw(
                _("Billing Cycle создаётся только typed command CA-13."),
                frappe.PermissionError,
            )

    def validate(self) -> None:
        self._validate_period()
        self._validate_process()
        self._validate_snapshots()
        self._freeze_identity()
        self._guard_lifecycle()

    def on_trash(self) -> None:
        frappe.throw(
            _("Billing Cycle не удаляется; используйте cancel."),
            frappe.PermissionError,
        )

    def _validate_period(self) -> None:
        start, end, due = (
            getdate(self.period_start),
            getdate(self.period_end),
            getdate(self.due_date),
        )
        if end < start:
            frappe.throw(
                _("Billing Cycle period_end не может быть раньше period_start.")
            )
        if due < end:
            frappe.throw(_("Billing Cycle due_date не может быть раньше period_end."))
        expected_key = f"{start.isoformat()}..{end.isoformat()}"
        if self.period_key != expected_key:
            frappe.throw(_("Billing Cycle period_key определяется границами периода."))

    def _validate_process(self) -> None:
        process = frappe.db.get_value(
            "Ferum Project Process",
            self.project_process,
            ("service_project", "process_type"),
            as_dict=True,
        )
        if not process or (
            process.service_project,
            process.process_type,
        ) != (self.service_project, "Period Closing"):
            frappe.throw(
                _("Billing Cycle требует Period Closing Process того же проекта.")
            )

    def _validate_snapshots(self) -> None:
        for fieldname in ("expected_work_snapshot", "completion_snapshot"):
            value = self.get(fieldname)
            try:
                payload = json.loads(value) if isinstance(value, str) else value
            except (TypeError, ValueError):
                frappe.throw(_("{0} должен быть JSON object.").format(fieldname))
            if not isinstance(payload, dict):
                frappe.throw(_("{0} должен быть JSON object.").format(fieldname))
            self.set(fieldname, frappe.as_json(payload))

    def _freeze_identity(self) -> None:
        before = self.get_doc_before_save()
        if before is None:
            return
        if any(self.get(field) != before.get(field) for field in _IDENTITY_FIELDS):
            frappe.throw(_("Billing Cycle identity/snapshots immutable."))

    def _guard_lifecycle(self) -> None:
        before = self.get_doc_before_save()
        if before is None:
            if self.status != "Open":
                frappe.throw(_("Новый Billing Cycle создаётся только в Open."))
            return
        changed = [
            field
            for field in _CONTROLLED_FIELDS
            if self.get(field) != before.get(field)
        ]
        if changed and not frappe.flags.get(BILLING_CYCLE_UPDATE_FLAG):
            frappe.throw(
                _("Billing Cycle lifecycle меняется только typed command."),
                frappe.PermissionError,
            )
        if before.status != self.status and (
            before.status != "Open" or self.status not in {"Completed", "Cancelled"}
        ):
            frappe.throw(_("Недопустимый Billing Cycle transition."))
        if self.status == "Completed" and (
            not self.completed_at
            or not self.completed_by
            or not json.loads(self.completion_snapshot or "{}")
        ):
            frappe.throw(_("Completed Billing Cycle требует actor/time/snapshot."))
        if self.status == "Cancelled" and not (self.cancellation_reason or "").strip():
            frappe.throw(_("Cancelled Billing Cycle требует reason."))


def on_doctype_update() -> None:
    frappe.db.add_unique(DOCTYPE, ["idempotency_key"], "ca_billing_cycle_key_uniq")
    frappe.db.add_unique(
        DOCTYPE,
        ["service_project", "period_start", "period_end"],
        "ca_billing_cycle_project_period_uniq",
    )
    frappe.db.add_index(
        DOCTYPE,
        ["service_project", "status", "due_date"],
        "ca_billing_cycle_project_status_idx",
    )
