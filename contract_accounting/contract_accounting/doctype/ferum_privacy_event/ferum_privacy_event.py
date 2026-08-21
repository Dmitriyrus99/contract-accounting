"""Append-only FR-05 audit event."""

import frappe
from frappe import _
from frappe.model.document import Document

PRIVACY_EVENT_WRITE_FLAG = "contract_accounting_privacy_event_writer"


class FerumPrivacyEvent(Document):
    def before_insert(self) -> None:
        if not frappe.flags.get(PRIVACY_EVENT_WRITE_FLAG):
            frappe.throw(_("Privacy Event создаётся только typed writer."), frappe.PermissionError)
        if not all((self.target_name, self.actor, self.reason, self.payload_json)):
            frappe.throw(_("Новый Privacy Event требует полного typed audit context."))

    def validate(self) -> None:
        if not self.is_new():
            frappe.throw(_("Privacy Event неизменяем."), frappe.PermissionError)
        if not frappe.db.exists(self.target_doctype, self.target_name):
            frappe.throw(_("Privacy Event target не найден."))

    def on_trash(self) -> None:
        frappe.throw(_("Удаление Privacy Event запрещено."), frappe.PermissionError)


def on_doctype_update() -> None:
    frappe.db.add_unique("Ferum Privacy Event", ["correlation_key"], "ca_privacy_event_key_uniq")
    frappe.db.add_index("Ferum Privacy Event", ["target_doctype", "target_name", "occurred_at"])
    frappe.db.add_index("Ferum Privacy Event", ["anonymized_at", "occurred_at"])
