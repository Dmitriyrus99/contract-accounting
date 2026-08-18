from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from contract_accounting.domain.process import (
	BASE_STEP_STATUSES,
	ProcessRuleError,
	derive_step_state,
	failed_blocking_steps,
	validate_step_transition,
)


class ProcessRuleTests(unittest.TestCase):
	def test_overdue_is_derived_and_not_a_base_status(self) -> None:
		self.assertNotIn("Overdue", BASE_STEP_STATUSES)
		now = datetime(2026, 8, 18, 12)
		state = derive_step_state(
			"Waiting External", due_at=now - timedelta(days=1), as_of=now
		)
		self.assertTrue(state.is_overdue)
		self.assertEqual(state.display_status, "Overdue")
		self.assertEqual(state.base_status, "Waiting External")

	def test_not_applicable_and_waiting_external_require_reason(self) -> None:
		with self.assertRaises(ProcessRuleError):
			validate_step_transition("Planned", "Not Applicable")
		with self.assertRaises(ProcessRuleError):
			validate_step_transition("In Progress", "Waiting External")

	def test_completion_requires_matching_validated_evidence(self) -> None:
		with self.assertRaises(ProcessRuleError):
			validate_step_transition(
				"In Progress",
				"Completed",
				required_evidence_type="File",
			)
		validate_step_transition(
			"In Progress",
			"Completed",
			required_evidence_type="File",
			has_required_evidence=True,
		)

	def test_gate_fails_on_one_open_blocking_step(self) -> None:
		failed = failed_blocking_steps(
			[
				{"name": "STEP-1", "blocking": 1, "status": "Completed"},
				{"name": "STEP-2", "blocking": 1, "status": "Blocked"},
				{"name": "STEP-3", "blocking": 0, "status": "Ready"},
			]
		)
		self.assertEqual([row["name"] for row in failed], ["STEP-2"])


if __name__ == "__main__":
	unittest.main()
