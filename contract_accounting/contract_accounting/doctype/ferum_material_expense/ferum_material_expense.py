"""Controlled management classification of material costs."""

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

DOCTYPE: Final[str] = "Ferum Material Expense"
MATERIAL_WRITER_FLAG: Final[str] = "contract_accounting_material_expense_writer"
MATERIAL_TRANSITION_FLAG: Final[str] = "contract_accounting_material_expense_transition"
TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Draft": frozenset({"Approved", "Cancelled"}),
	"Approved": frozenset({"Cancelled"}),
	"Cancelled": frozenset(),
}


class FerumMaterialExpense(Document):
	def before_insert(self) -> None:
		self._require_writer()

	def validate(self) -> None:
		self._require_writer()
		self._derive_project_context()
		self._validate_related_context()
		self._validate_amounts()
		self._validate_purchase_invoice()
		self._validate_transition()
		self._freeze_after_approval()
		self.purchase_invoice_claim_key = self.purchase_invoice if self.status == "Approved" else None

	def on_trash(self) -> None:
		if self.status != "Draft" or not frappe.flags.get(MATERIAL_WRITER_FLAG):
			frappe.throw(_("Material Expense удаляется только typed writer в Draft."), frappe.PermissionError)

	@staticmethod
	def _require_writer() -> None:
		if not frappe.flags.get(MATERIAL_WRITER_FLAG):
			frappe.throw(_("Material Expense меняется только командами CA-07."), frappe.PermissionError)

	def _derive_project_context(self) -> None:
		project = frappe.db.get_value(
			"Ferum Service Project", self.service_project, ("company", "currency"), as_dict=True
		)
		if not project:
			frappe.throw(_("Material Expense Service Project не найден."))
		company_currency = frappe.db.get_value("Company", project.company, "default_currency")
		if project.currency != company_currency:
			frappe.throw(_("CA-07 требует валюту Service Project, равную валюте Company."))
		self.company = project.company
		self.currency = company_currency

	def _validate_related_context(self) -> None:
		for fieldname, doctype in (
			("project_object", "Ferum Project Object"),
			("contract_obligation", "Ferum Contract Obligation"),
			("maintenance_visit", "Ferum Maintenance Visit"),
			("service_request", "Ferum Service Request"),
		):
			name = self.get(fieldname)
			if name and frappe.db.get_value(doctype, name, "service_project") != self.service_project:
				frappe.throw(_("Material Expense related context относится к другому Service Project."))
		if self.contractor_assignment:
			assignment = frappe.db.get_value(
				"Ferum Contractor Assignment", self.contractor_assignment,
				("service_project", "supplier", "status"), as_dict=True,
			)
			if not assignment or assignment.service_project != self.service_project:
				frappe.throw(_("Material Expense Assignment относится к другому Service Project."))
			if assignment.status in {"Completed", "Cancelled"}:
				frappe.throw(_("Material Expense требует действующий Contractor Assignment."))
			if self.supplier and assignment.supplier != self.supplier:
				frappe.throw(_("Material Expense Supplier не совпадает с Assignment."))

	def _validate_amounts(self) -> None:
		if flt(self.amount_with_vat) <= 0:
			frappe.throw(_("Material Expense amount_with_vat должен быть больше нуля."))
		if flt(self.amount_without_vat) < 0 or flt(self.amount_without_vat) > flt(self.amount_with_vat):
			frappe.throw(_("Material Expense net amount недопустим."))
		self.base_amount_with_vat = flt(self.amount_with_vat, 2)
		self.base_amount_without_vat = flt(self.amount_without_vat, 2)
		self.vat_amount = flt(self.amount_with_vat) - flt(self.amount_without_vat)
		if self.status == "Approved" and not self.purchase_invoice and flt(self.amount_without_vat) <= 0:
			frappe.throw(_("Approved Material Expense без Purchase Invoice требует net amount."))

	def _validate_purchase_invoice(self) -> None:
		if not self.purchase_invoice:
			return
		invoice = frappe.db.get_value(
			"Purchase Invoice",
			self.purchase_invoice,
			("docstatus", "company", "supplier", "ferum_service_project"),
			as_dict=True,
		)
		if not invoice or invoice.docstatus != 1:
			frappe.throw(_("Material Expense требует submitted Purchase Invoice."))
		if invoice.company != self.company or invoice.ferum_service_project != self.service_project:
			frappe.throw(_("Purchase Invoice context не совпадает с Material Expense."))
		if self.supplier and invoice.supplier != self.supplier:
			frappe.throw(_("Purchase Invoice supplier не совпадает с Material Expense."))
		if self.status == "Approved":
			from contract_accounting.api.finance import (
				assert_purchase_invoice_available,
			)

			assert_purchase_invoice_available(self.purchase_invoice, DOCTYPE, self.name)

	def _validate_transition(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if self.status != "Draft":
				frappe.throw(_("Новый Material Expense создаётся в Draft."))
			return
		if before.status == self.status:
			return
		if frappe.flags.get(MATERIAL_TRANSITION_FLAG) != self.status:
			frappe.throw(_("Material Expense transition context отсутствует."))
		if self.status not in TRANSITIONS.get(before.status, frozenset()):
			frappe.throw(_("Недопустимый Material Expense transition."))

	def _freeze_after_approval(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.status == "Draft":
			return
		allowed = {"status", "cancelled_at", "cancelled_by", "status_reason", "purchase_invoice_claim_key"}
		for field in self.meta.fields:
			if field.fieldname in allowed or field.fieldtype in {"Section Break", "Column Break", "Tab Break"}:
				continue
			if self.get(field.fieldname) != before.get(field.fieldname):
				frappe.throw(_("Approved Material Expense immutable; используйте Cancelled."))


def on_doctype_update() -> None:
	frappe.db.add_index(DOCTYPE, ["service_project", "status", "expense_date"], "ca_material_project_idx")
