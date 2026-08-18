"""Typed-writer managed snapshot of one process stage."""

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.infrastructure.process_guard import (
	PROCESS_WRITER_FLAG,
	reject_direct_managed_update,
	require_writer,
)


class FerumProjectStage(Document):
	def before_insert(self) -> None:
		require_writer(PROCESS_WRITER_FLAG, "Создание Project Stage")

	def validate(self) -> None:
		reject_direct_managed_update(self, "Project Stage")
		process = frappe.db.get_value(
			"Ferum Project Process",
			self.project_process,
			("service_project", "process_template"),
			as_dict=True,
		)
		stage_template_process = frappe.db.get_value(
			"Ferum Stage Template", self.stage_template, "process_template"
		)
		if not process or (
			process.service_project != self.service_project
			or process.process_template != stage_template_process
		):
			frappe.throw(_("Project Stage context не совпадает с process/template."))

	def on_trash(self) -> None:
		frappe.throw(_("Удаление Project Stage запрещено."), frappe.PermissionError)


def on_doctype_update() -> None:
	frappe.db.add_unique(
		"Ferum Project Stage",
		["project_process", "stage_code"],
		"ca_project_stage_code_uniq",
	)
	frappe.db.add_index("Ferum Project Stage", ["project_process", "sequence"])
