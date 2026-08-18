"""Pure recurrence preview for CA-02 contract obligations."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta


class ObligationRuleError(ValueError):
	"""Raised when an obligation recurrence cannot be evaluated safely."""


@dataclass(frozen=True, slots=True)
class RecurrenceRule:
	frequency: str
	interval: int = 1
	due_offset_days: int = 0
	window_before_days: int = 0
	window_after_days: int = 0
	generation_horizon_days: int = 365

	def __post_init__(self) -> None:
		if self.interval < 1:
			raise ObligationRuleError("recurrence interval must be at least 1")
		if self.window_before_days < 0 or self.window_after_days < 0:
			raise ObligationRuleError("recurrence window cannot be negative")
		if self.generation_horizon_days < 1:
			raise ObligationRuleError("generation horizon must be at least 1 day")
		if self.frequency not in {
			"Daily",
			"Weekly",
			"Monthly",
			"Quarterly",
			"Semiannual",
			"Annual",
		}:
			raise ObligationRuleError(f"unsupported recurrence frequency: {self.frequency}")


@dataclass(frozen=True, slots=True)
class ObligationOccurrence:
	period_key: str
	planned_date: date
	due_date: date
	window_start: date
	window_end: date


def preview_occurrences(
	*,
	effective_from: date,
	effective_to: date | None,
	horizon_start: date,
	horizon_end: date,
	rules: tuple[RecurrenceRule, ...],
) -> tuple[ObligationOccurrence, ...]:
	"""Return deterministic future periods without writing schedule records."""

	if effective_to and effective_from > effective_to:
		raise ObligationRuleError("effective_from cannot be after effective_to")
	if horizon_start > horizon_end:
		raise ObligationRuleError("horizon_start cannot be after horizon_end")
	if not rules:
		raise ObligationRuleError("at least one recurrence rule is required")

	last_date = min(effective_to, horizon_end) if effective_to else horizon_end
	occurrences: dict[str, ObligationOccurrence] = {}
	for rule in rules:
		rule_last_date = min(
			last_date,
			horizon_start + timedelta(days=rule.generation_horizon_days - 1),
		)
		current = effective_from
		iterations = 0
		while current <= rule_last_date:
			iterations += 1
			if iterations > 10000:
				raise ObligationRuleError("recurrence preview exceeds safety limit")
			if current >= horizon_start:
				period_key = current.isoformat()
				candidate = ObligationOccurrence(
					period_key=period_key,
					planned_date=current,
					due_date=current + timedelta(days=rule.due_offset_days),
					window_start=current - timedelta(days=rule.window_before_days),
					window_end=current + timedelta(days=rule.window_after_days),
				)
				existing = occurrences.get(period_key)
				if existing is not None and existing != candidate:
					raise ObligationRuleError(
						f"conflicting recurrence rules for period: {period_key}"
					)
				occurrences.setdefault(period_key, candidate)
			current = _next_date(effective_from, rule, iterations)
	return tuple(occurrences[key] for key in sorted(occurrences))


def _next_date(anchor: date, rule: RecurrenceRule, occurrences_elapsed: int) -> date:
	if rule.frequency == "Daily":
		return anchor + timedelta(days=rule.interval * occurrences_elapsed)
	if rule.frequency == "Weekly":
		return anchor + timedelta(weeks=rule.interval * occurrences_elapsed)
	months = {
		"Monthly": 1,
		"Quarterly": 3,
		"Semiannual": 6,
		"Annual": 12,
	}[rule.frequency]
	return _add_months(anchor, months * rule.interval * occurrences_elapsed)


def _add_months(value: date, months: int) -> date:
	month_index = value.month - 1 + months
	year = value.year + month_index // 12
	month = month_index % 12 + 1
	day = min(value.day, calendar.monthrange(year, month)[1])
	return date(year, month, day)
