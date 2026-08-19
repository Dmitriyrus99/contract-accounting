"""Frappe adapter for selecting and verifying immutable DP-05 calendars."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import get_datetime, get_time, getdate

from contract_accounting.domain.deadline import (
    CalendarSnapshot,
    DeadlineRuleError,
    calendar_configuration_hash,
)


@dataclass(frozen=True, slots=True)
class ResolvedCalendar:
    calendar: CalendarSnapshot
    assignment_name: str
    revision_name: str
    scope_type: str


def calendar_from_document(document: Any, *, verify_hash: bool = True) -> CalendarSnapshot:
    holidays: set[date] = set()
    working_days: set[date] = set()
    shortened_days: list[tuple[date, time]] = []
    for row in document.get("days") or []:
        day = getdate(row.calendar_date)
        if row.day_type == "Holiday":
            holidays.add(day)
        elif row.day_type == "Working":
            working_days.add(day)
        elif row.day_type == "Shortened":
            working_days.add(day)
            shortened_days.append((day, _time(row.work_end_time)))
        else:
            raise DeadlineRuleError(f"unsupported calendar day type: {row.day_type}")
    snapshot = CalendarSnapshot(
        calendar_id=str(document.calendar_code),
        timezone=str(document.timezone),
        revision=str(document.revision),
        calendar_hash=str(document.calendar_hash or "").lower(),
        holidays=frozenset(holidays),
        working_days=frozenset(working_days),
        shortened_days=tuple(shortened_days),
        weekend_days=frozenset(
            int(value.strip()) for value in str(document.weekend_days).split(",") if value.strip()
        ),
        work_start_time=_time(document.work_start_time),
        work_end_time=_time(document.work_end_time),
        cutoff_time=_time(document.cutoff_time),
        after_cutoff_policy=str(document.after_cutoff_policy),
        valid_from=getdate(document.valid_from),
        valid_until=getdate(document.valid_until),
    )
    if verify_hash and snapshot.calendar_hash:
        unhashed = replace(snapshot, calendar_hash="")
        if calendar_configuration_hash(unhashed) != snapshot.calendar_hash:
            raise DeadlineRuleError("calendar configuration hash mismatch")
    return snapshot


def resolve_calendar(service_project: str, triggered_at: str | datetime) -> ResolvedCalendar:
    project = frappe.get_doc("Ferum Service Project", service_project)
    project.check_permission("read")
    trigger = get_datetime(triggered_at)
    year = trigger.year
    filters = {
        "service_project": project.name,
        "calendar_year": year,
        "scope_type": "Contract",
        "status": "Active",
    }
    assignment_name = frappe.db.get_value(
        "Ferum Calendar Assignment", filters, "name", order_by="assigned_at desc"
    )
    if assignment_name:
        scope_type = "Contract"
    else:
        assignment_name = frappe.db.get_value(
            "Ferum Calendar Assignment",
            {
                "company": project.company,
                "calendar_year": year,
                "scope_type": "Company",
                "status": "Active",
            },
            "name",
            order_by="assigned_at desc",
        )
        scope_type = "Company"
    if not assignment_name:
        frappe.throw(
            _("Для Company/Contract не назначена published calendar revision на {0} год.").format(
                year
            )
        )
    assignment = frappe.get_doc("Ferum Calendar Assignment", assignment_name)
    revision = frappe.get_doc("Ferum Calendar Revision", assignment.calendar_revision)
    if revision.status != "Published":
        frappe.throw(_("Назначенная calendar revision не Published."))
    try:
        calendar = calendar_from_document(revision)
    except DeadlineRuleError as exc:
        frappe.throw(
            _("Calendar revision не прошла hash/config verification: {0}.").format(str(exc))
        )
        raise AssertionError from exc
    if revision.calendar_year != year:
        frappe.throw(_("Calendar assignment не соответствует году source datetime."))
    return ResolvedCalendar(
        calendar=calendar,
        assignment_name=assignment.name,
        revision_name=revision.name,
        scope_type=scope_type,
    )


def calendar_day_counts(calendar: CalendarSnapshot) -> tuple[int, int, int]:
    if calendar.valid_from is None or calendar.valid_until is None:
        raise DeadlineRuleError("calendar validity is required for count verification")
    current = calendar.valid_from
    working = 0
    nonworking = 0
    while current <= calendar.valid_until:
        if current not in calendar.holidays and (
            current in calendar.working_days or current.weekday() not in calendar.weekend_days
        ):
            working += 1
        else:
            nonworking += 1
        current += timedelta(days=1)
    return working, nonworking, len(calendar.shortened_days)


def _time(value: Any) -> time:
    parsed = get_time(value)
    if isinstance(parsed, time):
        return parsed
    return time(parsed.seconds // 3600, (parsed.seconds % 3600) // 60, parsed.seconds % 60)
