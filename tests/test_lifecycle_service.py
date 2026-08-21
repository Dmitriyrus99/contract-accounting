from __future__ import annotations

import unittest
from copy import deepcopy
from datetime import date, datetime, timezone
from types import TracebackType

from contract_accounting.application.lifecycle_service import (
	apply_lifecycle_transition,
	resume_project_execution,
	suspend_project_execution,
)
from contract_accounting.domain.lifecycle import (
	ExecutionStatus,
	LegalStatus,
	LifecycleAuditEvent,
	LifecycleState,
	LifecycleTransitionError,
	TransitionContext,
)

PROJECT = "FSP-2026-00001"
NOW = datetime(2026, 8, 18, 7, 0, tzinfo=timezone.utc)


def context(**overrides: object) -> TransitionContext:
	values: dict[str, object] = {
		"actor": "test.user@example.com",
		"occurred_at": NOW,
		"correlation_id": "corr-service-001",
	}
	values.update(overrides)
	return TransitionContext(**values)  # type: ignore[arg-type]


class MemoryUnitOfWork:
	"""Rollback-capable test double for the persistence contract."""

	def __init__(self, state: LifecycleState) -> None:
		self.states = {PROJECT: state}
		self.events: list[tuple[str, LifecycleAuditEvent]] = []
		self.calls: list[str] = []
		self.fail_audit = False
		self._snapshot: tuple[
			dict[str, LifecycleState], list[tuple[str, LifecycleAuditEvent]]
		] | None = None

	def __enter__(self) -> MemoryUnitOfWork:
		self.calls.append("enter")
		self._snapshot = (deepcopy(self.states), deepcopy(self.events))
		return self

	def __exit__(
		self,
		exc_type: type[BaseException] | None,
		exc_value: BaseException | None,
		traceback: TracebackType | None,
	) -> bool | None:
		self.calls.append("rollback" if exc_type else "commit")
		if exc_type and self._snapshot is not None:
			self.states, self.events = self._snapshot
		self._snapshot = None
		return None

	def lock_state(self, service_project: str) -> LifecycleState:
		self.calls.append("lock")
		return self.states[service_project]

	def save_state(self, service_project: str, state: LifecycleState) -> None:
		self.calls.append("save")
		self.states[service_project] = state

	def append_audit_events(
		self,
		service_project: str,
		events: tuple[LifecycleAuditEvent, ...],
	) -> None:
		self.calls.append("audit")
		if self.fail_audit:
			raise RuntimeError("simulated audit insert failure")
		self.events.extend((service_project, event) for event in events)


class TestLifecycleApplicationService(unittest.TestCase):
	def test_state_and_correlated_audit_commit_atomically(self) -> None:
		uow = MemoryUnitOfWork(LifecycleState())
		result = apply_lifecycle_transition(
			uow,
			PROJECT,
			context(
				reason="Tender withdrawn",
				comment="Agreement was not concluded",
				effective_date=date(2026, 8, 18),
				evidence=("Project Document/CANCEL-0001",),
			),
			target_legal_status=LegalStatus.CANCELLED,
			target_execution_status=ExecutionStatus.STOPPED,
		)
		self.assertEqual(uow.states[PROJECT], result.state)
		self.assertEqual(len(uow.events), 2)
		self.assertEqual(
			{event.correlation_id for _, event in uow.events},
			{"corr-service-001"},
		)
		self.assertEqual(uow.calls, ["enter", "lock", "save", "audit", "commit"])

	def test_audit_failure_rolls_state_back(self) -> None:
		initial = LifecycleState()
		uow = MemoryUnitOfWork(initial)
		uow.fail_audit = True
		with self.assertRaisesRegex(RuntimeError, "audit insert failure"):
			apply_lifecycle_transition(
				uow,
				PROJECT,
				context(),
				target_legal_status=LegalStatus.ON_APPROVAL,
			)
		self.assertEqual(uow.states[PROJECT], initial)
		self.assertEqual(uow.events, [])
		self.assertEqual(uow.calls, ["enter", "lock", "save", "audit", "rollback"])

	def test_policy_failure_writes_nothing_and_rolls_back(self) -> None:
		uow = MemoryUnitOfWork(LifecycleState())
		with self.assertRaises(LifecycleTransitionError):
			apply_lifecycle_transition(
				uow,
				PROJECT,
				context(),
				target_legal_status=LegalStatus.TERMINATED,
			)
		self.assertEqual(uow.states[PROJECT], LifecycleState())
		self.assertEqual(uow.events, [])
		self.assertEqual(uow.calls, ["enter", "lock", "rollback"])

	def test_suspend_and_resume_use_locked_current_state(self) -> None:
		uow = MemoryUnitOfWork(
			LifecycleState(LegalStatus.IN_FORCE, ExecutionStatus.ACTIVE)
		)
		suspended = suspend_project_execution(
			uow,
			PROJECT,
			context(reason="Safety hold", effective_date=date(2026, 8, 18)),
		)
		self.assertEqual(
			suspended.state.suspended_from_status,
			ExecutionStatus.ACTIVE,
		)
		resumed = resume_project_execution(uow, PROJECT, context())
		self.assertEqual(
			resumed.state,
			LifecycleState(LegalStatus.IN_FORCE, ExecutionStatus.ACTIVE),
		)
		self.assertEqual(uow.calls.count("lock"), 2)

	def test_blank_project_name_is_rejected_before_transaction(self) -> None:
		uow = MemoryUnitOfWork(LifecycleState())
		with self.assertRaisesRegex(LifecycleTransitionError, "service_project"):
			apply_lifecycle_transition(
				uow,
				"  ",
				context(),
				target_legal_status=LegalStatus.ON_APPROVAL,
			)
		self.assertEqual(uow.calls, [])


if __name__ == "__main__":
	unittest.main()
