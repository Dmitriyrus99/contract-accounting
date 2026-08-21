"""Exact-target, time-boxed FR-05 break-glass request."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime

from contract_accounting.domain.privacy import (
    POLICY_HASH,
    POLICY_REFERENCE,
    PrivacyRuleError,
    validate_break_glass_minutes,
)

BREAK_GLASS_WRITE_FLAG = "contract_accounting_break_glass_writer"
ALLOWED_TARGETS = frozenset({"Ferum Contractor Worker", "Ferum Personnel Credential", "File"})
ALLOWED_ACTIONS = frozenset({"Read", "Preview", "Download"})


class FerumPrivacyBreakGlass(Document):
    def before_insert(self) -> None:
        self._require_writer()

    def validate(self) -> None:
        self._require_writer()
        if self.target_doctype not in ALLOWED_TARGETS or self.action not in ALLOWED_ACTIONS:
            frappe.throw(_("Break-glass target/action не входит в allowlist."))
        if not frappe.db.exists(self.target_doctype, self.target_name):
            frappe.throw(_("Break-glass exact target не найден."))
        try:
            validate_break_glass_minutes(int(self.requested_minutes or 0))
        except PrivacyRuleError as exc:
            frappe.throw(_(str(exc)))
        if self.policy_reference != POLICY_REFERENCE or self.policy_hash != POLICY_HASH:
            frappe.throw(_("Break-glass policy stamp не совпадает с FR-05."))
        self._validate_state_invariants()
        self._freeze_request()

    def on_trash(self) -> None:
        frappe.throw(_("Удаление break-glass audit запрещено."), frappe.PermissionError)

    @staticmethod
    def _require_writer() -> None:
        if not frappe.flags.get(BREAK_GLASS_WRITE_FLAG):
            frappe.throw(_("Break-glass изменяется только typed command."), frappe.PermissionError)

    def _validate_state_invariants(self) -> None:
        approval_pairs = (
            (self.security_approved_by, self.security_approved_at),
            (self.dpo_approved_by, self.dpo_approved_at),
            (self.product_owner_approved_by, self.product_owner_approved_at),
        )
        if any(bool(actor) != bool(approved_at) for actor, approved_at in approval_pairs):
            frappe.throw(_("Break-glass approval требует actor и timestamp вместе."))
        actors = [
            actor
            for actor in (
                self.requester,
                self.security_approved_by,
                self.dpo_approved_by,
                self.product_owner_approved_by,
            )
            if actor
        ]
        if len(actors) != len(set(actors)):
            frappe.throw(_("Break-glass requester и approvers должны быть разными."))

        requester_is_security = bool(self.requester_is_security)
        required = (
            (self.dpo_approved_by, self.product_owner_approved_by)
            if requester_is_security
            else (self.dpo_approved_by, self.security_approved_by)
        )
        forbidden = (
            self.security_approved_by if requester_is_security else self.product_owner_approved_by
        )
        approval_count = sum(bool(value) for value in required)
        if forbidden:
            frappe.throw(_("Break-glass содержит approval вне separation rule."))
        if self.status == "Requested" and approval_count:
            frappe.throw(_("Requested break-glass не должен содержать approvals."))
        if self.status == "Partially Approved" and approval_count != 1:
            frappe.throw(_("Partially Approved break-glass требует ровно один approval."))
        if self.status == "Active":
            if approval_count != 2 or not self.activated_at or not self.expires_at:
                frappe.throw(_("Active break-glass требует два approvals и timebox."))
            if get_datetime(self.expires_at) <= get_datetime(self.activated_at):
                frappe.throw(_("Break-glass expiry должен быть позже activation."))
        if self.status in {"Requested", "Partially Approved"} and (
            self.activated_at or self.expires_at or self.revoked_at or self.revoked_by
        ):
            frappe.throw(_("Неактивный break-glass содержит terminal watermark."))
        if self.status == "Active" and (self.revoked_at or self.revoked_by):
            frappe.throw(_("Active break-glass не должен быть revoked."))
        if self.status in {"Expired", "Revoked"} and not (self.revoked_at and self.revoked_by):
            frappe.throw(_("Terminal break-glass требует revoked actor/timestamp."))

    def _freeze_request(self) -> None:
        before = self.get_doc_before_save()
        if before is None:
            return
        for fieldname in (
            "requester",
            "requester_is_security",
            "ticket",
            "reason",
            "target_doctype",
            "target_name",
            "action",
            "requested_minutes",
            "policy_reference",
            "policy_hash",
        ):
            if self.get(fieldname) != before.get(fieldname):
                frappe.throw(_("Break-glass request fields неизменяемы."))


def on_doctype_update() -> None:
    frappe.db.add_index("Ferum Privacy Break Glass", ["requester", "status", "expires_at"])
    frappe.db.add_index("Ferum Privacy Break Glass", ["target_doctype", "target_name", "status"])
