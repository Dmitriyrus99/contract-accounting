"""Pure, fail-closed DP-05 deadline calculation over an immutable calendar."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ALGORITHM_VERSION = "dp05-v1"


class DeadlineRuleError(ValueError):
    """Raised when a deadline cannot be calculated deterministically."""


@dataclass(frozen=True, slots=True)
class CalendarSnapshot:
    timezone: str
    revision: str
    holidays: frozenset[date] = frozenset()
    weekend_days: frozenset[int] = frozenset({5, 6})
    cutoff_time: time = time(19, 0)
    after_cutoff_policy: str = "Next Business Day"
    calendar_id: str = "explicit"
    calendar_hash: str = ""
    work_start_time: time = time(8, 0)
    work_end_time: time = time(19, 0)
    working_days: frozenset[date] = frozenset()
    shortened_days: tuple[tuple[date, time], ...] = ()
    valid_from: date | None = None
    valid_until: date | None = None

    def __post_init__(self) -> None:
        if not self.revision.strip():
            raise DeadlineRuleError("calendar revision is required")
        if not self.calendar_id.strip():
            raise DeadlineRuleError("calendar id is required")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise DeadlineRuleError(f"unknown timezone: {self.timezone}") from exc
        if not self.weekend_days.issubset(set(range(7))):
            raise DeadlineRuleError("weekend days must be in range 0..6")
        if self.after_cutoff_policy not in {"Same Day", "Next Business Day"}:
            raise DeadlineRuleError("unsupported after-cutoff policy")
        if self.work_start_time >= self.work_end_time:
            raise DeadlineRuleError("working window start must be before end")
        if self.cutoff_time > self.work_end_time:
            raise DeadlineRuleError("cut-off cannot be after working window end")
        if self.valid_from and self.valid_until and self.valid_from > self.valid_until:
            raise DeadlineRuleError("calendar validity range is invalid")
        if self.holidays & self.working_days:
            raise DeadlineRuleError("a day cannot be both holiday and working override")
        shortened_dates: set[date] = set()
        for day, end_time in self.shortened_days:
            if day in shortened_dates:
                raise DeadlineRuleError("duplicate shortened-day override")
            if day in self.holidays:
                raise DeadlineRuleError("holiday cannot be shortened working day")
            if not self.work_start_time < end_time <= self.work_end_time:
                raise DeadlineRuleError("shortened-day end is outside working window")
            shortened_dates.add(day)
        for day in self.holidays | self.working_days | shortened_dates:
            _ensure_in_validity(day, self)
        if self.calendar_hash and (
            len(self.calendar_hash) != 64
            or any(character not in "0123456789abcdef" for character in self.calendar_hash.lower())
        ):
            raise DeadlineRuleError("calendar hash must be SHA-256")


@dataclass(frozen=True, slots=True)
class DeadlineRule:
    offset_days: int
    offset_unit: str
    due_time: time = time(19, 0)
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
    anchor_at: datetime
    due_at: datetime
    warning_at: datetime
    escalation_at: datetime
    calendar_id: str
    calendar_revision: str
    calendar_hash: str
    timezone: str
    algorithm_version: str
    snapshot_json: str
    snapshot_hash: str


def calculate_deadline(
    *,
    triggered_at: datetime | None,
    rule: DeadlineRule,
    calendar: CalendarSnapshot,
) -> DeadlineSnapshot:
    """Apply DP-05 cut-offs, working-day roll and immutable snapshot rules."""

    if triggered_at is None:
        raise DeadlineRuleError("trigger event is required")
    tz = ZoneInfo(calendar.timezone)
    local_trigger = (
        triggered_at.replace(tzinfo=tz)
        if triggered_at.tzinfo is None
        else triggered_at.astimezone(tz)
    )
    _ensure_in_validity(local_trigger.date(), calendar)
    anchor_at = _normalize_trigger(local_trigger, calendar)

    if rule.offset_unit == "Business Days":
        due_date = _move_business_days(anchor_at.date(), rule.offset_days, calendar)
        warning_date = _move_business_days(due_date, -rule.warning_days, calendar)
        escalation_date = _move_business_days(due_date, rule.escalation_days, calendar)
    else:
        due_date = _roll_forward_to_business_day(
            anchor_at.date() + timedelta(days=rule.offset_days), calendar
        )
        warning_date = due_date - timedelta(days=rule.warning_days)
        escalation_date = due_date + timedelta(days=rule.escalation_days)

    for result_date in (due_date, warning_date, escalation_date):
        _ensure_in_validity(result_date, calendar)
    due_at = _combine_result(due_date, rule.due_time, calendar, cap_to_work_end=True)
    warning_at = _combine_result(warning_date, rule.due_time, calendar)
    escalation_at = _combine_result(escalation_date, rule.due_time, calendar)
    effective_calendar_hash = calendar.calendar_hash or calendar_configuration_hash(calendar)
    payload = {
        "algorithm_version": ALGORITHM_VERSION,
        "source": {
            "triggered_at": local_trigger.isoformat(),
            "normalized_anchor_at": anchor_at.isoformat(),
        },
        "rule": {
            "offset_days": rule.offset_days,
            "offset_unit": rule.offset_unit,
            "due_time": rule.due_time.isoformat(),
            "warning_days": rule.warning_days,
            "escalation_days": rule.escalation_days,
        },
        "calendar": {
            **calendar_configuration_payload(calendar),
            "calendar_hash": effective_calendar_hash,
        },
        "result": {
            "due_at": due_at.isoformat(),
            "warning_at": warning_at.isoformat(),
            "escalation_at": escalation_at.isoformat(),
        },
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return DeadlineSnapshot(
        triggered_at=local_trigger,
        anchor_at=anchor_at,
        due_at=due_at,
        warning_at=warning_at,
        escalation_at=escalation_at,
        calendar_id=calendar.calendar_id,
        calendar_revision=calendar.revision,
        calendar_hash=effective_calendar_hash,
        timezone=calendar.timezone,
        algorithm_version=ALGORITHM_VERSION,
        snapshot_json=canonical,
        snapshot_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )


def calendar_configuration_payload(calendar: CalendarSnapshot) -> dict[str, object]:
    """Return the canonical configuration portion used for fixture verification."""

    return {
        "calendar_id": calendar.calendar_id,
        "timezone": calendar.timezone,
        "revision": calendar.revision,
        "holidays": sorted(item.isoformat() for item in calendar.holidays),
        "working_days": sorted(item.isoformat() for item in calendar.working_days),
        "shortened_days": [
            {"date": day.isoformat(), "work_end_time": end_time.isoformat()}
            for day, end_time in sorted(calendar.shortened_days)
        ],
        "weekend_days": sorted(calendar.weekend_days),
        "work_start_time": calendar.work_start_time.isoformat(),
        "work_end_time": calendar.work_end_time.isoformat(),
        "cutoff_time": calendar.cutoff_time.isoformat(),
        "after_cutoff_policy": calendar.after_cutoff_policy,
        "valid_from": calendar.valid_from.isoformat() if calendar.valid_from else None,
        "valid_until": calendar.valid_until.isoformat() if calendar.valid_until else None,
    }


def calendar_configuration_hash(calendar: CalendarSnapshot) -> str:
    payload = json.dumps(
        calendar_configuration_payload(calendar),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_trigger(value: datetime, calendar: CalendarSnapshot) -> datetime:
    tz = value.tzinfo
    current = value.date()
    window = _work_window(current, calendar)
    if window is None:
        next_day = _move_business_days(current, 1, calendar)
        next_window = _work_window(next_day, calendar)
        assert next_window is not None
        return datetime.combine(next_day, next_window[0], tz)
    start_time, end_time = window
    local_time = value.timetz().replace(tzinfo=None)
    if local_time < start_time:
        return datetime.combine(current, start_time, tz)
    effective_cutoff = min(calendar.cutoff_time, end_time)
    if local_time > effective_cutoff and calendar.after_cutoff_policy == "Next Business Day":
        next_day = _move_business_days(current, 1, calendar)
        next_window = _work_window(next_day, calendar)
        assert next_window is not None
        return datetime.combine(next_day, next_window[0], tz)
    return value


def _combine_result(
    value: date,
    requested_time: time,
    calendar: CalendarSnapshot,
    *,
    cap_to_work_end: bool = False,
) -> datetime:
    result_time = requested_time
    window = _work_window(value, calendar)
    if cap_to_work_end and window is not None:
        result_time = min(requested_time, window[1])
    return datetime.combine(value, result_time, ZoneInfo(calendar.timezone))


def _move_business_days(value: date, days: int, calendar: CalendarSnapshot) -> date:
    current = value
    if days == 0:
        return _roll_forward_to_business_day(current, calendar)
    direction = 1 if days > 0 else -1
    remaining = abs(days)
    while remaining:
        current += timedelta(days=direction)
        _ensure_in_validity(current, calendar)
        if _is_business_day(current, calendar):
            remaining -= 1
    return current


def move_business_days(value: date, days: int, calendar: CalendarSnapshot) -> date:
    """Public, validity-checked business-day movement for dependent policies."""

    return _move_business_days(value, days, calendar)


def _roll_forward_to_business_day(value: date, calendar: CalendarSnapshot) -> date:
    current = value
    while not _is_business_day(current, calendar):
        current += timedelta(days=1)
        _ensure_in_validity(current, calendar)
    return current


def _is_business_day(value: date, calendar: CalendarSnapshot) -> bool:
    if value in calendar.holidays:
        return False
    return value in calendar.working_days or value.weekday() not in calendar.weekend_days


def _work_window(value: date, calendar: CalendarSnapshot) -> tuple[time, time] | None:
    if not _is_business_day(value, calendar):
        return None
    shortened = dict(calendar.shortened_days).get(value)
    return calendar.work_start_time, shortened or calendar.work_end_time


def _ensure_in_validity(value: date, calendar: CalendarSnapshot) -> None:
    if calendar.valid_from and value < calendar.valid_from:
        raise DeadlineRuleError("date is before calendar validity")
    if calendar.valid_until and value > calendar.valid_until:
        raise DeadlineRuleError("date is after calendar validity")
