"""Effective-dated Service Project to Service Object membership."""

from datetime import date
from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

DOCTYPE: Final[str] = "Ferum Project Object"
AMENDMENT_DOCTYPE: Final[str] = "Ferum Contract Amendment"
_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
	"service_project",
	"service_object",
	"effective_from",
)


class FerumProjectObject(Document):
	def validate(self) -> None:
		self._set_status()
		self._validate_dates()
		self._validate_identity_immutable()
		self._validate_customer_compatibility()
		self._validate_within_contract_term()
		self._validate_no_interval_overlap()
		self._validate_amendment_links()

	def on_trash(self) -> None:
		frappe.throw(
			_("Project Object ведётся append-only; закройте effective_to вместо удаления."),
			frappe.PermissionError,
		)

	def _set_status(self) -> None:
		self.status = "Closed" if self.get("effective_to") else "Active"

	def _validate_dates(self) -> None:
		if self.get("effective_from") and self.get("effective_to"):
			if getdate(self.effective_from) > getdate(self.effective_to):
				frappe.throw(_("effective_from не может быть позже effective_to."))

	def _validate_identity_immutable(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			return
		changed = [field for field in _IDENTITY_FIELDS if self.get(field) != before.get(field)]
		if changed:
			frappe.throw(
				_("Project Object append-only: неизменяемые поля: {0}.").format(", ".join(changed))
			)
		if before.get("effective_to") and self.get("effective_to") != before.get("effective_to"):
			frappe.throw(_("Закрытый Project Object нельзя переоткрыть или датировать заново."))

	def _validate_customer_compatibility(self) -> None:
		project_customer = frappe.db.get_value(
			"Ferum Service Project", self.service_project, "customer"
		)
		object_customer = frappe.db.get_value(
			"Ferum Service Object", self.service_object, "customer"
		)
		if project_customer != object_customer:
			frappe.throw(
				_("Service Object должен принадлежать Customer договора: {0} != {1}.").format(
					object_customer, project_customer
				)
			)

	def _validate_within_contract_term(self) -> None:
		contract_start, contract_end = frappe.db.get_value(
			"Ferum Service Project",
			self.service_project,
			("effective_from", "effective_to"),
		) or (None, None)
		for fieldname in ("effective_from", "effective_to"):
			value = self.get(fieldname)
			if not value:
				continue
			value_date = getdate(value)
			if contract_start and value_date < getdate(contract_start):
				frappe.throw(_("{0} раньше начала договора.").format(fieldname))
			if contract_end and value_date > getdate(contract_end):
				frappe.throw(_("{0} позже окончания договора.").format(fieldname))

	def _validate_no_interval_overlap(self) -> None:
		if not self.get("effective_from"):
			return
		start = getdate(self.effective_from)
		end = getdate(self.effective_to) if self.get("effective_to") else date.max
		rows = frappe.get_all(
			DOCTYPE,
			filters={
				"service_project": self.service_project,
				"service_object": self.service_object,
				"name": ["!=", self.name or ""],
			},
			fields=["name", "effective_from", "effective_to"],
		)
		for row in rows:
			other_start = getdate(row.effective_from)
			other_end = getdate(row.effective_to) if row.effective_to else date.max
			if start <= other_end and other_start <= end:
				frappe.throw(_("Интервал Project Object пересекается с {0}.").format(row.name))

	def _validate_amendment_links(self) -> None:
		for fieldname in ("added_by", "removed_by"):
			amendment = self.get(fieldname)
			if not amendment:
				continue
			amendment_project = frappe.db.get_value(
				AMENDMENT_DOCTYPE, amendment, "service_project"
			)
			if amendment_project != self.service_project:
				frappe.throw(_("{0} должен относиться к тому же Service Project.").format(fieldname))


def on_doctype_update() -> None:
	frappe.db.add_index(DOCTYPE, ["service_project", "effective_to"])
	frappe.db.add_index(DOCTYPE, ["service_object", "effective_to"])
