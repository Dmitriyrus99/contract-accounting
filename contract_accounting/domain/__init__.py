"""Pure domain policies shared by server-side adapters."""

from contract_accounting.domain.lifecycle import (
	EXECUTION_TRANSITIONS,
	LEGAL_TRANSITIONS,
	ExecutionStatus,
	LegalStatus,
	LifecycleAuditEvent,
	LifecycleState,
	LifecycleTransitionError,
	TransitionContext,
	TransitionResult,
	can_create_new_execution,
	is_execution_transition_allowed,
	is_legal_transition_allowed,
	resume_execution,
	suspend_execution,
	transition,
)

__all__ = [
	"EXECUTION_TRANSITIONS",
	"LEGAL_TRANSITIONS",
	"ExecutionStatus",
	"LegalStatus",
	"LifecycleAuditEvent",
	"LifecycleState",
	"LifecycleTransitionError",
	"TransitionContext",
	"TransitionResult",
	"can_create_new_execution",
	"is_execution_transition_allowed",
	"is_legal_transition_allowed",
	"resume_execution",
	"suspend_execution",
	"transition",
]
