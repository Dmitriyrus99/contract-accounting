"""Version root for one immutable published CA-11 process graph."""

from __future__ import annotations

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from contract_accounting.infrastructure.process_guard import (
	TEMPLATE_PUBLISH_FLAG,
	parse_rule,
)

DOCTYPE: Final[str] = "Ferum Process Template"


class FerumProcessTemplate(Document):
	def validate(self) -> None:
		self.code = (self.get("code") or "").strip().upper()
		parse_rule(self.scope_rule, "scope_rule")
		if self.version < 1:
			frappe.throw(_("Process Template version должна быть положительной."))
		if self.effective_to and getdate(self.effective_from) > getdate(self.effective_to):
			frappe.throw(_("effective_from не может быть позже effective_to."))
		before = self.get_doc_before_save()
		if before is None:
			if self.status != "Draft":
				frappe.throw(_("Новый Process Template создаётся только в Draft."))
			return
		if before.status == "Published":
			frappe.throw(_("Published Process Template неизменяем; создайте новую version."), frappe.PermissionError)
		if self.status != before.status and not frappe.flags.get(TEMPLATE_PUBLISH_FLAG):
			frappe.throw(_("Template status изменяется только typed command."), frappe.PermissionError)

	def on_trash(self) -> None:
		if self.status != "Draft":
			frappe.throw(_("Удаление published/retired Process Template запрещено."), frappe.PermissionError)


def on_doctype_update() -> None:
	frappe.db.add_unique(DOCTYPE, ["code", "version"], "ca_process_template_code_version_uniq")
	frappe.db.add_index(DOCTYPE, ["process_type", "status"])
