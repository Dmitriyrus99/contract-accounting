"""Insert-only audit controller for every CA-01 lifecycle transition."""

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.infrastructure.frappe_lifecycle import (
	LIFECYCLE_AUDIT_DOCTYPE,
	LIFECYCLE_AUDIT_WRITER_FLAG,
)


class FerumLifecycleAuditEvent(Document):
	def before_insert(self) -> None:
		if not frappe.flags.get(LIFECYCLE_AUDIT_WRITER_FLAG):
			frappe.throw(
				_("Lifecycle audit event создаётся только typed writer CA-01."),
				frappe.PermissionError,
			)

	def validate(self) -> None:
		if not self.is_new():
			frappe.throw(
				_("Lifecycle audit event неизменяем после вставки."),
				frappe.PermissionError,
			)

	def on_trash(self) -> None:
		frappe.throw(
			_("Удаление lifecycle audit event запрещено."),
			frappe.PermissionError,
		)


def on_doctype_update() -> None:
	frappe.db.add_index(LIFECYCLE_AUDIT_DOCTYPE, ["service_project", "occurred_at"])
