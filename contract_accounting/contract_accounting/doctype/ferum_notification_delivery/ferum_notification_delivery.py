"""Guarded delivery fact with immutable identity/payload and mutable transport state."""

from __future__ import annotations

import hashlib
import json

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.domain.notification import POLICY_VERSION
from contract_accounting.infrastructure.notification_guard import (
    NOTIFICATION_DELIVERY_WRITE_FLAG,
)

IMMUTABLE_FIELDS = (
    "delivery_key",
    "correlation_key",
    "policy_version",
    "service_project",
    "source_doctype",
    "source_name",
    "source_field",
    "source_key",
    "due_at",
    "threshold",
    "threshold_at",
    "recipient",
    "channel",
    "payload_json",
    "payload_hash",
)

ALLOWED_TRANSITIONS = {
    "Pending": frozenset({"Processing", "Skipped"}),
    "Processing": frozenset({"Queued", "Sent", "Retry", "Dead Letter"}),
    "Queued": frozenset({"Sent", "Retry", "Dead Letter"}),
    "Retry": frozenset({"Processing"}),
    "Dead Letter": frozenset({"Retry"}),
    "Sent": frozenset(),
    "Skipped": frozenset(),
}


class FerumNotificationDelivery(Document):
    def before_insert(self) -> None:
        self._require_writer()

    def validate(self) -> None:
        self._require_writer()
        payload = self._validate_payload()
        self._validate_digest_membership(payload)
        if not self.is_new():
            previous = frappe.db.get_value(
                self.doctype,
                self.name,
                (*IMMUTABLE_FIELDS, "status"),
                as_dict=True,
            )
            if previous and any(
                self.get(field) != previous.get(field) for field in IMMUTABLE_FIELDS
            ):
                frappe.throw(_("Notification Delivery identity/payload неизменяемы."))
            if previous and self.status != previous.status:
                allowed = ALLOWED_TRANSITIONS.get(previous.status, frozenset())
                if self.status not in allowed:
                    frappe.throw(_("Недопустимый Notification Delivery status transition."))
        elif self.status != "Pending":
            frappe.throw(_("Новая Notification Delivery должна быть Pending."))

    def on_trash(self) -> None:
        frappe.throw(_("Удаление Notification Delivery запрещено."), frappe.PermissionError)

    def _require_writer(self) -> None:
        if not frappe.flags.get(NOTIFICATION_DELIVERY_WRITE_FLAG):
            frappe.throw(
                _("Notification Delivery изменяется только scheduler/typed command."),
                frappe.PermissionError,
            )

    def _validate_payload(self) -> dict[str, object]:
        if self.policy_version != POLICY_VERSION:
            frappe.throw(_("Notification Delivery policy version не поддерживается."))
        try:
            payload = json.loads(self.payload_json)
        except (TypeError, ValueError):
            frappe.throw(_("Notification Delivery payload должен быть valid JSON."))
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if canonical != self.payload_json:
            frappe.throw(_("Notification Delivery payload должен быть canonical JSON."))
        if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != self.payload_hash:
            frappe.throw(_("Notification Delivery payload hash mismatch."))
        return payload

    def _validate_digest_membership(self, payload: dict[str, object]) -> None:
        expected = sorted(str(value) for value in payload.get("item_keys", []))
        actual = sorted(str(row.item_key) for row in (self.get("digest_items") or []))
        if expected != actual:
            frappe.throw(_("Notification digest items не совпадают с immutable payload."))


def on_doctype_update() -> None:
    frappe.db.add_index(
        "Ferum Notification Delivery",
        ["status", "next_retry_at"],
        "ca_notification_retry_idx",
    )
    frappe.db.add_index(
        "Ferum Notification Delivery",
        ["service_project", "source_doctype", "source_name"],
        "ca_notification_source_idx",
    )
