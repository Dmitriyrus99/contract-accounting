"""CA-14 permission-safe, read-only My Actions and Project Launch projections."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Any, Final

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

from contract_accounting.domain.work_queue import (
	TERMINAL_STATUSES,
	classify_action,
	deduplicate_actions,
	progress,
	sort_actions,
)
from contract_accounting.setup.launch_template import TEMPLATE_CODE, TEMPLATE_VERSION

_LAUNCH_ROLES: Final[frozenset[str]] = frozenset(
	{
		"Владелец процесса",
		"Менеджер проектов",
		"Руководитель проектов",
		"System Manager",
	}
)
_TIME_BUCKETS: Final[frozenset[str]] = frozenset(
	{"Overdue", "Today", "Upcoming", "Unscheduled"}
)
_STATE_BUCKETS: Final[frozenset[str]] = frozenset(
	{"Blocked", "Waiting External", "Waiting Approval", "Actionable"}
)
_PROCESS_ACTION_STATUSES: Final[frozenset[str]] = frozenset(
	{"Ready", "In Progress", "Waiting External", "Waiting Approval", "Blocked"}
)
_DIRECT_SOURCES: Final[tuple[tuple[str, str, tuple[str, ...]], ...]] = (
	(
		"Ferum Service Request",
		"assigned_engineer",
		("Open", "Assigned", "In Progress"),
	),
	(
		"Ferum Maintenance Visit",
		"assigned_engineer",
		("Planned", "In Progress"),
	),
	("Ferum Project Document", "owner_user", ("Draft", "Active")),
)


@frappe.whitelist()
def get_my_actions(
	as_of: str | None = None,
	time_bucket: str | None = None,
	state_bucket: str | None = None,
	source_type: str | None = None,
	limit_start: int | str = 0,
	limit_page_length: int | str = 100,
) -> dict[str, Any]:
	"""Return one row per permitted operation assigned to the session user."""

	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	classification_at = _as_of(as_of)
	_validate_filter(time_bucket, _TIME_BUCKETS, "time_bucket")
	_validate_filter(state_bucket, _STATE_BUCKETS, "state_bucket")
	start = max(cint(limit_start), 0)
	page_length = min(max(cint(limit_page_length), 1), 200)

	todo_rows, referenced = _todo_actions(user, classification_at)
	rows = todo_rows
	rows.extend(_step_actions(user, classification_at, referenced))
	for doctype, owner_field, statuses in _DIRECT_SOURCES:
		rows.extend(
			_owned_actions(
				doctype,
				owner_field,
				statuses,
				user,
				classification_at,
				referenced,
			)
		)

	ordered = sort_actions(deduplicate_actions(rows))
	if time_bucket:
		ordered = [row for row in ordered if row["time_bucket"] == time_bucket]
	if state_bucket:
		ordered = [row for row in ordered if row["state_bucket"] == state_bucket]
	if source_type:
		ordered = [row for row in ordered if row["source_type"] == source_type]
	total = len(ordered)
	page = ordered[start : start + page_length]
	return {
		"generated_at": now_datetime(),
		"as_of": classification_at.isoformat(),
		"user": user,
		"ssot_policy": "SOURCE_OPERATION_SSOT_TODO_DELIVERY_ONLY",
		"sort_policy": "OVERDUE_TODAY_UPCOMING_UNSCHEDULED_THEN_STATE_DUE_SOURCE",
		"pagination": {
			"limit_start": start,
			"limit_page_length": page_length,
			"total": total,
			"returned": len(page),
		},
		"kpi": {
			"by_time": dict(sorted(Counter(row["time_bucket"] for row in ordered).items())),
			"by_state": dict(sorted(Counter(row["state_bucket"] for row in ordered).items())),
			"by_source": dict(sorted(Counter(row["source_type"] for row in ordered).items())),
		},
		"actions": page,
	}


@frappe.whitelist()
def get_project_launch_view(
	service_project: str, as_of: str | None = None
) -> dict[str, Any]:
	"""Render the Launch tab for one readable Service Project."""

	_require_launch_role()
	project = _authorized_project(service_project)
	return _launch_view(project, _as_of(as_of))


@frappe.whitelist()
def get_launch_projects(
	as_of: str | None = None,
	flag: str | None = None,
	company: str | None = None,
	project_manager: str | None = None,
	limit_start: int | str = 0,
	limit_page_length: int | str = 50,
) -> dict[str, Any]:
	"""Return readable projects in launch with exact blocking drill-downs."""

	_require_launch_role()
	allowed_flags = {
		"overdue",
		"blocked",
		"missing_contractor",
		"waiting_customer",
		"missing_credentials",
	}
	_validate_filter(flag, frozenset(allowed_flags), "flag")
	start = max(cint(limit_start), 0)
	page_length = min(max(cint(limit_page_length), 1), 100)
	filters: dict[str, Any] = {
		"execution_status": ["in", ["Not Started", "Launching"]],
		"legal_status": ["in", ["Approved", "Signing", "Signed", "In Force"]],
	}
	if company:
		filters["company"] = company
	if project_manager:
		filters["project_manager"] = project_manager
	project_names = frappe.get_list(
		"Ferum Service Project",
		filters=filters,
		pluck="name",
		order_by="launch_date asc, modified asc, name asc",
		limit_page_length=0,
	)
	classification_at = _as_of(as_of)
	projects = [
		_launch_view(_authorized_project(str(name)), classification_at)
		for name in project_names
	]
	projects.sort(key=_launch_sort_key)
	if flag:
		projects = [row for row in projects if bool(row["flags"].get(flag))]
	total = len(projects)
	page = projects[start : start + page_length]
	return {
		"generated_at": now_datetime(),
		"as_of": classification_at.isoformat(),
		"projection_policy": "READ_ONLY_NO_CACHE_NO_SECOND_SSOT",
		"credentials_policy": "BLOCKED_PENDING_MG-CA-015",
		"pagination": {
			"limit_start": start,
			"limit_page_length": page_length,
			"total": total,
			"returned": len(page),
		},
		"kpi": {
			"project_count": total,
			**{
				name: sum(bool(row["flags"].get(name)) for row in projects)
				for name in sorted(allowed_flags)
			},
		},
		"projects": page,
	}


def _todo_actions(
	user: str, as_of: datetime
) -> tuple[list[dict[str, Any]], dict[str, set[str]]]:
	rows: list[dict[str, Any]] = []
	referenced: dict[str, set[str]] = {}
	for todo in frappe.get_all(
		"ToDo",
		filters={"allocated_to": user, "status": "Open"},
		fields=[
			"name",
			"reference_type",
			"reference_name",
			"description",
			"date",
			"priority",
			"assigned_by",
		],
		order_by="date asc, name asc",
		limit_page_length=0,
	):
		if not todo.reference_type or not todo.reference_name:
			continue
		referenced.setdefault(str(todo.reference_type), set()).add(
			str(todo.reference_name)
		)
		row = _source_action(
			str(todo.reference_type),
			str(todo.reference_name),
			as_of,
			fallback_title=str(todo.description or todo.reference_name),
			fallback_due=todo.date,
		)
		if row is None:
			continue
		row["source_rank"] = 10
		row["assignment_mode"] = "ToDo"
		row["delivery_todos"] = [todo.name]
		row["assigned_by"] = todo.assigned_by
		rows.append(row)
	return rows, referenced


def _step_actions(
	user: str, as_of: datetime, referenced: dict[str, set[str]]
) -> list[dict[str, Any]]:
	names = set(referenced.get("Ferum Project Process Step", set()))
	names.update(
		frappe.get_all(
			"Ferum Project Process Step",
			filters={
				"responsible_user": user,
				"status": ["in", sorted(_PROCESS_ACTION_STATUSES)],
			},
			pluck="name",
			limit_page_length=0,
		)
	)
	roles = [role for role in frappe.get_roles(user) if role not in {"All", "Guest"}]
	if roles:
		names.update(
			frappe.get_all(
				"Ferum Project Process Step",
				filters={
					"responsible_role": ["in", roles],
					"responsible_user": ["is", "not set"],
					"status": ["in", sorted(_PROCESS_ACTION_STATUSES)],
				},
				pluck="name",
				limit_page_length=0,
			)
		)
	rows = []
	for name in sorted(names):
		row = _source_action("Ferum Project Process Step", str(name), as_of)
		if row:
			row["assignment_mode"] = (
				"User" if row.get("responsible_user") == user else "Role"
			)
			rows.append(row)
	return rows


def _owned_actions(
	doctype: str,
	owner_field: str,
	statuses: tuple[str, ...],
	user: str,
	as_of: datetime,
	referenced: dict[str, set[str]],
) -> list[dict[str, Any]]:
	names = set(referenced.get(doctype, set()))
	names.update(
		frappe.get_all(
			doctype,
			filters={owner_field: user, "status": ["in", list(statuses)]},
			pluck="name",
			limit_page_length=0,
		)
	)
	rows = []
	for name in sorted(names):
		row = _source_action(doctype, str(name), as_of)
		if row:
			row["assignment_mode"] = "Source Owner"
			rows.append(row)
	return rows


def _source_action(
	doctype: str,
	name: str,
	as_of: datetime,
	*,
	fallback_title: str | None = None,
	fallback_due: Any = None,
) -> dict[str, Any] | None:
	if not frappe.db.exists(doctype, name) or not _can_read(doctype, name):
		return None
	doc = frappe.get_doc(doctype, name)
	project = doc.get("service_project")
	if not project or not _can_read("Ferum Service Project", str(project)):
		return None

	if doctype == "Ferum Project Process Step":
		if doc.status not in _PROCESS_ACTION_STATUSES:
			return None
		title = doc.title
		due_at = doc.due_at or fallback_due
		status = doc.status
		details = {
			"project_process": doc.project_process,
			"project_stage": doc.project_stage,
			"responsible_role": doc.responsible_role,
			"responsible_user": doc.responsible_user,
			"warning_at": doc.warning_at,
			"escalation_at": doc.escalation_at,
			"failure_action": doc.failure_action,
			"timeout_action": doc.timeout_action,
		}
		source_rank = 0
	elif doctype == "Ferum Service Request":
		if doc.status not in {"Open", "Assigned", "In Progress"}:
			return None
		title = f"{doc.request_type}: {doc.name}"
		due_at = (
			doc.resolution_due
			if doc.actual_start or doc.status == "In Progress"
			else (doc.reaction_due or doc.resolution_due)
		) or fallback_due
		status = doc.status
		details = {"priority": doc.priority, "assigned_engineer": doc.assigned_engineer}
		source_rank = 1
	elif doctype == "Ferum Maintenance Visit":
		if doc.status not in {"Planned", "In Progress"}:
			return None
		title = f"Maintenance visit {doc.name}"
		due_at = doc.window_end or doc.planned_date or fallback_due
		status = doc.status
		details = {"assigned_engineer": doc.assigned_engineer, "planned_date": doc.planned_date}
		source_rank = 1
	elif doctype == "Ferum Project Document":
		if doc.status not in {"Draft", "Active"}:
			return None
		if doc.original_status in {"Requested", "In Transit"}:
			title = f"Receive original: {doc.document_type} {doc.document_number}"
			due_at = doc.original_expected_at or fallback_due
		elif doc.digital_copy_status in {"Missing", "Rejected"}:
			title = f"Prepare document: {doc.document_type} {doc.document_number}"
			due_at = doc.valid_until or fallback_due
		else:
			return None
		status = "Waiting External" if doc.original_status in {"Requested", "In Transit"} else "Ready"
		details = {
			"owner_user": doc.owner_user,
			"digital_copy_status": doc.digital_copy_status,
			"original_status": doc.original_status,
		}
		source_rank = 1
	else:
		status = str(doc.get("status") or "Ready")
		if status in TERMINAL_STATUSES:
			return None
		title = fallback_title or str(doc.get("title") or doc.get("subject") or name)
		due_at = fallback_due
		details = {}
		source_rank = 5

	due_datetime = get_datetime(due_at) if due_at else None
	classification = classify_action(status=status, due_at=due_datetime, as_of=as_of)
	return {
		"canonical_key": f"{doctype}:{name}",
		"source_type": doctype,
		"source_name": name,
		"source_rank": source_rank,
		"service_project": str(project),
		"project_label": frappe.db.get_value(
			"Ferum Service Project", project, "contract_number"
		)
		or str(project),
		"title": str(title),
		"status": status,
		"due_at": due_datetime.isoformat() if due_datetime else None,
		"details": details,
		"delivery_todos": [],
		"drilldown": _drilldown(
			doctype,
			name,
			"ferum-my-actions",
			{"time_bucket": classification["time_bucket"], "state_bucket": classification["state_bucket"]},
		),
		**classification,
	}


def _launch_view(project: Any, as_of: datetime) -> dict[str, Any]:
	process_row = frappe.db.get_value(
		"Ferum Project Process",
		{"service_project": project.name, "process_type": "Launch"},
		["name", "status", "template_version", "active_stage", "generated_at"],
		as_dict=True,
		order_by="generated_at desc, name desc",
	)
	template = frappe.db.get_value(
		"Ferum Process Template",
		{"code": TEMPLATE_CODE, "version": TEMPLATE_VERSION, "status": "Published"},
		"name",
	)
	requirements = frappe.get_all(
		"Ferum Contract Requirement",
		filters={"service_project": project.name},
		fields=["name", "assessment_status"],
		order_by="name asc",
		limit_page_length=0,
	)
	unassessed = [row.name for row in requirements if row.assessment_status == "Draft"]
	assessment_ready = bool(requirements) and not unassessed
	stages: list[dict[str, Any]] = []
	all_steps: list[dict[str, Any]] = []
	failed_gates: list[dict[str, Any]] = []
	if process_row:
		for stage in frappe.get_all(
			"Ferum Project Stage",
			filters={"project_process": process_row.name},
			fields=["name", "stage_code", "title", "sequence", "status", "primary_exit_gate"],
			order_by="sequence asc, name asc",
			limit_page_length=0,
		):
			steps = []
			for step in frappe.get_all(
				"Ferum Project Process Step",
				filters={"project_stage": stage.name},
				fields=[
					"name",
					"template_step_code",
					"title",
					"status",
					"due_at",
					"warning_at",
					"escalation_at",
					"responsible_role",
					"responsible_user",
					"blocking",
					"failure_action",
					"timeout_action",
				],
				order_by="creation asc, name asc",
				limit_page_length=0,
			):
				due_at = get_datetime(step.due_at) if step.due_at else None
				classified = classify_action(status=step.status, due_at=due_at, as_of=as_of)
				item = {
					**dict(step),
					"due_at": due_at.isoformat() if due_at else None,
					"drilldown": _drilldown(
						"Ferum Project Process Step",
						step.name,
						"ferum-project-launches",
						{"service_project": project.name},
					),
					**classified,
				}
				steps.append(item)
				all_steps.append(item)
			completed = sum(
				row["status"] in {"Completed", "Not Applicable"} for row in steps
			)
			gate = _gate_projection(stage.primary_exit_gate, project.name)
			if gate and gate["status"] == "Failed":
				failed_gates.append(gate)
			stages.append(
				{
					**dict(stage),
					"completed_steps": completed,
					"total_steps": len(steps),
					"progress_percent": progress(completed, len(steps)),
					"gate": gate,
					"steps": steps,
					"drilldown": _drilldown(
						"Ferum Project Stage",
						stage.name,
						"ferum-project-launches",
						{"service_project": project.name},
					),
				}
			)

	completed_steps = sum(
		row["status"] in {"Completed", "Not Applicable"} for row in all_steps
	)
	contractor_assignments = frappe.get_all(
		"Ferum Contractor Assignment",
		filters={"service_project": project.name, "execution_mode": "Contractor"},
		fields=["name", "status", "credentials_readiness"],
		order_by="name asc",
		limit_page_length=0,
	)
	contractor_step = next(
		(row for row in all_steps if row["template_step_code"] == "EXEC_CONTRACTOR_DOCS"),
		None,
	)
	missing_contractor = bool(
		contractor_step
		and contractor_step["status"] not in {"Completed", "Not Applicable", "Cancelled"}
		and not any(row.status == "Approved" for row in contractor_assignments)
	)
	waiting_customer = any(
		row["status"] == "Waiting External"
		and row["template_step_code"].startswith(("CUST_", "MOB_", "INSPECT_CUSTOMER_"))
		for row in all_steps
	)
	personnel_step = next(
		(row for row in all_steps if row["template_step_code"] == "PERSONNEL_READY"),
		None,
	)
	missing_credentials = bool(
		personnel_step
		and personnel_step["status"] not in {"Completed", "Not Applicable", "Cancelled"}
	)
	overdue = any(row["is_overdue"] for row in all_steps)
	blocking_conditions: list[dict[str, Any]] = []
	if not template:
		blocking_conditions.append(
			{"code": "REFERENCE_TEMPLATE_MISSING", "title": "Published FERUM-LAUNCH v1 is missing"}
		)
	if not assessment_ready:
		blocking_conditions.append(
			{
				"code": "REQUIREMENT_ASSESSMENT_INCOMPLETE",
				"title": "Requirement Assessment must exist and contain no Draft requirement",
				"sources": [
					_drilldown("Ferum Contract Requirement", name, "ferum-project-launches", {"service_project": project.name})
					for name in unassessed
				],
			}
		)
	for gate in failed_gates:
		blocking_conditions.append(
			{
				"code": "FAILED_STAGE_GATE",
				"title": gate["title"],
				"source": gate["drilldown"],
				"failed_criteria": gate["failed_criteria"],
			}
		)
	for step in all_steps:
		if step["status"] == "Blocked":
			blocking_conditions.append(
				{
					"code": "BLOCKED_PROCESS_STEP",
					"title": step["title"],
					"source": step["drilldown"],
					"failure_action": step["failure_action"],
				}
			)
	if missing_contractor:
		blocking_conditions.append(
			{
				"code": "CONTRACTOR_NOT_CONFIRMED",
				"title": "Contractor documents step is open and no Approved contractor assignment exists",
				"source": contractor_step["drilldown"] if contractor_step else None,
			}
		)
	if missing_credentials:
		blocking_conditions.append(
			{
				"code": "MG-CA-015",
				"title": "Personnel credential readiness is blocked pending legal/privacy evidence",
				"source": personnel_step["drilldown"] if personnel_step else None,
			}
		)

	flags = {
		"overdue": overdue,
		"blocked": bool(
			failed_gates
			or any(row["status"] == "Blocked" for row in all_steps)
			or not assessment_ready
		),
		"missing_contractor": missing_contractor,
		"waiting_customer": waiting_customer,
		"missing_credentials": missing_credentials,
	}
	return {
		"service_project": project.name,
		"contract_number": project.contract_number,
		"project_name": project.project_name,
		"customer": project.customer,
		"company": project.company,
		"project_manager": project.project_manager,
		"legal_status": project.legal_status,
		"execution_status": project.execution_status,
		"reference_template": template,
		"reference_version": TEMPLATE_VERSION,
		"requirement_assessment": {
			"ready": assessment_ready,
			"count": len(requirements),
			"draft_count": len(unassessed),
		},
		"eligible_for_generation": bool(
			template
			and assessment_ready
			and project.legal_status in {"Approved", "Signing", "Signed", "In Force"}
			and project.execution_status in {"Not Started", "Launching"}
			and not process_row
		),
		"process": dict(process_row) if process_row else None,
		"progress_percent": progress(completed_steps, len(all_steps)),
		"completed_steps": completed_steps,
		"total_steps": len(all_steps),
		"stages": stages,
		"failed_gates": failed_gates,
		"blocking_conditions": blocking_conditions,
		"flags": flags,
		"credentials_policy": "BLOCKED_PENDING_MG-CA-015",
		"drilldown": _drilldown(
			"Ferum Service Project",
			project.name,
			"ferum-project-launches",
			{"flag": next((name for name, value in flags.items() if value), "")},
		),
	}


def _gate_projection(name: str | None, project: str) -> dict[str, Any] | None:
	if not name or not frappe.db.exists("Ferum Stage Gate", name):
		return None
	gate = frappe.get_doc("Ferum Stage Gate", name)
	try:
		failed = json.loads(gate.failed_criteria or "[]")
	except (TypeError, ValueError):
		failed = [{"error": "INVALID_FAILED_CRITERIA_JSON"}]
	return {
		"name": gate.name,
		"title": gate.title,
		"status": gate.status,
		"evaluated_at": gate.evaluated_at,
		"failed_criteria": failed,
		"drilldown": _drilldown(
			gate.doctype,
			gate.name,
			"ferum-project-launches",
			{"service_project": project},
		),
	}


def _launch_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
	flags = row["flags"]
	return (
		0 if flags["overdue"] else 1,
		0 if flags["blocked"] else 1,
		row["progress_percent"],
		str(row["contract_number"] or ""),
		row["service_project"],
	)


def _authorized_project(service_project: str) -> Any:
	if not frappe.db.exists("Ferum Service Project", service_project):
		frappe.throw(_("Ferum Service Project not found."), frappe.DoesNotExistError)
	project = frappe.get_doc("Ferum Service Project", service_project)
	project.check_permission("read")
	return project


def _can_read(doctype: str, name: str) -> bool:
	return frappe.session.user == "Administrator" or bool(
		frappe.has_permission(doctype, "read", doc=name)
	)


def _require_launch_role() -> None:
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles(frappe.session.user)).intersection(_LAUNCH_ROLES):
		frappe.throw(_("Role does not allow Project Launches."), frappe.PermissionError)


def _as_of(value: str | None) -> datetime:
	return get_datetime(value).replace(tzinfo=None) if value else now_datetime().replace(tzinfo=None)


def _validate_filter(value: str | None, allowed: frozenset[str], fieldname: str) -> None:
	if value and value not in allowed:
		frappe.throw(_("Invalid {0} filter.").format(fieldname))


def _drilldown(
	doctype: str,
	name: str,
	return_route: str,
	return_filters: dict[str, Any],
) -> dict[str, Any]:
	return {
		"doctype": doctype,
		"name": name,
		"route": ["Form", doctype, name],
		"context": {
			"return_route": return_route,
			"return_filters": return_filters,
		},
	}
