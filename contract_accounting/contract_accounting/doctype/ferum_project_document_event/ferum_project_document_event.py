"""Insert-only event controller for CA-05 project-document transitions."""

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.contract_accounting.doctype.ferum_project_document.ferum_project_document import (
	DOCUMENT_EVENT_DOCTYPE,
	DOCUMENT_EVENT_WRITER_FLAG,
)


class FerumProjectDocumentEvent(Document):
	def before_insert(self) -> None:
		if not frappe.flags.get(DOCUMENT_EVENT_WRITER_FLAG):
			frappe.throw(
				_("Project Document Event создаётся только typed writer CA-05."),
				frappe.PermissionError,
			)

	def validate(self) -> None:
		if not self.is_new():
			frappe.throw(_("Project Document Event неизменяем."), frappe.PermissionError)

	def on_trash(self) -> None:
		frappe.throw(_("Удаление Project Document Event запрещено."), frappe.PermissionError)


def on_doctype_update() -> None:
	frappe.db.add_index(
		DOCUMENT_EVENT_DOCTYPE,
		["project_document", "occurred_at"],
		"ca_project_document_event_timeline_idx",
	)
