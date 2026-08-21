"""Typed and auditable Company/Contract calendar precedence assignment."""

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.infrastructure.deadline_guard import CALENDAR_ASSIGNMENT_WRITE_FLAG


class FerumCalendarAssignment(Document):
    def before_insert(self) -> None:
        self._require_writer()

    def validate(self) -> None:
        self._require_writer()
        self._validate_scope()

    def on_trash(self) -> None:
        frappe.throw(_("Удаление Calendar Assignment запрещено."), frappe.PermissionError)

    def _require_writer(self) -> None:
        if not frappe.flags.get(CALENDAR_ASSIGNMENT_WRITE_FLAG):
            frappe.throw(
                _("Calendar Assignment изменяется только typed command."),
                frappe.PermissionError,
            )

    def _validate_scope(self) -> None:
        revision = frappe.db.get_value(
            "Ferum Calendar Revision",
            self.calendar_revision,
            ("calendar_year", "status"),
            as_dict=True,
        )
        if not revision or revision.status != "Published":
            frappe.throw(_("Calendar Assignment требует Published revision."))
        if revision.calendar_year != self.calendar_year:
            frappe.throw(_("Calendar Assignment year не совпадает с revision."))
        if self.scope_type == "Company":
            if self.service_project or self.contract_basis or self.evidence_document:
                frappe.throw(_("Company calendar не содержит Contract-specific fields."))
        elif self.scope_type == "Contract":
            if not self.service_project or not self.contract_basis or not self.evidence_document:
                frappe.throw(_("Contract Calendar требует project, basis и evidence document."))
            project_company = frappe.db.get_value(
                "Ferum Service Project", self.service_project, "company"
            )
            if project_company != self.company:
                frappe.throw(_("Contract Calendar Company не совпадает с Service Project."))
            document_project = frappe.db.get_value(
                "Ferum Project Document", self.evidence_document, "service_project"
            )
            if document_project != self.service_project:
                frappe.throw(_("Contract Calendar evidence относится к другому project."))
        else:
            frappe.throw(_("Неизвестный Calendar Assignment scope."))


def on_doctype_update() -> None:
    frappe.db.add_index(
        "Ferum Calendar Assignment",
        ["scope_type", "company", "service_project", "calendar_year", "status"],
        "ca_calendar_assignment_lookup_idx",
    )
