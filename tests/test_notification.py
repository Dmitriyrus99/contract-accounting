from __future__ import annotations

import unittest
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from contract_accounting.domain.deadline import CalendarSnapshot
from contract_accounting.domain.notification import delivery_identity, threshold_occurrences


def calendar() -> CalendarSnapshot:
    return CalendarSnapshot(
        calendar_id="RU-5D-2026",
        timezone="Europe/Moscow",
        revision="v1",
        holidays=frozenset({date(2026, 6, 12)}),
        work_start_time=time(8),
        work_end_time=time(19),
        valid_from=date(2026, 1, 1),
        valid_until=date(2026, 12, 31),
    )


class TestNotificationPolicy(unittest.TestCase):
    def test_standard_thresholds_skip_weekend_and_holiday(self) -> None:
        due = datetime(2026, 6, 16, 19, tzinfo=ZoneInfo("Europe/Moscow"))
        occurrences = {
            item.code: item for item in threshold_occurrences(due_at=due, calendar=calendar())
        }
        self.assertEqual(occurrences["MINUS_3"].occurs_at.isoformat(), "2026-06-10T08:00:00+03:00")
        self.assertEqual(occurrences["MINUS_1"].occurs_at.isoformat(), "2026-06-15T08:00:00+03:00")
        self.assertEqual(occurrences["DUE_0800"].occurs_at.isoformat(), "2026-06-16T08:00:00+03:00")
        self.assertEqual(
            occurrences["OVERDUE_PLUS_1"].occurs_at.isoformat(),
            "2026-06-17T08:00:00+03:00",
        )

    def test_short_deadline_replaces_fixed_pre_due_thresholds(self) -> None:
        trigger = datetime(2026, 6, 15, 8, tzinfo=ZoneInfo("Europe/Moscow"))
        due = datetime(2026, 6, 16, 18, tzinfo=ZoneInfo("Europe/Moscow"))
        occurrences = threshold_occurrences(
            due_at=due,
            triggered_at=trigger,
            calendar=calendar(),
        )
        self.assertEqual(
            [item.code for item in occurrences],
            ["SHORT_50", "SHORT_80", "BREACH", "OVERDUE_PLUS_1"],
        )
        self.assertEqual(occurrences[0].occurs_at.isoformat(), "2026-06-16T01:00:00+03:00")
        self.assertEqual(occurrences[1].occurs_at.isoformat(), "2026-06-16T11:12:00+03:00")

    def test_due_change_and_channel_change_have_explicit_identities(self) -> None:
        base = {
            "source_key": "Ferum Project Document:FPD-1:signature_due_at",
            "due_at": datetime(2026, 6, 16, 19),
            "threshold": "MINUS_1",
            "recipient": "owner@example.com",
        }
        correlation, in_app = delivery_identity(**base, channel="In App")
        same_correlation, email = delivery_identity(**base, channel="Email")
        changed, _ = delivery_identity(
            **{**base, "due_at": datetime(2026, 6, 17, 19)},
            channel="In App",
        )
        self.assertEqual(correlation, same_correlation)
        self.assertNotEqual(in_app, email)
        self.assertNotEqual(correlation, changed)


if __name__ == "__main__":
    unittest.main()
