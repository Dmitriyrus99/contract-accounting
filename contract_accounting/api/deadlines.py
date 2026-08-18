"""Read-only CA-09 projection of primary deadline sources."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate


@frappe.whitelist()
def get_deadline_timeline(
	service_project: str,
	as_of: str | None = None,
	include_closed: int | str = 1,
) -> dict[str, Any]:
	"""Project primary dates without persisting a second deadline SSOT.

	Automatic Company-calendar warning/escalation remains disabled until
	MG-CA-013. An explicit ``as_of`` enables deterministic absolute-date
	overdue classification only; it does not claim business-calendar readiness.
	"""

	project = _authorized_project(service_project)
	classification_at = _local_datetime(as_of) if as_of else None
	rows: list[dict[str, Any]] = []
	_add(
		rows,
		kind="Contract Start",
		doctype=project.doctype,
		name=project.name,
		fieldname="effective_from",
		value=project.effective_from,
		status=project.execution_status,
		owner=project.project_manager,
		terminal=project.execution_status != "Not Started",
		date_only=True,
		as_of=classification_at,
	)
	_add(
		rows,
		kind="Contract Expiry",
		doctype=project.doctype,
		name=project.name,
		fieldname="effective_to",
		value=project.effective_to,
		status=project.legal_status,
		owner=project.project_manager,
		terminal=project.legal_status in {"Cancelled", "Terminated", "Expired"},
		date_only=True,
		as_of=classification_at,
	)
	_schedule_rows(rows, project.name, classification_at)
	_request_rows(rows, project.name, classification_at)
	_stage_rows(rows, project.name, classification_at)
	_security_rows(rows, project.name, classification_at)
	_document_rows(rows, project.name, classification_at)
	_finding_rows(rows, project.name, classification_at)
	_invoice_rows(rows, project.name, classification_at)
	_billing_cycle_rows(rows, project.name, classification_at)
	_process_step_rows(rows, project.name, classification_at)

	if not cint(include_closed):
		rows = [row for row in rows if row["severity"] != "Closed"]
	rows.sort(key=lambda row: (row["due_at"], row["kind"], row["source_key"]))
	_seen_source_keys(rows)
	source_payload = [
		{
			"source_key": row["source_key"],
			"kind": row["kind"],
			"due_at": row["due_at"],
			"source_status": row["source_status"],
			"owner": row["owner"],
		}
		for row in rows
	]
	fingerprint = hashlib.sha256(
		json.dumps(source_payload, ensure_ascii=False, sort_keys=True).encode()
	).hexdigest()
	return {
		"service_project": project.name,
		"source_fingerprint": fingerprint,
		"row_count": len(rows),
		"classification": {
			"absolute_overdue": "explicit_as_of_site_local" if classification_at else "disabled",
			"as_of": classification_at.isoformat() if classification_at else None,
			"warning_escalation": "disabled_pending_MG-CA-013",
		},
		"rows": rows,
	}


def _schedule_rows(rows: list[dict[str, Any]], project: str, as_of: datetime | None) -> None:
	for row in _readable_rows(
		"Ferum Maintenance Schedule",
		project,
		["name", "due_date", "status", "modified"],
	):
		_add(
			rows,
			kind="Maintenance Due",
			doctype="Ferum Maintenance Schedule",
			name=row.name,
			fieldname="due_date",
			value=row.due_date,
			status=row.status,
			terminal=row.status in {"Completed", "Cancelled"},
			date_only=True,
			as_of=as_of,
		)


def _request_rows(rows: list[dict[str, Any]], project: str, as_of: datetime | None) -> None:
	for row in _readable_rows(
		"Ferum Service Request",
		project,
		[
			"name", "reaction_due", "resolution_due", "status", "assigned_engineer",
			"actual_start", "actual_end",
		],
	):
		_add(
			rows,
			kind="Request Reaction Due",
			doctype="Ferum Service Request",
			name=row.name,
			fieldname="reaction_due",
			value=row.reaction_due,
			status=row.status,
			owner=row.assigned_engineer,
			terminal=bool(row.actual_start) or row.status in {"In Progress", "Resolved", "Closed", "Cancelled"},
			date_only=False,
			as_of=as_of,
		)
		_add(
			rows,
			kind="Request Resolution Due",
			doctype="Ferum Service Request",
			name=row.name,
			fieldname="resolution_due",
			value=row.resolution_due,
			status=row.status,
			owner=row.assigned_engineer,
			terminal=bool(row.actual_end) or row.status in {"Resolved", "Closed", "Cancelled"},
			date_only=False,
			as_of=as_of,
		)


def _stage_rows(rows: list[dict[str, Any]], project: str, as_of: datetime | None) -> None:
	for row in _readable_rows(
		"Ferum Contract Execution Stage",
		project,
		["name", "acceptance_due_date", "billing_due_date", "payment_due_date", "status"],
	):
		terminal = row.status in {"Superseded", "Cancelled"}
		for fieldname, kind in (
			("acceptance_due_date", "Acceptance Due"),
			("billing_due_date", "Billing Issue Due"),
			("payment_due_date", "Stage Payment Due"),
		):
			_add(
				rows,
				kind=kind,
				doctype="Ferum Contract Execution Stage",
				name=row.name,
				fieldname=fieldname,
				value=row.get(fieldname),
				status=row.status,
				terminal=terminal or (fieldname == "acceptance_due_date" and row.status == "Accepted"),
				date_only=True,
				as_of=as_of,
			)


def _security_rows(rows: list[dict[str, Any]], project: str, as_of: datetime | None) -> None:
	for row in _readable_rows(
		"Ferum Contract Security",
		project,
		[
			"name", "security_type", "security_method", "status", "valid_until",
			"return_due_date", "reminder_date",
		],
	):
		terminal = row.status in {"Replaced", "Released", "Returned", "Expired", "Cancelled"}
		if row.security_method == "Independent Guarantee":
			expiry_kind = "Bank Guarantee Expiry"
		elif row.security_type == "Warranty Obligations":
			expiry_kind = "Warranty Security Expiry"
		else:
			expiry_kind = "Performance Security Expiry"
		for fieldname, kind in (
			("reminder_date", "Security Reminder"),
			("valid_until", expiry_kind),
			("return_due_date", "Security Return Due"),
		):
			_add(
				rows,
				kind=kind,
				doctype="Ferum Contract Security",
				name=row.name,
				fieldname=fieldname,
				value=row.get(fieldname),
				status=row.status,
				terminal=terminal,
				date_only=True,
				as_of=as_of,
			)


def _document_rows(rows: list[dict[str, Any]], project: str, as_of: datetime | None) -> None:
	for row in _readable_rows(
		"Ferum Project Document",
		project,
		["name", "valid_until", "original_expected_at", "status", "original_status", "owner_user"],
	):
		terminal = row.status in {"Superseded", "Cancelled", "Archived"}
		_add(
			rows,
			kind="Document Expiry",
			doctype="Ferum Project Document",
			name=row.name,
			fieldname="valid_until",
			value=row.valid_until,
			status=row.status,
			owner=row.owner_user,
			terminal=terminal,
			date_only=True,
			as_of=as_of,
		)
		_add(
			rows,
			kind="Document Original Expected",
			doctype="Ferum Project Document",
			name=row.name,
			fieldname="original_expected_at",
			value=row.original_expected_at,
			status=row.original_status,
			owner=row.owner_user,
			terminal=row.original_status in {"Received", "Archived", "Not Required"},
			date_only=False,
			as_of=as_of,
		)


def _finding_rows(rows: list[dict[str, Any]], project: str, as_of: datetime | None) -> None:
	for row in _readable_rows(
		"Ferum Finding",
		project,
		["name", "due_date", "status", "responsible"],
	):
		_add(
			rows,
			kind="Finding Resolution Due",
			doctype="Ferum Finding",
			name=row.name,
			fieldname="due_date",
			value=row.due_date,
			status=row.status,
			owner=row.responsible,
			terminal=row.status in {"Resolved", "Closed", "Cancelled"},
			date_only=False,
			as_of=as_of,
		)


def _invoice_rows(rows: list[dict[str, Any]], project: str, as_of: datetime | None) -> None:
	if not frappe.db.has_column("Sales Invoice", "ferum_service_project"):
		return
	for row in _readable_rows(
		"Sales Invoice",
		project,
		["name", "due_date", "status", "outstanding_amount"],
		project_field="ferum_service_project",
		additional_filters={"docstatus": 1},
	):
		_add(
			rows,
			kind="Invoice Payment Due",
			doctype="Sales Invoice",
			name=row.name,
			fieldname="due_date",
			value=row.due_date,
			status=row.status,
			terminal=float(row.outstanding_amount or 0) <= 0,
			date_only=True,
			as_of=as_of,
		)


def _billing_cycle_rows(
	rows: list[dict[str, Any]], project: str, as_of: datetime | None
) -> None:
	for row in _readable_rows(
		"Ferum Billing Cycle",
		project,
		["name", "due_date", "status", "created_by"],
	):
		_add(
			rows,
			kind="Billing Cycle Due",
			doctype="Ferum Billing Cycle",
			name=row.name,
			fieldname="due_date",
			value=row.due_date,
			status=row.status,
			owner=row.created_by,
			terminal=row.status in {"Completed", "Cancelled"},
			date_only=True,
			as_of=as_of,
		)


def _process_step_rows(
	rows: list[dict[str, Any]], project: str, as_of: datetime | None
) -> None:
	for row in _readable_rows(
		"Ferum Project Process Step",
		project,
		["name", "due_at", "status", "responsible_user"],
	):
		_add(
			rows,
			kind="Process Step Due",
			doctype="Ferum Project Process Step",
			name=row.name,
			fieldname="due_at",
			value=row.due_at,
			status=row.status,
			owner=row.responsible_user,
			terminal=row.status in {"Completed", "Not Applicable", "Cancelled"},
			date_only=False,
			as_of=as_of,
		)


def _readable_rows(
	doctype: str,
	project: str,
	fields: list[str],
	*,
	project_field: str = "service_project",
	additional_filters: dict[str, Any] | None = None,
) -> list[Any]:
	filters = {project_field: project, **(additional_filters or {})}
	result = []
	for row in frappe.get_all(doctype, filters=filters, fields=fields, order_by="name asc"):
		if frappe.session.user == "Administrator" or frappe.has_permission(
			doctype, "read", doc=row.name
		):
			result.append(row)
	return result


def _add(
	rows: list[dict[str, Any]],
	*,
	kind: str,
	doctype: str,
	name: str,
	fieldname: str,
	value: Any,
	status: str,
	terminal: bool,
	date_only: bool,
	as_of: datetime | None,
	owner: str | None = None,
) -> None:
	if not value:
		return
	due_at = getdate(value).isoformat() if date_only else _local_datetime(value).isoformat()
	if terminal:
		is_overdue: bool | None = False
		severity = "Closed"
	elif as_of is None:
		is_overdue = None
		severity = "Unclassified"
	elif date_only:
		is_overdue = getdate(value) < as_of.date()
		severity = "Overdue" if is_overdue else "Normal"
	else:
		is_overdue = _local_datetime(value) < as_of
		severity = "Overdue" if is_overdue else "Normal"
	rows.append(
		{
			"kind": kind,
			"source_doctype": doctype,
			"source_name": name,
			"source_field": fieldname,
			"source_key": f"{doctype}:{name}:{fieldname}",
			"owner": owner,
			"due_at": due_at,
			"source_status": status or "Open",
			"is_overdue": is_overdue,
			"overdue_since": due_at if is_overdue else None,
			"display_status": "Overdue" if is_overdue else (status or "Open"),
			"severity": severity,
		}
	)


def _authorized_project(service_project: str) -> Any:
	if not frappe.db.exists("Ferum Service Project", service_project):
		frappe.throw(_("Ferum Service Project не найден."), frappe.DoesNotExistError)
	project = frappe.get_doc("Ferum Service Project", service_project)
	project.check_permission("read")
	return project


def _local_datetime(value: str | date | datetime) -> datetime:
	return get_datetime(value).replace(tzinfo=None)


def _seen_source_keys(rows: list[dict[str, Any]]) -> None:
	seen: set[str] = set()
	for row in rows:
		if row["source_key"] in seen:
			frappe.throw(_("Deadline projection содержит duplicate source key."))
		seen.add(row["source_key"])
