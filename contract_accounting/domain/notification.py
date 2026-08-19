"""Pure DP-06 threshold and idempotency policy."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

from contract_accounting.domain.deadline import CalendarSnapshot, move_business_days

POLICY_VERSION = "dp06-v1"


class NotificationPolicyError(ValueError):
    """Raised when notification timing cannot be derived deterministically."""


@dataclass(frozen=True, slots=True)
class ThresholdOccurrence:
    code: str
    occurs_at: datetime
    audience: str
    email_mode: str


def threshold_occurrences(
    *,
    due_at: datetime,
    calendar: CalendarSnapshot,
    triggered_at: datetime | None = None,
) -> tuple[ThresholdOccurrence, ...]:
    """Return DP-06 events; percentage thresholds replace unusable −3/−1 events."""

    due = _local(due_at, calendar)
    trigger = _local(triggered_at, calendar) if triggered_at else None
    minus_three = datetime.combine(
        move_business_days(due.date(), -3, calendar),
        time(8, 0),
        ZoneInfo(calendar.timezone),
    )
    minus_one = datetime.combine(
        move_business_days(due.date(), -1, calendar),
        time(8, 0),
        ZoneInfo(calendar.timezone),
    )
    due_morning = datetime.combine(due.date(), time(8, 0), ZoneInfo(calendar.timezone))
    plus_one = datetime.combine(
        move_business_days(due.date(), 1, calendar),
        time(8, 0),
        ZoneInfo(calendar.timezone),
    )

    primary: tuple[ThresholdOccurrence, ...]
    if trigger and minus_three <= trigger:
        if trigger >= due:
            raise NotificationPolicyError("short deadline trigger must precede due time")
        duration = due - trigger
        primary = (
            ThresholdOccurrence("SHORT_50", trigger + duration * 0.5, "RESPONSIBLE_PM", "DIGEST"),
            ThresholdOccurrence(
                "SHORT_80", trigger + duration * 0.8, "RESPONSIBLE_PM", "IMMEDIATE"
            ),
            ThresholdOccurrence("BREACH", due, "RESPONSIBLE_PM_PROCESS", "IMMEDIATE"),
        )
    else:
        primary = (
            ThresholdOccurrence("MINUS_3", minus_three, "RESPONSIBLE_PM", "DIGEST"),
            ThresholdOccurrence("MINUS_1", minus_one, "RESPONSIBLE_PM", "IMMEDIATE"),
            ThresholdOccurrence("DUE_0800", due_morning, "RESPONSIBLE_PM", "IMMEDIATE"),
            ThresholdOccurrence("OVERDUE", due, "RESPONSIBLE_PM_PROCESS", "IMMEDIATE"),
        )
    return (*primary, ThresholdOccurrence("OVERDUE_PLUS_1", plus_one, "DIRECTOR", "IMMEDIATE"))


def delivery_identity(
    *,
    source_key: str,
    due_at: datetime,
    threshold: str,
    recipient: str,
    channel: str,
    occurrence_date: str | None = None,
) -> tuple[str, str]:
    """Return correlation key and per-channel delivery key."""

    correlation_payload = {
        "due_at": due_at.isoformat(),
        "occurrence_date": occurrence_date,
        "policy_version": POLICY_VERSION,
        "recipient": recipient,
        "source_key": source_key,
        "threshold": threshold,
    }
    canonical = json.dumps(
        correlation_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    correlation_key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    delivery_key = hashlib.sha256(f"{correlation_key}:{channel}".encode("utf-8")).hexdigest()
    return correlation_key, delivery_key


def _local(value: datetime, calendar: CalendarSnapshot) -> datetime:
    zone = ZoneInfo(calendar.timezone)
    return value.replace(tzinfo=zone) if value.tzinfo is None else value.astimezone(zone)
