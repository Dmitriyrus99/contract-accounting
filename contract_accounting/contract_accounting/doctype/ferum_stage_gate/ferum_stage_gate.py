"""Persisted evaluation result for a stage exit, never a percentage proxy."""

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.infrastructure.process_guard import (
	GATE_WRITER_FLAG,
	require_writer,
)


class FerumStageGate(Document):
	def before_insert(self) -> None:
		require_writer(GATE_WRITER_FLAG, "Создание Stage Gate")

	def validate(self) -> None:
		if self.get_doc_before_save() is not None and not frappe.flags.get(GATE_WRITER_FLAG):
			frappe.throw(_("Stage Gate изменяется только evaluator CA-11."), frappe.PermissionError)
		stage = frappe.db.get_value(
			"Ferum Project Stage",
			self.project_stage,
			("service_project", "project_process"),
			as_dict=True,
		)
		if not stage or (
			stage.service_project != self.service_project
			or stage.project_process != self.project_process
		):
			frappe.throw(_("Stage Gate context не совпадает с Project Stage."))

	def on_trash(self) -> None:
		frappe.throw(_("Удаление Stage Gate запрещено."), frappe.PermissionError)


def on_doctype_update() -> None:
	frappe.db.add_unique(
		"Ferum Stage Gate",
		["project_stage", "gate_code"],
		"ca_stage_gate_code_uniq",
	)
	frappe.db.add_index("Ferum Stage Gate", ["project_process", "status"])
