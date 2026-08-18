"""Planned maintenance execution fact with review and acceptance gates."""

from __future__ import annotations

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


DOCTYPE: Final[str] = "Ferum Maintenance Visit"
STATUS_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Planned": frozenset({"In Progress", "Cancelled"}),
	"In Progress": frozenset({"Completed", "Cancelled"}),
	"Completed": frozenset(),
	"Cancelled": frozenset(),
}
REVIEW_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Pending": frozenset({"Approved", "Rejected"}),
	"Rejected": frozenset({"Pending"}),
	"Approved": frozenset(),
}
ACCEPTANCE_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Pending": frozenset({"Accepted", "Rejected"}),
	"Rejected": frozenset({"Pending"}),
	"Accepted": frozenset(),
}
_EXECUTION_ROLES: Final[frozenset[str]] = frozenset(
	{"Инженер", "Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_REVIEW_ROLES: Final[frozenset[str]] = frozenset(
	{"Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_ACCEPTANCE_ROLES: Final[frozenset[str]] = frozenset(
	{"Руководитель проектов", "System Manager"}
)
_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
	"service_project",
	"contract_obligation",
	"maintenance_schedule",
	"project_object",
	"service_object",
	"object_system",
	"period_key",
	"planned_date",
	"window_start",
	"window_end",
	"generation_key",
	"replacement_for",
)


class FerumMaintenanceVisit(Document):
	def validate(self) -> None:
		self._set_service_object()
		self._validate_context()
		self._validate_status_transition()
		self._validate_review_transition()
		self._validate_acceptance_transition()
		self._validate_actual_dates()
		self._validate_checklist()
		self._validate_completion_and_acceptance()
		self._validate_identity_immutable()
		self._freeze_reviewed_fact()
		self._freeze_accepted_fact()
		self.billing_eligible = int(self.get("acceptance_status") == "Accepted")

	def on_update(self) -> None:
		self._project_schedule_status()

	def on_trash(self) -> None:
		frappe.throw(
			_("Maintenance Visit is an execution fact; cancel instead of deleting."),
			frappe.PermissionError,
		)

	def _set_service_object(self) -> None:
		service_object = frappe.db.get_value(
			"Ferum Project Object", self.project_object, "service_object"
		)
		if not service_object:
			frappe.throw(_("Project Object не найден."))
		if self.get("service_object") and self.service_object != service_object:
			frappe.throw(_("service_object должен определяться выбранным Project Object."))
		self.service_object = service_object

	def _validate_context(self) -> None:
		schedule = frappe.db.get_value(
			"Ferum Maintenance Schedule",
			self.maintenance_schedule,
			(
				"service_project",
				"contract_obligation",
				"project_object",
				"object_system",
				"period_key",
				"planned_date",
				"window_start",
				"window_end",
			),
			as_dict=True,
		)
		if not schedule:
			frappe.throw(_("Maintenance Schedule не найден."))
		for fieldname in (
			"service_project",
			"contract_obligation",
			"project_object",
			"object_system",
			"period_key",
			"planned_date",
			"window_start",
			"window_end",
		):
			if self.get(fieldname) != schedule.get(fieldname):
				frappe.throw(_("Visit.{0} не совпадает с Schedule.").format(fieldname))
		system_object = frappe.db.get_value(
			"Ferum Object System", self.object_system, "service_object"
		)
		if system_object != self.service_object:
			frappe.throw(_("Object System должен входить в Service Object визита."))
		if self.get("replacement_for"):
			original = frappe.db.get_value(
				DOCTYPE,
				self.replacement_for,
				("maintenance_schedule", "status"),
				as_dict=True,
			)
			if not original or original.maintenance_schedule != self.maintenance_schedule:
				frappe.throw(_("Replacement должен относиться к тому же Schedule."))
			if original.status != "Cancelled":
				frappe.throw(_("Replacement разрешён только для Cancelled Visit."))

	def _validate_status_transition(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if self.get("status") != "Planned":
				frappe.throw(_("Новый Maintenance Visit создаётся только в Planned."))
			return
		old, new = before.get("status"), self.get("status")
		if old == new:
			return
		if new not in STATUS_TRANSITIONS.get(old, frozenset()):
			frappe.throw(_("Недопустимый Visit transition: {0} → {1}.").format(old, new))
		self._require_role(_EXECUTION_ROLES, "Visit transition")

	def _validate_review_transition(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if self.get("review_status") != "Pending":
				frappe.throw(_("Новый Visit начинает review в Pending."))
			return
		old, new = before.get("review_status"), self.get("review_status")
		if old == new:
			return
		if new not in REVIEW_TRANSITIONS.get(old, frozenset()):
			frappe.throw(_("Недопустимый review transition: {0} → {1}.").format(old, new))
		self._require_role(_REVIEW_ROLES, "Visit review")
		if new in {"Approved", "Rejected"}:
			if self.get("status") != "Completed":
				frappe.throw(_("Review возможен только для Completed Visit."))
			if new == "Approved":
				self._validate_evidence_ready("Approved review")
			self.reviewed_by = frappe.session.user
			self.reviewed_on = now_datetime()
		elif new == "Pending":
			self.reviewed_by = None
			self.reviewed_on = None

	def _validate_acceptance_transition(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if self.get("acceptance_status") != "Pending":
				frappe.throw(_("Новый Visit начинает acceptance в Pending."))
			return
		old, new = before.get("acceptance_status"), self.get("acceptance_status")
		if old == new:
			return
		if new not in ACCEPTANCE_TRANSITIONS.get(old, frozenset()):
			frappe.throw(_("Недопустимый acceptance transition: {0} → {1}.").format(old, new))
		self._require_role(_ACCEPTANCE_ROLES, "Visit acceptance")
		if new == "Accepted":
			self.accepted_by = frappe.session.user
			self.accepted_on = now_datetime()
		elif new == "Pending":
			self.accepted_by = None
			self.accepted_on = None

	def _validate_actual_dates(self) -> None:
		if self.get("status") in {"In Progress", "Completed"} and not self.get("actual_start"):
			frappe.throw(_("In Progress/Completed Visit требует actual_start."))
		if self.get("status") == "Completed" and not self.get("actual_end"):
			frappe.throw(_("Completed Visit требует actual_end."))
		if self.get("actual_start") and self.get("actual_end"):
			if get_datetime(self.actual_start) > get_datetime(self.actual_end):
				frappe.throw(_("actual_start не может быть позже actual_end."))
		if self.get("status") == "Cancelled" and not (self.get("cancellation_reason") or "").strip():
			frappe.throw(_("Cancelled Visit требует cancellation_reason."))

	def _validate_checklist(self) -> None:
		codes: set[str] = set()
		for row in self.get("checklist") or []:
			code = (row.get("item_code") or "").strip()
			if code in codes:
				frappe.throw(_("Duplicate checklist item_code: {0}.").format(code))
			codes.add(code)
			if row.get("is_completed") and not row.get("result"):
				frappe.throw(_("Completed checklist row требует result."))

	def _validate_completion_and_acceptance(self) -> None:
		if self.get("status") == "Completed":
			if not self.get("work_result") or not (self.get("visit_report") or "").strip():
				frappe.throw(_("Completed Visit требует work_result и visit_report."))
		if self.get("acceptance_status") != "Accepted":
			return
		if self.get("status") != "Completed" or self.get("review_status") != "Approved":
			frappe.throw(_("Accepted Visit требует Completed status и Approved review."))
		self._validate_evidence_ready("Accepted Visit")

	def _validate_evidence_ready(self, operation: str) -> None:
		if not self.get("checklist") or not all(row.get("is_completed") for row in self.checklist):
			frappe.throw(_("{0} требует полностью выполненный checklist.").format(operation))
		if not self.get("evidence"):
			frappe.throw(_("{0} требует execution evidence.").format(operation))

	def _validate_identity_immutable(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			return
		changed = [field for field in _IDENTITY_FIELDS if self.get(field) != before.get(field)]
		if changed:
			frappe.throw(_("Visit provenance неизменяема: {0}.").format(", ".join(changed)))

	def _freeze_reviewed_fact(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.get("review_status") != "Approved":
			return
		fields = (
			"status", "actual_start", "actual_end", "work_result", "checklist",
			"evidence", "visit_report", "recommendations",
		)
		changed = [field for field in fields if self._signature(field) != self._signature(field, before)]
		if changed:
			frappe.throw(_("Approved review snapshot неизменяем: {0}.").format(", ".join(changed)))

	def _freeze_accepted_fact(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.get("acceptance_status") != "Accepted":
			return
		changed = [
			field.fieldname
			for field in self.meta.fields
			if self._signature(field.fieldname) != self._signature(field.fieldname, before)
		]
		if changed:
			frappe.throw(_("Accepted Visit immutable."))

	def _signature(self, fieldname: str, document: Document | None = None) -> str:
		document = document or self
		value = document.get(fieldname)
		if isinstance(value, list):
			value = [row.as_dict(no_nulls=False) for row in value]
		return frappe.as_json(value)

	def _project_schedule_status(self) -> None:
		if self.get("status") == "Completed":
			frappe.db.set_value(
				"Ferum Maintenance Schedule",
				self.maintenance_schedule,
				"status",
				"Completed",
				update_modified=False,
			)

	@staticmethod
	def _require_role(allowed: frozenset[str], operation: str) -> None:
		if frappe.session.user == "Administrator":
			return
		if not set(frappe.get_roles(frappe.session.user)).intersection(allowed):
			frappe.throw(_("Недостаточно прав: {0}.").format(operation), frappe.PermissionError)


def on_doctype_update() -> None:
	frappe.db.add_unique(DOCTYPE, ["generation_key"], "ca_visit_generation_uniq")
	frappe.db.add_unique(DOCTYPE, ["replacement_for"], "ca_visit_replacement_uniq")
	frappe.db.add_index(DOCTYPE, ["service_project", "planned_date"], "ca_visit_project_date_idx")
	frappe.db.add_index(DOCTYPE, ["status", "review_status"], "ca_visit_status_review_idx")
