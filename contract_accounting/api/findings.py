"""Transactional CA-04 Finding commands and read-only exception reports."""

from __future__ import annotations

from typing import Final

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime


FINDING_DOCTYPE: Final[str] = "Ferum Finding"
REQUEST_DOCTYPE: Final[str] = "Ferum Service Request"


@frappe.whitelist(methods=["POST"])
def triage_finding(
	finding_name: str,
	confirmation_status: str,
	decision: str | None = None,
	responsible: str | None = None,
	due_date: str | None = None,
	resolution: str | None = None,
) -> dict[str, object]:
	"""Confirm a Finding for action or reject it as an evidenced false positive."""

	document = frappe.get_doc(FINDING_DOCTYPE, finding_name)
	document.check_permission("write")
	document.confirmation_status = confirmation_status
	if decision is not None:
		document.decision = decision
	if responsible is not None:
		document.responsible = responsible
	if due_date is not None:
		document.due_date = get_datetime(due_date)
	if confirmation_status == "Rejected":
		document.status = "Rejected"
		document.resolution_class = "False Positive"
		document.resolution = resolution
	document.save()
	return _finding_state(document)


@frappe.whitelist(methods=["POST"])
def change_finding_status(
	finding_name: str,
	target_status: str,
	resolution_class: str | None = None,
	resolution: str | None = None,
) -> dict[str, object]:
	"""Advance the independent resolution lifecycle; timestamps are server-owned."""

	document = frappe.get_doc(FINDING_DOCTYPE, finding_name)
	document.check_permission("write")
	document.status = target_status
	if resolution_class is not None:
		document.resolution_class = resolution_class
	if resolution is not None:
		document.resolution = resolution
	document.save()
	return _finding_state(document)


@frappe.whitelist(methods=["POST"])
def link_finding_execution(
	finding_name: str,
	target_doctype: str,
	target_name: str,
	relation_type: str,
	source_event_key: str,
) -> dict[str, object]:
	"""Idempotently bind an allowlisted execution record without changing source."""

	source_event_key = _normalized_event_key(source_event_key)
	frappe.db.sql(
		f"SELECT name FROM `tab{FINDING_DOCTYPE}` WHERE name=%s FOR UPDATE",
		(finding_name,),
	)
	document = frappe.get_doc(FINDING_DOCTYPE, finding_name)
	document.check_permission("write")
	existing = next(
		(
			row
			for row in document.get("execution_links") or []
			if row.source_event_key == source_event_key
		),
		None,
	)
	if existing:
		if (existing.target_doctype, existing.target_name) != (target_doctype, target_name):
			frappe.throw(_("source_event_key уже связан с другим execution target."))
		return _link_result(document, existing, created=False)
	row = document.append(
		"execution_links",
		{
			"target_doctype": target_doctype,
			"target_name": target_name,
			"relation_type": relation_type,
			"source_event_key": source_event_key,
		},
	)
	document.save()
	return _link_result(document, row, created=True)


@frappe.whitelist(methods=["POST"])
def create_service_request_from_finding(
	finding_name: str,
	source_event_key: str,
	relation_type: str = "Execution",
) -> dict[str, object]:
	"""Explicitly create and provenance-link a Service Request; never runs on insert."""

	source_event_key = _normalized_event_key(source_event_key)
	frappe.db.sql(
		f"SELECT name FROM `tab{FINDING_DOCTYPE}` WHERE name=%s FOR UPDATE",
		(finding_name,),
	)
	finding = frappe.get_doc(FINDING_DOCTYPE, finding_name)
	finding.check_permission("write")
	if finding.confirmation_status != "Confirmed" or finding.status in {"Closed", "Rejected"}:
		frappe.throw(_("Service Request можно создать только для active Confirmed Finding."))
	existing = next(
		(
			row
			for row in finding.get("execution_links") or []
			if row.source_event_key == source_event_key
		),
		None,
	)
	if existing:
		if existing.target_doctype != REQUEST_DOCTYPE:
			frappe.throw(_("source_event_key уже занят другим execution target."))
		return {
			"finding": finding.name,
			"service_request": existing.target_name,
			"created": False,
		}
	request = frappe.get_doc(
		{
			"doctype": REQUEST_DOCTYPE,
			"service_project": finding.service_project,
			"project_object": finding.project_object,
			"object_system": finding.object_system,
			"source_type": "Finding",
			"source_reference": finding.name,
			"request_type": "Additional Work"
			if finding.decision == "Additional Work"
			else "Repair",
			"priority": finding.severity,
			"requested_at": now_datetime(),
		}
	).insert()
	finding.append(
		"execution_links",
		{
			"target_doctype": REQUEST_DOCTYPE,
			"target_name": request.name,
			"relation_type": relation_type,
			"source_event_key": source_event_key,
		},
	)
	finding.save()
	return {
		"finding": finding.name,
		"service_request": request.name,
		"created": True,
	}


@frappe.whitelist()
def get_finding_exception_report(service_project: str | None = None) -> dict[str, object]:
	"""Return active critical, overdue or untriaged Findings with derived flags."""

	filters: dict[str, object] = {"status": ["in", ["Open", "In Resolution"]]}
	if service_project:
		filters["service_project"] = service_project
	rows = frappe.get_list(
		FINDING_DOCTYPE,
		filters=filters,
		fields=[
			"name",
			"service_project",
			"source_doctype",
			"source_name",
			"category",
			"severity",
			"confirmation_status",
			"status",
			"decision",
			"responsible",
			"due_date",
		],
		order_by="due_date asc, found_at asc",
	)
	now = now_datetime()
	exceptions: list[dict[str, object]] = []
	for row in rows:
		flags = {
			"open_critical": row.severity == "Critical",
			"overdue": bool(row.due_date and get_datetime(row.due_date) < now),
			"without_decision": not bool(row.decision),
		}
		if any(flags.values()):
			exceptions.append({**dict(row), **flags})
	return {"service_project": service_project, "count": len(exceptions), "items": exceptions}


def _finding_state(document) -> dict[str, object]:
	return {
		"name": document.name,
		"confirmation_status": document.confirmation_status,
		"status": document.status,
		"resolved_at": document.resolved_at,
		"resolved_by": document.resolved_by,
		"closed_at": document.closed_at,
		"closed_by": document.closed_by,
	}


def _link_result(document, row, *, created: bool) -> dict[str, object]:
	return {
		"finding": document.name,
		"target_doctype": row.target_doctype,
		"target_name": row.target_name,
		"source_event_key": row.source_event_key,
		"created": created,
	}


def _normalized_event_key(value: str) -> str:
	key = (value or "").strip()
	if not key:
		frappe.throw(_("source_event_key обязателен."))
	return key
