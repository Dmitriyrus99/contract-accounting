"""Idempotently install the source-controlled official 2026 calendar revision."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import frappe
from frappe import _

from contract_accounting.infrastructure.calendar_registry import calendar_from_document
from contract_accounting.infrastructure.deadline_guard import CALENDAR_FIXTURE_WRITE_FLAG

FIXTURE_PATH = Path(__file__).with_name("calendar_fixtures") / "ru_5d_2026_v1.json"


def ensure_production_calendar_fixture() -> None:
    payload: dict[str, Any] = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    for row in payload["days"]:
        row.setdefault("work_start_time", "00:00:00")
        row.setdefault("work_end_time", "00:00:00")
    name = str(payload["revision_key"])
    previous = frappe.flags.get(CALENDAR_FIXTURE_WRITE_FLAG)
    frappe.flags[CALENDAR_FIXTURE_WRITE_FLAG] = True
    try:
        candidate = frappe.get_doc(payload)
        if not frappe.db.exists("Ferum Calendar Revision", name):
            candidate.insert(ignore_permissions=True)
            return
        candidate.set("__islocal", True)
        candidate.run_method("validate")
        existing = frappe.get_doc("Ferum Calendar Revision", name)
        calendar_from_document(existing)
        if existing.calendar_hash != candidate.calendar_hash:
            frappe.throw(
                _("Versioned calendar fixture hash changed in-place; create a new revision."),
                frappe.ValidationError,
            )
    finally:
        frappe.flags[CALENDAR_FIXTURE_WRITE_FLAG] = previous
