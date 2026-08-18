"""Separate parent step template with typed deadlines/evidence and safe rules."""

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.infrastructure.process_guard import (
	parse_rule,
	require_template_draft,
)


class FerumStepTemplate(Document):
	def before_insert(self) -> None:
		require_template_draft(self._process_template())

	def validate(self) -> None:
		self.step_code = (self.get("step_code") or "").strip().upper()
		if self.sequence < 1:
			frappe.throw(_("Step sequence должна быть положительной."))
		for fieldname in ("requirement_match_rule", "condition_rule", "activation_rule"):
			parse_rule(self.get(fieldname), fieldname)
		if min(self.offset_days, self.warning_days, self.escalation_days) < 0:
			frappe.throw(_("Deadline offsets не могут быть отрицательными."))
		if self.deadline_type == "Absolute" and not self.absolute_due_at:
			frappe.throw(_("Absolute deadline требует absolute_due_at."))
		if self.deadline_type == "Relative" and not self.trigger_event:
			frappe.throw(_("Relative deadline требует trigger_event."))
		if self.requirement_source_policy == "Approved One-time Requirement" and not parse_rule(
			self.requirement_match_rule, "requirement_match_rule"
		):
			frappe.throw(_("Requirement source policy требует match rule."))
		dependencies = {
			item.strip().upper()
			for item in (self.depends_on_step_codes or "").replace("\n", ",").split(",")
			if item.strip()
		}
		if self.step_code in dependencies:
			frappe.throw(_("Step Template не может зависеть от себя."))
		self.depends_on_step_codes = "\n".join(sorted(dependencies))
		if self.get_doc_before_save() is not None:
			require_template_draft(self._process_template())

	def on_trash(self) -> None:
		require_template_draft(self._process_template())

	def _process_template(self) -> str:
		process_template = frappe.db.get_value(
			"Ferum Stage Template", self.stage_template, "process_template"
		)
		if not process_template:
			frappe.throw(_("Stage Template не найден."))
		return str(process_template)


def on_doctype_update() -> None:
	frappe.db.add_unique(
		"Ferum Step Template",
		["stage_template", "step_code"],
		"ca_step_template_code_uniq",
	)
	frappe.db.add_index("Ferum Step Template", ["stage_template", "sequence"])
