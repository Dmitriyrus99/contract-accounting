"""Append-only evidence for initial and explicitly authorized recalculation."""

import hashlib
import json

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.infrastructure.deadline_guard import DEADLINE_EVENT_WRITE_FLAG


class FerumDeadlineCalculation(Document):
    def before_insert(self) -> None:
        if not frappe.flags.get(DEADLINE_EVENT_WRITE_FLAG):
            frappe.throw(
                _("Deadline Calculation создаётся только typed deadline writer."),
                frappe.PermissionError,
            )

    def validate(self) -> None:
        if not self.is_new():
            frappe.throw(_("Deadline Calculation неизменяема."), frappe.PermissionError)
        if not frappe.db.exists(self.source_doctype, self.source_name):
            frappe.throw(_("Deadline Calculation source не найден."))
        try:
            payload = json.loads(self.calendar_snapshot_json)
        except (TypeError, ValueError):
            frappe.throw(_("Deadline Calculation snapshot должен быть valid JSON."))
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if canonical != self.calendar_snapshot_json:
            frappe.throw(_("Deadline Calculation snapshot должен быть canonical JSON."))
        if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != self.calculation_hash:
            frappe.throw(_("Deadline Calculation hash mismatch."))
        if payload.get("calendar", {}).get("calendar_hash") != self.calendar_hash:
            frappe.throw(_("Deadline Calculation calendar hash mismatch."))
        if payload.get("algorithm_version") != self.algorithm_version:
            frappe.throw(_("Deadline Calculation algorithm version mismatch."))
        if self.calculation_kind == "Manual Recalculation" and not self.supersedes:
            frappe.throw(_("Manual Recalculation требует superseded calculation."))

    def on_trash(self) -> None:
        frappe.throw(_("Удаление Deadline Calculation запрещено."), frappe.PermissionError)


def on_doctype_update() -> None:
    frappe.db.add_index(
        "Ferum Deadline Calculation",
        ["source_doctype", "source_name", "source_field", "occurred_at"],
        "ca_deadline_calculation_source_idx",
    )
    frappe.db.add_index(
        "Ferum Deadline Calculation", ["service_project", "due_at"], "ca_deadline_project_due_idx"
    )
