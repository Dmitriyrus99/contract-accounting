"""Exact-target joint Legal/Product Owner retention hold."""

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.domain.privacy import POLICY_HASH, POLICY_REFERENCE

LEGAL_HOLD_WRITE_FLAG = "contract_accounting_legal_hold_writer"
ALLOWED_TARGETS = frozenset(
    {"Ferum Contractor Worker", "Ferum Personnel Credential", "Ferum Privacy Event", "File"}
)


class FerumPrivacyLegalHold(Document):
    def before_insert(self) -> None:
        self._require_writer()

    def validate(self) -> None:
        self._require_writer()
        if self.target_doctype not in ALLOWED_TARGETS:
            frappe.throw(_("Legal hold target не входит в allowlist."))
        if not frappe.db.exists(self.target_doctype, self.target_name):
            frappe.throw(_("Legal hold exact target не найден."))
        if self.policy_reference != POLICY_REFERENCE or self.policy_hash != POLICY_HASH:
            frappe.throw(_("Legal hold policy stamp не совпадает с FR-05."))
        self._validate_state_invariants()
        self._freeze_request()

    def on_trash(self) -> None:
        frappe.throw(_("Удаление legal hold audit запрещено."), frappe.PermissionError)

    @staticmethod
    def _require_writer() -> None:
        if not frappe.flags.get(LEGAL_HOLD_WRITE_FLAG):
            frappe.throw(_("Legal hold изменяется только typed command."), frappe.PermissionError)

    def _validate_state_invariants(self) -> None:
        pairs = (
            (self.legal_approved_by, self.legal_approved_at),
            (self.product_owner_approved_by, self.product_owner_approved_at),
            (self.release_requested_by, self.release_requested_at),
            (self.release_legal_approved_by, self.release_legal_approved_at),
            (self.release_product_owner_approved_by, self.release_product_owner_approved_at),
        )
        if any(bool(actor) != bool(event_at) for actor, event_at in pairs):
            frappe.throw(_("Legal hold actor и timestamp должны быть заполнены вместе."))

        activation_actors = [
            actor
            for actor in (
                self.requested_by,
                self.legal_approved_by,
                self.product_owner_approved_by,
            )
            if actor
        ]
        if len(activation_actors) != len(set(activation_actors)):
            frappe.throw(_("Legal hold requester и activation approvers должны быть разными."))
        release_actors = [
            actor
            for actor in (
                self.release_requested_by,
                self.release_legal_approved_by,
                self.release_product_owner_approved_by,
            )
            if actor
        ]
        if len(release_actors) != len(set(release_actors)):
            frappe.throw(_("Legal hold release requester и approvers должны быть разными."))

        activation_count = sum(
            bool(value) for value in (self.legal_approved_by, self.product_owner_approved_by)
        )
        release_count = sum(
            bool(value)
            for value in (
                self.release_legal_approved_by,
                self.release_product_owner_approved_by,
            )
        )
        if self.status == "Pending":
            if activation_count > 1 or any(
                (
                    self.release_reason,
                    self.release_requested_by,
                    self.release_requested_at,
                    self.release_legal_approved_by,
                    self.release_product_owner_approved_by,
                    self.released_at,
                )
            ):
                frappe.throw(_("Pending legal hold содержит недопустимые state fields."))
        elif self.status == "Active":
            if activation_count != 2 or any(
                (
                    self.release_reason,
                    self.release_requested_by,
                    self.release_requested_at,
                    self.release_legal_approved_by,
                    self.release_product_owner_approved_by,
                    self.released_at,
                )
            ):
                frappe.throw(_("Active legal hold требует joint activation без release fields."))
        elif self.status == "Release Pending":
            if (
                activation_count != 2
                or not self.release_reason
                or not self.release_requested_by
                or release_count > 1
                or self.released_at
            ):
                frappe.throw(_("Release Pending legal hold имеет неполный approval state."))
        elif self.status == "Released":
            if (
                activation_count != 2
                or not self.release_reason
                or not self.release_requested_by
                or release_count != 2
                or not self.released_at
            ):
                frappe.throw(_("Released legal hold требует joint release approvals."))
        else:
            frappe.throw(_("Legal hold status не поддерживается."))

    def _freeze_request(self) -> None:
        before = self.get_doc_before_save()
        if before is None:
            return
        for fieldname in (
            "target_doctype",
            "target_name",
            "reason",
            "review_on",
            "requested_by",
            "requested_at",
            "policy_reference",
            "policy_hash",
        ):
            if self.get(fieldname) != before.get(fieldname):
                frappe.throw(_("Legal hold request fields неизменяемы."))


def on_doctype_update() -> None:
    frappe.db.add_index("Ferum Privacy Legal Hold", ["target_doctype", "target_name", "status"])
