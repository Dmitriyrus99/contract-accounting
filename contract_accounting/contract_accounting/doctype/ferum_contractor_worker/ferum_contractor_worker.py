"""Fail-closed protected worker schema pending MG-CA-015."""

import frappe
from frappe import _
from frappe.model.document import Document

MG_CA_015_MESSAGE = "Contractor Worker production data заблокированы до закрытия MG-CA-015."


class FerumContractorWorker(Document):
	def before_insert(self) -> None:
		frappe.throw(_(MG_CA_015_MESSAGE), frappe.PermissionError)

	def validate(self) -> None:
		frappe.throw(_(MG_CA_015_MESSAGE), frappe.PermissionError)

	def on_trash(self) -> None:
		frappe.throw(_(MG_CA_015_MESSAGE), frappe.PermissionError)
