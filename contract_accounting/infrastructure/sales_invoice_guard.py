"""Zero-trust boundary between Ferum billing metadata and standard Sales Invoice."""

import frappe
from frappe import _


def validate_project_context(doc: object, method: str | None = None) -> None:
	project_name = getattr(doc, "ferum_service_project", None)
	if not project_name:
		return
	project = frappe.db.get_value(
		"Ferum Service Project",
		project_name,
		("company", "customer"),
		as_dict=True,
	)
	if not project:
		frappe.throw(_("Sales Invoice Ferum Service Project не найден."))
	if project.company != getattr(doc, "company", None):
		frappe.throw(_("Sales Invoice company не совпадает с Service Project."))
	if project.customer != getattr(doc, "customer", None):
		frappe.throw(_("Sales Invoice customer не совпадает с Service Project."))


def prevent_active_output_cancel(doc: object, method: str | None = None) -> None:
	if not frappe.db.table_exists("Ferum Billing Output"):
		return
	active = frappe.db.exists(
		"Ferum Billing Output",
		{
			"sales_invoice": getattr(doc, "name", None),
			"status": ["in", ["Draft", "Generated", "Issued", "Signed"]],
		},
	)
	if active:
		frappe.throw(
			_("Сначала отмените или supersede активный Ferum Billing Output {0}.").format(active),
			frappe.ValidationError,
		)
