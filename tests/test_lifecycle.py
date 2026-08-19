from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from contract_accounting.domain.lifecycle import (
	EXECUTION_TRANSITIONS,
	LEGAL_TRANSITIONS,
	ExecutionStatus,
	LegalStatus,
	LifecycleState,
	LifecycleTransitionError,
	TransitionContext,
	can_create_new_execution,
	is_execution_transition_allowed,
	is_legal_transition_allowed,
	resume_execution,
	suspend_execution,
	transition,
)

NOW = datetime(2026, 8, 18, 6, 0, tzinfo=timezone.utc)


def context(**overrides: object) -> TransitionContext:
	values: dict[str, object] = {
		"actor": "test.user@example.com",
		"occurred_at": NOW,
		"correlation_id": "corr-test-001",
	}
	values.update(overrides)
	return TransitionContext(**values)  # type: ignore[arg-type]


def termination_context(**overrides: object) -> TransitionContext:
	values: dict[str, object] = {
		"reason": "Owner-approved termination",
		"comment": "Terminated under the signed agreement",
		"effective_date": date(2026, 8, 18),
		"evidence": ("Project Document/TERM-0001",),
		"termination_basis": "Mutual agreement",
		"related_document": "Project Document/TERM-0001",
	}
	values.update(overrides)
	return context(**values)


class TestApprovedEnumsAndMatrices(unittest.TestCase):
	def test_legal_enum_is_exact(self) -> None:
		self.assertEqual(
			{status.value for status in LegalStatus},
			{
				"Draft",
				"On Approval",
				"Approved",
				"Signing",
				"Signed",
				"In Force",
				"Cancelled",
				"Terminated",
				"Expired",
			},
		)

	def test_execution_enum_is_exact(self) -> None:
		self.assertEqual(
			{status.value for status in ExecutionStatus},
			{"Not Started", "Launching", "Active", "Suspended", "Completed", "Stopped"},
		)

	def test_legal_matrix_is_exhaustive(self) -> None:
		for source in LegalStatus:
			for target in LegalStatus:
				self.assertEqual(
					is_legal_transition_allowed(source, target),
					target in LEGAL_TRANSITIONS[source],
					f"{source.value} -> {target.value}",
				)

	def test_execution_matrix_is_exhaustive(self) -> None:
		for source in ExecutionStatus:
			for target in ExecutionStatus:
				self.assertEqual(
					is_execution_transition_allowed(source, target),
					target in EXECUTION_TRANSITIONS[source],
					f"{source.value} -> {target.value}",
				)

	def test_terminal_states_have_no_outgoing_transitions(self) -> None:
		for status in (LegalStatus.CANCELLED, LegalStatus.TERMINATED, LegalStatus.EXPIRED):
			self.assertEqual(LEGAL_TRANSITIONS[status], frozenset())
		for status in (ExecutionStatus.COMPLETED, ExecutionStatus.STOPPED):
			self.assertEqual(EXECUTION_TRANSITIONS[status], frozenset())


class TestPairInvariants(unittest.TestCase):
	def test_default_state_is_valid(self) -> None:
		self.assertEqual(LifecycleState(), LifecycleState(LegalStatus.DRAFT, ExecutionStatus.NOT_STARTED))

	def test_active_requires_in_force(self) -> None:
		with self.assertRaisesRegex(LifecycleTransitionError, "status pair"):
			LifecycleState(LegalStatus.SIGNED, ExecutionStatus.ACTIVE)

	def test_signed_suspension_must_come_from_launching(self) -> None:
		LifecycleState(
			LegalStatus.SIGNED,
			ExecutionStatus.SUSPENDED,
			suspended_from_status=ExecutionStatus.LAUNCHING,
		)
		with self.assertRaisesRegex(LifecycleTransitionError, "status pair"):
			LifecycleState(
				LegalStatus.SIGNED,
				ExecutionStatus.SUSPENDED,
				suspended_from_status=ExecutionStatus.ACTIVE,
			)

	def test_cancelled_requires_stopped(self) -> None:
		with self.assertRaisesRegex(LifecycleTransitionError, "status pair"):
			LifecycleState(LegalStatus.CANCELLED, ExecutionStatus.NOT_STARTED)

	def test_terminated_completed_requires_documented_exception(self) -> None:
		with self.assertRaisesRegex(LifecycleTransitionError, "status pair"):
			LifecycleState(LegalStatus.TERMINATED, ExecutionStatus.COMPLETED)
		LifecycleState(
			LegalStatus.TERMINATED,
			ExecutionStatus.COMPLETED,
			documented_termination_completion_exception=True,
		)

	def test_expired_accepts_completed_or_stopped_only(self) -> None:
		LifecycleState(LegalStatus.EXPIRED, ExecutionStatus.COMPLETED)
		LifecycleState(LegalStatus.EXPIRED, ExecutionStatus.STOPPED)
		with self.assertRaises(LifecycleTransitionError):
			LifecycleState(LegalStatus.EXPIRED, ExecutionStatus.ACTIVE)


class TestAtomicTransitions(unittest.TestCase):
	def test_simple_legal_transition_writes_one_event(self) -> None:
		result = transition(
			LifecycleState(), context(), target_legal_status=LegalStatus.ON_APPROVAL
		)
		self.assertEqual(result.state.legal_status, LegalStatus.ON_APPROVAL)
		self.assertEqual(result.state.execution_status, ExecutionStatus.NOT_STARTED)
		self.assertEqual(len(result.audit_events), 1)
		self.assertEqual(result.audit_events[0].dimension, "legal_status")

	def test_cancel_is_atomic_with_stopped_and_shared_correlation(self) -> None:
		result = transition(
			LifecycleState(),
			context(
				reason="Tender withdrawn",
				comment="Contract was not concluded",
				effective_date=date(2026, 8, 18),
				evidence=("Project Document/CANCEL-0001",),
			),
			target_legal_status=LegalStatus.CANCELLED,
			target_execution_status=ExecutionStatus.STOPPED,
		)
		self.assertEqual(
			result.state,
			LifecycleState(LegalStatus.CANCELLED, ExecutionStatus.STOPPED),
		)
		self.assertEqual(len(result.audit_events), 2)
		self.assertEqual({event.correlation_id for event in result.audit_events}, {"corr-test-001"})

	def test_cancel_without_atomic_stop_is_rejected(self) -> None:
		original = LifecycleState()
		with self.assertRaisesRegex(LifecycleTransitionError, "status pair"):
			transition(
				original,
				context(
					reason="Tender withdrawn",
					comment="Contract was not concluded",
					effective_date=date(2026, 8, 18),
					evidence=("Project Document/CANCEL-0001",),
				),
				target_legal_status=LegalStatus.CANCELLED,
			)
		self.assertEqual(original, LifecycleState())

	def test_signed_contract_can_terminate_atomically(self) -> None:
		result = transition(
			LifecycleState(LegalStatus.SIGNED, ExecutionStatus.NOT_STARTED),
			termination_context(),
			target_legal_status=LegalStatus.TERMINATED,
			target_execution_status=ExecutionStatus.STOPPED,
		)
		self.assertEqual(result.state, LifecycleState(LegalStatus.TERMINATED, ExecutionStatus.STOPPED))

	def test_completed_termination_requires_explicit_exception(self) -> None:
		state = LifecycleState(LegalStatus.IN_FORCE, ExecutionStatus.COMPLETED)
		with self.assertRaisesRegex(LifecycleTransitionError, "status pair"):
			transition(state, termination_context(), target_legal_status=LegalStatus.TERMINATED)
		result = transition(
			state,
			termination_context(),
			target_legal_status=LegalStatus.TERMINATED,
			documented_termination_completion_exception=True,
		)
		self.assertTrue(result.state.documented_termination_completion_exception)
		self.assertEqual(len(result.audit_events), 1)
		event = result.audit_events[0]
		self.assertEqual(event.termination_basis, "Mutual agreement")
		self.assertEqual(event.related_document, "Project Document/TERM-0001")
		self.assertTrue(event.documented_termination_completion_exception)

	def test_expiry_can_complete_active_execution_atomically(self) -> None:
		result = transition(
			LifecycleState(LegalStatus.IN_FORCE, ExecutionStatus.ACTIVE),
			context(),
			target_legal_status=LegalStatus.EXPIRED,
			target_execution_status=ExecutionStatus.COMPLETED,
		)
		self.assertEqual(result.state, LifecycleState(LegalStatus.EXPIRED, ExecutionStatus.COMPLETED))

	def test_draft_to_terminated_is_forbidden(self) -> None:
		with self.assertRaisesRegex(LifecycleTransitionError, "legal transition"):
			transition(
				LifecycleState(),
				termination_context(),
				target_legal_status=LegalStatus.TERMINATED,
				target_execution_status=ExecutionStatus.STOPPED,
			)

	def test_noop_is_forbidden(self) -> None:
		with self.assertRaisesRegex(LifecycleTransitionError, "at least one dimension"):
			transition(LifecycleState(), context())


class TestRequiredEvidence(unittest.TestCase):
	def test_cancel_requires_reason_comment_date_and_evidence(self) -> None:
		base = {
			"reason": "Cancelled",
			"comment": "Not concluded",
			"effective_date": date(2026, 8, 18),
			"evidence": ("Project Document/CANCEL-0001",),
		}
		for missing in base:
			values = dict(base)
			values[missing] = () if missing == "evidence" else None
			with self.subTest(missing=missing), self.assertRaises(LifecycleTransitionError):
				transition(
					LifecycleState(),
					context(**values),
					target_legal_status=LegalStatus.CANCELLED,
					target_execution_status=ExecutionStatus.STOPPED,
				)

	def test_termination_requires_basis_and_related_document(self) -> None:
		for missing in ("termination_basis", "related_document"):
			with self.subTest(missing=missing), self.assertRaisesRegex(
				LifecycleTransitionError, missing
			):
				transition(
					LifecycleState(LegalStatus.SIGNED, ExecutionStatus.NOT_STARTED),
					termination_context(**{missing: None}),
					target_legal_status=LegalStatus.TERMINATED,
					target_execution_status=ExecutionStatus.STOPPED,
				)

	def test_stopped_requires_reason(self) -> None:
		with self.assertRaisesRegex(LifecycleTransitionError, "reason"):
			transition(
				LifecycleState(),
				context(),
				target_execution_status=ExecutionStatus.STOPPED,
			)

	def test_context_requires_actor_and_aware_time(self) -> None:
		with self.assertRaisesRegex(LifecycleTransitionError, "actor"):
			context(actor=" ")
		with self.assertRaisesRegex(LifecycleTransitionError, "timezone-aware"):
			context(occurred_at=datetime(2026, 8, 18, 6, 0))


class TestSuspendResume(unittest.TestCase):
	def test_launching_suspend_resume(self) -> None:
		original = LifecycleState(LegalStatus.SIGNED, ExecutionStatus.LAUNCHING)
		suspended = suspend_execution(
			original,
			context(reason="Waiting for access", effective_date=date(2026, 8, 18)),
		)
		self.assertEqual(suspended.state.legal_status, LegalStatus.SIGNED)
		self.assertEqual(suspended.state.execution_status, ExecutionStatus.SUSPENDED)
		self.assertEqual(suspended.state.suspended_from_status, ExecutionStatus.LAUNCHING)
		resumed = resume_execution(suspended.state, context(reason="Access granted"))
		self.assertEqual(resumed.state, original)

	def test_active_suspend_resume(self) -> None:
		original = LifecycleState(LegalStatus.IN_FORCE, ExecutionStatus.ACTIVE)
		suspended = suspend_execution(
			original,
			context(reason="Safety hold", effective_date=date(2026, 8, 18)),
		)
		self.assertEqual(suspended.state.suspended_from_status, ExecutionStatus.ACTIVE)
		self.assertEqual(resume_execution(suspended.state, context()).state, original)

	def test_suspend_requires_reason_and_effective_date(self) -> None:
		state = LifecycleState(LegalStatus.SIGNED, ExecutionStatus.LAUNCHING)
		with self.assertRaisesRegex(LifecycleTransitionError, "reason"):
			suspend_execution(state, context(effective_date=date(2026, 8, 18)))
		with self.assertRaisesRegex(LifecycleTransitionError, "effective_date"):
			suspend_execution(state, context(reason="Waiting"))

	def test_suspended_to_completed_is_forbidden(self) -> None:
		state = LifecycleState(
			LegalStatus.IN_FORCE,
			ExecutionStatus.SUSPENDED,
			suspended_from_status=ExecutionStatus.ACTIVE,
		)
		with self.assertRaisesRegex(LifecycleTransitionError, "execution transition"):
			transition(state, context(), target_execution_status=ExecutionStatus.COMPLETED)

	def test_resume_does_not_change_legal_status(self) -> None:
		state = LifecycleState(
			LegalStatus.IN_FORCE,
			ExecutionStatus.SUSPENDED,
			suspended_from_status=ExecutionStatus.LAUNCHING,
		)
		result = resume_execution(state, context())
		self.assertEqual(result.state.legal_status, LegalStatus.IN_FORCE)
		self.assertEqual(result.state.execution_status, ExecutionStatus.LAUNCHING)

	def test_terminal_execution_cannot_resume(self) -> None:
		for status, legal in (
			(ExecutionStatus.COMPLETED, LegalStatus.IN_FORCE),
			(ExecutionStatus.STOPPED, LegalStatus.CANCELLED),
		):
			with self.subTest(status=status), self.assertRaisesRegex(
				LifecycleTransitionError, "only Suspended"
			):
				resume_execution(LifecycleState(legal, status), context())


class TestOperationalBoundary(unittest.TestCase):
	def test_terminal_legal_states_forbid_new_execution(self) -> None:
		for status in LegalStatus:
			self.assertEqual(
				can_create_new_execution(status),
				status not in {LegalStatus.CANCELLED, LegalStatus.TERMINATED, LegalStatus.EXPIRED},
			)


if __name__ == "__main__":
	unittest.main()
