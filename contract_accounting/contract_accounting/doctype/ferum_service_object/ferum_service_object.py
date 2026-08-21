"""Customer-owned service location; project participation is indirect."""

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document

DOCTYPE: Final[str] = "Ferum Service Object"


class FerumServiceObject(Document):
    def validate(self) -> None:
        self._validate_customer_link("Address", self.address)
        if self.main_contact:
            self._validate_customer_link("Contact", self.main_contact)

    def _validate_customer_link(self, parenttype: str, parent: str) -> None:
        linked = frappe.db.exists(
            "Dynamic Link",
            {
                "parenttype": parenttype,
                "parent": parent,
                "link_doctype": "Customer",
                "link_name": self.customer,
            },
        )
        if not linked:
            frappe.throw(
                _("{0} должен быть стандартной ERPNext записью Customer {1}.").format(
                    parenttype, self.customer
                )
            )


def on_doctype_update() -> None:
    frappe.db.add_index(DOCTYPE, ["customer", "status"])
