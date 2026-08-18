"""Zero-trust boundary between management cost classification and Purchase Invoice."""

import frappe
from frappe import _


def validate_project_context(doc: object, method: str | None = None) -> None:
	project_name = getattr(doc, "ferum_service_project", None)
	if not project_name:
		return
	company = frappe.db.get_value("Ferum Service Project", project_name, "company")
	if not company:
		frappe.throw(_("Purchase Invoice Ferum Service Project не найден."))
	if company != getattr(doc, "company", None):
		frappe.throw(_("Purchase Invoice company не совпадает с Service Project."))


def prevent_recognized_cost_cancel(doc: object, method: str | None = None) -> None:
	purchase_invoice = getattr(doc, "name", None)
	checks = (
		("Ferum Material Expense", ["Approved"]),
		("Ferum Contractor Settlement", ["Approved", "Settled"]),
	)
	for doctype, statuses in checks:
		if not frappe.db.table_exists(doctype):
			continue
		claim = frappe.db.exists(
			doctype,
			{"purchase_invoice": purchase_invoice, "status": ["in", statuses]},
		)
		if claim:
			frappe.throw(
				_("Сначала отмените признанную классификацию затрат {0} {1}.").format(
					doctype, claim
				),
				frappe.ValidationError,
			)
