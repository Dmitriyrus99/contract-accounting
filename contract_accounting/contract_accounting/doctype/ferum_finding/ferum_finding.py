"""Independent discovered fact with explicit confirmation and resolution lifecycles."""

from __future__ import annotations

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


DOCTYPE: Final[str] = "Ferum Finding"
ALLOWED_SOURCE_DOCTYPES: Final[frozenset[str]] = frozenset(
	{"Ferum Maintenance Visit", "Ferum Inspection"}
)
ALLOWED_EXECUTION_DOCTYPES: Final[frozenset[str]] = frozenset(
	{"Ferum Service Request"}
)
CONFIRMATION_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Pending": frozenset({"Confirmed", "Rejected"}),
	"Confirmed": frozenset(),
	"Rejected": frozenset(),
}
STATUS_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Open": frozenset({"In Resolution", "Resolved", "Rejected"}),
	"In Resolution": frozenset({"Resolved"}),
	"Resolved": frozenset({"In Resolution", "Closed"}),
	"Closed": frozenset(),
	"Rejected": frozenset(),
}
_TRIAGE_ROLES: Final[frozenset[str]] = frozenset(
	{"Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_RESOLUTION_ROLES: Final[frozenset[str]] = frozenset(
	{"Инженер", "Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_CLOSE_ROLES: Final[frozenset[str]] = frozenset(
	{"Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
	"source_doctype",
	"source_name",
	"service_project",
	"project_object",
	"service_object",
	"object_system",
	"found_at",
	"found_by",
	"detected_context_snapshot",
)


class FerumFinding(Document):
	def validate(self) -> None:
		self._normalize()
		self._derive_source_context()
		self._validate_execution_links()
		self._validate_transitions()
		self._validate_status_contract()
		self._validate_dates()
		self._freeze_provenance()
		self._freeze_confirmed_classification()
		self._freeze_terminal_record()

	def on_trash(self) -> None:
		if self.get("confirmation_status") != "Pending" or self.get("status") != "Open":
			frappe.throw(
				_("Удаление Finding разрешено только до подтверждения в Pending/Open."),
				frappe.PermissionError,
			)

	def _normalize(self) -> None:
		for fieldname in ("title", "description", "resolution", "comment"):
			if self.get(fieldname) is not None:
				self.set(fieldname, str(self.get(fieldname)).strip())
		if self.is_new():
			self.found_at = self.get("found_at") or now_datetime()
			self.found_by = self.get("found_by") or frappe.session.user

	def _derive_source_context(self) -> None:
		if self.get("source_doctype") not in ALLOWED_SOURCE_DOCTYPES:
			frappe.throw(
				_("Finding source DocType не разрешён: {0}.").format(
					self.get("source_doctype") or "<empty>"
				)
			)
		if not frappe.db.exists("DocType", self.source_doctype):
			frappe.throw(
				_("Finding source DocType ещё не установлен: {0}.").format(
					self.source_doctype
				)
			)
		if not frappe.db.exists(self.source_doctype, self.source_name):
			frappe.throw(_("Finding source не найден."))
		source = frappe.get_doc(self.source_doctype, self.source_name)
		source.check_permission("read")
		project_object = frappe.db.get_value(
			"Ferum Project Object",
			source.get("project_object"),
			("service_project", "service_object"),
			as_dict=True,
		)
		if not project_object:
			frappe.throw(_("Source Project Object не найден."))
		context = {
			"service_project": source.get("service_project"),
			"project_object": source.get("project_object"),
			"service_object": source.get("service_object") or project_object.service_object,
			"object_system": source.get("object_system"),
		}
		if context["service_project"] != project_object.service_project:
			frappe.throw(_("Finding source содержит несогласованный Service Project."))
		if context["object_system"]:
			system_object = frappe.db.get_value(
				"Ferum Object System", context["object_system"], "service_object"
			)
			if system_object != context["service_object"]:
				frappe.throw(_("Finding source содержит несогласованный Object System."))
		for fieldname, value in context.items():
			if self.get(fieldname) and self.get(fieldname) != value:
				frappe.throw(
					_("Finding.{0} определяется source и не может отличаться.").format(
						fieldname
					)
				)
			self.set(fieldname, value)
		if self.is_new():
			self.detected_context_snapshot = frappe.as_json(
				{
					"source_doctype": self.source_doctype,
					"source_name": self.source_name,
					**context,
					"found_at": str(self.found_at),
					"found_by": self.found_by,
				}
			)

	def _validate_execution_links(self) -> None:
		events: set[str] = set()
		targets: set[tuple[str, str]] = set()
		for row in self.get("execution_links") or []:
			if row.target_doctype not in ALLOWED_EXECUTION_DOCTYPES:
				frappe.throw(
					_("Finding execution target DocType не разрешён: {0}.").format(
						row.target_doctype
					)
				)
			if not frappe.db.exists(row.target_doctype, row.target_name):
				frappe.throw(_("Finding execution target не найден."))
			key = (row.source_event_key or "").strip()
			if not key or key in events:
				frappe.throw(_("Execution link требует уникальный source_event_key."))
			events.add(key)
			row.source_event_key = key
			target_key = (row.target_doctype, row.target_name)
			if target_key in targets:
				frappe.throw(_("Execution target уже связан с Finding."))
			targets.add(target_key)
			target = frappe.db.get_value(
				row.target_doctype,
				row.target_name,
				("service_project", "project_object", "object_system"),
				as_dict=True,
			)
			if not target or target.service_project != self.service_project:
				frappe.throw(_("Execution target должен относиться к Service Project Finding."))
			if target.project_object != self.project_object:
				frappe.throw(_("Execution target должен относиться к Project Object Finding."))
			if self.object_system and target.object_system != self.object_system:
				frappe.throw(_("Execution target/Object System не совпадает с Finding."))

	def _validate_transitions(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if self.confirmation_status != "Pending" or self.status != "Open":
				frappe.throw(_("Новый Finding создаётся только в Pending/Open."))
			return
		old_confirmation, new_confirmation = (
			before.confirmation_status,
			self.confirmation_status,
		)
		if old_confirmation != new_confirmation:
			if new_confirmation not in CONFIRMATION_TRANSITIONS.get(
				old_confirmation, frozenset()
			):
				frappe.throw(
					_("Недопустимый confirmation transition: {0} → {1}.").format(
						old_confirmation, new_confirmation
					)
				)
			self._require_role(_TRIAGE_ROLES, "Finding confirmation")
		old_status, new_status = before.status, self.status
		if old_status == new_status:
			return
		if new_status not in STATUS_TRANSITIONS.get(old_status, frozenset()):
			frappe.throw(
				_("Недопустимый Finding transition: {0} → {1}.").format(
					old_status, new_status
				)
			)
		self._require_role(
			_CLOSE_ROLES if new_status in {"Closed", "Rejected"} else _RESOLUTION_ROLES,
			"Finding status transition",
		)
		if new_status in {"Resolved", "Rejected"}:
			self.resolved_at = now_datetime()
			self.resolved_by = frappe.session.user
		if new_status in {"Closed", "Rejected"}:
			self.closed_at = now_datetime()
			self.closed_by = frappe.session.user
		if new_status == "In Resolution" and old_status == "Resolved":
			self.resolved_at = None
			self.resolved_by = None

	def _validate_status_contract(self) -> None:
		if self.confirmation_status == "Pending" and self.status != "Open":
			frappe.throw(_("Pending Finding должен оставаться Open."))
		if self.confirmation_status == "Rejected":
			if self.status != "Rejected" or self.resolution_class != "False Positive":
				frappe.throw(
					_("Rejected confirmation требует status=Rejected и False Positive.")
				)
		if self.status == "Rejected" and self.confirmation_status != "Rejected":
			frappe.throw(_("Rejected status требует Rejected confirmation."))
		if self.status in {"In Resolution", "Resolved", "Closed"}:
			if self.confirmation_status != "Confirmed":
				frappe.throw(_("Resolution lifecycle требует Confirmed Finding."))
		if self.confirmation_status == "Confirmed":
			if not self.decision or not self.responsible or not self.due_date:
				frappe.throw(_("Confirmed Finding требует decision, responsible и due_date."))
		if self.status in {"Resolved", "Closed", "Rejected"}:
			if not self.resolution_class or not self.resolution:
				frappe.throw(_("Resolved/Closed/Rejected Finding требует resolution class/text."))
			if not self.resolved_at or not self.resolved_by:
				frappe.throw(_("Resolved/Closed/Rejected Finding требует resolved actor/date."))
			self._validate_evidence()
		if self.status in {"Closed", "Rejected"}:
			if not self.closed_at or not self.closed_by or not self.due_date:
				frappe.throw(_("Closed/Rejected Finding требует due/closed dates и actor."))

	def _validate_evidence(self) -> None:
		accepted_photo_exists = bool(
			self.name
			and frappe.db.exists(
				"Ferum Photo Evidence",
				{
					"source_doctype": DOCTYPE,
					"source_name": self.name,
					"review_status": "Accepted",
				},
			)
		)
		if not self.get("evidence") and not accepted_photo_exists:
			frappe.throw(_("Finding resolution/close требует evidence."))
		for row in self.evidence:
			if not frappe.db.exists("File", row.file):
				frappe.throw(_("Finding evidence File не найден."))

	def _validate_dates(self) -> None:
		found_at = get_datetime(self.found_at)
		if self.due_date and get_datetime(self.due_date) < found_at:
			frappe.throw(_("Finding due_date не может быть раньше found_at."))
		if self.resolved_at and get_datetime(self.resolved_at) < found_at:
			frappe.throw(_("resolved_at не может быть раньше found_at."))
		if self.closed_at:
			if not self.resolved_at or get_datetime(self.closed_at) < get_datetime(self.resolved_at):
				frappe.throw(_("closed_at не может быть раньше resolved_at."))

	def _freeze_provenance(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			return
		changed = [field for field in _IDENTITY_FIELDS if self.get(field) != before.get(field)]
		if changed:
			frappe.throw(_("Finding provenance неизменяема: {0}.").format(", ".join(changed)))

	def _freeze_confirmed_classification(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.confirmation_status == "Pending":
			return
		changed = [
			field
			for field in ("category", "severity", "title", "description")
			if self.get(field) != before.get(field)
		]
		if changed:
			frappe.throw(
				_("Confirmed Finding classification неизменяема: {0}.").format(", ".join(changed))
			)

	def _freeze_terminal_record(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.status not in {"Closed", "Rejected"}:
			return
		changed = [
			field.fieldname
			for field in self.meta.fields
			if self._signature(field.fieldname) != self._signature(field.fieldname, before)
		]
		if changed:
			frappe.throw(_("Closed/Rejected Finding immutable."))

	def _signature(self, fieldname: str, document: Document | None = None) -> str:
		document = document or self
		value = document.get(fieldname)
		if isinstance(value, list):
			value = [row.as_dict(no_nulls=False) for row in value]
		return frappe.as_json(value)

	@staticmethod
	def _require_role(allowed: frozenset[str], operation: str) -> None:
		if frappe.session.user == "Administrator":
			return
		if not set(frappe.get_roles(frappe.session.user)).intersection(allowed):
			frappe.throw(_("Недостаточно прав: {0}.").format(operation), frappe.PermissionError)


def on_doctype_update() -> None:
	frappe.db.add_index(DOCTYPE, ["service_project", "status"], "ca_finding_project_status_idx")
	frappe.db.add_index(DOCTYPE, ["severity", "status"], "ca_finding_severity_status_idx")
	frappe.db.add_index(DOCTYPE, ["due_date", "status"], "ca_finding_due_status_idx")
	frappe.db.add_index(DOCTYPE, ["source_doctype", "source_name"], "ca_finding_source_idx")
