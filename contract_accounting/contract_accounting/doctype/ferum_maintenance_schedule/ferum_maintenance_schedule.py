"""Immutable planned period generated from one Contract Obligation."""

from __future__ import annotations

from datetime import date
from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


DOCTYPE: Final[str] = "Ferum Maintenance Schedule"
_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
	"service_project",
	"contract_obligation",
	"project_object",
	"object_system",
	"work_type",
	"period_key",
	"planned_date",
	"window_start",
	"window_end",
	"due_date",
)


class FerumMaintenanceSchedule(Document):
	def validate(self) -> None:
		self.period_key = (self.get("period_key") or "").strip()
		self.work_type = (self.get("work_type") or "").strip()
		self._validate_dates()
		self._validate_obligation_context()
		self._validate_identity_immutable()
		self._validate_generated_visit()

	def on_trash(self) -> None:
		frappe.throw(
			_("Generated Schedule append-only; cancel execution instead of deleting."),
			frappe.PermissionError,
		)

	def _validate_dates(self) -> None:
		planned = getdate(self.planned_date)
		if self.period_key != planned.isoformat():
			frappe.throw(_("period_key должен совпадать с planned_date ISO-8601."))
		if getdate(self.window_start) > planned or getdate(self.window_end) < planned:
			frappe.throw(_("planned_date должен входить в execution window."))

	def _validate_obligation_context(self) -> None:
		obligation = frappe.db.get_value(
			"Ferum Contract Obligation",
			self.contract_obligation,
			(
				"service_project",
				"project_object",
				"object_system",
				"work_type",
				"effective_from",
				"effective_to",
				"status",
			),
			as_dict=True,
		)
		if not obligation:
			frappe.throw(_("Contract Obligation не найден."))
		for fieldname in ("service_project", "project_object", "object_system", "work_type"):
			if self.get(fieldname) != obligation.get(fieldname):
				frappe.throw(_("Schedule.{0} не совпадает с Contract Obligation.").format(fieldname))
		if self.is_new() and obligation.status != "Active":
			frappe.throw(_("Новый Schedule генерируется только из Active Obligation."))
		planned = getdate(self.planned_date)
		if planned < getdate(obligation.effective_from):
			frappe.throw(_("planned_date раньше effective_from Obligation."))
		if obligation.effective_to and planned > getdate(obligation.effective_to):
			frappe.throw(_("planned_date позже effective_to Obligation."))

	def _validate_identity_immutable(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			return
		changed = [field for field in _IDENTITY_FIELDS if self.get(field) != before.get(field)]
		if changed:
			frappe.throw(_("Schedule identity неизменяема: {0}.").format(", ".join(changed)))

	def _validate_generated_visit(self) -> None:
		if not self.get("generated_visit"):
			return
		visit_schedule = frappe.db.get_value(
			"Ferum Maintenance Visit", self.generated_visit, "maintenance_schedule"
		)
		if visit_schedule != self.name:
			frappe.throw(_("generated_visit должен ссылаться обратно на этот Schedule."))


def on_doctype_update() -> None:
	frappe.db.add_unique(
		DOCTYPE,
		["contract_obligation", "period_key"],
		"ca_sched_period_uniq",
	)
	frappe.db.add_index(DOCTYPE, ["service_project", "planned_date"], "ca_sched_project_date_idx")
	frappe.db.add_index(DOCTYPE, ["status", "planned_date"], "ca_sched_status_date_idx")
