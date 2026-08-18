"""Effective-dated normalized promise: what, where, when and with what result."""

from __future__ import annotations

import json
from datetime import date
from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from contract_accounting.domain.obligation import (
	ObligationRuleError,
	RecurrenceRule,
	preview_occurrences,
)


DOCTYPE: Final[str] = "Ferum Contract Obligation"
ACTIVE_STATES: Final[frozenset[str]] = frozenset({"Active", "Suspended"})
TERMINAL_STATES: Final[frozenset[str]] = frozenset({"Closed", "Cancelled"})
TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Draft": frozenset({"Active", "Cancelled"}),
	"Active": frozenset({"Suspended", "Closed"}),
	"Suspended": frozenset({"Active", "Closed"}),
	"Closed": frozenset(),
	"Cancelled": frozenset(),
}
TRANSITION_ROLES: Final[dict[tuple[str, str], frozenset[str]]] = {
	("Draft", "Active"): frozenset({"Руководитель проектов", "System Manager"}),
	("Draft", "Cancelled"): frozenset({"Юрист", "Руководитель проектов", "System Manager"}),
	("Active", "Suspended"): frozenset({"Руководитель проектов", "System Manager"}),
	("Active", "Closed"): frozenset({"Руководитель проектов", "System Manager"}),
	("Suspended", "Active"): frozenset({"Руководитель проектов", "System Manager"}),
	("Suspended", "Closed"): frozenset({"Руководитель проектов", "System Manager"}),
}
_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
	"service_project", "requirement", "obligor_type", "obligor",
	"beneficiary_type", "beneficiary", "project_object", "object_system",
	"work_type", "obligation_type", "deadline_rule", "effective_from",
)
_RECURRENCE_FIELDS: Final[tuple[str, ...]] = (
	"frequency", "interval", "period_anchor", "window_before_days",
	"window_after_days", "due_offset_days", "calendar_type",
	"generation_horizon_days",
)


class FerumContractObligation(Document):
	def validate(self) -> None:
		self.work_type = (self.get("work_type") or "").strip()
		self._validate_transition()
		self._validate_dates()
		self._validate_json_rules()
		self._validate_parties_and_values()
		self._validate_context()
		self._validate_recurrence()
		self._validate_currency()
		self._validate_no_overlap()
		self._freeze_activated_record()

	def on_trash(self) -> None:
		if self.get("status") != "Draft":
			frappe.throw(_("Удаление Obligation разрешено только в Draft."), frappe.PermissionError)

	def _validate_transition(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if self.get("status") != "Draft":
				frappe.throw(_("Новый Obligation создаётся только в Draft."))
			return
		old, new = before.get("status"), self.get("status")
		if old == new:
			return
		if new not in TRANSITIONS.get(old, frozenset()):
			frappe.throw(_("Недопустимый Obligation transition: {0} → {1}.").format(old, new))
		if frappe.session.user != "Administrator":
			allowed = TRANSITION_ROLES.get((old, new), frozenset())
			if not set(frappe.get_roles(frappe.session.user)).intersection(allowed):
				frappe.throw(_("Недостаточно прав для Obligation transition."), frappe.PermissionError)

	def _validate_dates(self) -> None:
		if self.get("effective_to") and getdate(self.effective_from) > getdate(self.effective_to):
			frappe.throw(_("effective_from не может быть позже effective_to."))

	def _validate_json_rules(self) -> None:
		for fieldname in ("deadline_rule", "acceptance_rule", "evidence_rule"):
			value = self.get(fieldname)
			if value in (None, ""):
				continue
			try:
				parsed = value if isinstance(value, dict) else json.loads(value)
			except (TypeError, ValueError):
				frappe.throw(_("{0} должен быть валидным JSON object.").format(fieldname))
			if not isinstance(parsed, dict):
				frappe.throw(_("{0} должен быть JSON object.").format(fieldname))

	def _validate_parties_and_values(self) -> None:
		allowed_party_types = {"Company", "Customer", "Supplier"}
		for type_field, value_field in (
			("obligor_type", "obligor"),
			("beneficiary_type", "beneficiary"),
		):
			party_type, party = self.get(type_field), self.get(value_field)
			if bool(party_type) != bool(party):
				frappe.throw(_("{0} и {1} должны быть заполнены вместе.").format(type_field, value_field))
			if party_type and party_type not in allowed_party_types:
				frappe.throw(_("Недопустимый party DocType: {0}.").format(party_type))
		if self.get("quantity") is not None and self.quantity <= 0:
			frappe.throw(_("quantity должна быть больше нуля."))
		if self.get("price_component") is not None and self.price_component < 0:
			frappe.throw(_("price_component не может быть отрицательным."))

	def _validate_context(self) -> None:
		requirement = frappe.db.get_value(
			"Ferum Contract Requirement", self.requirement,
			("service_project", "assessment_status", "applicability", "routing_decision"),
			as_dict=True,
		)
		if not requirement or requirement.service_project != self.service_project:
			frappe.throw(_("Requirement должен относиться к тому же Service Project."))
		if (requirement.assessment_status, requirement.applicability, requirement.routing_decision) != (
			"Approved", "Applicable", "Recurring Obligation"
		):
			frappe.throw(_("Obligation требует Approved Applicable Requirement с recurring routing."))

		project_object = frappe.db.get_value(
			"Ferum Project Object", self.project_object,
			("service_project", "service_object", "effective_from", "effective_to"),
			as_dict=True,
		)
		if not project_object or project_object.service_project != self.service_project:
			frappe.throw(_("Project Object должен относиться к тому же Service Project."))
		system_object = frappe.db.get_value(
			"Ferum Object System", self.object_system, "service_object"
		)
		if system_object != project_object.service_object:
			frappe.throw(_("Object System должен входить в Service Object выбранного Project Object."))
		start = getdate(self.effective_from)
		end = getdate(self.effective_to) if self.get("effective_to") else date.max
		membership_start = getdate(project_object.effective_from)
		membership_end = getdate(project_object.effective_to) if project_object.effective_to else date.max
		if start < membership_start or end > membership_end:
			frappe.throw(_("Период Obligation должен входить в effective interval Project Object."))

	def _validate_recurrence(self) -> None:
		if self.get("status") in ACTIVE_STATES and not self.get("recurrence"):
			frappe.throw(_("Active/Suspended Obligation требует recurrence rule."))
		for row in self.get("recurrence") or []:
			if row.get("period_anchor") != "Contract Start":
				frappe.throw(_("CA-02 поддерживает только Contract Start period anchor."))
			if row.get("calendar_type") != "Calendar Days":
				frappe.throw(_("CA-02 поддерживает только Calendar Days."))
			try:
				RecurrenceRule(
					frequency=row.frequency,
					interval=row.interval,
					due_offset_days=row.due_offset_days or 0,
					window_before_days=row.window_before_days or 0,
					window_after_days=row.window_after_days or 0,
					generation_horizon_days=row.generation_horizon_days,
				)
			except ObligationRuleError as exc:
				frappe.throw(_("Некорректное recurrence rule: {0}.").format(str(exc)))

	def _validate_currency(self) -> None:
		project_currency = frappe.db.get_value(
			"Ferum Service Project", self.service_project, "currency"
		)
		if project_currency != self.currency:
			frappe.throw(_("Obligation currency должна совпадать с Service Project currency."))

	def _validate_no_overlap(self) -> None:
		if self.get("status") not in ACTIVE_STATES:
			return
		start = getdate(self.effective_from)
		end = getdate(self.effective_to) if self.get("effective_to") else date.max
		rows = frappe.get_all(
			DOCTYPE,
			filters={
				"requirement": self.requirement,
				"project_object": self.project_object,
				"object_system": self.object_system,
				"work_type": self.work_type,
				"status": ["in", list(ACTIVE_STATES)],
				"name": ["!=", self.name or ""],
			},
			fields=["name", "effective_from", "effective_to"],
		)
		for row in rows:
			other_start = getdate(row.effective_from)
			other_end = getdate(row.effective_to) if row.effective_to else date.max
			if start <= other_end and other_start <= end:
				frappe.throw(_("Active Obligation interval пересекается с {0}.").format(row.name))

	def _freeze_activated_record(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.get("status") == "Draft":
			return
		changed = [field for field in _IDENTITY_FIELDS if self.get(field) != before.get(field)]
		if self._recurrence_signature(self) != self._recurrence_signature(before):
			changed.append("recurrence")
		if changed:
			frappe.throw(_("Activated Obligation identity неизменяема: {0}.").format(", ".join(changed)))
		if before.get("status") in TERMINAL_STATES and self.get("status") != before.get("status"):
			frappe.throw(_("Closed/Cancelled Obligation нельзя переоткрыть."))

	@staticmethod
	def _recurrence_signature(document: Document) -> tuple[tuple[object, ...], ...]:
		return tuple(
			tuple(row.get(field) for field in _RECURRENCE_FIELDS)
			for row in document.get("recurrence") or []
		)


def _rules_from_document(document: Document) -> tuple[RecurrenceRule, ...]:
	return tuple(
		RecurrenceRule(
			frequency=row.frequency,
			interval=row.interval,
			due_offset_days=row.due_offset_days or 0,
			window_before_days=row.window_before_days or 0,
			window_after_days=row.window_after_days or 0,
			generation_horizon_days=row.generation_horizon_days,
		)
		for row in document.get("recurrence") or []
	)


@frappe.whitelist()
def preview_obligation(name: str, horizon_start: str, horizon_end: str) -> list[dict[str, str]]:
	"""Preview deterministic periods without creating schedules or visits."""

	document = frappe.get_doc(DOCTYPE, name)
	document.check_permission("read")
	result = preview_occurrences(
		effective_from=getdate(document.effective_from),
		effective_to=getdate(document.effective_to) if document.effective_to else None,
		horizon_start=getdate(horizon_start),
		horizon_end=getdate(horizon_end),
		rules=_rules_from_document(document),
	)
	return [
		{
			"period_key": item.period_key,
			"planned_date": item.planned_date.isoformat(),
			"due_date": item.due_date.isoformat(),
			"window_start": item.window_start.isoformat(),
			"window_end": item.window_end.isoformat(),
		}
		for item in result
	]


def on_doctype_update() -> None:
	frappe.db.add_index(DOCTYPE, ["service_project", "status"])
	frappe.db.add_index(DOCTYPE, ["requirement", "status"])
	frappe.db.add_index(DOCTYPE, ["project_object", "object_system"])
