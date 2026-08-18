"""Pure CA-11 process-step transitions, evidence and gate decisions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Final


class ProcessRuleError(ValueError):
	"""Raised when a process command violates the frozen template contract."""


BASE_STEP_STATUSES: Final[tuple[str, ...]] = (
	"Planned",
	"Ready",
	"In Progress",
	"Waiting External",
	"Waiting Approval",
	"Blocked",
	"Completed",
	"Not Applicable",
	"Cancelled",
)
TERMINAL_STEP_STATUSES: Final[frozenset[str]] = frozenset(
	{"Completed", "Not Applicable", "Cancelled"}
)
STEP_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Planned": frozenset({"Ready", "Not Applicable", "Cancelled"}),
	"Ready": frozenset({"In Progress", "Blocked", "Not Applicable", "Cancelled"}),
	"In Progress": frozenset(
		{
			"Waiting External",
			"Waiting Approval",
			"Blocked",
			"Completed",
			"Not Applicable",
			"Cancelled",
		}
	),
	"Waiting External": frozenset(
		{"In Progress", "Waiting Approval", "Blocked", "Completed", "Not Applicable", "Cancelled"}
	),
	"Waiting Approval": frozenset(
		{"In Progress", "Blocked", "Completed", "Not Applicable", "Cancelled"}
	),
	"Blocked": frozenset({"Ready", "In Progress", "Not Applicable", "Cancelled"}),
	"Completed": frozenset(),
	"Not Applicable": frozenset(),
	"Cancelled": frozenset(),
}


@dataclass(frozen=True, slots=True)
class StepDisplayState:
	base_status: str
	is_overdue: bool
	overdue_since: datetime | None
	display_status: str


def validate_step_transition(
	old_status: str,
	new_status: str,
	*,
	reason: str | None = None,
	not_applicable_reason: str | None = None,
	has_required_evidence: bool = False,
	required_evidence_type: str = "None",
) -> None:
	if old_status not in STEP_TRANSITIONS or new_status not in BASE_STEP_STATUSES:
		raise ProcessRuleError("unknown base step status")
	if new_status not in STEP_TRANSITIONS[old_status]:
		raise ProcessRuleError(f"transition is not allowed: {old_status} -> {new_status}")
	if new_status == "Not Applicable" and not str(not_applicable_reason or "").strip():
		raise ProcessRuleError("Not Applicable requires a reason")
	if new_status in {"Blocked", "Waiting External", "Cancelled"} and not str(reason or "").strip():
		raise ProcessRuleError(f"{new_status} requires a reason")
	if (
		new_status == "Completed"
		and required_evidence_type != "None"
		and not has_required_evidence
	):
		raise ProcessRuleError("Completed requires validated completion evidence")


def derive_step_state(
	base_status: str,
	*,
	due_at: datetime | None,
	as_of: datetime | None,
) -> StepDisplayState:
	if base_status not in BASE_STEP_STATUSES:
		raise ProcessRuleError("unknown base step status")
	is_overdue = bool(
		as_of
		and due_at
		and due_at < as_of
		and base_status not in TERMINAL_STEP_STATUSES
	)
	return StepDisplayState(
		base_status=base_status,
		is_overdue=is_overdue,
		overdue_since=due_at if is_overdue else None,
		display_status="Overdue" if is_overdue else base_status,
	)


def failed_blocking_steps(rows: list[dict[str, object]]) -> list[dict[str, object]]:
	return [
		row
		for row in rows
		if bool(row.get("blocking"))
		and row.get("status") not in {"Completed", "Not Applicable"}
	]


def canonical_snapshot(value: object) -> tuple[str, str]:
	serialized = json.dumps(
		value,
		ensure_ascii=False,
		sort_keys=True,
		separators=(",", ":"),
		default=str,
	)
	return serialized, hashlib.sha256(serialized.encode()).hexdigest()
