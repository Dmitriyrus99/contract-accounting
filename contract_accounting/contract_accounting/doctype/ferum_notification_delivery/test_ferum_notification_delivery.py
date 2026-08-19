"""Bench acceptance for DP-06 idempotency, digest and dead-letter behavior."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_system_timezone

from contract_accounting.api.calendars import assign_calendar, set_signature_deadline
from contract_accounting.api.deadlines import get_deadline_timeline
from contract_accounting.api.documents import change_project_document_status
from contract_accounting.api.notifications import (
    activate_deadline_notifications,
    deactivate_deadline_notifications,
    retry_dead_letter,
)
from contract_accounting.domain.notification import POLICY_VERSION
from contract_accounting.infrastructure.notification_guard import (
    NOTIFICATION_SETTINGS_WRITE_FLAG,
)
from contract_accounting.scheduler.notifications import (
    _collect_occurrences,
    _enabled_settings,
    process_deadline_digest,
    process_deadline_notifications,
)


class TestNotificationDelivery(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.company, self.customer, self.project, self.document = _make_context()
        assign_calendar(
            scope_type="Company",
            company=self.company.name,
            calendar_revision="RU-5D-2026-v1",
            reason="DP-06 runtime notification calendar",
        )
        _set_settings(enabled=1, activated_at="2026-06-01 00:00:00", max_attempts=2)

    def tearDown(self) -> None:
        _set_settings(enabled=0, activated_at=None, max_attempts=3)
        frappe.set_user(self._previous_user)
        super().tearDown()

    def test_activation_is_typed_and_resets_safe_watermark(self) -> None:
        _set_settings(enabled=0, activated_at=None, max_attempts=3)
        result = activate_deadline_notifications(
            reason="Approved DP-06 local runtime activation",
            max_attempts=3,
        )
        self.assertTrue(result["enabled"])
        self.assertTrue(result["activated_at"])
        result = deactivate_deadline_notifications(
            reason="End deterministic local acceptance run",
        )
        self.assertFalse(result["enabled"])

    def test_individual_thresholds_are_idempotent_and_in_app_is_real(self) -> None:
        self._signature(self.document)
        with patch(
            "contract_accounting.scheduler.notifications._queue_email",
            side_effect=RuntimeError("simulated transport failure"),
        ):
            first = process_deadline_notifications("2026-06-16 18:00:00")
            repeated = process_deadline_notifications("2026-06-16 18:00:00")
        self.assertEqual(first["disabled"], 0)
        self.assertEqual(repeated["created"], 0)
        deliveries = frappe.get_all(
            "Ferum Notification Delivery",
            filters={"source_name": self.document.name},
            fields=["channel", "status", "attempts", "notification_log"],
        )
        self.assertEqual(len(deliveries), 5)
        in_app = [row for row in deliveries if row.channel == "In App"]
        email = [row for row in deliveries if row.channel == "Email"]
        self.assertEqual(len(in_app), 3)
        self.assertTrue(all(row.status == "Sent" and row.notification_log for row in in_app))
        self.assertEqual(len(email), 2)
        self.assertTrue(all(row.status == "Retry" and row.attempts == 1 for row in email))
        self.assertEqual(
            frappe.db.count("Notification Log", {"document_name": self.document.name}),
            3,
        )

    def test_minus_three_email_is_one_digest_with_two_immutable_items(self) -> None:
        self._signature(self.document)
        second = _make_document(self.project.name)
        self._signature(second)
        self.document.reload()
        second.reload()
        self.assertEqual(str(self.document.signature_due_at), "2026-06-16 19:00:00")
        self.assertEqual(str(second.signature_due_at), "2026-06-16 19:00:00")
        timeline = get_deadline_timeline(
            self.project.name,
            as_of="2026-06-10 09:00:00",
            include_closed=0,
        )
        signature_rows = [row for row in timeline["rows"] if row["kind"] == "Signature Due"]
        self.assertEqual(len(signature_rows), 2, timeline["rows"])
        collected, _collection_errors = _collect_occurrences(
            _site_time("2026-06-10 09:00:00"),
            _enabled_settings(),
        )
        current_items = [
            item
            for item in collected
            if item["row"]["source_name"] in {self.document.name, second.name}
        ]
        self.assertEqual(len(current_items), 2, current_items)
        self.assertTrue(all(item["recipients"] == ["Administrator"] for item in current_items))
        self.assertTrue(all(item["occurrence"].code == "MINUS_3" for item in current_items))
        with patch(
            "contract_accounting.scheduler.notifications._queue_email",
            side_effect=RuntimeError("simulated digest transport failure"),
        ):
            first = process_deadline_digest(_site_time("2026-06-10 09:00:00"))
            repeated = process_deadline_digest(_site_time("2026-06-10 09:00:00"))
        self.assertEqual(first["created"], 1, first)
        self.assertEqual(repeated["created"], 0)
        parent_names = frappe.get_all(
            "Ferum Notification Digest Item",
            filters={"source_name": ("in", [self.document.name, second.name])},
            pluck="parent",
        )
        self.assertEqual(len(set(parent_names)), 1)
        delivery = frappe.get_doc("Ferum Notification Delivery", parent_names[0])
        current_digest_items = [
            item
            for item in delivery.digest_items
            if item.source_name in {self.document.name, second.name}
        ]
        self.assertEqual(len(current_digest_items), 2)
        self.assertEqual(len({item.item_key for item in current_digest_items}), 2)
        self.assertEqual(delivery.status, "Retry")

    def test_failed_email_reaches_dead_letter_and_requires_typed_manual_retry(self) -> None:
        self._signature(self.document)
        with patch(
            "contract_accounting.scheduler.notifications._queue_email",
            side_effect=RuntimeError("simulated permanent transport failure"),
        ):
            first = process_deadline_notifications(_site_time("2026-06-15 08:00:00"))
            second = process_deadline_notifications(_site_time("2026-06-15 08:06:00"))
        delivery_name = frappe.db.get_value(
            "Ferum Notification Delivery",
            {
                "source_name": self.document.name,
                "threshold": "MINUS_1",
                "channel": "Email",
            },
            "name",
        )
        self.assertTrue(delivery_name, {"first": first, "second": second})
        delivery = frappe.get_doc("Ferum Notification Delivery", delivery_name)
        self.assertEqual((delivery.status, delivery.attempts), ("Dead Letter", 2))
        result = retry_dead_letter(
            delivery=delivery.name,
            reason="Operator confirmed corrected outgoing transport",
        )
        self.assertEqual(result["status"], "Retry")
        delivery.reload()
        self.assertEqual(delivery.attempts, 0)
        with self.assertRaises(frappe.PermissionError):
            delivery.status = "Sent"
            delivery.save(ignore_permissions=True)

    def test_email_channel_creates_real_delayed_email_queue(self) -> None:
        _make_outgoing_email_account()
        self._signature(self.document)
        process_deadline_notifications(_site_time("2026-06-15 08:00:00"))
        delivery_name = frappe.db.get_value(
            "Ferum Notification Delivery",
            {
                "source_name": self.document.name,
                "threshold": "MINUS_1",
                "channel": "Email",
            },
            "name",
        )
        delivery = frappe.get_doc("Ferum Notification Delivery", delivery_name)
        self.assertEqual(delivery.status, "Queued", delivery.error_code)
        self.assertTrue(frappe.db.exists("Email Queue", delivery.email_queue))
        queue = frappe.get_doc("Email Queue", delivery.email_queue)
        self.assertEqual(queue.status, "Not Sent")
        self.assertEqual(
            queue.message_id,
            f"{delivery.delivery_key}@contract-accounting.local",
        )
        queue.db_set("status", "Sent", update_modified=False)
        process_deadline_notifications(_site_time("2026-06-15 08:01:00"))
        delivery.reload()
        self.assertEqual(delivery.status, "Sent")

    def test_overdue_director_daily_digest_and_closed_source_exclusion(self) -> None:
        director = _make_role_user("Генеральный директор")
        self._signature(self.document)
        with patch(
            "contract_accounting.scheduler.notifications._queue_email",
            side_effect=RuntimeError("simulated transport failure"),
        ):
            process_deadline_notifications(_site_time("2026-06-17 08:00:00"))
            process_deadline_digest(_site_time("2026-06-17 09:00:00"))
        escalation = frappe.get_all(
            "Ferum Notification Delivery",
            filters={
                "source_name": self.document.name,
                "threshold": "OVERDUE_PLUS_1",
                "recipient": director.name,
            },
            pluck="channel",
        )
        self.assertEqual(set(escalation), {"In App", "Email"})
        digest_parents = frappe.get_all(
            "Ferum Notification Digest Item",
            filters={"source_name": self.document.name, "threshold": "DAILY_DIGEST"},
            pluck="parent",
        )
        director_digest_channels = {
            frappe.db.get_value("Ferum Notification Delivery", parent, "channel")
            for parent in set(digest_parents)
            if frappe.db.get_value("Ferum Notification Delivery", parent, "recipient")
            == director.name
        }
        self.assertEqual(director_digest_channels, {"In App Digest", "Email Digest"})

        closed = _make_document(self.project.name)
        self._signature(closed)
        change_project_document_status(
            project_document=closed.name,
            target_status="Cancelled",
            reason="Close source before notification acceptance",
        )
        process_deadline_notifications(_site_time("2026-06-17 09:15:00"))
        self.assertEqual(
            frappe.db.count("Ferum Notification Delivery", {"source_name": closed.name}),
            0,
        )

    def _signature(self, document) -> None:
        set_signature_deadline(
            project_document=document.name,
            triggered_at="2026-06-08 08:00:00",
            offset_days=5,
            offset_unit="Business Days",
            reason="DP-06 deterministic threshold acceptance",
        )


def _set_settings(*, enabled: int, activated_at: str | None, max_attempts: int) -> None:
    settings = frappe.get_single("Ferum Notification Settings")
    previous = frappe.flags.get(NOTIFICATION_SETTINGS_WRITE_FLAG)
    frappe.flags[NOTIFICATION_SETTINGS_WRITE_FLAG] = True
    try:
        settings.enabled = enabled
        settings.activated_at = activated_at
        settings.activated_by = "Administrator" if activated_at else None
        settings.configuration_revision = int(settings.configuration_revision or 0) + 1
        settings.last_reason = "Runtime test setup with explicit activation watermark"
        settings.max_attempts = max_attempts
        settings.policy_version = POLICY_VERSION
        settings.save(ignore_permissions=True)
    finally:
        frappe.flags[NOTIFICATION_SETTINGS_WRITE_FLAG] = previous


def _make_context():
    suffix = uuid4().hex[:10]
    company = frappe.get_doc(
        {
            "doctype": "Company",
            "company_name": f"CA-18 Company {suffix}",
            "abbr": uuid4().hex[:5].upper(),
            "default_currency": "RUB",
            "country": "Russia",
        }
    ).insert(ignore_permissions=True)
    customer = frappe.get_doc(
        {
            "doctype": "Customer",
            "customer_name": f"CA-18 Customer {suffix}",
            "customer_type": "Company",
            "customer_group": "Commercial",
            "territory": "Russia",
        }
    ).insert(ignore_permissions=True)
    project = frappe.get_doc(
        {
            "doctype": "Ferum Service Project",
            "project_name": f"CA-18 project {suffix}",
            "company": company.name,
            "customer": customer.name,
            "contract_number": f"CA18-{suffix}",
            "contract_date": date(2026, 1, 15),
            "contract_subject": "DP-06 runtime acceptance",
            "effective_from": date(2026, 1, 15),
            "effective_to": date(2026, 12, 31),
            "currency": "RUB",
            "project_manager": "Administrator",
        }
    ).insert(ignore_permissions=True)
    return company, customer, project, _make_document(project.name)


def _make_document(project: str):
    suffix = uuid4().hex[:10]
    return frappe.get_doc(
        {
            "doctype": "Ferum Project Document",
            "source_doctype": "Ferum Service Project",
            "source_name": project,
            "document_type": "Other",
            "document_number": f"CA18-DOC-{suffix}",
            "document_date": date(2026, 1, 15),
            "version": "1",
            "owner_user": "Administrator",
        }
    ).insert(ignore_permissions=True)


def _site_time(moscow_value: str) -> datetime:
    moscow = datetime.fromisoformat(moscow_value).replace(tzinfo=ZoneInfo("Europe/Moscow"))
    return moscow.astimezone(ZoneInfo(get_system_timezone())).replace(tzinfo=None)


def _make_outgoing_email_account():
    suffix = uuid4().hex[:10]
    return frappe.get_doc(
        {
            "doctype": "Email Account",
            "email_account_name": f"CA18 Outgoing {suffix}",
            "email_id": f"ca18-{suffix}@example.invalid",
            "enable_outgoing": 1,
            "default_outgoing": 1,
            "smtp_server": "smtp.example.invalid",
            "smtp_port": "2525",
            "no_smtp_authentication": 1,
        }
    ).insert(ignore_permissions=True)


def _make_role_user(role: str):
    suffix = uuid4().hex[:10]
    return frappe.get_doc(
        {
            "doctype": "User",
            "email": f"ca18-{suffix}@example.invalid",
            "first_name": f"CA18 {suffix}",
            "enabled": 1,
            "send_welcome_email": 0,
            "roles": [{"role": role}],
        }
    ).insert(ignore_permissions=True)
