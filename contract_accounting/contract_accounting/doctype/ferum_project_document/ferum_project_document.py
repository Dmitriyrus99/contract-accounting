"""Universal project-document registry with three guarded status dimensions."""

from __future__ import annotations

import hashlib
import json
from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


PROJECT_DOCUMENT_DOCTYPE: Final[str] = "Ferum Project Document"
DOCUMENT_EVENT_DOCTYPE: Final[str] = "Ferum Project Document Event"
DOCUMENT_WRITE_FLAG: Final[str] = "contract_accounting_project_document_write"
DOCUMENT_TRANSITION_CONTEXT_FLAG: Final[str] = (
	"contract_accounting_project_document_transition_context"
)
DOCUMENT_EVENT_WRITER_FLAG: Final[str] = (
	"contract_accounting_project_document_event_writer"
)

ALLOWED_SOURCE_DOCTYPES: Final[frozenset[str]] = frozenset(
	{
		"Ferum Service Project",
		"Ferum Project Object",
		"Ferum Contract Requirement",
		"Ferum Contract Obligation",
		"Ferum Maintenance Schedule",
		"Ferum Maintenance Visit",
		"Ferum Service Request",
		"Ferum Finding",
		"Ferum Photo Evidence",
		"Ferum Inspection",
	}
)
ALLOWED_PARTY_DOCTYPES: Final[frozenset[str]] = frozenset(
	{"Company", "Customer", "Supplier"}
)
ALLOWED_BILLING_DOCTYPES: Final[frozenset[str]] = frozenset(
	{"Ferum Billing Artifact", "Ferum Billing Output", "Sales Invoice", "Purchase Invoice"}
)
DOCUMENT_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Draft": frozenset({"Active", "Cancelled"}),
	"Active": frozenset({"Superseded", "Archived", "Cancelled"}),
	"Superseded": frozenset(),
	"Cancelled": frozenset(),
	"Archived": frozenset(),
}
DIGITAL_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Missing": frozenset({"Uploaded", "Not Required"}),
	"Uploaded": frozenset({"Verified", "Signed", "Rejected"}),
	"Rejected": frozenset({"Uploaded"}),
	"Verified": frozenset({"Signed", "Superseded"}),
	"Signed": frozenset({"Superseded"}),
	"Superseded": frozenset(),
	"Not Required": frozenset(),
}
ORIGINAL_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Not Requested": frozenset({"Requested", "Not Required"}),
	"Requested": frozenset({"In Transit", "Received"}),
	"In Transit": frozenset({"Received"}),
	"Received": frozenset({"Archived"}),
	"Archived": frozenset(),
	"Not Required": frozenset(),
}

_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
	"service_project",
	"project_object",
	"service_object",
	"document_type",
	"document_number",
	"document_date",
	"version",
	"source_doctype",
	"source_name",
	"issuer_doctype",
	"issuer",
	"version_key",
)
_GUARDED_FIELDS: Final[tuple[str, ...]] = (
	"status",
	"digital_copy_status",
	"digital_not_required_basis",
	"original_status",
	"original_not_required_basis",
	"original_requested_at",
	"original_expected_at",
	"original_shipment_date",
	"original_tracking_number",
	"original_received_at",
	"original_received_by",
	"original_archived_at",
	"original_archived_by",
	"original_storage_location",
	"file",
	"content_hash",
)


class FerumProjectDocument(Document):
	def validate(self) -> None:
		self._derive_source_context()
		self._validate_dates()
		self._validate_party("issuer_doctype", "issuer")
		self._validate_party("recipient_doctype", "recipient")
		self._validate_file()
		self._validate_billing_reference()
		self._validate_related_entities()
		self._derive_version_key()
		self._freeze_identity()
		self._guard_state_changes()
		self._validate_transition()

	def on_trash(self) -> None:
		if (
			self.status != "Draft"
			or self.digital_copy_status != "Missing"
			or self.original_status != "Not Requested"
		):
			frappe.throw(
				_("Удаление Project Document разрешено только до первого перехода."),
				frappe.PermissionError,
			)
		if frappe.db.exists(DOCUMENT_EVENT_DOCTYPE, {"project_document": self.name}):
			frappe.throw(_("Project Document с audit events удалить нельзя."))

	def _derive_source_context(self) -> None:
		if self.source_doctype not in ALLOWED_SOURCE_DOCTYPES:
			frappe.throw(_("Project Document source DocType не разрешён."))
		if not frappe.db.exists("DocType", self.source_doctype):
			frappe.throw(
				_("Project Document source DocType ещё не установлен: {0}.").format(
					self.source_doctype
				)
			)
		if not frappe.db.exists(self.source_doctype, self.source_name):
			frappe.throw(_("Project Document source не найден."))
		source = frappe.get_doc(self.source_doctype, self.source_name)
		source.check_permission("read")

		if self.source_doctype == "Ferum Service Project":
			service_project = source.name
			project_object = self.get("project_object")
			service_object = self.get("service_object")
		elif self.source_doctype == "Ferum Project Object":
			service_project = source.service_project
			project_object = source.name
			service_object = source.service_object
		else:
			service_project = source.get("service_project")
			project_object = source.get("project_object")
			service_object = source.get("service_object")

		if not service_project:
			frappe.throw(_("Project Document source не определяет Service Project."))
		if project_object:
			membership = frappe.db.get_value(
				"Ferum Project Object",
				project_object,
				("service_project", "service_object"),
				as_dict=True,
			)
			if not membership or membership.service_project != service_project:
				frappe.throw(_("Project Document source context несогласован."))
			service_object = membership.service_object

		context = {
			"service_project": service_project,
			"project_object": project_object,
			"service_object": service_object,
		}
		for fieldname, value in context.items():
			if self.get(fieldname) and self.get(fieldname) != value:
				frappe.throw(_("Project Document context определяется source."))
			self.set(fieldname, value)

	def _validate_dates(self) -> None:
		if self.valid_from and self.valid_until:
			if getdate(self.valid_until) < getdate(self.valid_from):
				frappe.throw(_("Valid Until не может быть раньше Valid From."))

	def _validate_party(self, doctype_field: str, name_field: str) -> None:
		doctype, name = self.get(doctype_field), self.get(name_field)
		if bool(doctype) != bool(name):
			frappe.throw(_("Тип и значение стороны задаются вместе."))
		if not doctype:
			return
		if doctype not in ALLOWED_PARTY_DOCTYPES:
			frappe.throw(_("DocType стороны не разрешён."))
		if not frappe.db.exists(doctype, name):
			frappe.throw(_("Указанная сторона не найдена."))

	def _validate_file(self) -> None:
		if not self.file:
			self.content_hash = None
			return
		row = frappe.db.get_value("File", self.file, "content_hash", as_dict=True)
		if not row or not row.content_hash:
			frappe.throw(_("Project Document требует File с content_hash."))
		if self.content_hash and self.content_hash != row.content_hash:
			frappe.throw(_("Project Document content_hash определяется File."))
		self.content_hash = row.content_hash

	def _validate_billing_reference(self) -> None:
		doctype = self.billing_reference_doctype
		name = self.billing_reference_name
		if bool(doctype) != bool(name):
			frappe.throw(_("Billing reference DocType и имя задаются вместе."))
		if not doctype:
			return
		if doctype not in ALLOWED_BILLING_DOCTYPES:
			frappe.throw(_("Billing reference DocType не разрешён."))
		self._validate_related_document(doctype, name)
		billing = frappe.get_doc(doctype, name)
		if billing.meta.has_field("file") and billing.get("file"):
			if self.file and self.file != billing.get("file"):
				frappe.throw(_("Billing Artifact и Project Document используют один File."))
			self.file = billing.get("file")
			self._validate_file()

	def _validate_related_entities(self) -> None:
		for row in self.get("related_entities") or []:
			self._validate_related_document(row.linked_doctype, row.linked_name)
			if row.effective_from and row.effective_until:
				if getdate(row.effective_until) < getdate(row.effective_from):
					frappe.throw(_("Document Link effective period некорректен."))

	def _validate_related_document(self, doctype: str, name: str) -> None:
		if not frappe.db.exists("DocType", doctype) or not frappe.db.exists(doctype, name):
			frappe.throw(_("Связанный документ не найден."))
		related = frappe.get_doc(doctype, name)
		related.check_permission("read")
		if related.meta.has_field("service_project"):
			if related.get("service_project") != self.service_project:
				frappe.throw(_("Связанный документ относится к другому Service Project."))

	def _derive_version_key(self) -> None:
		identity = [
			self.service_project,
			self.document_type,
			self.document_number,
			str(getdate(self.document_date)),
			self.version,
			self.issuer_doctype or "",
			self.issuer or "",
		]
		payload = json.dumps(identity, ensure_ascii=False, separators=(",", ":"))
		self.version_key = hashlib.sha256(payload.encode("utf-8")).hexdigest()

	def _freeze_identity(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			return
		changed = [field for field in _IDENTITY_FIELDS if self.get(field) != before.get(field)]
		if changed:
			frappe.throw(_("Project Document identity/provenance неизменяемы."))

	def _guard_state_changes(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if (
				self.status != "Draft"
				or self.digital_copy_status != "Missing"
				or self.original_status != "Not Requested"
			):
				frappe.throw(_("Новый Project Document создаётся в начальных состояниях."))
			return
		changed = [field for field in _GUARDED_FIELDS if self.get(field) != before.get(field)]
		if changed and not frappe.flags.get(DOCUMENT_WRITE_FLAG):
			frappe.throw(
				_("Project Document status/file меняются только командами CA-05."),
				frappe.PermissionError,
			)

	def _validate_transition(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			return
		context = frappe.flags.get(DOCUMENT_TRANSITION_CONTEXT_FLAG) or {}
		changes = {
			"Document": ("status", DOCUMENT_TRANSITIONS),
			"Digital Copy": ("digital_copy_status", DIGITAL_TRANSITIONS),
			"Original": ("original_status", ORIGINAL_TRANSITIONS),
		}
		changed_dimensions = []
		for dimension, (fieldname, matrix) in changes.items():
			old, new = before.get(fieldname), self.get(fieldname)
			if old == new:
				continue
			changed_dimensions.append(dimension)
			if new not in matrix.get(old, frozenset()):
				frappe.throw(_("Недопустимый Project Document transition: {0}.").format(dimension))
		if changed_dimensions and changed_dimensions != [context.get("dimension")]:
			frappe.throw(_("Одна команда меняет ровно одно status-измерение."))
		if not changed_dimensions:
			return
		if context.get("dimension") == "Document":
			self._validate_document_target()
		elif context.get("dimension") == "Digital Copy":
			self._validate_digital_target(context)
		elif context.get("dimension") == "Original":
			self._validate_original_target(context)

	def _validate_document_target(self) -> None:
		if self.status in {"Active", "Archived"} and not self._has_accepted_form():
			frappe.throw(_("Active/Archived требует проверенную копию или полученный оригинал."))

	def _validate_digital_target(self, context: dict[str, object]) -> None:
		target = self.digital_copy_status
		if target in {"Uploaded", "Verified", "Signed"} and not self.file:
			frappe.throw(_("Digital Copy transition требует File."))
		if target in {"Verified", "Signed"} and not context.get("evidence_file"):
			frappe.throw(_("Verified/Signed требует evidence File."))
		if target == "Not Required":
			if not self.digital_not_required_basis or not context.get("evidence_file"):
				frappe.throw(_("Digital Not Required требует основания и evidence File."))

	def _validate_original_target(self, context: dict[str, object]) -> None:
		target = self.original_status
		if target in {"Received", "Archived"} and not context.get("evidence_file"):
			frappe.throw(_("Received/Archived требует evidence File."))
		if target == "Received" and not self.original_received_at:
			frappe.throw(_("Received требует server stamp."))
		if target == "Archived":
			if not self.original_archived_at or not self.original_storage_location:
				frappe.throw(_("Archived требует server stamp и storage location."))
		if target == "Not Required":
			if not self.original_not_required_basis or not context.get("evidence_file"):
				frappe.throw(_("Original Not Required требует основания и evidence File."))

	def _has_accepted_form(self) -> bool:
		return self.digital_copy_status in {"Verified", "Signed"} or self.original_status in {
			"Received",
			"Archived",
		}


def on_doctype_update() -> None:
	frappe.db.add_index(
		PROJECT_DOCUMENT_DOCTYPE,
		["service_project", "document_type", "document_date"],
		"ca_project_document_registry_idx",
	)
	frappe.db.add_unique(PROJECT_DOCUMENT_DOCTYPE, ["version_key"], "ca_project_document_version_uniq")
