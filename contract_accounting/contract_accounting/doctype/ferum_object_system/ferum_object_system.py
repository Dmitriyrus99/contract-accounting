"""Engineering system belonging to one Service Object."""

from typing import Final

import frappe
from frappe.model.document import Document

DOCTYPE: Final[str] = "Ferum Object System"


class FerumObjectSystem(Document):
	def validate(self) -> None:
		if self.get("equipment_count") is not None and self.get("equipment_count") < 0:
			frappe.throw("Equipment Count не может быть отрицательным.")


def on_doctype_update() -> None:
	frappe.db.add_index(DOCTYPE, ["service_object", "status"])
