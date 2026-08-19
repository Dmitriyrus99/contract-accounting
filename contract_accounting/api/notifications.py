"""Typed operational commands for fail-closed DP-06 delivery."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from contract_accounting.domain.notification import POLICY_VERSION
from contract_accounting.infrastructure.notification_guard import (
    NOTIFICATION_DELIVERY_WRITE_FLAG,
    NOTIFICATION_SETTINGS_WRITE_FLAG,
)


@frappe.whitelist(methods=["POST"])
def activate_deadline_notifications(reason: str, max_attempts: int | str = 3) -> dict[str, Any]:
    frappe.only_for("System Manager")
    reason = _reason(reason)
    attempts = cint(max_attempts)
    if not 1 <= attempts <= 10:
        frappe.throw(_("Maximum delivery attempts должен быть от 1 до 10."))
    settings = frappe.get_single("Ferum Notification Settings")
    if settings.enabled:
        frappe.throw(_("Deadline notifications уже активированы."))
    with _flag(NOTIFICATION_SETTINGS_WRITE_FLAG):
        settings.enabled = 1
        settings.activated_at = now_datetime()
        settings.activated_by = frappe.session.user
        settings.configuration_revision = cint(settings.configuration_revision) + 1
        settings.last_reason = reason
        settings.max_attempts = attempts
        settings.policy_version = POLICY_VERSION
        settings.save(ignore_permissions=True)
    return _settings_result(settings)


@frappe.whitelist(methods=["POST"])
def deactivate_deadline_notifications(reason: str) -> dict[str, Any]:
    frappe.only_for("System Manager")
    settings = frappe.get_single("Ferum Notification Settings")
    if not settings.enabled:
        frappe.throw(_("Deadline notifications уже выключены."))
    with _flag(NOTIFICATION_SETTINGS_WRITE_FLAG):
        settings.enabled = 0
        settings.configuration_revision = cint(settings.configuration_revision) + 1
        settings.last_reason = _reason(reason)
        settings.policy_version = POLICY_VERSION
        settings.save(ignore_permissions=True)
    return _settings_result(settings)


@frappe.whitelist(methods=["POST"])
def retry_dead_letter(delivery: str, reason: str) -> dict[str, Any]:
    frappe.only_for("System Manager")
    document = frappe.get_doc("Ferum Notification Delivery", delivery)
    if document.status != "Dead Letter":
        frappe.throw(_("Manual retry разрешён только для Dead Letter."))
    with _flag(NOTIFICATION_DELIVERY_WRITE_FLAG):
        document.status = "Retry"
        document.attempts = 0
        document.next_retry_at = now_datetime()
        document.email_queue = None
        document.error_code = f"MANUAL_RETRY:{_reason(reason)[:100]}"
        document.save(ignore_permissions=True)
    return {"delivery": document.name, "status": document.status}


@frappe.whitelist()
def get_notification_status() -> dict[str, Any]:
    settings = frappe.get_single("Ferum Notification Settings")
    settings.check_permission("read")
    return _settings_result(settings)


def _settings_result(settings: Any) -> dict[str, Any]:
    return {
        "enabled": bool(settings.enabled),
        "activated_at": str(settings.activated_at) if settings.activated_at else None,
        "activated_by": settings.activated_by,
        "configuration_revision": cint(settings.configuration_revision),
        "max_attempts": cint(settings.max_attempts),
        "policy_version": settings.policy_version,
    }


def _reason(value: str) -> str:
    value = (value or "").strip()
    if len(value) < 10:
        frappe.throw(_("Требуется содержательная причина не короче 10 символов."))
    return value


class _flag:
    def __init__(self, name: str) -> None:
        self.name = name
        self.previous: Any = None

    def __enter__(self) -> None:
        self.previous = frappe.flags.get(self.name)
        frappe.flags[self.name] = True

    def __exit__(self, *_: object) -> None:
        frappe.flags[self.name] = self.previous
