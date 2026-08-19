from __future__ import annotations

import unittest
from datetime import date, datetime, time

from contract_accounting.domain.deadline import (
    CalendarSnapshot,
    DeadlineRule,
    DeadlineRuleError,
    calculate_deadline,
)


class TestDeadlineCalculation(unittest.TestCase):
    def setUp(self) -> None:
        self.calendar = CalendarSnapshot(
            timezone="Europe/Moscow",
            revision="fixture-2026-08-v1",
            holidays=frozenset({date(2026, 8, 18)}),
            cutoff_time=time(18, 0),
        )

    def test_business_days_skip_holiday_and_emit_immutable_hash(self) -> None:
        result = calculate_deadline(
            triggered_at=datetime(2026, 8, 17, 10, 0),
            rule=DeadlineRule(
                offset_days=2,
                offset_unit="Business Days",
                warning_days=1,
                escalation_days=1,
            ),
            calendar=self.calendar,
        )
        self.assertEqual(result.warning_at.date(), date(2026, 8, 19))
        self.assertEqual(result.due_at.date(), date(2026, 8, 20))
        self.assertEqual(result.escalation_at.date(), date(2026, 8, 21))
        self.assertEqual(len(result.snapshot_hash), 64)
        self.assertEqual(
            result.snapshot_hash,
            calculate_deadline(
                triggered_at=datetime(2026, 8, 17, 10, 0),
                rule=DeadlineRule(2, "Business Days", warning_days=1, escalation_days=1),
                calendar=self.calendar,
            ).snapshot_hash,
        )

    def test_calendar_days_do_not_apply_holiday_list(self) -> None:
        result = calculate_deadline(
            triggered_at=datetime(2026, 8, 17, 10, 0),
            rule=DeadlineRule(2, "Calendar Days"),
            calendar=self.calendar,
        )
        self.assertEqual(result.due_at.date(), date(2026, 8, 19))

    def test_after_cutoff_policy_is_explicit(self) -> None:
        calendar = CalendarSnapshot(
            timezone="Europe/Moscow",
            revision="fixture-cutoff-v1",
            holidays=frozenset({date(2026, 8, 18)}),
            cutoff_time=time(9, 0),
            after_cutoff_policy="Next Business Day",
        )
        result = calculate_deadline(
            triggered_at=datetime(2026, 8, 17, 10, 0),
            rule=DeadlineRule(0, "Business Days"),
            calendar=calendar,
        )
        self.assertEqual(result.due_at.date(), date(2026, 8, 19))

    def test_unknown_trigger_and_configuration_fail_closed(self) -> None:
        with self.assertRaisesRegex(DeadlineRuleError, "trigger"):
            calculate_deadline(
                triggered_at=None,
                rule=DeadlineRule(1, "Business Days"),
                calendar=self.calendar,
            )
        with self.assertRaisesRegex(DeadlineRuleError, "timezone"):
            CalendarSnapshot(timezone="Unknown/Zone", revision="v1")
        with self.assertRaisesRegex(DeadlineRuleError, "offset unit"):
            DeadlineRule(1, "Working Maybe")

    def test_dp05_before_after_hours_and_nonworking_trigger_normalization(self) -> None:
        calendar = CalendarSnapshot(
            timezone="Europe/Moscow",
            revision="dp05-window-v1",
            holidays=frozenset({date(2026, 6, 12)}),
        )
        before = calculate_deadline(
            triggered_at=datetime(2026, 6, 11, 7, 15),
            rule=DeadlineRule(0, "Business Days"),
            calendar=calendar,
        )
        after = calculate_deadline(
            triggered_at=datetime(2026, 6, 11, 19, 1),
            rule=DeadlineRule(0, "Business Days"),
            calendar=calendar,
        )
        holiday = calculate_deadline(
            triggered_at=datetime(2026, 6, 12, 12, 0),
            rule=DeadlineRule(0, "Business Days"),
            calendar=calendar,
        )
        self.assertEqual(before.anchor_at, before.anchor_at.replace(hour=8, minute=0))
        self.assertEqual(after.anchor_at, after.anchor_at.replace(day=15, hour=8, minute=0))
        self.assertEqual(holiday.anchor_at, holiday.anchor_at.replace(day=15, hour=8, minute=0))

    def test_calendar_due_rolls_and_shortened_day_caps_at_work_end(self) -> None:
        calendar = CalendarSnapshot(
            timezone="Europe/Moscow",
            revision="dp05-short-v1",
            holidays=frozenset({date(2026, 5, 1)}),
            shortened_days=((date(2026, 4, 30), time(18, 0)),),
        )
        shortened = calculate_deadline(
            triggered_at=datetime(2026, 4, 30, 10, 0),
            rule=DeadlineRule(0, "Calendar Days"),
            calendar=calendar,
        )
        rolled = calculate_deadline(
            triggered_at=datetime(2026, 4, 30, 10, 0),
            rule=DeadlineRule(1, "Calendar Days"),
            calendar=calendar,
        )
        self.assertEqual(shortened.due_at.time(), time(18, 0))
        self.assertEqual(rolled.due_at.date(), date(2026, 5, 4))
        self.assertIn('"algorithm_version":"dp05-v1"', rolled.snapshot_json)

    def test_revision_changes_new_result_without_mutating_old_snapshot(self) -> None:
        old = calculate_deadline(
            triggered_at=datetime(2026, 8, 17, 10, 0),
            rule=DeadlineRule(1, "Business Days"),
            calendar=CalendarSnapshot(timezone="Europe/Moscow", revision="old-v1"),
        )
        old_json = old.snapshot_json
        new = calculate_deadline(
            triggered_at=datetime(2026, 8, 17, 10, 0),
            rule=DeadlineRule(1, "Business Days"),
            calendar=CalendarSnapshot(
                timezone="Europe/Moscow",
                revision="new-v2",
                holidays=frozenset({date(2026, 8, 18)}),
            ),
        )
        self.assertEqual(old.due_at.date(), date(2026, 8, 18))
        self.assertEqual(new.due_at.date(), date(2026, 8, 19))
        self.assertEqual(old.snapshot_json, old_json)
        self.assertNotEqual(old.snapshot_hash, new.snapshot_hash)


if __name__ == "__main__":
    unittest.main()
