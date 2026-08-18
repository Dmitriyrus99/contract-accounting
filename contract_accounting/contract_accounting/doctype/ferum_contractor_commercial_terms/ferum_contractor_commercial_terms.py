"""Separate commercial basis for an operational Contractor Assignment."""

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

DOCTYPE: Final[str] = "Ferum Contractor Commercial Terms"
TERMS_WRITER_FLAG: Final[str] = "contract_accounting_terms_writer"
TERMS_TRANSITION_FLAG: Final[str] = "contract_accounting_terms_transition"
TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Draft": frozenset({"Approved", "Cancelled"}),
	"Approved": frozenset({"Cancelled"}),
	"Cancelled": frozenset(),
}


class FerumContractorCommercialTerms(Document):
	def before_insert(self) -> None:
		self._require_writer()

	def validate(self) -> None:
		self._require_writer()
		self._derive_assignment_context()
		self._validate_amounts()
		self._validate_transition()
		self._freeze_after_approval()
		self.assignment_claim_key = self.contractor_assignment if self.status == "Approved" else None

	def on_trash(self) -> None:
		if self.status != "Draft" or not frappe.flags.get(TERMS_WRITER_FLAG):
			frappe.throw(_("Commercial Terms удаляются только typed writer в Draft."), frappe.PermissionError)

	@staticmethod
	def _require_writer() -> None:
		if not frappe.flags.get(TERMS_WRITER_FLAG):
			frappe.throw(_("Contractor Commercial Terms меняются только командами CA-08."), frappe.PermissionError)

	def _derive_assignment_context(self) -> None:
		assignment = frappe.db.get_value(
			"Ferum Contractor Assignment", self.contractor_assignment,
			(
				"service_project", "company", "execution_mode", "supplier", "project_object",
				"object_system", "work_type", "effective_from", "effective_to", "status",
			),
			as_dict=True,
		)
		if not assignment or assignment.execution_mode != "Contractor":
			frappe.throw(_("Commercial Terms требуют Contractor Assignment."))
		if assignment.status == "Cancelled":
			frappe.throw(_("Commercial Terms нельзя связать с Cancelled Assignment."))
		self.service_project = assignment.service_project
		self.company = assignment.company
		self.supplier = assignment.supplier
		self.project_object = assignment.project_object
		self.object_system = assignment.object_system
		self.work_type = assignment.work_type
		self.currency = frappe.db.get_value("Company", assignment.company, "default_currency")
		if not self.effective_to:
			self.effective_to = assignment.effective_to
		if getdate(self.effective_from) < getdate(assignment.effective_from):
			frappe.throw(_("Commercial Terms начинаются раньше Assignment."))
		if assignment.effective_to and (
			not self.effective_to or getdate(self.effective_to) > getdate(assignment.effective_to)
		):
			frappe.throw(_("Commercial Terms заканчиваются позже Assignment."))
		if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
			frappe.throw(_("Commercial Terms effective_to раньше effective_from."))

	def _validate_amounts(self) -> None:
		if flt(self.client_price) < 0 or flt(self.contractor_cost) < 0:
			frappe.throw(_("Commercial Terms amounts не могут быть отрицательными."))
		self.margin_amount = flt(self.client_price) - flt(self.contractor_cost)
		self.margin_percent = (
			flt(self.margin_amount / flt(self.client_price) * 100, 6) if flt(self.client_price) else 0
		)
		if self.status == "Approved" and flt(self.client_price) <= 0:
			frappe.throw(_("Approved Commercial Terms требуют client_price > 0."))

	def _validate_transition(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if self.status != "Draft":
				frappe.throw(_("Новые Commercial Terms создаются в Draft."))
			return
		if before.status == self.status:
			return
		if frappe.flags.get(TERMS_TRANSITION_FLAG) != self.status:
			frappe.throw(_("Commercial Terms transition context отсутствует."))
		if self.status not in TRANSITIONS.get(before.status, frozenset()):
			frappe.throw(_("Недопустимый Commercial Terms transition."))

	def _freeze_after_approval(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.status == "Draft":
			return
		allowed = {
			"status", "cancelled_at", "cancelled_by", "status_reason", "assignment_claim_key",
		}
		for field in self.meta.fields:
			if field.fieldname in allowed or field.fieldtype in {"Section Break", "Column Break", "Tab Break"}:
				continue
			if self.get(field.fieldname) != before.get(field.fieldname):
				frappe.throw(_("Approved Commercial Terms immutable."))


def on_doctype_update() -> None:
	frappe.db.add_index(DOCTYPE, ["service_project", "supplier", "status"], "ca_terms_project_idx")
