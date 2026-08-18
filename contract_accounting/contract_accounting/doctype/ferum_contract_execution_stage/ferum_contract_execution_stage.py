"""Legal/financial execution stage linked directly to Service Project."""

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


DOCTYPE: Final[str] = "Ferum Contract Execution Stage"


class FerumContractExecutionStage(Document):
	def validate(self) -> None:
		self._validate_dates()
		self._validate_amendment()

	def _validate_dates(self) -> None:
		for start_field, end_field in (
			("execution_start_date", "execution_end_date"),
			("service_period_start", "service_period_end"),
		):
			start, end = self.get(start_field), self.get(end_field)
			if start and end and getdate(start) > getdate(end):
				frappe.throw(_("{0} не может быть позже {1}.").format(start_field, end_field))

	def _validate_amendment(self) -> None:
		if not self.get("contract_amendment"):
			return
		project = frappe.db.get_value(
			"Ferum Contract Amendment", self.contract_amendment, "service_project"
		)
		if project != self.service_project:
			frappe.throw(_("Contract Amendment должен относиться к тому же Service Project."))


def on_doctype_update() -> None:
	frappe.db.add_unique(DOCTYPE, ["service_project", "stage_number"])
	frappe.db.add_index(DOCTYPE, ["service_project", "status"])
