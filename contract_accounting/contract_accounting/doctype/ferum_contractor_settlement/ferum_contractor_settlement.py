"""Controlled management classification of contractor costs."""

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

DOCTYPE: Final[str] = "Ferum Contractor Settlement"
SETTLEMENT_WRITER_FLAG: Final[str] = "contract_accounting_contractor_settlement_writer"
SETTLEMENT_TRANSITION_FLAG: Final[str] = "contract_accounting_contractor_settlement_transition"
RECOGNIZED_STATUSES: Final[frozenset[str]] = frozenset({"Approved", "Settled"})
TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Draft": frozenset({"Approved", "Cancelled"}),
	"Approved": frozenset({"Settled", "Cancelled"}),
	"Settled": frozenset(),
	"Cancelled": frozenset(),
}


class FerumContractorSettlement(Document):
	def before_insert(self) -> None:
		self._require_writer()

	def validate(self) -> None:
		self._require_writer()
		self._derive_project_context()
		self._validate_related_context()
		self._validate_period_amounts()
		self._validate_purchase_invoice()
		self._validate_payment_entry()
		self._validate_transition()
		self._freeze_after_approval()
		self.purchase_invoice_claim_key = (
			self.purchase_invoice if self.status in RECOGNIZED_STATUSES else None
		)

	def on_trash(self) -> None:
		if self.status != "Draft" or not frappe.flags.get(SETTLEMENT_WRITER_FLAG):
			frappe.throw(_("Contractor Settlement удаляется только typed writer в Draft."), frappe.PermissionError)

	@staticmethod
	def _require_writer() -> None:
		if not frappe.flags.get(SETTLEMENT_WRITER_FLAG):
			frappe.throw(_("Contractor Settlement меняется только командами CA-07."), frappe.PermissionError)

	def _derive_project_context(self) -> None:
		project = frappe.db.get_value(
			"Ferum Service Project", self.service_project, ("company", "currency"), as_dict=True
		)
		if not project:
			frappe.throw(_("Contractor Settlement Service Project не найден."))
		company_currency = frappe.db.get_value("Company", project.company, "default_currency")
		if project.currency != company_currency:
			frappe.throw(_("CA-07 требует валюту Service Project, равную валюте Company."))
		self.company = project.company
		self.currency = company_currency

	def _validate_related_context(self) -> None:
		for fieldname, doctype in (
			("project_object", "Ferum Project Object"),
			("contract_obligation", "Ferum Contract Obligation"),
		):
			name = self.get(fieldname)
			if name and frappe.db.get_value(doctype, name, "service_project") != self.service_project:
				frappe.throw(_("Contractor Settlement context относится к другому Service Project."))

	def _validate_period_amounts(self) -> None:
		if getdate(self.period_end) < getdate(self.period_start):
			frappe.throw(_("Contractor Settlement period_end раньше period_start."))
		if flt(self.planned_amount) < 0 or flt(self.approved_amount) < 0:
			frappe.throw(_("Contractor Settlement amounts не могут быть отрицательными."))
		if self.status in RECOGNIZED_STATUSES and flt(self.approved_amount) <= 0:
			frappe.throw(_("Approved Contractor Settlement требует approved_amount > 0."))
		self.base_approved_amount = flt(self.approved_amount, 2)
		self.payable_amount = max(flt(self.base_approved_amount) - flt(self.paid_amount), 0)

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
			frappe.throw(_("Contractor Settlement требует submitted Purchase Invoice."))
		if (
			invoice.company != self.company
			or invoice.supplier != self.supplier
			or invoice.ferum_service_project != self.service_project
		):
			frappe.throw(_("Purchase Invoice context не совпадает с Contractor Settlement."))
		if self.status in RECOGNIZED_STATUSES:
			from contract_accounting.api.finance import (
				assert_purchase_invoice_available,
			)

			assert_purchase_invoice_available(self.purchase_invoice, DOCTYPE, self.name)

	def _validate_payment_entry(self) -> None:
		if not self.payment_entry:
			self.paid_amount = 0
			self.payable_amount = flt(self.base_approved_amount, 2)
			return
		payment = frappe.db.get_value(
			"Payment Entry",
			self.payment_entry,
			("docstatus", "company", "party_type", "party", "payment_type", "paid_amount"),
			as_dict=True,
		)
		if not payment or payment.docstatus != 1:
			frappe.throw(_("Contractor Settlement требует submitted Payment Entry."))
		if (
			payment.company != self.company
			or payment.party_type != "Supplier"
			or payment.party != self.supplier
			or payment.payment_type != "Pay"
		):
			frappe.throw(_("Payment Entry context не совпадает с Contractor Settlement."))
		if self.purchase_invoice and not frappe.db.exists(
			"Payment Entry Reference",
			{
				"parent": self.payment_entry,
				"reference_doctype": "Purchase Invoice",
				"reference_name": self.purchase_invoice,
			},
		):
			frappe.throw(_("Payment Entry не содержит ссылку на Purchase Invoice Settlement."))
		self.paid_amount = flt(payment.paid_amount, 2)
		self.payable_amount = max(flt(self.base_approved_amount) - self.paid_amount, 0)
		if self.status == "Settled" and self.paid_amount < self.base_approved_amount:
			frappe.throw(_("Settled Contractor Settlement требует полной оплаты."))

	def _validate_transition(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if self.status != "Draft":
				frappe.throw(_("Новый Contractor Settlement создаётся в Draft."))
			return
		if before.status == self.status:
			return
		if frappe.flags.get(SETTLEMENT_TRANSITION_FLAG) != self.status:
			frappe.throw(_("Contractor Settlement transition context отсутствует."))
		if self.status not in TRANSITIONS.get(before.status, frozenset()):
			frappe.throw(_("Недопустимый Contractor Settlement transition."))
		if self.status == "Settled" and not self.payment_entry:
			frappe.throw(_("Settled Contractor Settlement требует Payment Entry."))

	def _freeze_after_approval(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.status == "Draft":
			return
		allowed = {
			"status", "payment_entry", "paid_amount", "payable_amount", "settled_at", "settled_by",
			"cancelled_at", "cancelled_by", "status_reason", "purchase_invoice_claim_key",
		}
		for field in self.meta.fields:
			if field.fieldname in allowed or field.fieldtype in {"Section Break", "Column Break", "Tab Break"}:
				continue
			if self.get(field.fieldname) != before.get(field.fieldname):
				frappe.throw(_("Approved Contractor Settlement identity immutable."))


def on_doctype_update() -> None:
	frappe.db.add_index(DOCTYPE, ["service_project", "status", "period_end"], "ca_settlement_project_idx")
	frappe.db.add_index(DOCTYPE, ["supplier", "status"], "ca_settlement_supplier_idx")
