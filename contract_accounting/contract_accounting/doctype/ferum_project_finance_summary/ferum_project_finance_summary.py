"""Service-managed, fully rebuildable financial read-model."""

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document

DOCTYPE: Final[str] = "Ferum Project Finance Summary"
SUMMARY_WRITER_FLAG: Final[str] = "contract_accounting_finance_summary_writer"


class FerumProjectFinanceSummary(Document):
	def before_insert(self) -> None:
		self._require_writer()

	def validate(self) -> None:
		self._require_writer()
		project = frappe.db.get_value(
			"Ferum Service Project",
			self.service_project,
			("company", "customer", "project_manager"),
			as_dict=True,
		)
		if not project:
			frappe.throw(_("Finance Summary Service Project не найден."))
		company_currency = frappe.db.get_value("Company", project.company, "default_currency")
		self.company = project.company
		self.customer = project.customer
		self.project_manager = project.project_manager
		self.currency = company_currency

	def on_trash(self) -> None:
		frappe.throw(_("Finance Summary rebuildable, но не удаляется через CRUD."), frappe.PermissionError)

	@staticmethod
	def _require_writer() -> None:
		if not frappe.flags.get(SUMMARY_WRITER_FLAG):
			frappe.throw(_("Finance Summary меняется только CA-07 rebuild service."), frappe.PermissionError)


def on_doctype_update() -> None:
	frappe.db.add_unique(DOCTYPE, ["service_project"], "ca_finance_summary_project_uniq")
	frappe.db.add_index(DOCTYPE, ["company", "customer"], "ca_finance_summary_portfolio_idx")
