"""Structured source requirement routed to exactly one execution path."""

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


DOCTYPE: Final[str] = "Ferum Contract Requirement"
TERMINAL_STATES: Final[frozenset[str]] = frozenset({"Approved", "Rejected"})
TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Draft": frozenset({"Assessed"}),
	"Assessed": frozenset({"Approved", "Rejected"}),
	"Approved": frozenset(),
	"Rejected": frozenset(),
}
TRANSITION_ROLES: Final[dict[tuple[str, str], frozenset[str]]] = {
	("Draft", "Assessed"): frozenset({"Юрист", "System Manager"}),
	("Assessed", "Approved"): frozenset({"Руководитель проектов", "System Manager"}),
	("Assessed", "Rejected"): frozenset({"Руководитель проектов", "System Manager"}),
}
_FROZEN_FIELDS: Final[tuple[str, ...]] = (
	"service_project",
	"requirement_type",
	"requirement_source",
	"source_document_reference",
	"source_clause",
	"description",
	"value_data",
	"value_date",
	"value_number",
	"value_check",
	"applicability",
	"routing_decision",
)


class FerumContractRequirement(Document):
	def validate(self) -> None:
		self.source_document_reference = (self.get("source_document_reference") or "").strip()
		self.source_clause = (self.get("source_clause") or "").strip()
		self._validate_transition()
		self._validate_routing()
		self._validate_unique_source()
		self._freeze_terminal_record()
		self._stamp_assessment()

	def on_trash(self) -> None:
		if self.get("assessment_status") != "Draft":
			frappe.throw(_("Удаление Requirement разрешено только в Draft."), frappe.PermissionError)

	def _validate_transition(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if self.get("assessment_status") != "Draft":
				frappe.throw(_("Новый Requirement создаётся только в Draft."))
			return
		old, new = before.get("assessment_status"), self.get("assessment_status")
		if old == new:
			return
		if new not in TRANSITIONS.get(old, frozenset()):
			frappe.throw(_("Недопустимый Requirement transition: {0} → {1}.").format(old, new))
		if frappe.session.user != "Administrator":
			allowed = TRANSITION_ROLES.get((old, new), frozenset())
			if not set(frappe.get_roles(frappe.session.user)).intersection(allowed):
				frappe.throw(_("Недостаточно прав для Requirement transition."), frappe.PermissionError)

	def _validate_routing(self) -> None:
		if self.get("applicability") == "Not Applicable":
			if self.get("routing_decision") != "Not Applicable":
				frappe.throw(_("Not Applicable requirement должен иметь такой же routing decision."))
		if self.get("routing_decision") == "Recurring Obligation":
			if self.get("applicability") != "Applicable":
				frappe.throw(_("Recurring Obligation разрешён только для Applicable requirement."))
		if self.get("assessment_status") == "Approved" and not self.get("routing_decision"):
			frappe.throw(_("Approved Requirement должен иметь routing decision."))

	def _validate_unique_source(self) -> None:
		duplicate = frappe.db.exists(
			DOCTYPE,
			{
				"service_project": self.service_project,
				"source_document_reference": self.source_document_reference,
				"source_clause": self.source_clause,
				"requirement_type": self.requirement_type,
				"name": ["!=", self.name or ""],
			},
		)
		if duplicate:
			frappe.throw(_("Requirement source уже зарегистрирован: {0}.").format(duplicate))

	def _freeze_terminal_record(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.get("assessment_status") not in TERMINAL_STATES:
			return
		changed = [field for field in _FROZEN_FIELDS if self.get(field) != before.get(field)]
		if changed or self.get("assessment_status") != before.get("assessment_status"):
			frappe.throw(_("Approved/Rejected Requirement неизменяем; создайте новую версию."))

	def _stamp_assessment(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.get("assessment_status") == self.get("assessment_status"):
			return
		if self.get("assessment_status") in {"Assessed", "Approved", "Rejected"}:
			self.assessed_by = frappe.session.user
			self.assessed_on = now_datetime()


def on_doctype_update() -> None:
	frappe.db.add_index(
		DOCTYPE,
		["service_project", "source_document_reference", "source_clause", "requirement_type"],
		"ca_req_source_idx",
	)
	frappe.db.add_index(DOCTYPE, ["service_project", "assessment_status"])
