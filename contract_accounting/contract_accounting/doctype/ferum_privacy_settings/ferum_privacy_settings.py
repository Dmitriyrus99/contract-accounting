"""Fail-closed activation watermark for FR-05 protected data."""

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.domain.privacy import POLICY_HASH, POLICY_REFERENCE

PRIVACY_SETTINGS_WRITE_FLAG = "contract_accounting_privacy_settings_writer"


class FerumPrivacySettings(Document):
    def validate(self) -> None:
        if not frappe.flags.get(PRIVACY_SETTINGS_WRITE_FLAG):
            frappe.throw(
                _("Privacy Settings изменяются только typed command."), frappe.PermissionError
            )
        if self.policy_reference != POLICY_REFERENCE or self.policy_hash != POLICY_HASH:
            frappe.throw(_("Privacy policy stamp не совпадает с утверждённым FR-05."))
        if self.enabled:
            if self.activation_mode not in {"Synthetic Test", "Production"}:
                frappe.throw(_("Enabled privacy policy требует точный activation mode."))
            if not self.activated_at or not self.activated_by or not self.approval_reference:
                frappe.throw(_("Enabled privacy policy требует полный activation watermark."))
        elif self.activation_mode != "Disabled":
            frappe.throw(_("Disabled privacy policy должна иметь activation_mode Disabled."))
