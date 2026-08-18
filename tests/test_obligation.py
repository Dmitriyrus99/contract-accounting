from __future__ import annotations

import unittest
from datetime import date

from contract_accounting.domain.obligation import (
	ObligationRuleError,
	RecurrenceRule,
	preview_occurrences,
)


class TestObligationPreview(unittest.TestCase):
	def test_month_end_preview_is_deterministic_and_bounded(self) -> None:
		result = preview_occurrences(
			effective_from=date(2026, 1, 31),
			effective_to=None,
			horizon_start=date(2026, 1, 1),
			horizon_end=date(2026, 4, 30),
			rules=(RecurrenceRule("Monthly", due_offset_days=5),),
		)
		self.assertEqual(
			[item.period_key for item in result],
			["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"],
		)
		self.assertEqual(result[0].due_date, date(2026, 2, 5))
		self.assertEqual(result[0].window_start, date(2026, 1, 31))

	def test_multiple_rules_deduplicate_period_keys(self) -> None:
		result = preview_occurrences(
			effective_from=date(2026, 1, 1),
			effective_to=date(2026, 1, 15),
			horizon_start=date(2026, 1, 1),
			horizon_end=date(2026, 1, 31),
			rules=(RecurrenceRule("Weekly"), RecurrenceRule("Weekly")),
		)
		self.assertEqual(len(result), 3)

	def test_invalid_or_unsupported_rules_fail_closed(self) -> None:
		with self.assertRaisesRegex(ObligationRuleError, "interval"):
			RecurrenceRule("Monthly", interval=0)
		with self.assertRaisesRegex(ObligationRuleError, "unsupported"):
			RecurrenceRule("Custom")
		with self.assertRaisesRegex(ObligationRuleError, "window"):
			RecurrenceRule("Monthly", window_before_days=-1)
		with self.assertRaisesRegex(ObligationRuleError, "at least one"):
			preview_occurrences(
				effective_from=date(2026, 1, 1),
				effective_to=None,
				horizon_start=date(2026, 1, 1),
				horizon_end=date(2026, 1, 31),
				rules=(),
			)

	def test_conflicting_rules_for_same_period_fail_closed(self) -> None:
		with self.assertRaisesRegex(ObligationRuleError, "conflicting"):
			preview_occurrences(
				effective_from=date(2026, 1, 1),
				effective_to=None,
				horizon_start=date(2026, 1, 1),
				horizon_end=date(2026, 1, 31),
				rules=(
					RecurrenceRule("Monthly", due_offset_days=1),
					RecurrenceRule("Monthly", due_offset_days=2),
				),
			)


if __name__ == "__main__":
	unittest.main()
