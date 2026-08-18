"""Normalized typed evidence with immutable validated provenance."""

from __future__ import annotations

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.infrastructure.process_guard import (
	EVIDENCE_WRITER_FLAG,
	require_writer,
)

SOURCE_ALLOWLIST: Final[dict[str, frozenset[str]]] = {
	"Document": frozenset({"Ferum Project Document"}),
	"File": frozenset({"File"}),
	"Email": frozenset({"Communication"}),
	"Outgoing Letter": frozenset({"Ferum Project Document"}),
	"Incoming Letter": frozenset({"Ferum Project Document"}),
	"Call Record": frozenset({"Communication"}),
	"Meeting Record": frozenset({"Communication"}),
	"Photo": frozenset({"File", "Ferum Photo Evidence"}),
	"Approval": frozenset({"User", "Ferum Project Document"}),
	"ERP Document": frozenset(
		{"Sales Invoice", "Purchase Invoice", "Payment Entry", "Ferum Billing Output"}
	),
	"Payment": frozenset({"Payment Entry"}),
	"Inspection": frozenset({"Ferum Inspection"}),
	"Manual Confirmation": frozenset(),
}


class FerumProcessEvidence(Document):
	def before_insert(self) -> None:
		require_writer(EVIDENCE_WRITER_FLAG, "Создание Process Evidence")

	def validate(self) -> None:
		before = self.get_doc_before_save()
		if before is not None and not frappe.flags.get(EVIDENCE_WRITER_FLAG):
			frappe.throw(_("Process Evidence изменяется только typed command."), frappe.PermissionError)
		if before is not None:
			immutable = (
				"process_step", "evidence_type", "source_doctype", "source_name",
				"evidence_file", "captured_at", "captured_by", "content_hash",
				"snapshot", "is_completion_evidence", "evidence_key",
			)
			if any(self.get(field) != before.get(field) for field in immutable):
				frappe.throw(_("Process Evidence provenance неизменяем."), frappe.PermissionError)
			if before.validation_status != "Draft":
				frappe.throw(_("Validated/Rejected Process Evidence неизменяем."), frappe.PermissionError)
		if not self.content_hash:
			frappe.throw(_("Process Evidence требует content_hash."))
		allowed = SOURCE_ALLOWLIST.get(self.evidence_type)
		if allowed is None:
			frappe.throw(_("Неизвестный evidence_type."))
		if self.evidence_type == "Manual Confirmation":
			if self.source_doctype or self.source_name:
				frappe.throw(_("Manual Confirmation не использует внешний source."))
		elif not self.source_doctype or not self.source_name or self.source_doctype not in allowed:
			frappe.throw(_("Evidence source не соответствует evidence_type."))
		elif not frappe.db.exists(self.source_doctype, self.source_name):
			frappe.throw(_("Evidence source не найден."))

	def on_trash(self) -> None:
		frappe.throw(_("Удаление Process Evidence запрещено."), frappe.PermissionError)


def on_doctype_update() -> None:
	frappe.db.add_unique(
		"Ferum Process Evidence", ["evidence_key"], "ca_process_evidence_key_uniq"
	)
	frappe.db.add_index("Ferum Process Evidence", ["process_step", "validation_status"])
