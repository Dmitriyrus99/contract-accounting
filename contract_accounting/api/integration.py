"""CA-15 permission-safe end-to-end trace and read-only integrity diagnostics."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from typing import Any, Final

import frappe
from frappe import _
from frappe.utils import now_datetime

from contract_accounting.api.contract_360 import get_contract_360
from contract_accounting.api.finance import can_read_finance, get_finance_trace

_INTEGRITY_ROLES: Final[frozenset[str]] = frozenset(
	{"Генеральный директор", "Руководитель проектов", "System Manager"}
)


@dataclass(frozen=True, slots=True)
class EdgeSpec:
	child_doctype: str
	fieldname: str
	target_doctype: str | None
	dynamic_type_field: str | None = None
	required: bool = False


_EDGE_SPECS: Final[tuple[EdgeSpec, ...]] = (
	EdgeSpec("Ferum Contract Amendment", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Contract Requirement", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Contract Obligation", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Contract Obligation", "requirement", "Ferum Contract Requirement"),
	EdgeSpec("Ferum Contract Obligation", "project_object", "Ferum Project Object"),
	EdgeSpec("Ferum Contract Obligation", "object_system", "Ferum Object System"),
	EdgeSpec("Ferum Project Object", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Project Object", "service_object", "Ferum Service Object", required=True),
	EdgeSpec("Ferum Object System", "service_object", "Ferum Service Object", required=True),
	EdgeSpec("Ferum Maintenance Schedule", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Maintenance Schedule", "contract_obligation", "Ferum Contract Obligation", required=True),
	EdgeSpec("Ferum Maintenance Schedule", "project_object", "Ferum Project Object", required=True),
	EdgeSpec("Ferum Maintenance Schedule", "object_system", "Ferum Object System"),
	EdgeSpec("Ferum Maintenance Schedule", "generated_visit", "Ferum Maintenance Visit"),
	EdgeSpec("Ferum Maintenance Visit", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Maintenance Visit", "contract_obligation", "Ferum Contract Obligation", required=True),
	EdgeSpec("Ferum Maintenance Visit", "maintenance_schedule", "Ferum Maintenance Schedule"),
	EdgeSpec("Ferum Maintenance Visit", "project_object", "Ferum Project Object", required=True),
	EdgeSpec("Ferum Maintenance Visit", "service_object", "Ferum Service Object", required=True),
	EdgeSpec("Ferum Maintenance Visit", "object_system", "Ferum Object System"),
	EdgeSpec("Ferum Service Request", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Service Request", "contract_obligation", "Ferum Contract Obligation"),
	EdgeSpec("Ferum Service Request", "project_object", "Ferum Project Object", required=True),
	EdgeSpec("Ferum Service Request", "service_object", "Ferum Service Object"),
	EdgeSpec("Ferum Service Request", "object_system", "Ferum Object System"),
	EdgeSpec("Ferum Finding", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Finding", "project_object", "Ferum Project Object"),
	EdgeSpec("Ferum Finding", "service_object", "Ferum Service Object"),
	EdgeSpec("Ferum Finding", "object_system", "Ferum Object System"),
	EdgeSpec("Ferum Finding", "source_name", None, dynamic_type_field="source_doctype"),
	EdgeSpec("Ferum Photo Evidence", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Photo Evidence", "project_object", "Ferum Project Object"),
	EdgeSpec("Ferum Photo Evidence", "service_object", "Ferum Service Object"),
	EdgeSpec("Ferum Photo Evidence", "object_system", "Ferum Object System"),
	EdgeSpec("Ferum Photo Evidence", "source_name", None, dynamic_type_field="source_doctype", required=True),
	EdgeSpec("Ferum Project Document", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Project Document", "project_object", "Ferum Project Object"),
	EdgeSpec("Ferum Project Document", "service_object", "Ferum Service Object"),
	EdgeSpec("Ferum Project Document", "source_name", None, dynamic_type_field="source_doctype"),
	EdgeSpec("Ferum Project Process", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Project Process Step", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Project Process Step", "project_process", "Ferum Project Process", required=True),
	EdgeSpec("Ferum Project Process Step", "contract_requirement", "Ferum Contract Requirement"),
	EdgeSpec("Ferum Project Process Step", "contract_obligation", "Ferum Contract Obligation"),
	EdgeSpec("Ferum Billing Cycle", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Billing Cycle", "project_process", "Ferum Project Process"),
	EdgeSpec("Ferum Billing Output", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Billing Output", "billing_cycle", "Ferum Billing Cycle"),
	EdgeSpec("Ferum Billing Output", "sales_invoice", "Sales Invoice"),
	EdgeSpec("Ferum Contractor Assignment", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Contractor Assignment", "project_object", "Ferum Project Object", required=True),
	EdgeSpec("Ferum Contractor Assignment", "object_system", "Ferum Object System"),
	EdgeSpec("Ferum Contractor Assignment", "contract_obligation", "Ferum Contract Obligation"),
	EdgeSpec("Ferum Material Expense", "service_project", "Ferum Service Project", required=True),
	EdgeSpec("Ferum Material Expense", "contract_obligation", "Ferum Contract Obligation"),
	EdgeSpec("Ferum Material Expense", "contractor_assignment", "Ferum Contractor Assignment"),
	EdgeSpec("Ferum Material Expense", "maintenance_visit", "Ferum Maintenance Visit"),
	EdgeSpec("Ferum Material Expense", "service_request", "Ferum Service Request"),
	EdgeSpec("Ferum Project Finance Summary", "service_project", "Ferum Service Project", required=True),
)


@frappe.whitelist()
def get_end_to_end_trace(service_project: str, as_of: str | None = None) -> dict[str, Any]:
	"""Answer why/where/when/who/result/evidence/billing/payment/margin from source records."""

	_project(service_project).check_permission("read")
	card = get_contract_360(service_project, as_of=as_of)
	widgets = card["widgets"]
	photo_evidence = _visible_project_rows(
		"Ferum Photo Evidence",
		service_project,
		["source_doctype", "source_name", "project_object", "service_object", "object_system", "file", "captured_at", "captured_by", "review_status"],
	)
	documents = widgets["documents"]["items"]
	finance_trace = _finance_trace(service_project)
	audit_events = _visible_project_rows(
		"Ferum Lifecycle Audit Event",
		service_project,
		["dimension", "from_status", "to_status", "actor", "occurred_at", "reason", "correlation_id"],
	) + _visible_project_rows(
		"Ferum Process Event",
		service_project,
		["event_type", "source_doctype", "source_name", "project_process", "occurred_at", "actor", "event_hash"],
	)

	segments = [
		_segment("why", "Почему", widgets["requirements"]["items"] + widgets["obligations"]["items"]),
		_segment("where", "Где", widgets["objects"]["items"] + widgets["systems"]["items"]),
		_segment("when", "Когда", widgets["maintenance"]["schedules"] + widgets["deadlines"]["rows"]),
		_segment("who", "Кто", _actors(widgets)),
		_segment("result", "Что сделано", widgets["maintenance"]["visits"] + widgets["requests"]["items"] + widgets["findings"]["items"]),
		_segment("evidence", "Чем подтверждено", photo_evidence + documents),
		_segment("billing", "Что выставлено", _billing_items(widgets, finance_trace)),
		_segment("payment", "Что оплачено", finance_trace.get("payment_entries", []), access=finance_trace["access"]),
		_segment("margin", "Сколько заработали", _margin_items(card["finance"]), access=card["finance"]["access"]),
	]
	payload: dict[str, Any] = {
		"generated_at": now_datetime(),
		"service_project": service_project,
		"identity": card["identity"],
		"segments": segments,
		"cross_cutting_dimensions": [
			_segment("contractors", "Подрядчики", widgets["contractors"]["items"]),
			_segment("materials", "Материалы", finance_trace.get("material_expenses", []), access=finance_trace["access"]),
			_segment(
				"costs",
				"Затраты",
				finance_trace.get("purchase_invoices", []) + finance_trace.get("contractor_settlements", []),
				access=finance_trace["access"],
			),
			_segment("documents", "Документы", documents),
			_segment(
				"communications",
				"Коммуникации",
				[row for row in documents if row.get("document_type") == "Correspondence"],
			),
			_segment("deadlines", "Сроки", widgets["deadlines"]["rows"]),
			_segment("audit", "Аудит", audit_events),
		],
		"exceptions": card["exceptions"],
		"policies": {
			"project_ssot": "Ferum Service Project",
			"projection": "READ_ONLY_NO_CACHE_NO_SECOND_SSOT",
			"finance": "ERPNext submitted accounting SSOT; Ferum summary is rebuildable",
			"import_batch": "INACTIVE_NOT_PRODUCTION_PROVEN_PENDING_MG-CA-023",
		},
	}
	payload["source_fingerprint"] = _fingerprint(payload)
	return payload


@frappe.whitelist()
def get_project_integrity_report(service_project: str) -> dict[str, Any]:
	"""Scan CA-15 project graph without changing source records."""

	_require_integrity_role()
	_project(service_project).check_permission("read")
	rows_by_doctype, skipped = _integrity_rows(service_project)
	issues: list[dict[str, Any]] = []
	edges: list[dict[str, Any]] = []
	for spec in _EDGE_SPECS:
		if spec.child_doctype not in rows_by_doctype:
			continue
		for row in rows_by_doctype[spec.child_doctype]:
			value = row.get(spec.fieldname)
			target_doctype = row.get(spec.dynamic_type_field) if spec.dynamic_type_field else spec.target_doctype
			state = "valid"
			if not value:
				state = "missing_required" if spec.required else "optional_absent"
				if spec.required:
					issues.append(_issue("MISSING_REQUIRED_LINK", spec, row, target_doctype, value))
			elif not _target_exists(target_doctype, value):
				state = "orphan"
				issues.append(_issue("ORPHAN_LINK", spec, row, target_doctype, value))
			elif _target_project_mismatch(str(target_doctype), str(value), service_project):
				state = "project_mismatch"
				issues.append(_issue("PROJECT_SCOPE_MISMATCH", spec, row, target_doctype, value))
			edges.append(
				{
					"source": {"doctype": spec.child_doctype, "name": row["name"]},
					"fieldname": spec.fieldname,
					"target": {"doctype": target_doctype, "name": value} if value else None,
					"state": state,
				}
			)
	issues.sort(key=lambda row: row["issue_key"])
	state_counts = Counter(edge["state"] for edge in edges)
	return {
		"generated_at": now_datetime(),
		"service_project": service_project,
		"mode": "READ_ONLY_DRY_RUN",
		"visibility_scope": "AUTHORIZED_RECORDS_ONLY",
		"summary": {
			"records_scanned": sum(len(rows) for rows in rows_by_doctype.values()),
			"edges_scanned": len(edges),
			"issues": len(issues),
			"orphans": sum(issue["code"] == "ORPHAN_LINK" for issue in issues),
			"project_scope_mismatches": sum(issue["code"] == "PROJECT_SCOPE_MISMATCH" for issue in issues),
			"by_edge_state": dict(sorted(state_counts.items())),
			"records_hidden_by_permission": skipped,
		},
		"issues": issues,
		"edges": edges,
		"release_capabilities": {
			"end_to_end_trace": "IMPLEMENTED_READ_ONLY",
			"integrity_scan": "IMPLEMENTED_PROJECT_SCOPE",
			"import_batch": "INACTIVE_NOT_PRODUCTION_PROVEN_PENDING_MG-CA-023",
		},
	}


def _integrity_rows(service_project: str) -> tuple[dict[str, list[dict[str, Any]]], int]:
	doctypes = sorted({spec.child_doctype for spec in _EDGE_SPECS})
	project_objects = frappe.get_all(
		"Ferum Project Object", filters={"service_project": service_project}, fields=["name", "service_object"]
	)
	service_objects = sorted({str(row.service_object) for row in project_objects if row.service_object})
	rows_by_doctype: dict[str, list[dict[str, Any]]] = {}
	skipped = 0
	for doctype in doctypes:
		if not frappe.db.table_exists(doctype):
			continue
		meta = frappe.get_meta(doctype)
		fields = sorted(
			{"name"}
			| {
				spec.fieldname
				for spec in _EDGE_SPECS
				if spec.child_doctype == doctype and meta.has_field(spec.fieldname)
			}
			| {
				spec.dynamic_type_field
				for spec in _EDGE_SPECS
				if spec.child_doctype == doctype and spec.dynamic_type_field and meta.has_field(spec.dynamic_type_field)
			}
		)
		if meta.has_field("service_project"):
			filters: dict[str, Any] = {"service_project": service_project}
		elif doctype == "Ferum Object System":
			filters = {"service_object": ["in", service_objects]} if service_objects else {"name": ["in", []]}
		else:
			continue
		visible: list[dict[str, Any]] = []
		for row in frappe.get_all(doctype, filters=filters, fields=fields, order_by="name asc", limit_page_length=0):
			if frappe.session.user != "Administrator" and not frappe.has_permission(doctype, "read", doc=row.name):
				skipped += 1
				continue
			visible.append(dict(row))
		rows_by_doctype[doctype] = visible
	return rows_by_doctype, skipped


def _target_project_mismatch(target_doctype: str, target_name: str, service_project: str) -> bool:
	if not frappe.db.table_exists(target_doctype):
		return False
	meta = frappe.get_meta(target_doctype)
	if not meta.has_field("service_project"):
		return False
	target_project = frappe.db.get_value(target_doctype, target_name, "service_project")
	return bool(target_project and target_project != service_project)


def _target_exists(target_doctype: Any, target_name: Any) -> bool:
	if not target_doctype or not target_name:
		return False
	doctype = str(target_doctype)
	if not frappe.db.exists("DocType", doctype) or not frappe.db.table_exists(doctype):
		return False
	return bool(frappe.db.exists(doctype, str(target_name)))


def _issue(code: str, spec: EdgeSpec, row: dict[str, Any], target_doctype: Any, value: Any) -> dict[str, Any]:
	canonical = f"{code}|{spec.child_doctype}|{row['name']}|{spec.fieldname}|{target_doctype or ''}|{value or ''}"
	return {
		"issue_key": hashlib.sha256(canonical.encode()).hexdigest()[:20],
		"code": code,
		"source_doctype": spec.child_doctype,
		"source_name": row["name"],
		"fieldname": spec.fieldname,
		"target_doctype": target_doctype,
		"target_name": value,
	}


def _visible_project_rows(doctype: str, service_project: str, fields: list[str]) -> list[dict[str, Any]]:
	result: list[dict[str, Any]] = []
	for row in frappe.get_all(
		doctype,
		filters={"service_project": service_project},
		fields=["name", *fields],
		order_by="name asc",
		limit_page_length=0,
	):
		if frappe.session.user != "Administrator" and not frappe.has_permission(doctype, "read", doc=row.name):
			continue
		item = dict(row)
		if "source_doctype" in item:
			item["evidence_source_doctype"] = item["source_doctype"]
			item["evidence_source_name"] = item.get("source_name")
		item.update({"source_doctype": doctype, "source_name": row.name, "drilldown": _drilldown(doctype, row.name)})
		result.append(item)
	return result


def _actors(widgets: dict[str, Any]) -> list[dict[str, Any]]:
	items: list[dict[str, Any]] = list(widgets["contractors"]["items"])
	for collection, fieldname in (
		(widgets["maintenance"]["visits"], "assigned_engineer"),
		(widgets["requests"]["items"], "assigned_engineer"),
		(widgets["findings"]["items"], "responsible"),
	):
		for row in collection:
			if row.get(fieldname):
				items.append(
					{
						"actor": row[fieldname],
						"actor_kind": "User",
						"source_doctype": row["source_doctype"],
						"source_name": row["source_name"],
						"drilldown": row["drilldown"],
					}
				)
	return items


def _finance_trace(service_project: str) -> dict[str, Any]:
	if not can_read_finance():
		return {"access": "restricted", "sales_invoices": [], "payment_entries": []}
	trace = get_finance_trace(service_project)
	for row in trace["sales_invoices"]:
		row.update({"source_doctype": "Sales Invoice", "source_name": row["name"], "drilldown": _drilldown("Sales Invoice", row["name"])})
	for row in trace["payment_entries"]:
		row.update({"source_doctype": "Payment Entry", "source_name": row["parent"], "drilldown": _drilldown("Payment Entry", row["parent"])})
	for key, doctype in (
		("purchase_invoices", "Purchase Invoice"),
		("material_expenses", "Ferum Material Expense"),
		("contractor_settlements", "Ferum Contractor Settlement"),
	):
		for row in trace[key]:
			row.update({"source_doctype": doctype, "source_name": row["name"], "drilldown": _drilldown(doctype, row["name"])})
	trace["access"] = "granted"
	return trace


def _billing_items(widgets: dict[str, Any], finance_trace: dict[str, Any]) -> list[dict[str, Any]]:
	return list(widgets["billing"]["items"]) + list(finance_trace.get("sales_invoices", []))


def _margin_items(finance: dict[str, Any]) -> list[dict[str, Any]]:
	if finance.get("access") != "granted" or finance.get("status") != "available":
		return []
	return [
		{
			"source_doctype": "Ferum Project Finance Summary",
			"source_name": finance["summary"],
			"profit_without_vat": finance["profit_without_vat"],
			"profitability_percent": finance["profitability_percent"],
			"currency": finance["currency"],
			"drilldown": finance["drilldown"],
		}
	]


def _segment(key: str, label: str, items: list[dict[str, Any]], access: str = "granted") -> dict[str, Any]:
	return {"key": key, "label": label, "access": access, "count": len(items), "items": items}


def _fingerprint(payload: dict[str, Any]) -> str:
	stable = {key: value for key, value in payload.items() if key not in {"generated_at", "source_fingerprint"}}
	return hashlib.sha256(json.dumps(stable, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def _project(service_project: str) -> Any:
	if not frappe.db.exists("Ferum Service Project", service_project):
		frappe.throw(_("Ferum Service Project не найден."), frappe.DoesNotExistError)
	return frappe.get_doc("Ferum Service Project", service_project)


def _require_integrity_role() -> None:
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles(frappe.session.user)).intersection(_INTEGRITY_ROLES):
		frappe.throw(_("Недостаточно прав: project integrity report."), frappe.PermissionError)


def _drilldown(doctype: str, name: str) -> dict[str, str]:
	return {"doctype": doctype, "name": name}
