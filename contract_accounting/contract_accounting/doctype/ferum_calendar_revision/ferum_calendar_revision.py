"""Immutable, source-traceable production calendar revision."""

from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from contract_accounting.domain.deadline import (
    DeadlineRuleError,
    calendar_configuration_hash,
)
from contract_accounting.infrastructure.calendar_registry import (
    calendar_day_counts,
    calendar_from_document,
)
from contract_accounting.infrastructure.deadline_guard import CALENDAR_FIXTURE_WRITE_FLAG


class FerumCalendarRevision(Document):
    def before_insert(self) -> None:
        if not frappe.flags.get(CALENDAR_FIXTURE_WRITE_FLAG):
            frappe.throw(
                _("Calendar Revision создаётся только versioned typed importer."),
                frappe.PermissionError,
            )

    def validate(self) -> None:
        if not self.is_new():
            frappe.throw(
                _("Published Calendar Revision неизменяема; создайте новую revision."),
                frappe.PermissionError,
            )
        self._validate_identity()
        try:
            calendar = calendar_from_document(self, verify_hash=False)
        except DeadlineRuleError as exc:
            frappe.throw(_("Некорректная Calendar Revision: {0}.").format(str(exc)))
            raise AssertionError from exc
        working, nonworking, shortened = calendar_day_counts(calendar)
        if (working, nonworking, shortened) != (
            self.expected_working_days,
            self.expected_nonworking_days,
            self.expected_shortened_days,
        ):
            frappe.throw(
                _("Calendar count verification failed: {0}/{1}/{2}.").format(
                    working, nonworking, shortened
                )
            )
        self.calendar_hash = calendar_configuration_hash(calendar)

    def on_trash(self) -> None:
        frappe.throw(_("Удаление Calendar Revision запрещено."), frappe.PermissionError)

    def _validate_identity(self) -> None:
        year = int(self.calendar_year)
        if year < 2000 or year > 2100:
            frappe.throw(_("Calendar year вне поддерживаемого диапазона."))
        if getdate(self.valid_from) != date(year, 1, 1):
            frappe.throw(_("Calendar valid_from должен быть первым днём года."))
        if getdate(self.valid_until) != date(year, 12, 31):
            frappe.throw(_("Calendar valid_until должен быть последним днём года."))
        expected_key = f"{self.calendar_code}-{self.revision}"
        if self.revision_key != expected_key:
            frappe.throw(_("Calendar revision_key должен быть {0}.").format(expected_key))
        seen = set()
        for row in self.days:
            day = getdate(row.calendar_date)
            if day.year != year or day in seen:
                frappe.throw(_("Calendar exception date вне года или дублируется."))
            seen.add(day)
            if row.day_type == "Shortened" and not row.work_end_time:
                frappe.throw(_("Shortened day требует work_end_time."))
            if row.day_type != "Shortened" and (
                _has_explicit_time(row.work_start_time) or _has_explicit_time(row.work_end_time)
            ):
                frappe.throw(
                    _("Индивидуальное окно разрешено только Shortened day: {0}, {1}, {2}.").format(
                        row.calendar_date, row.work_start_time, row.work_end_time
                    )
                )


def on_doctype_update() -> None:
    frappe.db.add_unique(
        "Ferum Calendar Revision", ["calendar_code", "revision"], "ca_calendar_revision_uniq"
    )
    frappe.db.add_index("Ferum Calendar Revision", ["calendar_year", "status"])


def _has_explicit_time(value: object) -> bool:
    return str(value or "") not in {"", "0:00:00", "00:00:00"}
