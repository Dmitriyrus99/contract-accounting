"""CA-10 read-only Contract 360 and Director Control Center projections."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from typing import Any, Final

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime

from contract_accounting.api.deadlines import get_deadline_timeline
from contract_accounting.api.finance import (
	can_read_finance,
	get_finance_summary_snapshot,
)
from contract_accounting.domain.control_center import (
	ExceptionItem,
	age_in_days,
	risk_flag,
	sort_exceptions,
)

_DIRECTOR_ROLES: Final[frozenset[str]] = frozenset(
	{"Генеральный директор", "Руководитель проектов", "System Manager"}
)
_OPEN_REQUEST_STATUSES: Final[frozenset[str]] = frozenset(
	{"Open", "Assigned", "In Progress"}
)
_OPEN_FINDING_STATUSES: Final[frozenset[str]] = frozenset({"Open", "In Resolution"})


@frappe.whitelist()
def get_contract_360(service_project: str, as_of: str | None = None) -> dict[str, Any]:
	"""Return one permission-filtered project card with exact source drill-downs."""

	project = _authorized_project(service_project)
	payload, _items = _build_contract_360(project, _as_of_date(as_of))
	return payload


@frappe.whitelist()
def get_director_control_center(
	company: str | None = None,
	project_manager: str | None = None,
	as_of: str | None = None,
	limit_start: int | str = 0,
	limit_page_length: int | str = 50,
) -> dict[str, Any]:
	"""Return intervention-only portfolio data for director roles."""

	_require_director_role()
	start = max(cint(limit_start), 0)
	page_length = min(max(cint(limit_page_length), 1), 100)
	filters: dict[str, Any] = {}
	if company:
		filters["company"] = company
	if project_manager:
		filters["project_manager"] = project_manager
	project_names = frappe.get_list(
		"Ferum Service Project",
		filters=filters,
		pluck="name",
		order_by="modified desc, name asc",
		limit_start=start,
		limit_page_length=page_length,
	)
	as_of_date = _as_of_date(as_of)
	all_items: list[ExceptionItem] = []
	projects: list[dict[str, Any]] = []
	status_sources: dict[tuple[str, str], list[dict[str, str]]] = {}
	for name in project_names:
		project = _authorized_project(str(name))
		card, items = _build_contract_360(project, as_of_date)
		all_items.extend(items)
		projects.append(
			{
				"service_project": project.name,
				"contract_number": project.contract_number,
				"customer": project.customer,
				"company": project.company,
				"project_manager": project.project_manager,
				"legal_status": project.legal_status,
				"execution_status": project.execution_status,
				"risk_flag": card["risk_flag"],
				"exception_count": len(items),
				"finance": card["finance"],
				"drilldown": _drilldown(project.doctype, project.name),
			}
		)
		status_sources.setdefault(
			(project.legal_status, project.execution_status), []
		).append(_drilldown(project.doctype, project.name))

	ordered = sort_exceptions(all_items)
	by_rule = Counter(str(item["rule"]) for item in ordered)
	by_severity = Counter(str(item["severity"]) for item in ordered)
	return {
		"generated_at": now_datetime(),
		"as_of": as_of_date.isoformat() if as_of_date else None,
		"time_rules": "explicit_as_of" if as_of_date else "disabled_pending_MG-CA-013",
		"thresholds": {"expiring_contract_days": 30, "old_finding_days": 30},
		"pagination": {
			"limit_start": start,
			"limit_page_length": page_length,
			"returned_projects": len(projects),
		},
		"status_matrix": [
			{
				"legal_status": legal,
				"execution_status": execution,
				"count": len(sources),
				"sources": sources,
			}
			for (legal, execution), sources in sorted(status_sources.items())
		],
		"kpi": {
			"project_count": len(projects),
			"exception_count": len(ordered),
			"by_rule": dict(sorted(by_rule.items())),
			"by_severity": dict(sorted(by_severity.items())),
		},
		"projects": projects,
		"exceptions": ordered,
	}


def _build_contract_360(
	project: Any,
	as_of: date | None,
) -> tuple[dict[str, Any], list[ExceptionItem]]:
	requirements = _rows(
		"Ferum Contract Requirement",
		{"service_project": project.name},
		["name", "requirement_type", "requirement_source", "source_clause", "applicability", "assessment_status"],
	)
	obligations = _rows(
		"Ferum Contract Obligation",
		{"service_project": project.name},
		["name", "project_object", "object_system", "work_type", "obligation_type", "criticality", "status"],
	)
	project_objects = _rows(
		"Ferum Project Object",
		{"service_project": project.name},
		["name", "service_object", "effective_from", "effective_to", "status", "responsible_engineer"],
	)
	service_objects = sorted({str(row["service_object"]) for row in project_objects})
	systems = _rows(
		"Ferum Object System",
		{"service_object": ["in", service_objects]},
		["name", "service_object", "system_type", "system_name", "status"],
	) if service_objects else []
	schedules = _rows(
		"Ferum Maintenance Schedule",
		{"service_project": project.name},
		["name", "contract_obligation", "project_object", "object_system", "planned_date", "due_date", "status"],
	)
	visits = _rows(
		"Ferum Maintenance Visit",
		{"service_project": project.name},
		[
			"name", "contract_obligation", "project_object", "object_system", "planned_date",
			"actual_end", "assigned_engineer", "status", "review_status", "acceptance_status",
			"billing_eligible",
		],
	)
	requests = _rows(
		"Ferum Service Request",
		{"service_project": project.name},
		["name", "project_object", "object_system", "request_type", "priority", "requested_at", "resolution_due", "assigned_engineer", "status"],
	)
	findings = _rows(
		"Ferum Finding",
		{"service_project": project.name},
		["name", "category", "severity", "title", "found_at", "confirmation_status", "status", "decision", "responsible", "due_date"],
	)
	documents = _rows(
		"Ferum Project Document",
		{"service_project": project.name},
		["name", "document_type", "document_number", "document_date", "status", "valid_until", "digital_copy_status", "original_status", "original_expected_at", "owner_user"],
	)
	billing_outputs = _rows(
		"Ferum Billing Output",
		{"service_project": project.name},
		["name", "output_type", "document_date", "period_start", "period_end", "status", "final_artifact_status", "sales_invoice"],
	)
	assignments = _rows(
		"Ferum Contractor Assignment",
		{"service_project": project.name},
		["name", "execution_mode", "supplier", "employee", "project_object", "object_system", "work_type", "effective_from", "effective_to", "status", "credentials_readiness"],
	)
	deadlines = get_deadline_timeline(
		project.name,
		as_of=as_of.isoformat() if as_of else None,
		include_closed=0,
	)
	finance = _finance_widget(project.name)
	unpaid_invoices = _unpaid_invoices(project.name) if can_read_finance() else []
	finance["unpaid_invoices"] = unpaid_invoices if finance["access"] == "granted" else []

	widgets = {
		"requirements": _widget(requirements),
		"obligations": _widget(obligations),
		"objects": _widget(project_objects),
		"systems": _widget(systems),
		"maintenance": {
			"planned": sum(row["status"] != "Cancelled" for row in schedules),
			"completed": sum(row["status"] == "Completed" for row in visits),
			"accepted": sum(row["acceptance_status"] == "Accepted" for row in visits),
			"schedules": schedules,
			"visits": visits,
		},
		"requests": {
			"count": len(requests),
			"open_count": sum(row["status"] in _OPEN_REQUEST_STATUSES for row in requests),
			"items": requests,
		},
		"findings": {
			"count": len(findings),
			"open_count": sum(row["status"] in _OPEN_FINDING_STATUSES for row in findings),
			"items": findings,
		},
		"documents": _widget(documents),
		"billing": _widget(billing_outputs),
		"contractors": _widget(assignments),
		"deadlines": deadlines,
	}
	items = _project_exceptions(project, widgets, finance, as_of)
	payload: dict[str, Any] = {
		"generated_at": now_datetime(),
		"service_project": project.name,
		"identity": {
			"contract_number": project.contract_number,
			"contract_date": project.contract_date,
			"customer": project.customer,
			"company": project.company,
			"effective_from": project.effective_from,
			"effective_to": project.effective_to,
			"project_manager": project.project_manager,
			"legal_status": project.legal_status,
			"execution_status": project.execution_status,
			"drilldown": _drilldown(project.doctype, project.name),
		},
		"finance": finance,
		"widgets": widgets,
		"risk_flag": risk_flag(items),
		"exceptions": sort_exceptions(items),
		"time_rules": "explicit_as_of" if as_of else "disabled_pending_MG-CA-013",
	}
	payload["source_fingerprint"] = _fingerprint(payload)
	return payload, items


def _project_exceptions(
	project: Any,
	widgets: dict[str, Any],
	finance: dict[str, Any],
	as_of: date | None,
) -> list[ExceptionItem]:
	items: list[ExceptionItem] = []
	owner = project.project_manager
	if project.execution_status == "Active" and project.legal_status != "In Force":
		items.append(
			_exception(project, "Active Legal Mismatch", "Active work without In Force contract", "Critical", project.doctype, project.name, "legal_status")
		)
	if as_of and project.effective_to:
		days_left = (getdate(project.effective_to) - as_of).days
		if 0 <= days_left <= 30:
			items.append(
				_exception(project, "Expiring Contract", "Contract expires within 30 days", "Medium", project.doctype, project.name, "effective_to", due_at=str(project.effective_to), details={"days_left": days_left})
			)

	schedule_by_obligation = {
		str(row["contract_obligation"])
		for row in widgets["maintenance"]["schedules"]
		if row["status"] != "Cancelled"
	}
	for obligation in widgets["obligations"]["items"]:
		if obligation["status"] == "Active" and obligation["name"] not in schedule_by_obligation:
			items.append(
				_exception(project, "Obligation Without Schedule", "Active obligation has no maintenance schedule", "High", "Ferum Contract Obligation", obligation["name"], owner=owner)
			)
	object_services_with_systems = {
		str(row["service_object"]) for row in widgets["systems"]["items"]
	}
	for membership in widgets["objects"]["items"]:
		if membership["status"] == "Active" and str(membership["service_object"]) not in object_services_with_systems:
			items.append(
				_exception(project, "Object Without System Inventory", "Active project object has no system inventory", "High", "Ferum Project Object", membership["name"], owner=membership.get("responsible_engineer") or owner)
			)
	for visit in widgets["maintenance"]["visits"]:
		if visit["status"] == "Completed" and visit["review_status"] == "Pending":
			items.append(
				_exception(project, "Visit Review Pending", "Completed maintenance visit awaits PM review", "Medium", "Ferum Maintenance Visit", visit["name"], "review_status", owner=owner, age_days=_age(visit.get("actual_end"), as_of))
			)
		if visit["acceptance_status"] == "Accepted" and not _billing_basis_exists("Ferum Maintenance Visit", visit["name"]):
			items.append(
				_exception(project, "Accepted Work Without Billing Basis", "Accepted visit is not included in Billing Basis", "High", "Ferum Maintenance Visit", visit["name"], "acceptance_status", owner=owner, age_days=_age(visit.get("actual_end"), as_of))
			)
	for finding in widgets["findings"]["items"]:
		if finding["status"] not in _OPEN_FINDING_STATUSES:
			continue
		age = _age(finding.get("found_at"), as_of)
		if finding["severity"] == "Critical" and not finding.get("decision"):
			items.append(
				_exception(project, "Critical Finding Without Decision", "Critical Finding has no decision", "Critical", "Ferum Finding", finding["name"], "decision", owner=finding.get("responsible") or owner, age_days=age)
			)
		if as_of and finding["category"] == "Defect" and age > 30:
			items.append(
				_exception(project, "Old Defect", "Open defect is older than 30 days", "High", "Ferum Finding", finding["name"], "found_at", owner=finding.get("responsible") or owner, age_days=age)
			)
	for output in widgets["billing"]["items"]:
		if output["output_type"] in {"Act", "UPD"} and output["status"] == "Issued":
			items.append(
				_exception(project, "Unsigned Act", "Issued act/UPD is not signed", "High", "Ferum Billing Output", output["name"], "status", owner=owner, age_days=_age(output.get("document_date"), as_of))
			)

	if as_of:
		for deadline in widgets["deadlines"]["rows"]:
			if not deadline["is_overdue"]:
				continue
			rule, title, severity = _deadline_exception(deadline["kind"])
			if not rule:
				continue
			items.append(
				_exception(project, rule, title, severity, deadline["source_doctype"], deadline["source_name"], deadline["source_field"], owner=deadline.get("owner") or owner, age_days=age_in_days(getdate(deadline["due_at"]), as_of), due_at=deadline["due_at"])
			)

	if finance.get("access") == "granted" and finance.get("status") == "available":
		summary_name = str(finance["summary"])
		if flt(finance.get("overdue_ar_with_vat")) > 0:
			items.append(
				_exception(project, "Overdue Receivable", "Project has overdue accounts receivable", "High", "Ferum Project Finance Summary", summary_name, "overdue_ar_with_vat", owner=owner, details={"amount": finance["overdue_ar_with_vat"], "currency": finance["currency"]})
			)
		if flt(finance.get("profit_without_vat")) < 0:
			items.append(
				_exception(project, "Negative Margin", "Project margin is negative", "Critical", "Ferum Project Finance Summary", summary_name, "profit_without_vat", owner=owner, details={"amount": finance["profit_without_vat"], "currency": finance["currency"]})
			)
		for invoice in finance.get("unpaid_invoices", []):
			items.append(
				_exception(project, "Unpaid Invoice", "Submitted invoice has outstanding amount", "High", "Sales Invoice", invoice["name"], "outstanding_amount", owner=owner, age_days=_age(invoice.get("posting_date"), as_of), due_at=str(invoice.get("due_date") or "") or None, details={"amount": invoice["outstanding_amount"], "currency": invoice["currency"]})
			)
	return items


def _finance_widget(service_project: str) -> dict[str, Any]:
	if not can_read_finance():
		return {"access": "restricted", "status": "hidden", "unpaid_invoices": []}
	return get_finance_summary_snapshot(service_project)


def _unpaid_invoices(service_project: str) -> list[dict[str, Any]]:
	if not frappe.db.has_column("Sales Invoice", "ferum_service_project"):
		return []
	rows = _rows(
		"Sales Invoice",
		{
			"ferum_service_project": service_project,
			"docstatus": 1,
			"outstanding_amount": [">", 0],
		},
		["name", "posting_date", "due_date", "status", "currency", "outstanding_amount"],
	)
	return rows


def _rows(doctype: str, filters: dict[str, Any], fields: list[str]) -> list[dict[str, Any]]:
	result: list[dict[str, Any]] = []
	for row in frappe.get_all(
		doctype,
		filters=filters,
		fields=fields,
		order_by="name asc",
		limit_page_length=0,
	):
		if frappe.session.user != "Administrator" and not frappe.has_permission(
			doctype, "read", doc=row.name
		):
			continue
		item = dict(row)
		item["source_doctype"] = doctype
		item["source_name"] = row.name
		item["drilldown"] = _drilldown(doctype, row.name)
		result.append(item)
	return result


def _widget(items: list[dict[str, Any]]) -> dict[str, Any]:
	return {"count": len(items), "items": items}


def _exception(
	project: Any,
	rule: str,
	title: str,
	severity: str,
	doctype: str,
	name: str,
	fieldname: str | None = None,
	*,
	owner: str | None = None,
	age_days: int = 0,
	due_at: str | None = None,
	details: dict[str, object] | None = None,
) -> ExceptionItem:
	return ExceptionItem(
		rule=rule,
		title=title,
		severity=severity,
		service_project=project.name,
		source_doctype=doctype,
		source_name=name,
		source_field=fieldname,
		owner=owner or project.project_manager,
		age_days=age_days,
		due_at=due_at,
		details=details,
	)


def _deadline_exception(kind: str) -> tuple[str | None, str, str]:
	return {
		"Maintenance Due": ("Overdue Maintenance", "Maintenance deadline is overdue", "High"),
		"Bank Guarantee Expiry": ("Expired Bank Guarantee", "Bank guarantee is expired", "Critical"),
		"Invoice Payment Due": ("Overdue Invoice", "Invoice payment deadline is overdue", "High"),
		"Document Original Expected": ("Original Document Overdue", "Expected original document is overdue", "High"),
	}.get(kind, (None, "", "Low"))


def _billing_basis_exists(source_doctype: str, source_name: str) -> bool:
	return bool(
		frappe.db.exists(
			"Ferum Billing Basis Item",
			{"source_doctype": source_doctype, "source_name": source_name},
		)
	)


def _age(value: Any, as_of: date | None) -> int:
	if not value or not as_of:
		return 0
	return age_in_days(get_datetime(value), as_of)


def _drilldown(doctype: str, name: str) -> dict[str, str]:
	return {"doctype": doctype, "name": name}


def _authorized_project(service_project: str) -> Any:
	if not frappe.db.exists("Ferum Service Project", service_project):
		frappe.throw(_("Ferum Service Project не найден."), frappe.DoesNotExistError)
	project = frappe.get_doc("Ferum Service Project", service_project)
	project.check_permission("read")
	return project


def _require_director_role() -> None:
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles(frappe.session.user)).intersection(_DIRECTOR_ROLES):
		frappe.throw(_("Роль не разрешает Director Control Center."), frappe.PermissionError)


def _as_of_date(value: str | None) -> date | None:
	return getdate(value) if value else None


def _fingerprint(payload: dict[str, Any]) -> str:
	source_payload = {
		key: value
		for key, value in payload.items()
		if key not in {"generated_at", "source_fingerprint"}
	}
	return hashlib.sha256(
		json.dumps(source_payload, ensure_ascii=False, sort_keys=True, default=str).encode()
	).hexdigest()
