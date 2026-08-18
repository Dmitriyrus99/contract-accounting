"""Insert-only event used for process trace and explicit deadline triggers."""

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.infrastructure.process_guard import (
	EVENT_WRITER_FLAG,
	require_writer,
)


class FerumProcessEvent(Document):
	def before_insert(self) -> None:
		require_writer(EVENT_WRITER_FLAG, "Создание Process Event")

	def validate(self) -> None:
		if not self.is_new():
			frappe.throw(_("Process Event неизменяем."), frappe.PermissionError)
		if not frappe.db.exists(self.source_doctype, self.source_name):
			frappe.throw(_("Process Event source не найден."))

	def on_trash(self) -> None:
		frappe.throw(_("Удаление Process Event запрещено."), frappe.PermissionError)


def on_doctype_update() -> None:
	frappe.db.add_unique(
		"Ferum Process Event", ["idempotency_key"], "ca_process_event_key_uniq"
	)
	frappe.db.add_index("Ferum Process Event", ["service_project", "occurred_at"])
