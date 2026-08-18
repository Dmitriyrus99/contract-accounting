"""Transactional application boundary for CA-01 lifecycle commands.

The concrete Frappe adapter must implement :class:`LifecycleUnitOfWork` with a
row lock and one database transaction. This module deliberately performs no
implicit commit: an exception from state or audit persistence must escape the
context manager so the adapter can roll the whole transaction back.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from contract_accounting.domain.lifecycle import (
	ExecutionStatus,
	LegalStatus,
	LifecycleAuditEvent,
	LifecycleState,
	LifecycleTransitionError,
	TransitionContext,
	TransitionResult,
	resume_execution,
	suspend_execution,
	transition,
)


class LifecycleUnitOfWork(Protocol):
	"""Persistence port required by lifecycle application commands."""

	def __enter__(self) -> Self:
		"""Start a transaction and return this unit of work."""

	def __exit__(
		self,
		exc_type: type[BaseException] | None,
		exc_value: BaseException | None,
		traceback: TracebackType | None,
	) -> bool | None:
		"""Commit on success or roll back when an exception escapes."""

	def lock_state(self, service_project: str) -> LifecycleState:
		"""Load the current projection while holding a row-level write lock."""

	def save_state(self, service_project: str, state: LifecycleState) -> None:
		"""Persist the new projection without committing the transaction."""

	def append_audit_events(
		self,
		service_project: str,
		events: tuple[LifecycleAuditEvent, ...],
	) -> None:
		"""Append immutable events without committing the transaction."""


def apply_lifecycle_transition(
	uow: LifecycleUnitOfWork,
	service_project: str,
	context: TransitionContext,
	*,
	target_legal_status: LegalStatus | None = None,
	target_execution_status: ExecutionStatus | None = None,
	documented_termination_completion_exception: bool = False,
) -> TransitionResult:
	"""Apply a dual-axis transition under one persistence transaction."""

	project_name = _required_project_name(service_project)
	with uow:
		current = uow.lock_state(project_name)
		result = transition(
			current,
			context,
			target_legal_status=target_legal_status,
			target_execution_status=target_execution_status,
			documented_termination_completion_exception=(
				documented_termination_completion_exception
			),
		)
		uow.save_state(project_name, result.state)
		uow.append_audit_events(project_name, result.audit_events)
		return result


def suspend_project_execution(
	uow: LifecycleUnitOfWork,
	service_project: str,
	context: TransitionContext,
) -> TransitionResult:
	"""Suspend execution under the same atomic state/audit boundary."""

	project_name = _required_project_name(service_project)
	with uow:
		current = uow.lock_state(project_name)
		result = suspend_execution(current, context)
		uow.save_state(project_name, result.state)
		uow.append_audit_events(project_name, result.audit_events)
		return result


def resume_project_execution(
	uow: LifecycleUnitOfWork,
	service_project: str,
	context: TransitionContext,
) -> TransitionResult:
	"""Resume execution to its persisted predecessor in one transaction."""

	project_name = _required_project_name(service_project)
	with uow:
		current = uow.lock_state(project_name)
		result = resume_execution(current, context)
		uow.save_state(project_name, result.state)
		uow.append_audit_events(project_name, result.audit_events)
		return result


def _required_project_name(service_project: str) -> str:
	project_name = service_project.strip()
	if not project_name:
		raise LifecycleTransitionError("service_project is required")
	return project_name
