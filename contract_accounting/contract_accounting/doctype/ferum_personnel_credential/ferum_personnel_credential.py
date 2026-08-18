"""Fail-closed credential topology pending MG-CA-015."""

import frappe
from frappe import _
from frappe.model.document import Document

ALLOWED_HOLDER_TYPES = frozenset({"Employee", "Ferum Contractor Worker"})
MG_CA_015_MESSAGE = "Personnel Credential production data заблокированы до закрытия MG-CA-015."


class FerumPersonnelCredential(Document):
	def before_insert(self) -> None:
		self._validate_holder_type()
		frappe.throw(_(MG_CA_015_MESSAGE), frappe.PermissionError)

	def validate(self) -> None:
		self._validate_holder_type()
		frappe.throw(_(MG_CA_015_MESSAGE), frappe.PermissionError)

	def on_trash(self) -> None:
		frappe.throw(_(MG_CA_015_MESSAGE), frappe.PermissionError)

	def _validate_holder_type(self) -> None:
		if self.holder_type not in ALLOWED_HOLDER_TYPES:
			frappe.throw(_("Credential holder_type не входит в approved allowlist."))
