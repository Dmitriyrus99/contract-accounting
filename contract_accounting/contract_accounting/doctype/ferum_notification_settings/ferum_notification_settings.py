"""Fail-closed activation watermark for deadline delivery."""

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.domain.notification import POLICY_VERSION
from contract_accounting.infrastructure.notification_guard import (
    NOTIFICATION_SETTINGS_WRITE_FLAG,
)


class FerumNotificationSettings(Document):
    def validate(self) -> None:
        if not frappe.flags.get(NOTIFICATION_SETTINGS_WRITE_FLAG):
            frappe.throw(
                _("Notification Settings изменяются только typed command."),
                frappe.PermissionError,
            )
        if self.enabled and not self.activated_at:
            frappe.throw(_("Enabled notifications требуют activation watermark."))
        if not 1 <= int(self.max_attempts or 0) <= 10:
            frappe.throw(_("Maximum delivery attempts должен быть от 1 до 10."))
        if self.policy_version != POLICY_VERSION:
            frappe.throw(_("Notification policy version не поддерживается."))
