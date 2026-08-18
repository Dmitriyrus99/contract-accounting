"""Immutable-template project process instance managed by typed CA-11 commands."""

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.infrastructure.process_guard import (
	PROCESS_WRITER_FLAG,
	reject_direct_managed_update,
	require_writer,
)


class FerumProjectProcess(Document):
	def before_insert(self) -> None:
		require_writer(PROCESS_WRITER_FLAG, "Создание Project Process")

	def validate(self) -> None:
		reject_direct_managed_update(self, "Project Process")
		template = frappe.db.get_value(
			"Ferum Process Template",
			self.process_template,
			("version", "process_type", "status"),
			as_dict=True,
		)
		if not template or template.status != "Published":
			frappe.throw(_("Project Process требует Published Process Template."))
		if (self.template_version, self.process_type) != (
			template.version,
			template.process_type,
		):
			frappe.throw(_("Project Process template snapshot identity не совпадает."))

	def on_trash(self) -> None:
		frappe.throw(_("Удаление Project Process запрещено."), frappe.PermissionError)


def on_doctype_update() -> None:
	frappe.db.add_unique(
		"Ferum Project Process", ["generation_key"], "ca_project_process_generation_uniq"
	)
	frappe.db.add_index("Ferum Project Process", ["service_project", "status"])
