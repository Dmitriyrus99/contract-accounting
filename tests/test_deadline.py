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


if __name__ == "__main__":
	unittest.main()
