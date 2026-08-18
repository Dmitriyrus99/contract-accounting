"""Prevent deletion of files that are accepted or immutable CA-05 evidence."""

import frappe
from frappe import _


def prevent_locked_file_delete(doc: object, method: str | None = None) -> None:
	"""Fail closed when a File is a protected document binary or audit evidence."""

	file_name = getattr(doc, "name", None)
	if not file_name:
		return
	if not frappe.db.table_exists("Ferum Project Document"):
		return
	if frappe.db.exists(
		"Ferum Project Document Event", {"evidence_file": file_name}
	):
		frappe.throw(
			_("File является неизменяемым Project Document evidence."),
			frappe.PermissionError,
		)
	locked = frappe.db.sql(
		"""
		select name
		from `tabFerum Project Document`
		where file = %s
		  and (
			status = 'Archived'
			or digital_copy_status in ('Verified', 'Signed', 'Superseded')
			or original_status in ('Received', 'Archived')
		  )
		limit 1
		""",
		(file_name,),
	)
	if locked:
		frappe.throw(
			_("File закреплён в принятом/архивном Project Document."),
			frappe.PermissionError,
		)
