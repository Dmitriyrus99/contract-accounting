"""Pure, fail-closed deadline calculation over an explicit calendar snapshot."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class DeadlineRuleError(ValueError):
	"""Raised when a deadline cannot be calculated deterministically."""


@dataclass(frozen=True, slots=True)
class CalendarSnapshot:
	timezone: str
	revision: str
	holidays: frozenset[date] = frozenset()
	weekend_days: frozenset[int] = frozenset({5, 6})
	cutoff_time: time = time(23, 59, 59)
	after_cutoff_policy: str = "Same Day"

	def __post_init__(self) -> None:
		if not self.revision.strip():
			raise DeadlineRuleError("calendar revision is required")
		try:
			ZoneInfo(self.timezone)
		except ZoneInfoNotFoundError as exc:
			raise DeadlineRuleError(f"unknown timezone: {self.timezone}") from exc
		if not self.weekend_days.issubset(set(range(7))):
			raise DeadlineRuleError("weekend days must be in range 0..6")
		if self.after_cutoff_policy not in {"Same Day", "Next Business Day"}:
			raise DeadlineRuleError("unsupported after-cutoff policy")


@dataclass(frozen=True, slots=True)
class DeadlineRule:
	offset_days: int
	offset_unit: str
	due_time: time = time(23, 59, 59)
	warning_days: int = 0
	escalation_days: int = 0

	def __post_init__(self) -> None:
		if self.offset_days < 0 or self.warning_days < 0 or self.escalation_days < 0:
			raise DeadlineRuleError("deadline offsets cannot be negative")
		if self.offset_unit not in {"Calendar Days", "Business Days"}:
			raise DeadlineRuleError(f"unsupported offset unit: {self.offset_unit}")


@dataclass(frozen=True, slots=True)
class DeadlineSnapshot:
	triggered_at: datetime
	due_at: datetime
	warning_at: datetime
	escalation_at: datetime
	calendar_revision: str
	timezone: str
	snapshot_hash: str


def calculate_deadline(
	*,
	triggered_at: datetime | None,
	rule: DeadlineRule,
	calendar: CalendarSnapshot,
) -> DeadlineSnapshot:
	"""Calculate timestamps only when trigger, rule and calendar revision are explicit."""

	if triggered_at is None:
		raise DeadlineRuleError("trigger event is required")
	tz = ZoneInfo(calendar.timezone)
	local_trigger = (
		triggered_at.replace(tzinfo=tz)
		if triggered_at.tzinfo is None
		else triggered_at.astimezone(tz)
	)
	anchor = local_trigger.date()
	if (
		local_trigger.timetz().replace(tzinfo=None) > calendar.cutoff_time
		and calendar.after_cutoff_policy == "Next Business Day"
	):
		anchor = _move_business_days(anchor, 1, calendar)

	if rule.offset_unit == "Business Days":
		due_date = _move_business_days(anchor, rule.offset_days, calendar, roll_start=True)
		warning_date = _move_business_days(due_date, -rule.warning_days, calendar)
		escalation_date = _move_business_days(due_date, rule.escalation_days, calendar)
	else:
		due_date = anchor + timedelta(days=rule.offset_days)
		warning_date = due_date - timedelta(days=rule.warning_days)
		escalation_date = due_date + timedelta(days=rule.escalation_days)

	due_at = datetime.combine(due_date, rule.due_time, tz)
	warning_at = datetime.combine(warning_date, rule.due_time, tz)
	escalation_at = datetime.combine(escalation_date, rule.due_time, tz)
	payload = {
		"triggered_at": local_trigger.isoformat(),
		"rule": {
			"offset_days": rule.offset_days,
			"offset_unit": rule.offset_unit,
			"due_time": rule.due_time.isoformat(),
			"warning_days": rule.warning_days,
			"escalation_days": rule.escalation_days,
		},
		"calendar": {
			"timezone": calendar.timezone,
			"revision": calendar.revision,
			"holidays": sorted(item.isoformat() for item in calendar.holidays),
			"weekend_days": sorted(calendar.weekend_days),
			"cutoff_time": calendar.cutoff_time.isoformat(),
			"after_cutoff_policy": calendar.after_cutoff_policy,
		},
		"result": {
			"due_at": due_at.isoformat(),
			"warning_at": warning_at.isoformat(),
			"escalation_at": escalation_at.isoformat(),
		},
	}
	canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
	return DeadlineSnapshot(
		triggered_at=local_trigger,
		due_at=due_at,
		warning_at=warning_at,
		escalation_at=escalation_at,
		calendar_revision=calendar.revision,
		timezone=calendar.timezone,
		snapshot_hash=hashlib.sha256(canonical.encode()).hexdigest(),
	)


def _move_business_days(
	value: date,
	days: int,
	calendar: CalendarSnapshot,
	*,
	roll_start: bool = False,
) -> date:
	current = value
	if roll_start and days == 0 and not _is_business_day(current, calendar):
		days = 1
	direction = 1 if days >= 0 else -1
	remaining = abs(days)
	while remaining:
		current += timedelta(days=direction)
		if _is_business_day(current, calendar):
			remaining -= 1
	return current


def _is_business_day(value: date, calendar: CalendarSnapshot) -> bool:
	return value.weekday() not in calendar.weekend_days and value not in calendar.holidays
