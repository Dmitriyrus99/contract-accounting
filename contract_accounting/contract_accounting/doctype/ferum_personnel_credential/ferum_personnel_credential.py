"""Protected personnel credential lifecycle governed by FR05-PD-01."""

from __future__ import annotations

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from contract_accounting.api.privacy import (
    PRIVACY_RETENTION_FLAG,
    PRIVACY_TRANSITION_FLAG,
    PRIVACY_WRITE_FLAG,
    active_privacy_settings,
)
from contract_accounting.domain.privacy import (
    ALLOWED_CREDENTIAL_TYPES,
    ALLOWED_HOLDER_TYPES,
    POLICY_HASH,
    POLICY_REFERENCE,
    mask_credential_number,
)

TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "Draft": frozenset({"Verified", "Rejected"}),
    "Verified": frozenset({"Expired", "Revoked"}),
    "Rejected": frozenset(),
    "Expired": frozenset(),
    "Revoked": frozenset(),
}


class FerumPersonnelCredential(Document):
    def before_insert(self) -> None:
        self._require_writer()

    def validate(self) -> None:
        self._require_writer()
        if self.is_new():
            self.credential_number_masked = mask_credential_number(self.credential_number)
        settings = active_privacy_settings()
        if self.holder_type not in ALLOWED_HOLDER_TYPES:
            frappe.throw(_("Credential holder_type не входит в approved allowlist."))
        if self.credential_type not in ALLOWED_CREDENTIAL_TYPES:
            frappe.throw(_("Credential type не входит в approved allowlist."))
        if not frappe.db.exists(self.holder_type, self.holder):
            frappe.throw(_("Credential holder не найден."))
        if (
            self.privacy_policy_reference != POLICY_REFERENCE
            or self.privacy_policy_hash != POLICY_HASH
        ):
            frappe.throw(_("Personnel Credential policy stamp не совпадает с FR-05."))
        if settings.activation_mode == "Synthetic Test" and not str(
            self.privacy_basis_reference or ""
        ).startswith("TEST-"):
            frappe.throw(_("Synthetic Credential требует TEST- basis."))
        if self.retention_status != "Metadata Only" and not self._has_credential_number():
            frappe.throw(_("Active credential требует credential_number."))
        if self.no_expiry and self.expires_on:
            frappe.throw(_("No Expiry credential не должен иметь expires_on."))
        if not self.no_expiry and not self.expires_on:
            frappe.throw(_("Credential требует expires_on либо No Expiry."))
        if (
            self.issued_on
            and self.expires_on
            and getdate(self.expires_on) < getdate(self.issued_on)
        ):
            frappe.throw(_("Credential expires_on раньше issued_on."))
        if self.document and self.malware_status not in {"Pending", "Clean", "Rejected"}:
            frappe.throw(_("Credential attachment требует malware lifecycle."))
        if not self.document and self.malware_status != "Not Applicable":
            frappe.throw(_("Metadata-only credential должен иметь malware status Not Applicable."))
        scan_evidence = (self.scanned_file_hash, self.scanned_at, self.scanned_by)
        if self.malware_status in {"Clean", "Rejected"} and not all(scan_evidence):
            frappe.throw(_("Final malware status требует file hash, timestamp и recorder."))
        if self.scanned_file_hash and (
            len(self.scanned_file_hash) != 64
            or any(character not in "0123456789abcdef" for character in self.scanned_file_hash)
        ):
            frappe.throw(_("Scanned file hash должен быть lowercase SHA-256."))
        if self.malware_status in {"Pending", "Not Applicable"} and any(scan_evidence):
            frappe.throw(_("Незавершённый malware scan не должен иметь final evidence."))
        self._validate_transition()
        self._freeze_identity()

    def _has_credential_number(self) -> bool:
        if self.is_new():
            return bool(self.credential_number)
        return bool(self.get_password("credential_number", raise_exception=False))

    def on_trash(self) -> None:
        frappe.throw(
            _("Personnel Credential не удаляется напрямую; применяется retention."),
            frappe.PermissionError,
        )

    @staticmethod
    def _require_writer() -> None:
        if not frappe.flags.get(PRIVACY_WRITE_FLAG):
            frappe.throw(
                _("Personnel Credential изменяется только typed FR-06 command."),
                frappe.PermissionError,
            )

    def _validate_transition(self) -> None:
        before = self.get_doc_before_save()
        if before is None:
            if self.verification_status != "Draft":
                frappe.throw(_("Новый Personnel Credential создаётся в Draft."))
            return
        if before.verification_status == self.verification_status:
            return
        if frappe.flags.get(PRIVACY_TRANSITION_FLAG) != self.verification_status:
            frappe.throw(_("Personnel Credential transition context отсутствует."))
        if self.verification_status not in TRANSITIONS.get(before.verification_status, frozenset()):
            frappe.throw(_("Недопустимый Personnel Credential transition."))

    def _freeze_identity(self) -> None:
        before = self.get_doc_before_save()
        if before is None:
            return
        for fieldname in (
            "holder_type",
            "holder",
            "credential_type",
            "privacy_policy_reference",
            "privacy_policy_hash",
        ):
            if self.get(fieldname) != before.get(fieldname):
                frappe.throw(_("Personnel Credential holder/type/policy stamp неизменяемы."))
        number_changed = self.credential_number != before.credential_number or (
            self.credential_number_masked != before.credential_number_masked
        )
        retention_clear = bool(
            frappe.flags.get(PRIVACY_RETENTION_FLAG)
            and self.retention_status == "Metadata Only"
            and not self.credential_number
            and not self.credential_number_masked
        )
        if number_changed and not retention_clear:
            frappe.throw(_("Personnel Credential number изменяется только retention command."))


def on_doctype_update() -> None:
    frappe.db.add_index(
        "Ferum Personnel Credential", ["holder_type", "holder", "verification_status"]
    )
    frappe.db.add_index("Ferum Personnel Credential", ["expires_on", "verification_status"])
