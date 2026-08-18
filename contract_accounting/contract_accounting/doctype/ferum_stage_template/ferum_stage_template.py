"""Separate parent stage template required by approved OQ-CA-010."""

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.infrastructure.process_guard import (
	parse_json_object,
	parse_rule,
	require_template_draft,
)


class FerumStageTemplate(Document):
	def before_insert(self) -> None:
		require_template_draft(self.process_template)

	def validate(self) -> None:
		self.stage_code = (self.get("stage_code") or "").strip().upper()
		if self.sequence < 1:
			frappe.throw(_("Stage sequence должна быть положительной."))
		parse_rule(self.entry_rule, "entry_rule")
		parse_rule(self.exit_rule, "exit_rule")
		parse_json_object(self.gate_policy, "gate_policy")
		if self.get_doc_before_save() is not None:
			require_template_draft(self.process_template)

	def on_trash(self) -> None:
		require_template_draft(self.process_template)


def on_doctype_update() -> None:
	frappe.db.add_unique(
		"Ferum Stage Template",
		["process_template", "stage_code"],
		"ca_stage_template_code_uniq",
	)
	frappe.db.add_index("Ferum Stage Template", ["process_template", "sequence"])
