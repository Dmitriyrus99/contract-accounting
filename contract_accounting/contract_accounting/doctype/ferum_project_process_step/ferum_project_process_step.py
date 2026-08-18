"""Process SSOT step; user work is projected to standard ToDo."""

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.domain.process import BASE_STEP_STATUSES
from contract_accounting.infrastructure.process_guard import (
	PROCESS_WRITER_FLAG,
	reject_direct_managed_update,
	require_writer,
)


class FerumProjectProcessStep(Document):
	def before_insert(self) -> None:
		require_writer(PROCESS_WRITER_FLAG, "Создание Project Process Step")

	def validate(self) -> None:
		reject_direct_managed_update(self, "Project Process Step")
		if self.status not in BASE_STEP_STATUSES:
			frappe.throw(_("Недопустимый base step status."))
		process = frappe.db.get_value(
			"Ferum Project Process", self.project_process, "service_project"
		)
		stage_process = frappe.db.get_value(
			"Ferum Project Stage", self.project_stage, "project_process"
		)
		step_stage = frappe.db.get_value(
			"Ferum Step Template", self.step_template, "stage_template"
		)
		instance_stage_template = frappe.db.get_value(
			"Ferum Project Stage", self.project_stage, "stage_template"
		)
		if (
			process != self.service_project
			or stage_process != self.project_process
			or step_stage != instance_stage_template
		):
			frappe.throw(_("Project Process Step context не совпадает."))
		if self.contract_requirement:
			requirement_project = frappe.db.get_value(
				"Ferum Contract Requirement", self.contract_requirement, "service_project"
			)
			if requirement_project != self.service_project:
				frappe.throw(_("Step Requirement относится к другому Service Project."))

	def on_trash(self) -> None:
		frappe.throw(_("Удаление Project Process Step запрещено."), frappe.PermissionError)


def on_doctype_update() -> None:
	frappe.db.add_unique(
		"Ferum Project Process Step", ["instance_key"], "ca_process_step_instance_uniq"
	)
	frappe.db.add_index(
		"Ferum Project Process Step", ["project_stage", "status"]
	)
	frappe.db.add_index(
		"Ferum Project Process Step", ["responsible_user", "status"]
	)
