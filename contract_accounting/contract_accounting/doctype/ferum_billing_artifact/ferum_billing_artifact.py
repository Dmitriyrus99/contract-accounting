"""Immutable, versioned file metadata for a Billing Output."""

from __future__ import annotations

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

DOCTYPE: Final[str] = "Ferum Billing Artifact"
ARTIFACT_WRITER_FLAG: Final[str] = "contract_accounting_billing_artifact_writer"
ARTIFACT_UPDATE_FLAG: Final[str] = "contract_accounting_billing_artifact_update"


class FerumBillingArtifact(Document):
	def before_insert(self) -> None:
		if not frappe.flags.get(ARTIFACT_WRITER_FLAG):
			frappe.throw(_("Billing Artifact создаётся только typed writer CA-06."), frappe.PermissionError)
		self.created_at = now_datetime()
		self.created_by = frappe.session.user
		self.version = self._next_version()

	def validate(self) -> None:
		self._derive_context()
		self._validate_mode()
		self._derive_file_hash()
		self._derive_current_key()
		self._guard_update()

	def on_trash(self) -> None:
		frappe.throw(_("Billing Artifact не удаляется; создайте новую версию."), frappe.PermissionError)

	def _derive_context(self) -> None:
		output = frappe.db.get_value(
			"Ferum Billing Output",
			self.billing_output,
			("service_project", "status"),
			as_dict=True,
		)
		if not output:
			frappe.throw(_("Billing Output не найден."))
		if self.get("service_project") and self.service_project != output.service_project:
			frappe.throw(_("Billing Artifact context определяется Output."))
		self.service_project = output.service_project
		if output.status in {"Superseded", "Cancelled"}:
			frappe.throw(_("Нельзя добавлять Artifact к terminal Billing Output."))

	def _validate_mode(self) -> None:
		if self.artifact_type == "Generated":
			if self.generation_mode not in {"Preview", "Final"}:
				frappe.throw(_("Generated Artifact требует Preview/Final mode."))
		elif self.generation_mode:
			frappe.throw(_("generation_mode допустим только для Generated Artifact."))
		if self.artifact_type == "Signed Scan" and not cint(self.is_signed):
			frappe.throw(_("Signed Scan обязан иметь is_signed=1."))

	def _derive_file_hash(self) -> None:
		file_row = frappe.db.get_value("File", self.file, "content_hash", as_dict=True)
		if not file_row or not file_row.content_hash:
			frappe.throw(_("Billing Artifact требует File с content_hash."))
		if self.get("content_hash") and self.content_hash != file_row.content_hash:
			frappe.throw(_("Billing Artifact content_hash определяется File."))
		self.content_hash = file_row.content_hash

	def _derive_current_key(self) -> None:
		self.current_key = (
			f"{self.billing_output}::{self.artifact_type}" if cint(self.is_current) else None
		)

	def _next_version(self) -> int:
		frappe.db.get_value("Ferum Billing Output", self.billing_output, "name", for_update=True)
		current = frappe.db.sql(
			"""select max(version) from `tabFerum Billing Artifact`
			where billing_output=%s and artifact_type=%s""",
			(self.billing_output, self.artifact_type),
		)[0][0]
		return cint(current or 0) + 1

	def _guard_update(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			return
		if not frappe.flags.get(ARTIFACT_UPDATE_FLAG):
			frappe.throw(_("Billing Artifact immutable после вставки."), frappe.PermissionError)
		allowed = {"is_current", "current_key", "project_document"}
		changed = {
			field.fieldname
			for field in self.meta.fields
			if self.get(field.fieldname) != before.get(field.fieldname)
		}
		if changed - allowed:
			frappe.throw(_("Controlled Artifact update изменяет запрещённые поля."))


def on_doctype_update() -> None:
	frappe.db.add_index(DOCTYPE, ["billing_output", "artifact_type", "version"], "ca_artifact_version_idx")
	frappe.db.add_unique(DOCTYPE, ["current_key"], "ca_artifact_current_uniq")
