"""Performance, warranty and advance security linked to Service Project."""

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


DOCTYPE: Final[str] = "Ferum Contract Security"


class FerumContractSecurity(Document):
	def validate(self) -> None:
		self._validate_dates()
		self._validate_amounts()
		self._validate_amendment()

	def _validate_dates(self) -> None:
		if self.get("valid_from") and self.get("valid_until"):
			if getdate(self.valid_from) > getdate(self.valid_until):
				frappe.throw(_("valid_from не может быть позже valid_until."))
		if self.get("return_due_date") and self.get("valid_until"):
			if getdate(self.return_due_date) < getdate(self.valid_until):
				frappe.throw(_("return_due_date не может быть раньше valid_until."))

	def _validate_amounts(self) -> None:
		for fieldname in ("basis_amount", "required_amount", "actual_amount"):
			if flt(self.get(fieldname)) < 0:
				frappe.throw(_("{0} не может быть отрицательным.").format(fieldname))

	def _validate_amendment(self) -> None:
		if not self.get("contract_amendment"):
			return
		project = frappe.db.get_value(
			"Ferum Contract Amendment", self.contract_amendment, "service_project"
		)
		if project != self.service_project:
			frappe.throw(_("Contract Amendment должен относиться к тому же Service Project."))


def on_doctype_update() -> None:
	frappe.db.add_index(DOCTYPE, ["service_project", "status"])
	frappe.db.add_index(DOCTYPE, ["valid_until", "status"])
