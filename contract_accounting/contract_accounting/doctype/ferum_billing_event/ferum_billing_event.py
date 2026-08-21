"""Insert-only audit controller for CA-06 billing commands."""

import frappe
from frappe import _
from frappe.model.document import Document

BILLING_EVENT_WRITER_FLAG = "contract_accounting_billing_event_writer"


class FerumBillingEvent(Document):
	def before_insert(self) -> None:
		if not frappe.flags.get(BILLING_EVENT_WRITER_FLAG):
			frappe.throw(_("Billing Event создаётся только typed writer CA-06."), frappe.PermissionError)

	def validate(self) -> None:
		if not self.is_new():
			frappe.throw(_("Billing Event неизменяем."), frappe.PermissionError)

	def on_trash(self) -> None:
		frappe.throw(_("Удаление Billing Event запрещено."), frappe.PermissionError)


def on_doctype_update() -> None:
	frappe.db.add_index(
		"Ferum Billing Event",
		["billing_output", "timestamp"],
		"ca_billing_event_timeline_idx",
	)
