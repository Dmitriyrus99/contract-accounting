"""Independent unplanned customer/internal work request."""

from __future__ import annotations

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime


DOCTYPE: Final[str] = "Ferum Service Request"
TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Open": frozenset({"Assigned", "In Progress", "Cancelled"}),
	"Assigned": frozenset({"In Progress", "Cancelled"}),
	"In Progress": frozenset({"Resolved", "Cancelled"}),
	"Resolved": frozenset({"Closed", "In Progress"}),
	"Closed": frozenset(),
	"Cancelled": frozenset(),
}
_TRANSITION_ROLES: Final[frozenset[str]] = frozenset(
	{"Инженер", "Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
	"service_project",
	"project_object",
	"service_object",
	"object_system",
	"contract_obligation",
	"source_type",
	"source_reference",
)


class FerumServiceRequest(Document):
	def validate(self) -> None:
		self.source_reference = (self.get("source_reference") or "").strip()
		self._derive_context()
		self._validate_context()
		self._validate_transition()
		self._validate_dates()
		self._validate_resolution()
		self._freeze_identity()

	def on_trash(self) -> None:
		if self.get("status") != "Open":
			frappe.throw(_("Удаление Service Request разрешено только в Open."), frappe.PermissionError)

	def _derive_context(self) -> None:
		project_object = frappe.db.get_value(
			"Ferum Project Object",
			self.project_object,
			("service_project", "service_object"),
			as_dict=True,
		)
		if not project_object:
			frappe.throw(_("Project Object не найден."))
		if project_object.service_project != self.service_project:
			frappe.throw(_("Project Object должен относиться к Service Project заявки."))
		service_object_customer = frappe.db.get_value(
			"Ferum Service Object", project_object.service_object, "customer"
		)
		project_customer = frappe.db.get_value(
			"Ferum Service Project", self.service_project, "customer"
		)
		if service_object_customer != project_customer:
			frappe.throw(_("Customer проекта и Service Object не совпадают."))
		if self.get("service_object") and self.service_object != project_object.service_object:
			frappe.throw(_("service_object определяется Project Object."))
		if self.get("customer") and self.customer != project_customer:
			frappe.throw(_("customer определяется Service Project/Object."))
		self.service_object = project_object.service_object
		self.customer = project_customer

	def _validate_context(self) -> None:
		if self.get("object_system"):
			system_object = frappe.db.get_value(
				"Ferum Object System", self.object_system, "service_object"
			)
			if system_object != self.service_object:
				frappe.throw(_("Object System должен входить в Service Object заявки."))
		if self.get("contract_obligation"):
			obligation = frappe.db.get_value(
				"Ferum Contract Obligation",
				self.contract_obligation,
				("service_project", "project_object", "object_system"),
				as_dict=True,
			)
			if not obligation or obligation.service_project != self.service_project:
				frappe.throw(_("Obligation должен относиться к Service Project заявки."))
			if obligation.project_object != self.project_object:
				frappe.throw(_("Obligation должен относиться к Project Object заявки."))
			if self.object_system and obligation.object_system != self.object_system:
				frappe.throw(_("Obligation/Object System заявки не совпадают."))
		if self.get("source_type") != "Customer" and not self.source_reference:
			frappe.throw(_("Non-customer Service Request требует source_reference."))

	def _validate_transition(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if self.get("status") != "Open":
				frappe.throw(_("Новый Service Request создаётся только в Open."))
			return
		old, new = before.get("status"), self.get("status")
		if old == new:
			return
		if new not in TRANSITIONS.get(old, frozenset()):
			frappe.throw(_("Недопустимый Service Request transition: {0} → {1}.").format(old, new))
		if frappe.session.user != "Administrator":
			if not set(frappe.get_roles(frappe.session.user)).intersection(_TRANSITION_ROLES):
				frappe.throw(_("Недостаточно прав для Service Request transition."), frappe.PermissionError)

	def _validate_dates(self) -> None:
		if self.get("reaction_due") and get_datetime(self.reaction_due) < get_datetime(self.requested_at):
			frappe.throw(_("reaction_due не может быть раньше requested_at."))
		if self.get("resolution_due") and get_datetime(self.resolution_due) < get_datetime(self.requested_at):
			frappe.throw(_("resolution_due не может быть раньше requested_at."))
		if self.get("actual_start") and self.get("actual_end"):
			if get_datetime(self.actual_start) > get_datetime(self.actual_end):
				frappe.throw(_("actual_start не может быть позже actual_end."))

	def _validate_resolution(self) -> None:
		if self.get("status") in {"Resolved", "Closed"}:
			if not self.get("actual_start") or not self.get("actual_end"):
				frappe.throw(_("Resolved/Closed request требует actual start/end."))
			if not (self.get("resolution") or "").strip() or not self.get("work_result"):
				frappe.throw(_("Resolved/Closed request требует resolution и work_result."))
			if not self.get("evidence"):
				frappe.throw(_("Resolved/Closed request требует evidence."))
		if self.get("status") == "Cancelled" and not (self.get("cancellation_reason") or "").strip():
			frappe.throw(_("Cancelled request требует cancellation_reason."))

	def _freeze_identity(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.get("status") == "Open":
			return
		changed = [field for field in _IDENTITY_FIELDS if self.get(field) != before.get(field)]
		if changed:
			frappe.throw(_("Service Request context неизменяем: {0}.").format(", ".join(changed)))


def on_doctype_update() -> None:
	frappe.db.add_index(DOCTYPE, ["service_project", "status"], "ca_request_project_status_idx")
	frappe.db.add_index(DOCTYPE, ["object_system", "status"], "ca_request_system_status_idx")
	frappe.db.add_index(DOCTYPE, ["resolution_due", "status"], "ca_request_due_status_idx")
