"""Transactional CA-03 plan-to-fact commands."""

from __future__ import annotations

from typing import Final

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate

from contract_accounting.contract_accounting.doctype.ferum_contract_obligation.ferum_contract_obligation import (
	_rules_from_document,
)
from contract_accounting.domain.obligation import preview_occurrences

OBLIGATION_DOCTYPE: Final[str] = "Ferum Contract Obligation"
SCHEDULE_DOCTYPE: Final[str] = "Ferum Maintenance Schedule"
VISIT_DOCTYPE: Final[str] = "Ferum Maintenance Visit"
_PLAN_ROLES: Final[frozenset[str]] = frozenset(
	{"Руководитель проектов", "System Manager"}
)


@frappe.whitelist(methods=["POST"])
def generate_planned_visits(
	obligation_name: str,
	horizon_start: str,
	horizon_end: str,
) -> dict[str, object]:
	"""Idempotently materialize one Schedule and one primary Visit per period key."""

	_require_role(_PLAN_ROLES, "plan generation")
	frappe.db.sql(
		f"SELECT name FROM `tab{OBLIGATION_DOCTYPE}` WHERE name=%s FOR UPDATE",
		(obligation_name,),
	)
	obligation = frappe.get_doc(OBLIGATION_DOCTYPE, obligation_name)
	obligation.check_permission("write")
	if obligation.status != "Active":
		frappe.throw(_("Plan generation requires Active Obligation."))
	occurrences = preview_occurrences(
		effective_from=getdate(obligation.effective_from),
		effective_to=getdate(obligation.effective_to) if obligation.effective_to else None,
		horizon_start=getdate(horizon_start),
		horizon_end=getdate(horizon_end),
		rules=_rules_from_document(obligation),
	)
	items: list[dict[str, object]] = []
	created_schedule_count = 0
	created_visit_count = 0
	for occurrence in occurrences:
		schedule = _get_or_create_schedule(obligation, occurrence)
		if schedule.flags.get("ca03_created"):
			created_schedule_count += 1
		visit = _get_or_create_primary_visit(obligation, schedule)
		if visit.flags.get("ca03_created"):
			created_visit_count += 1
		if not schedule.generated_visit:
			schedule.generated_visit = visit.name
			schedule.status = "Visit Generated"
			schedule.save(ignore_permissions=True)
		items.append(
			{
				"period_key": occurrence.period_key,
				"schedule": schedule.name,
				"visit": visit.name,
				"visit_status": visit.status,
			}
		)
	return {
		"obligation": obligation.name,
		"created_schedules": created_schedule_count,
		"created_visits": created_visit_count,
		"items": items,
	}


@frappe.whitelist(methods=["POST"])
def create_replacement_visit(cancelled_visit: str) -> dict[str, str]:
	"""Create the single explicit coverage replacement for a cancelled primary visit."""

	_require_role(_PLAN_ROLES, "replacement planning")
	frappe.db.sql(
		f"SELECT name FROM `tab{VISIT_DOCTYPE}` WHERE name=%s FOR UPDATE",
		(cancelled_visit,),
	)
	original = frappe.get_doc(VISIT_DOCTYPE, cancelled_visit)
	original.check_permission("write")
	if original.status != "Cancelled":
		frappe.throw(_("Replacement requires Cancelled Visit."))
	existing = frappe.db.exists(VISIT_DOCTYPE, {"replacement_for": original.name})
	if existing:
		return {"original": original.name, "replacement": existing, "created": "0"}
	replacement = frappe.copy_doc(original)
	replacement.name = None
	replacement.status = "Planned"
	replacement.actual_start = None
	replacement.actual_end = None
	replacement.work_result = None
	replacement.checklist = []
	replacement.evidence = []
	replacement.visit_report = None
	replacement.recommendations = None
	replacement.review_status = "Pending"
	replacement.reviewed_by = None
	replacement.reviewed_on = None
	replacement.acceptance_status = "Pending"
	replacement.accepted_by = None
	replacement.accepted_on = None
	replacement.billing_eligible = 0
	replacement.cancellation_reason = None
	replacement.replacement_for = original.name
	replacement.generation_key = f"{original.generation_key}:replacement"
	replacement.insert(ignore_permissions=True)
	return {"original": original.name, "replacement": replacement.name, "created": "1"}


@frappe.whitelist(methods=["POST"])
def change_visit_status(
	visit_name: str,
	target_status: str,
	actual_start: str | None = None,
	actual_end: str | None = None,
	cancellation_reason: str | None = None,
) -> dict[str, str | None]:
	document = frappe.get_doc(VISIT_DOCTYPE, visit_name)
	document.check_permission("write")
	document.status = target_status
	if actual_start is not None:
		document.actual_start = get_datetime(actual_start)
	if actual_end is not None:
		document.actual_end = get_datetime(actual_end)
	if cancellation_reason is not None:
		document.cancellation_reason = cancellation_reason
	document.save()
	return _visit_state(document)


@frappe.whitelist(methods=["POST"])
def review_visit(visit_name: str, decision: str) -> dict[str, str | None]:
	document = frappe.get_doc(VISIT_DOCTYPE, visit_name)
	document.check_permission("write")
	document.review_status = decision
	document.save()
	return _visit_state(document)


@frappe.whitelist(methods=["POST"])
def accept_visit(visit_name: str, decision: str) -> dict[str, str | None]:
	document = frappe.get_doc(VISIT_DOCTYPE, visit_name)
	document.check_permission("write")
	document.acceptance_status = decision
	document.save()
	return _visit_state(document)


@frappe.whitelist()
def get_execution_trace(schedule_name: str) -> dict[str, object]:
	"""Return the exact obligation→schedule→visit trace and plan/fact deviation."""

	schedule = frappe.get_doc(SCHEDULE_DOCTYPE, schedule_name)
	schedule.check_permission("read")
	visits = frappe.get_all(
		VISIT_DOCTYPE,
		filters={"maintenance_schedule": schedule.name},
		fields=[
			"name",
			"status",
			"review_status",
			"acceptance_status",
			"planned_date",
			"actual_start",
			"actual_end",
			"replacement_for",
		],
		order_by="creation asc",
	)
	rows: list[dict[str, object]] = []
	for visit in visits:
		deviation_days = None
		if visit.actual_start:
			deviation_days = (
				get_datetime(visit.actual_start).date() - getdate(visit.planned_date)
			).days
		rows.append({**dict(visit), "start_deviation_days": deviation_days})
	return {
		"service_project": schedule.service_project,
		"contract_obligation": schedule.contract_obligation,
		"schedule": schedule.name,
		"period_key": schedule.period_key,
		"planned_date": str(schedule.planned_date),
		"visits": rows,
	}


def _get_or_create_schedule(obligation, occurrence):
	existing = frappe.db.exists(
		SCHEDULE_DOCTYPE,
		{"contract_obligation": obligation.name, "period_key": occurrence.period_key},
	)
	if existing:
		return frappe.get_doc(SCHEDULE_DOCTYPE, existing)
	document = frappe.get_doc(
		{
			"doctype": SCHEDULE_DOCTYPE,
			"service_project": obligation.service_project,
			"contract_obligation": obligation.name,
			"project_object": obligation.project_object,
			"object_system": obligation.object_system,
			"work_type": obligation.work_type,
			"period_key": occurrence.period_key,
			"planned_date": occurrence.planned_date,
			"window_start": occurrence.window_start,
			"window_end": occurrence.window_end,
			"due_date": occurrence.due_date,
		}
	).insert(ignore_permissions=True)
	document.flags.ca03_created = True
	return document


def _get_or_create_primary_visit(obligation, schedule):
	generation_key = f"{obligation.name}:{schedule.period_key}"
	existing = frappe.db.exists(VISIT_DOCTYPE, {"generation_key": generation_key})
	if existing:
		return frappe.get_doc(VISIT_DOCTYPE, existing)
	document = frappe.get_doc(
		{
			"doctype": VISIT_DOCTYPE,
			"service_project": obligation.service_project,
			"contract_obligation": obligation.name,
			"maintenance_schedule": schedule.name,
			"project_object": obligation.project_object,
			"object_system": obligation.object_system,
			"period_key": schedule.period_key,
			"planned_date": schedule.planned_date,
			"window_start": schedule.window_start,
			"window_end": schedule.window_end,
			"generation_key": generation_key,
		}
	).insert(ignore_permissions=True)
	document.flags.ca03_created = True
	return document


def _visit_state(document) -> dict[str, str | None]:
	return {
		"name": document.name,
		"status": document.status,
		"review_status": document.review_status,
		"acceptance_status": document.acceptance_status,
	}


def _require_role(allowed: frozenset[str], operation: str) -> None:
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles(frappe.session.user)).intersection(allowed):
		frappe.throw(_("Недостаточно прав: {0}.").format(operation), frappe.PermissionError)
