"""Specialized photo provenance that keeps Frappe File as the binary SSOT."""

from __future__ import annotations

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


DOCTYPE: Final[str] = "Ferum Photo Evidence"
ALLOWED_SOURCE_DOCTYPES: Final[frozenset[str]] = frozenset(
	{
		"Ferum Maintenance Visit",
		"Ferum Service Request",
		"Ferum Finding",
		"Ferum Inspection",
	}
)
REVIEW_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Pending": frozenset({"Accepted", "Rejected"}),
	"Rejected": frozenset({"Pending"}),
	"Accepted": frozenset(),
}
_REVIEW_ROLES: Final[frozenset[str]] = frozenset(
	{"Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
	"source_doctype",
	"source_name",
	"service_project",
	"project_object",
	"service_object",
	"object_system",
	"file",
	"captured_at",
	"captured_by",
	"content_hash",
)


class FerumPhotoEvidence(Document):
	def validate(self) -> None:
		if self.is_new():
			self.captured_at = self.get("captured_at") or now_datetime()
			self.captured_by = self.get("captured_by") or frappe.session.user
		self._derive_source_context()
		self._derive_file_hash()
		self._validate_review_transition()
		self._freeze_identity()
		self._freeze_accepted()

	def on_trash(self) -> None:
		if self.review_status != "Pending":
			frappe.throw(
				_("Удаление Photo Evidence разрешено только в Pending."),
				frappe.PermissionError,
			)

	def _derive_source_context(self) -> None:
		if self.get("source_doctype") not in ALLOWED_SOURCE_DOCTYPES:
			frappe.throw(_("Photo Evidence source DocType не разрешён."))
		if not frappe.db.exists("DocType", self.source_doctype):
			frappe.throw(
				_("Photo Evidence source DocType ещё не установлен: {0}.").format(
					self.source_doctype
				)
			)
		if not frappe.db.exists(self.source_doctype, self.source_name):
			frappe.throw(_("Photo Evidence source не найден."))
		source = frappe.get_doc(self.source_doctype, self.source_name)
		source.check_permission("read")
		project_object = frappe.db.get_value(
			"Ferum Project Object",
			source.get("project_object"),
			("service_project", "service_object"),
			as_dict=True,
		)
		if not project_object:
			frappe.throw(_("Photo Evidence source Project Object не найден."))
		context = {
			"service_project": source.get("service_project"),
			"project_object": source.get("project_object"),
			"service_object": source.get("service_object") or project_object.service_object,
			"object_system": source.get("object_system"),
		}
		if context["service_project"] != project_object.service_project:
			frappe.throw(_("Photo Evidence source context несогласован."))
		for fieldname, value in context.items():
			if self.get(fieldname) and self.get(fieldname) != value:
				frappe.throw(_("Photo Evidence context определяется source."))
			self.set(fieldname, value)

	def _derive_file_hash(self) -> None:
		file_row = frappe.db.get_value(
			"File",
			self.file,
			("content_hash", "attached_to_doctype", "attached_to_name"),
			as_dict=True,
		)
		if not file_row or not file_row.content_hash:
			frappe.throw(_("Photo Evidence требует существующий File с content_hash."))
		if (file_row.attached_to_doctype, file_row.attached_to_name) != (
			self.source_doctype,
			self.source_name,
		):
			frappe.throw(_("Photo Evidence File должен быть прикреплён к source."))
		if self.get("content_hash") and self.content_hash != file_row.content_hash:
			frappe.throw(_("Photo Evidence content_hash определяется File."))
		self.content_hash = file_row.content_hash

	def _validate_review_transition(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if self.review_status != "Pending":
				frappe.throw(_("Новый Photo Evidence создаётся только в Pending."))
			return
		old, new = before.review_status, self.review_status
		if old == new:
			return
		if new not in REVIEW_TRANSITIONS.get(old, frozenset()):
			frappe.throw(_("Недопустимый Photo Evidence review transition."))
		self._require_role()
		if new in {"Accepted", "Rejected"}:
			self.reviewed_at = now_datetime()
			self.reviewed_by = frappe.session.user
		else:
			self.reviewed_at = None
			self.reviewed_by = None

	def _freeze_identity(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			return
		changed = [field for field in _IDENTITY_FIELDS if self.get(field) != before.get(field)]
		if changed:
			frappe.throw(_("Photo Evidence provenance неизменяема."))

	def _freeze_accepted(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.review_status != "Accepted":
			return
		changed = [
			field.fieldname
			for field in self.meta.fields
			if self.get(field.fieldname) != before.get(field.fieldname)
		]
		if changed:
			frappe.throw(_("Accepted Photo Evidence immutable."))

	@staticmethod
	def _require_role() -> None:
		if frappe.session.user == "Administrator":
			return
		if not set(frappe.get_roles(frappe.session.user)).intersection(_REVIEW_ROLES):
			frappe.throw(_("Недостаточно прав для Photo Evidence review."), frappe.PermissionError)


def on_doctype_update() -> None:
	frappe.db.add_index(DOCTYPE, ["service_project", "review_status"], "ca_photo_project_review_idx")
	frappe.db.add_index(DOCTYPE, ["source_doctype", "source_name"], "ca_photo_source_idx")
