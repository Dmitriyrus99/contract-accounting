"""Pure ordering and de-duplication rules for CA-14 work queues."""

from __future__ import annotations

from datetime import datetime
from typing import Any

TERMINAL_STATUSES = frozenset(
	{"Completed", "Not Applicable", "Cancelled", "Closed", "Resolved", "Archived"}
)


def classify_action(
	*, status: str, due_at: datetime | None, as_of: datetime
) -> dict[str, Any]:
	"""Classify time and state independently so blocked/waiting never disappear."""

	terminal = status in TERMINAL_STATUSES
	is_overdue = bool(not terminal and due_at and due_at < as_of)
	if is_overdue:
		time_bucket = "Overdue"
		time_rank = 0
	elif due_at and due_at.date() == as_of.date():
		time_bucket = "Today"
		time_rank = 1
	elif due_at:
		time_bucket = "Upcoming"
		time_rank = 2
	else:
		time_bucket = "Unscheduled"
		time_rank = 3

	if status == "Blocked":
		state_bucket = "Blocked"
		state_rank = 0
	elif status == "Waiting External":
		state_bucket = "Waiting External"
		state_rank = 1
	elif status == "Waiting Approval":
		state_bucket = "Waiting Approval"
		state_rank = 2
	else:
		state_bucket = "Actionable"
		state_rank = 3
	return {
		"time_bucket": time_bucket,
		"state_bucket": state_bucket,
		"is_overdue": is_overdue,
		"time_rank": time_rank,
		"state_rank": state_rank,
	}


def deduplicate_actions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Keep one source operation and merge every ToDo delivery reference into it."""

	selected: dict[str, dict[str, Any]] = {}
	for original in rows:
		row = dict(original)
		key = str(row["canonical_key"])
		row.setdefault("delivery_todos", [])
		current = selected.get(key)
		if current is None:
			selected[key] = row
			continue
		merged_todos = sorted(
			set(current.get("delivery_todos", []))
			| set(row.get("delivery_todos", []))
		)
		if int(row.get("source_rank", 99)) < int(current.get("source_rank", 99)):
			row["delivery_todos"] = merged_todos
			selected[key] = row
		else:
			current["delivery_todos"] = merged_todos
	return list(selected.values())


def sort_actions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Stable priority: overdue, today, upcoming, unscheduled; then state and ID."""

	return sorted(
		rows,
		key=lambda row: (
			int(row["time_rank"]),
			int(row["state_rank"]),
			str(row.get("due_at") or "9999-12-31T23:59:59"),
			str(row.get("service_project") or ""),
			str(row["canonical_key"]),
		),
	)


def progress(completed: int, total: int) -> int:
	"""Return an integer percentage with a defined empty-state value."""

	if total <= 0:
		return 0
	return round(completed * 100 / total)
