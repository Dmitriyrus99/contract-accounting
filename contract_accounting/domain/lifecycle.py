"""Owner-approved dual-status lifecycle policy for CA-01.

This module is intentionally independent of Frappe. A server adapter must load the
current ``Ferum Service Project`` state, call this policy, persist the returned state
and immutable audit events in one database transaction, and reject direct field edits.

Sources:

* ``05_target_model.md`` section 4;
* OQ-CA-003 and OQ-CA-020 in ``08_open_questions.md``;
* ``06_roadmap.md`` CA-01 acceptance criteria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from types import MappingProxyType
from typing import Mapping
from uuid import uuid4


class LifecycleTransitionError(ValueError):
	"""The requested lifecycle operation violates the approved policy."""


class LegalStatus(str, Enum):
	DRAFT = "Draft"
	ON_APPROVAL = "On Approval"
	APPROVED = "Approved"
	SIGNING = "Signing"
	SIGNED = "Signed"
	IN_FORCE = "In Force"
	CANCELLED = "Cancelled"
	TERMINATED = "Terminated"
	EXPIRED = "Expired"


class ExecutionStatus(str, Enum):
	NOT_STARTED = "Not Started"
	LAUNCHING = "Launching"
	ACTIVE = "Active"
	SUSPENDED = "Suspended"
	COMPLETED = "Completed"
	STOPPED = "Stopped"


LEGAL_TRANSITIONS: Mapping[LegalStatus, frozenset[LegalStatus]] = MappingProxyType(
	{
		LegalStatus.DRAFT: frozenset({LegalStatus.ON_APPROVAL, LegalStatus.CANCELLED}),
		LegalStatus.ON_APPROVAL: frozenset(
			{LegalStatus.DRAFT, LegalStatus.APPROVED, LegalStatus.CANCELLED}
		),
		LegalStatus.APPROVED: frozenset(
			{LegalStatus.DRAFT, LegalStatus.SIGNING, LegalStatus.CANCELLED}
		),
		LegalStatus.SIGNING: frozenset(
			{LegalStatus.APPROVED, LegalStatus.SIGNED, LegalStatus.CANCELLED}
		),
		LegalStatus.SIGNED: frozenset({LegalStatus.IN_FORCE, LegalStatus.TERMINATED}),
		LegalStatus.IN_FORCE: frozenset({LegalStatus.TERMINATED, LegalStatus.EXPIRED}),
		LegalStatus.CANCELLED: frozenset(),
		LegalStatus.TERMINATED: frozenset(),
		LegalStatus.EXPIRED: frozenset(),
	}
)

EXECUTION_TRANSITIONS: Mapping[ExecutionStatus, frozenset[ExecutionStatus]] = MappingProxyType(
	{
		ExecutionStatus.NOT_STARTED: frozenset(
			{ExecutionStatus.LAUNCHING, ExecutionStatus.STOPPED}
		),
		ExecutionStatus.LAUNCHING: frozenset(
			{ExecutionStatus.ACTIVE, ExecutionStatus.SUSPENDED, ExecutionStatus.STOPPED}
		),
		ExecutionStatus.ACTIVE: frozenset(
			{ExecutionStatus.SUSPENDED, ExecutionStatus.COMPLETED, ExecutionStatus.STOPPED}
		),
		ExecutionStatus.SUSPENDED: frozenset(
			{ExecutionStatus.LAUNCHING, ExecutionStatus.ACTIVE, ExecutionStatus.STOPPED}
		),
		ExecutionStatus.COMPLETED: frozenset(),
		ExecutionStatus.STOPPED: frozenset(),
	}
)

_PRE_CONTRACT_STATUSES = frozenset(
	{
		LegalStatus.DRAFT,
		LegalStatus.ON_APPROVAL,
		LegalStatus.APPROVED,
		LegalStatus.SIGNING,
	}
)
_TERMINAL_LEGAL_STATUSES = frozenset(
	{LegalStatus.CANCELLED, LegalStatus.TERMINATED, LegalStatus.EXPIRED}
)
_SUSPENDABLE_EXECUTION_STATUSES = frozenset(
	{ExecutionStatus.LAUNCHING, ExecutionStatus.ACTIVE}
)


@dataclass(frozen=True, slots=True)
class LifecycleState:
	"""Persisted lifecycle projection of one Service Project."""

	legal_status: LegalStatus = LegalStatus.DRAFT
	execution_status: ExecutionStatus = ExecutionStatus.NOT_STARTED
	suspended_from_status: ExecutionStatus | None = None
	documented_termination_completion_exception: bool = False

	def __post_init__(self) -> None:
		_validate_state(self)


@dataclass(frozen=True, slots=True)
class TransitionContext:
	"""Evidence written to immutable lifecycle audit events."""

	actor: str
	occurred_at: datetime
	reason: str | None = None
	comment: str | None = None
	effective_date: date | None = None
	evidence: tuple[str, ...] = ()
	termination_basis: str | None = None
	related_document: str | None = None
	correlation_id: str = field(default_factory=lambda: str(uuid4()))

	def __post_init__(self) -> None:
		if not self.actor.strip():
			raise LifecycleTransitionError("actor is required for every lifecycle transition")
		if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
			raise LifecycleTransitionError("occurred_at must be timezone-aware")
		if not self.correlation_id.strip():
			raise LifecycleTransitionError("correlation_id must not be empty")


@dataclass(frozen=True, slots=True)
class LifecycleAuditEvent:
	dimension: str
	from_status: str
	to_status: str
	actor: str
	occurred_at: datetime
	reason: str | None
	comment: str | None
	effective_date: date | None
	evidence: tuple[str, ...]
	termination_basis: str | None
	related_document: str | None
	documented_termination_completion_exception: bool
	correlation_id: str


@dataclass(frozen=True, slots=True)
class TransitionResult:
	state: LifecycleState
	audit_events: tuple[LifecycleAuditEvent, ...]


def is_legal_transition_allowed(source: LegalStatus, target: LegalStatus) -> bool:
	return target in LEGAL_TRANSITIONS[source]


def is_execution_transition_allowed(source: ExecutionStatus, target: ExecutionStatus) -> bool:
	return target in EXECUTION_TRANSITIONS[source]


def can_create_new_execution(legal_status: LegalStatus) -> bool:
	"""Terminal legal states forbid new execution, not closeout/finance activity."""

	return legal_status not in _TERMINAL_LEGAL_STATUSES


def transition(
	state: LifecycleState,
	context: TransitionContext,
	*,
	target_legal_status: LegalStatus | None = None,
	target_execution_status: ExecutionStatus | None = None,
	documented_termination_completion_exception: bool = False,
) -> TransitionResult:
	"""Validate and plan one atomic server-side lifecycle operation.

	The input is immutable. On any error no candidate state or audit event is returned,
	which lets the Frappe adapter fail before performing a database mutation.
	"""

	legal_target = target_legal_status or state.legal_status
	execution_target = target_execution_status or state.execution_status
	legal_changed = legal_target != state.legal_status
	execution_changed = execution_target != state.execution_status
	if not legal_changed and not execution_changed:
		raise LifecycleTransitionError("a lifecycle operation must change at least one dimension")

	if legal_changed and not is_legal_transition_allowed(state.legal_status, legal_target):
		raise LifecycleTransitionError(
			f"legal transition {state.legal_status.value} -> {legal_target.value} is forbidden"
		)
	if execution_changed and not is_execution_transition_allowed(
		state.execution_status, execution_target
	):
		raise LifecycleTransitionError(
			"execution transition "
			f"{state.execution_status.value} -> {execution_target.value} is forbidden"
		)

	if state.execution_status is ExecutionStatus.SUSPENDED and execution_changed:
		if execution_target in _SUSPENDABLE_EXECUTION_STATUSES:
			if execution_target is not state.suspended_from_status:
				raise LifecycleTransitionError(
					"Resume must return to the saved suspended_from_status"
				)

	_validate_required_evidence(legal_target, execution_target, legal_changed, execution_changed, context)

	suspended_from: ExecutionStatus | None
	if execution_target is ExecutionStatus.SUSPENDED:
		if execution_changed:
			suspended_from = state.execution_status
		else:
			suspended_from = state.suspended_from_status
	else:
		suspended_from = None

	candidate = LifecycleState(
		legal_status=legal_target,
		execution_status=execution_target,
		suspended_from_status=suspended_from,
		documented_termination_completion_exception=(
			documented_termination_completion_exception
			if legal_target is LegalStatus.TERMINATED
			and execution_target is ExecutionStatus.COMPLETED
			else False
		),
	)

	events: list[LifecycleAuditEvent] = []
	if legal_changed:
		events.append(
			_make_event(
				"legal_status",
				state.legal_status.value,
				legal_target.value,
				context,
				documented_termination_completion_exception=(
					documented_termination_completion_exception
					and legal_target is LegalStatus.TERMINATED
					and execution_target is ExecutionStatus.COMPLETED
				),
			)
		)
	if execution_changed:
		events.append(
			_make_event(
				"execution_status",
				state.execution_status.value,
				execution_target.value,
				context,
				documented_termination_completion_exception=False,
			)
		)
	return TransitionResult(state=candidate, audit_events=tuple(events))


def suspend_execution(state: LifecycleState, context: TransitionContext) -> TransitionResult:
	"""Suspend Launching or Active execution without changing legal status."""

	if state.execution_status not in _SUSPENDABLE_EXECUTION_STATUSES:
		raise LifecycleTransitionError("only Launching or Active execution can be suspended")
	return transition(state, context, target_execution_status=ExecutionStatus.SUSPENDED)


def resume_execution(state: LifecycleState, context: TransitionContext) -> TransitionResult:
	"""Resume exactly to the persisted Launching/Active predecessor."""

	if state.execution_status is not ExecutionStatus.SUSPENDED:
		raise LifecycleTransitionError("only Suspended execution can be resumed")
	if state.suspended_from_status not in _SUSPENDABLE_EXECUTION_STATUSES:
		raise LifecycleTransitionError("Suspended state has no valid suspended_from_status")
	return transition(
		state,
		context,
		target_execution_status=state.suspended_from_status,
	)


def _validate_state(state: LifecycleState) -> None:
	legal = state.legal_status
	execution = state.execution_status
	if execution is ExecutionStatus.SUSPENDED:
		if state.suspended_from_status not in _SUSPENDABLE_EXECUTION_STATUSES:
			raise LifecycleTransitionError(
				"Suspended requires suspended_from_status = Launching or Active"
			)
	else:
		if state.suspended_from_status is not None:
			raise LifecycleTransitionError(
				"suspended_from_status is allowed only while execution is Suspended"
			)

	if legal in _PRE_CONTRACT_STATUSES:
		_allowed_pair(execution is ExecutionStatus.NOT_STARTED, legal, execution)
	elif legal is LegalStatus.SIGNED:
		allowed = execution in {ExecutionStatus.NOT_STARTED, ExecutionStatus.LAUNCHING}
		allowed = allowed or (
			execution is ExecutionStatus.SUSPENDED
			and state.suspended_from_status is ExecutionStatus.LAUNCHING
		)
		_allowed_pair(allowed, legal, execution)
	elif legal is LegalStatus.IN_FORCE:
		allowed = execution in {
			ExecutionStatus.NOT_STARTED,
			ExecutionStatus.LAUNCHING,
			ExecutionStatus.ACTIVE,
			ExecutionStatus.COMPLETED,
		}
		allowed = allowed or execution is ExecutionStatus.SUSPENDED
		_allowed_pair(allowed, legal, execution)
	elif legal is LegalStatus.CANCELLED:
		_allowed_pair(execution is ExecutionStatus.STOPPED, legal, execution)
	elif legal is LegalStatus.TERMINATED:
		allowed = execution is ExecutionStatus.STOPPED or (
			execution is ExecutionStatus.COMPLETED
			and state.documented_termination_completion_exception
		)
		_allowed_pair(allowed, legal, execution)
	elif legal is LegalStatus.EXPIRED:
		_allowed_pair(
			execution in {ExecutionStatus.COMPLETED, ExecutionStatus.STOPPED}, legal, execution
		)

	if not (
		legal is LegalStatus.TERMINATED and execution is ExecutionStatus.COMPLETED
	) and state.documented_termination_completion_exception:
		raise LifecycleTransitionError(
			"termination completion exception is valid only for Terminated + Completed"
		)


def _allowed_pair(allowed: bool, legal: LegalStatus, execution: ExecutionStatus) -> None:
	if not allowed:
		raise LifecycleTransitionError(
			f"status pair {legal.value} + {execution.value} is forbidden"
		)


def _validate_required_evidence(
	legal_target: LegalStatus,
	execution_target: ExecutionStatus,
	legal_changed: bool,
	execution_changed: bool,
	context: TransitionContext,
) -> None:
	if legal_changed and legal_target in {LegalStatus.CANCELLED, LegalStatus.TERMINATED}:
		_required(context.reason, "reason")
		_required(context.comment, "comment")
		if context.effective_date is None:
			raise LifecycleTransitionError(
				"effective_date is required for Cancelled or Terminated"
			)
		if not context.evidence:
			raise LifecycleTransitionError("evidence is required for Cancelled or Terminated")
	if legal_changed and legal_target is LegalStatus.TERMINATED:
		_required(context.termination_basis, "termination_basis")
		_required(context.related_document, "related_document")
	if execution_changed and execution_target is ExecutionStatus.STOPPED:
		_required(context.reason, "reason")
	if execution_changed and execution_target is ExecutionStatus.SUSPENDED:
		_required(context.reason, "reason")
		if context.effective_date is None:
			raise LifecycleTransitionError("effective_date is required for Suspend")


def _required(value: str | None, fieldname: str) -> None:
	if value is None or not value.strip():
		raise LifecycleTransitionError(f"{fieldname} is required")


def _make_event(
	dimension: str,
	from_status: str,
	to_status: str,
	context: TransitionContext,
	*,
	documented_termination_completion_exception: bool,
) -> LifecycleAuditEvent:
	return LifecycleAuditEvent(
		dimension=dimension,
		from_status=from_status,
		to_status=to_status,
		actor=context.actor,
		occurred_at=context.occurred_at,
		reason=context.reason,
		comment=context.comment,
		effective_date=context.effective_date,
		evidence=context.evidence,
		termination_basis=context.termination_basis,
		related_document=context.related_document,
		documented_termination_completion_exception=(
			documented_termination_completion_exception
		),
		correlation_id=context.correlation_id,
	)
