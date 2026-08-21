"""Structured customer-response source; the full FR-08 flow remains separate."""

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.infrastructure.deadline_guard import DEADLINE_SOURCE_WRITE_FLAG

ALLOWED_SOURCE_DOCTYPES: Final[frozenset[str]] = frozenset(
    {
        "Ferum Service Project",
        "Ferum Contract Requirement",
        "Ferum Contract Obligation",
        "Ferum Maintenance Visit",
        "Ferum Service Request",
        "Ferum Finding",
        "Ferum Inspection",
        "Ferum Project Document",
        "Ferum Billing Output",
    }
)


class FerumExternalDependency(Document):
    def before_insert(self) -> None:
        self._require_writer()

    def validate(self) -> None:
        self._require_writer()
        self._validate_source()
        self._validate_customer_contact()
        self._validate_evidence()
        if self.status == "Received" and (not self.received_at or not self.received_evidence):
            frappe.throw(_("Received External Dependency требует timestamp и evidence."))

    def on_trash(self) -> None:
        frappe.throw(_("Удаление External Dependency запрещено."), frappe.PermissionError)

    def _require_writer(self) -> None:
        if not frappe.flags.get(DEADLINE_SOURCE_WRITE_FLAG):
            frappe.throw(
                _("External Dependency изменяется только typed command."),
                frappe.PermissionError,
            )

    def _validate_source(self) -> None:
        if self.source_doctype not in ALLOWED_SOURCE_DOCTYPES:
            frappe.throw(_("External Dependency source DocType не разрешён."))
        if not frappe.db.exists(self.source_doctype, self.source_name):
            frappe.throw(_("External Dependency source не найден."))
        source = frappe.get_doc(self.source_doctype, self.source_name)
        if self.source_doctype == "Ferum Service Project":
            source_project = source.name
        else:
            source_project = source.get("service_project")
        if source_project != self.service_project:
            frappe.throw(_("External Dependency source относится к другому project."))

    def _validate_customer_contact(self) -> None:
        project_customer = frappe.db.get_value(
            "Ferum Service Project", self.service_project, "customer"
        )
        if project_customer != self.customer:
            frappe.throw(_("External Dependency Customer определяется Service Project."))
        if not frappe.db.exists(
            "Dynamic Link",
            {
                "parenttype": "Contact",
                "parent": self.contact,
                "link_doctype": "Customer",
                "link_name": self.customer,
            },
        ):
            frappe.throw(_("Contact не связан с Customer Service Project."))

    def _validate_evidence(self) -> None:
        for fieldname in ("sent_evidence", "received_evidence"):
            value = self.get(fieldname)
            if value and not frappe.db.exists("File", value):
                frappe.throw(_("External Dependency evidence File не найден."))


def on_doctype_update() -> None:
    frappe.db.add_index(
        "Ferum External Dependency",
        ["service_project", "status", "due_at"],
        "ca_external_dependency_due_idx",
    )
