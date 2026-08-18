from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from contract_accounting.domain.work_queue import (
	classify_action,
	deduplicate_actions,
	progress,
	sort_actions,
)


class WorkQueueRuleTests(unittest.TestCase):
	def test_time_and_blocked_state_are_independent(self) -> None:
		now = datetime(2026, 8, 18, 12, tzinfo=timezone.utc)
		state = classify_action(
			status="Blocked", due_at=now - timedelta(hours=1), as_of=now
		)
		self.assertEqual(state["time_bucket"], "Overdue")
		self.assertEqual(state["state_bucket"], "Blocked")
		self.assertTrue(state["is_overdue"])

	def test_sort_is_overdue_today_upcoming_then_unscheduled(self) -> None:
		now = datetime(2026, 8, 18, 12, tzinfo=timezone.utc)
		rows = []
		for key, due in (
			("upcoming", now + timedelta(days=1)),
			("none", None),
			("today", now + timedelta(hours=1)),
			("overdue", now - timedelta(minutes=1)),
		):
			rows.append(
				{
					"canonical_key": key,
					"due_at": due.isoformat() if due else None,
					**classify_action(status="Ready", due_at=due, as_of=now),
				}
			)
		self.assertEqual(
			[row["canonical_key"] for row in sort_actions(rows)],
			["overdue", "today", "upcoming", "none"],
		)

	def test_process_step_wins_over_todo_delivery(self) -> None:
		rows = deduplicate_actions(
			[
				{
					"canonical_key": "Ferum Project Process Step:STEP-1",
					"source_rank": 10,
					"title": "ToDo delivery",
					"delivery_todos": ["TODO-1"],
				},
				{
					"canonical_key": "Ferum Project Process Step:STEP-1",
					"source_rank": 0,
					"title": "Process SSOT",
					"delivery_todos": [],
				},
			]
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["title"], "Process SSOT")
		self.assertEqual(rows[0]["delivery_todos"], ["TODO-1"])

	def test_progress_has_deterministic_empty_value(self) -> None:
		self.assertEqual(progress(0, 0), 0)
		self.assertEqual(progress(2, 3), 67)


if __name__ == "__main__":
	unittest.main()
