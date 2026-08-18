"""Child snapshot row for accepted execution included in closing documents."""

import frappe
from frappe.model.document import Document


class FerumBillingBasisItem(Document):
	pass


def on_doctype_update() -> None:
	frappe.db.add_unique(
		"Ferum Billing Basis Item",
		["active_claim_key"],
		"ca_billing_basis_active_claim_uniq",
	)
