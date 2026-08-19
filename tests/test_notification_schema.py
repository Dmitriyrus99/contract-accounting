from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = ROOT / "contract_accounting" / "contract_accounting" / "doctype"


def schema(name: str) -> dict[str, object]:
    return json.loads((DOCTYPE_ROOT / name / f"{name}.json").read_text(encoding="utf-8"))


def fields(document: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        field["fieldname"]: field
        for field in document["fields"]  # type: ignore[index,union-attr]
    }


class TestNotificationSchema(unittest.TestCase):
    def test_settings_are_fail_closed_and_typed(self) -> None:
        settings = fields(schema("ferum_notification_settings"))
        self.assertEqual(settings["enabled"]["default"], "0")
        self.assertEqual(settings["activated_at"]["read_only"], 1)
        source = (ROOT / "contract_accounting" / "api" / "notifications.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('@frappe.whitelist(methods=["POST"])', source)
        controller = (
            DOCTYPE_ROOT / "ferum_notification_settings" / "ferum_notification_settings.py"
        ).read_text(encoding="utf-8")
        self.assertIn("activation watermark", controller)

    def test_delivery_has_deterministic_identity_transport_state_and_digest_items(self) -> None:
        delivery = schema("ferum_notification_delivery")
        delivery_fields = fields(delivery)
        self.assertEqual(delivery["autoname"], "field:delivery_key")
        self.assertEqual(delivery_fields["delivery_key"]["unique"], 1)
        self.assertEqual(delivery_fields["payload_hash"]["read_only"], 1)
        self.assertIn("Dead Letter", delivery_fields["status"]["options"])
        self.assertEqual(
            delivery_fields["digest_items"]["options"],
            "Ferum Notification Digest Item",
        )

    def test_scheduler_hooks_include_timezone_aware_quarter_hour_delivery_and_digest(self) -> None:
        hooks = (ROOT / "contract_accounting" / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('"*/15 * * * *"', hooks)
        self.assertIn("process_deadline_notifications", hooks)
        self.assertIn("process_deadline_digest", hooks)
        scheduler = (ROOT / "contract_accounting" / "scheduler" / "notifications.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("calendar_now.hour != 9", scheduler)

    def test_controller_guards_identity_and_deletion(self) -> None:
        controller = (
            DOCTYPE_ROOT / "ferum_notification_delivery" / "ferum_notification_delivery.py"
        ).read_text(encoding="utf-8")
        self.assertIn("identity/payload неизменяемы", controller)
        self.assertIn("Удаление Notification Delivery запрещено", controller)
        self.assertIn("payload hash mismatch", controller)


if __name__ == "__main__":
    unittest.main()
