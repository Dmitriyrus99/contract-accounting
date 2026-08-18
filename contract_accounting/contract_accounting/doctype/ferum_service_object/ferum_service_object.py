"""Customer-owned service location; project participation is indirect."""

from typing import Final

import frappe
from frappe.model.document import Document


DOCTYPE: Final[str] = "Ferum Service Object"


class FerumServiceObject(Document):
	pass


def on_doctype_update() -> None:
	frappe.db.add_index(DOCTYPE, ["customer", "status"])
