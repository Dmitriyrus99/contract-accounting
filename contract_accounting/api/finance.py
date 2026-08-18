"""CA-07 rebuildable finance read-model over standard ERPNext accounting SSOT."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any, Final, TypeVar

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime, today

from contract_accounting.contract_accounting.doctype.ferum_contractor_settlement.ferum_contractor_settlement import (
	DOCTYPE as SETTLEMENT_DOCTYPE,
)
from contract_accounting.contract_accounting.doctype.ferum_contractor_settlement.ferum_contractor_settlement import (
	RECOGNIZED_STATUSES,
	SETTLEMENT_TRANSITION_FLAG,
	SETTLEMENT_WRITER_FLAG,
)
from contract_accounting.contract_accounting.doctype.ferum_material_expense.ferum_material_expense import (
	DOCTYPE as MATERIAL_DOCTYPE,
)
from contract_accounting.contract_accounting.doctype.ferum_material_expense.ferum_material_expense import (
	MATERIAL_TRANSITION_FLAG,
	MATERIAL_WRITER_FLAG,
)
from contract_accounting.contract_accounting.doctype.ferum_project_finance_summary.ferum_project_finance_summary import (
	DOCTYPE as SUMMARY_DOCTYPE,
)
from contract_accounting.contract_accounting.doctype.ferum_project_finance_summary.ferum_project_finance_summary import (
	SUMMARY_WRITER_FLAG,
)

_T = TypeVar("_T")
_FINANCE_READ_ROLES: Final[frozenset[str]] = frozenset(
	{"Бухгалтер", "Руководитель проектов", "Генеральный директор", "System Manager"}
)
_MATERIAL_CREATE_ROLES: Final[frozenset[str]] = frozenset(
	{"Бухгалтер", "Менеджер проектов", "Инженер", "System Manager"}
)
_MATERIAL_APPROVE_ROLES: Final[frozenset[str]] = frozenset(
	{"Бухгалтер", "Руководитель проектов", "System Manager"}
)
_SETTLEMENT_CREATE_ROLES: Final[frozenset[str]] = frozenset(
	{"Бухгалтер", "Руководитель проектов", "System Manager"}
)
_SETTLEMENT_APPROVE_ROLES: Final[frozenset[str]] = _SETTLEMENT_CREATE_ROLES
_SETTLEMENT_SETTLE_ROLES: Final[frozenset[str]] = frozenset({"Бухгалтер", "System Manager"})
_MONEY_FIELDS: Final[tuple[str, ...]] = (
	"contract_amount_with_vat",
	"recognized_revenue_without_vat",
	"invoiced_with_vat",
	"paid_with_vat",
	"outstanding_with_vat",
	"overdue_ar_with_vat",
	"material_cost_without_vat",
	"contractor_cost_without_vat",
	"other_cost_without_vat",
	"total_cost_without_vat",
	"profit_without_vat",
	"profitability_percent",
)


@frappe.whitelist(methods=["POST"])
def create_material_expense(
	service_project: str,
	expense_date: str,
	amount_with_vat: float,
	amount_without_vat: float | None = None,
	project_object: str | None = None,
	contract_obligation: str | None = None,
	maintenance_visit: str | None = None,
	service_request: str | None = None,
	item: str | None = None,
	uom: str | None = None,
	qty: float | None = None,
	supplier: str | None = None,
	purchase_invoice: str | None = None,
	stock_entry: str | None = None,
	description: str | None = None,
) -> dict[str, str]:
	_require_role(_MATERIAL_CREATE_ROLES, "create Material Expense")
	_project(service_project).check_permission("read")
	doc = frappe.get_doc(
		{
			"doctype": MATERIAL_DOCTYPE,
			"service_project": service_project,
			"expense_date": expense_date,
			"amount_with_vat": amount_with_vat,
			"amount_without_vat": amount_without_vat,
			"project_object": project_object,
			"contract_obligation": contract_obligation,
			"maintenance_visit": maintenance_visit,
			"service_request": service_request,
			"item": item,
			"uom": uom,
			"qty": qty,
			"supplier": supplier,
			"purchase_invoice": purchase_invoice,
			"stock_entry": stock_entry,
			"description": description,
		}
	)
	_with_flag(MATERIAL_WRITER_FLAG, True, lambda: doc.insert(ignore_permissions=True))
	return {"material_expense": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def change_material_expense_status(name: str, target_status: str, reason: str) -> dict[str, str]:
	_require_role(_MATERIAL_APPROVE_ROLES, "Material Expense transition")
	if target_status not in {"Approved", "Cancelled"}:
		frappe.throw(_("Material Expense target status не разрешён."))
	if not str(reason or "").strip():
		frappe.throw(_("Material Expense transition требует reason."))
	save_point = _savepoint("material")
	try:
		frappe.db.get_value(MATERIAL_DOCTYPE, name, "name", for_update=True)
		doc = frappe.get_doc(MATERIAL_DOCTYPE, name)
		doc.check_permission("write")
		doc.status = target_status
		doc.status_reason = reason.strip()
		if target_status == "Approved":
			doc.approved_at = now_datetime()
			doc.approved_by = frappe.session.user
		else:
			doc.cancelled_at = now_datetime()
			doc.cancelled_by = frappe.session.user
		_with_transition(
			MATERIAL_WRITER_FLAG,
			MATERIAL_TRANSITION_FLAG,
			target_status,
			lambda: doc.save(ignore_permissions=True),
		)
		recalculate_project(doc.service_project)
		return {"material_expense": doc.name, "status": doc.status}
	except Exception:
		frappe.db.rollback(save_point=save_point)
		raise


@frappe.whitelist(methods=["POST"])
def create_contractor_settlement(
	service_project: str,
	supplier: str,
	period_start: str,
	period_end: str,
	planned_amount: float = 0,
	approved_amount: float = 0,
	project_object: str | None = None,
	contract_obligation: str | None = None,
	purchase_invoice: str | None = None,
	payment_entry: str | None = None,
) -> dict[str, str]:
	_require_role(_SETTLEMENT_CREATE_ROLES, "create Contractor Settlement")
	_project(service_project).check_permission("read")
	doc = frappe.get_doc(
		{
			"doctype": SETTLEMENT_DOCTYPE,
			"service_project": service_project,
			"supplier": supplier,
			"period_start": period_start,
			"period_end": period_end,
			"planned_amount": planned_amount,
			"approved_amount": approved_amount,
			"project_object": project_object,
			"contract_obligation": contract_obligation,
			"purchase_invoice": purchase_invoice,
			"payment_entry": payment_entry,
		}
	)
	_with_flag(SETTLEMENT_WRITER_FLAG, True, lambda: doc.insert(ignore_permissions=True))
	return {"contractor_settlement": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def change_contractor_settlement_status(
	name: str, target_status: str, reason: str
) -> dict[str, str]:
	roles = _SETTLEMENT_SETTLE_ROLES if target_status == "Settled" else _SETTLEMENT_APPROVE_ROLES
	_require_role(roles, "Contractor Settlement transition")
	if target_status not in {"Approved", "Settled", "Cancelled"}:
		frappe.throw(_("Contractor Settlement target status не разрешён."))
	if not str(reason or "").strip():
		frappe.throw(_("Contractor Settlement transition требует reason."))
	save_point = _savepoint("settlement")
	try:
		frappe.db.get_value(SETTLEMENT_DOCTYPE, name, "name", for_update=True)
		doc = frappe.get_doc(SETTLEMENT_DOCTYPE, name)
		doc.check_permission("write")
		doc.status = target_status
		doc.status_reason = reason.strip()
		if target_status == "Approved":
			doc.approved_at = now_datetime()
			doc.approved_by = frappe.session.user
		elif target_status == "Settled":
			doc.settled_at = now_datetime()
			doc.settled_by = frappe.session.user
		else:
			doc.cancelled_at = now_datetime()
			doc.cancelled_by = frappe.session.user
		_with_transition(
			SETTLEMENT_WRITER_FLAG,
			SETTLEMENT_TRANSITION_FLAG,
			target_status,
			lambda: doc.save(ignore_permissions=True),
		)
		recalculate_project(doc.service_project)
		return {"contractor_settlement": doc.name, "status": doc.status}
	except Exception:
		frappe.db.rollback(save_point=save_point)
		raise


@frappe.whitelist(methods=["POST"])
def recalculate_finance_summary(service_project: str) -> dict[str, Any]:
	_require_role(_FINANCE_READ_ROLES, "recalculate Finance Summary")
	_project(service_project).check_permission("read")
	doc = recalculate_project(service_project)
	return _summary_dict(doc)


@frappe.whitelist(methods=["POST"])
def recalculate_all_finance_summaries() -> dict[str, int]:
	_require_role(_FINANCE_READ_ROLES, "recalculate all Finance Summaries")
	count = 0
	for service_project in frappe.get_all("Ferum Service Project", pluck="name", order_by="name asc"):
		project = _project(str(service_project))
		project.check_permission("read")
		recalculate_project(str(service_project))
		count += 1
	return {"projects_recalculated": count}


@frappe.whitelist()
def get_finance_trace(service_project: str) -> dict[str, Any]:
	_require_role(_FINANCE_READ_ROLES, "read Finance Trace")
	_project(service_project).check_permission("read")
	fields, trace = _calculate(service_project)
	return {"service_project": service_project, "calculated": fields, **trace}


@frappe.whitelist()
def get_finance_reconciliation(service_project: str) -> dict[str, Any]:
	_require_role(_FINANCE_READ_ROLES, "read Finance Reconciliation")
	_project(service_project).check_permission("read")
	expected, _trace = _calculate(service_project)
	name = frappe.db.get_value(SUMMARY_DOCTYPE, {"service_project": service_project}, "name")
	if not name:
		return {"service_project": service_project, "is_reconciled": False, "reason": "summary_missing"}
	doc = frappe.get_doc(SUMMARY_DOCTYPE, name)
	differences = {
		field: {"stored": flt(doc.get(field), 6), "expected": flt(expected[field], 6)}
		for field in _MONEY_FIELDS
		if flt(doc.get(field), 6) != flt(expected[field], 6)
	}
	if doc.source_fingerprint != expected["source_fingerprint"]:
		differences["source_fingerprint"] = {
			"stored": doc.source_fingerprint,
			"expected": expected["source_fingerprint"],
		}
	return {
		"service_project": service_project,
		"summary": name,
		"is_reconciled": not differences,
		"differences": differences,
	}


@frappe.whitelist()
def get_portfolio_finance(
	company: str | None = None,
	customer: str | None = None,
	project_manager: str | None = None,
) -> dict[str, Any]:
	_require_role(_FINANCE_READ_ROLES, "read Finance Portfolio")
	filters: dict[str, Any] = {}
	if company:
		filters["company"] = company
	if customer:
		filters["customer"] = customer
	if project_manager:
		filters["project_manager"] = project_manager
	projects = frappe.get_all(
		"Ferum Service Project",
		filters=filters,
		fields=["name", "company", "customer", "project_manager"],
		order_by="name asc",
	)
	groups: dict[tuple[str, str], dict[str, Any]] = {}
	missing: list[str] = []
	for project_row in projects:
		project = _project(project_row.name)
		project.check_permission("read")
		name = frappe.db.get_value(SUMMARY_DOCTYPE, {"service_project": project.name}, "name")
		if not name:
			missing.append(project.name)
			continue
		summary = frappe.get_doc(SUMMARY_DOCTYPE, name)
		key = (summary.company, summary.currency)
		group = groups.setdefault(
			key,
			{
				"company": summary.company,
				"currency": summary.currency,
				"project_count": 0,
				**{field: 0.0 for field in _MONEY_FIELDS if field != "profitability_percent"},
			},
		)
		group["project_count"] += 1
		for field in _MONEY_FIELDS:
			if field != "profitability_percent":
				group[field] = flt(group[field]) + flt(summary.get(field))
	for group in groups.values():
		revenue = flt(group["recognized_revenue_without_vat"])
		group["profitability_percent"] = flt(group["profit_without_vat"] / revenue * 100, 6) if revenue else 0
	return {
		"groups": sorted(groups.values(), key=lambda row: (row["company"], row["currency"])),
		"missing_summaries": missing,
	}


def recalculate_project(service_project: str) -> Any:
	fields, _trace = _calculate(service_project)
	name = frappe.db.get_value(SUMMARY_DOCTYPE, {"service_project": service_project}, "name")
	doc = frappe.get_doc(SUMMARY_DOCTYPE, name) if name else frappe.new_doc(SUMMARY_DOCTYPE)
	doc.service_project = service_project
	for fieldname, value in fields.items():
		doc.set(fieldname, value)
	doc.last_recalculated_at = now_datetime()
	_with_flag(
		SUMMARY_WRITER_FLAG,
		True,
		lambda: doc.save(ignore_permissions=True) if name else doc.insert(ignore_permissions=True),
	)
	return doc


def assert_purchase_invoice_available(
	purchase_invoice: str, exclude_doctype: str, exclude_name: str | None
) -> None:
	checks = (
		(MATERIAL_DOCTYPE, ["Approved"]),
		(SETTLEMENT_DOCTYPE, sorted(RECOGNIZED_STATUSES)),
	)
	for doctype, statuses in checks:
		filters: dict[str, Any] = {
			"purchase_invoice": purchase_invoice,
			"status": ["in", statuses],
		}
		if doctype == exclude_doctype and exclude_name:
			filters["name"] = ["!=", exclude_name]
		claim = frappe.db.exists(doctype, filters)
		if claim:
			frappe.throw(
				_("Purchase Invoice уже классифицирован: {0} {1}.").format(doctype, claim),
				frappe.ValidationError,
			)


def _calculate(service_project: str) -> tuple[dict[str, Any], dict[str, Any]]:
	project = _project(service_project)
	company_currency = frappe.db.get_value("Company", project.company, "default_currency")
	if project.currency != company_currency:
		frappe.throw(_("CA-07 Finance Summary поддерживает только валюту Company."))
	sales_invoices = frappe.get_all(
		"Sales Invoice",
		filters={"ferum_service_project": service_project, "docstatus": 1},
		fields=[
			"name", "posting_date", "due_date", "is_opening", "base_net_total", "base_grand_total",
			"outstanding_amount", "conversion_rate", "currency",
		],
		order_by="posting_date asc, name asc",
	)
	purchase_invoices = frappe.get_all(
		"Purchase Invoice",
		filters={"ferum_service_project": service_project, "docstatus": 1},
		fields=[
			"name", "posting_date", "supplier", "base_net_total", "base_grand_total",
			"outstanding_amount", "currency",
		],
		order_by="posting_date asc, name asc",
	)
	materials = frappe.get_all(
		MATERIAL_DOCTYPE,
		filters={"service_project": service_project, "status": "Approved"},
		fields=[
			"name", "expense_date", "contract_obligation", "purchase_invoice",
			"base_amount_without_vat", "base_amount_with_vat", "status",
		],
		order_by="expense_date asc, name asc",
	)
	settlements = frappe.get_all(
		SETTLEMENT_DOCTYPE,
		filters={"service_project": service_project, "status": ["in", sorted(RECOGNIZED_STATUSES)]},
		fields=[
			"name", "period_start", "period_end", "contract_obligation", "supplier",
			"purchase_invoice", "payment_entry", "base_approved_amount", "paid_amount",
			"payable_amount", "status",
		],
		order_by="period_end asc, name asc",
	)
	pi_map = {row.name: row for row in purchase_invoices}
	classifications: dict[str, tuple[str, str]] = {}
	material_cost = 0.0
	contractor_cost = 0.0
	for kind, rows in (("Material", materials), ("Contractor", settlements)):
		for row in rows:
			if row.purchase_invoice:
				if row.purchase_invoice not in pi_map:
					frappe.throw(_("Признанная management-запись ссылается не на submitted project PI."))
				if row.purchase_invoice in classifications:
					frappe.throw(_("Purchase Invoice имеет две признанные cost classification."))
				classifications[row.purchase_invoice] = (kind, row.name)
			elif kind == "Material":
				material_cost += flt(row.base_amount_without_vat)
			else:
				contractor_cost += flt(row.base_approved_amount)
	other_cost = 0.0
	for invoice in purchase_invoices:
		kind, _source = classifications.setdefault(invoice.name, ("Other", ""))
		if kind == "Material":
			material_cost += flt(invoice.base_net_total)
		elif kind == "Contractor":
			contractor_cost += flt(invoice.base_net_total)
		else:
			other_cost += flt(invoice.base_net_total)
	recognized_revenue = sum(
		flt(row.base_net_total) for row in sales_invoices if row.is_opening != "Yes"
	)
	invoiced = sum(
		flt(row.base_grand_total) for row in sales_invoices if row.is_opening != "Yes"
	)
	outstanding = sum(
		flt(row.outstanding_amount) * (flt(row.conversion_rate) or 1) for row in sales_invoices
	)
	all_invoice_gross = sum(flt(row.base_grand_total) for row in sales_invoices)
	paid = all_invoice_gross - outstanding
	overdue = sum(
		flt(row.outstanding_amount) * (flt(row.conversion_rate) or 1)
		for row in sales_invoices
		if row.due_date and getdate(row.due_date) < getdate(today()) and flt(row.outstanding_amount) > 0
	)
	total_cost = material_cost + contractor_cost + other_cost
	profit = recognized_revenue - total_cost
	profitability = flt(profit / recognized_revenue * 100, 6) if recognized_revenue else 0
	obligation_dimension = _obligation_dimension(service_project, materials, settlements)
	billing_dimension = _billing_dimension(service_project)
	payment_entries = _payment_trace(sales_invoices, purchase_invoices)
	source_payload = {
		"sales_invoices": [dict(row) for row in sales_invoices],
		"purchase_invoices": [dict(row) for row in purchase_invoices],
		"payment_entries": payment_entries,
		"material_expenses": [dict(row) for row in materials],
		"contractor_settlements": [dict(row) for row in settlements],
		"classifications": classifications,
		"obligation_dimension": obligation_dimension,
		"billing_dimension": billing_dimension,
	}
	canonical = json.dumps(source_payload, ensure_ascii=False, sort_keys=True, default=str)
	fields = {
		"company": project.company,
		"customer": project.customer,
		"project_manager": project.project_manager,
		"currency": company_currency,
		"contract_amount_with_vat": flt(project.contract_amount_with_vat),
		"recognized_revenue_without_vat": flt(recognized_revenue, 2),
		"invoiced_with_vat": flt(invoiced, 2),
		"paid_with_vat": flt(paid, 2),
		"outstanding_with_vat": flt(outstanding, 2),
		"overdue_ar_with_vat": flt(overdue, 2),
		"material_cost_without_vat": flt(material_cost, 2),
		"contractor_cost_without_vat": flt(contractor_cost, 2),
		"other_cost_without_vat": flt(other_cost, 2),
		"total_cost_without_vat": flt(total_cost, 2),
		"profit_without_vat": flt(profit, 2),
		"profitability_percent": profitability,
		"obligation_dimension_json": json.dumps(obligation_dimension, ensure_ascii=False, sort_keys=True),
		"billing_cycle_dimension_json": json.dumps(billing_dimension, ensure_ascii=False, sort_keys=True),
		"source_fingerprint": hashlib.sha256(canonical.encode()).hexdigest(),
	}
	return fields, {
		"sales_invoices": [dict(row) for row in sales_invoices],
		"payment_entries": payment_entries,
		"purchase_invoices": [dict(row) for row in purchase_invoices],
		"material_expenses": [dict(row) for row in materials],
		"contractor_settlements": [dict(row) for row in settlements],
		"purchase_invoice_classification": classifications,
		"obligation_dimension": obligation_dimension,
		"billing_cycle_dimension": billing_dimension,
	}


def _obligation_dimension(service_project: str, materials: list[Any], settlements: list[Any]) -> list[dict[str, Any]]:
	rows = frappe.get_all(
		"Ferum Contract Obligation",
		filters={"service_project": service_project},
		fields=["name", "status", "work_type", "price_component", "currency"],
		order_by="name asc",
	)
	material_by_obligation: dict[str, float] = {}
	contractor_by_obligation: dict[str, float] = {}
	for row in materials:
		if row.contract_obligation:
			material_by_obligation[row.contract_obligation] = (
				material_by_obligation.get(row.contract_obligation, 0) + flt(row.base_amount_without_vat)
			)
	for row in settlements:
		if row.contract_obligation:
			contractor_by_obligation[row.contract_obligation] = (
				contractor_by_obligation.get(row.contract_obligation, 0) + flt(row.base_approved_amount)
			)
	return [
		{
			**dict(row),
			"material_management_amount": flt(material_by_obligation.get(row.name), 2),
			"contractor_management_amount": flt(contractor_by_obligation.get(row.name), 2),
		}
		for row in rows
	]


def _billing_dimension(service_project: str) -> list[dict[str, Any]]:
	if not frappe.db.table_exists("Ferum Billing Output"):
		return []
	return [
		dict(row)
		for row in frappe.get_all(
			"Ferum Billing Output",
			filters={"service_project": service_project},
			fields=[
				"name", "period_start", "period_end", "output_type", "status", "basis_amount",
				"sales_invoice",
			],
			order_by="period_end asc, name asc",
		)
	]


def _payment_trace(sales_invoices: list[Any], purchase_invoices: list[Any]) -> list[dict[str, Any]]:
	references = [("Sales Invoice", row.name) for row in sales_invoices]
	references.extend(("Purchase Invoice", row.name) for row in purchase_invoices)
	if not references:
		return []
	result: list[dict[str, Any]] = []
	for reference_doctype, reference_name in references:
		for row in frappe.get_all(
			"Payment Entry Reference",
			filters={
				"reference_doctype": reference_doctype,
				"reference_name": reference_name,
				"docstatus": 1,
			},
			fields=["parent", "reference_doctype", "reference_name", "allocated_amount"],
			order_by="parent asc",
		):
			payment = frappe.db.get_value(
				"Payment Entry", row.parent, ("docstatus", "posting_date", "payment_type", "party_type", "party"), as_dict=True
			)
			if payment and payment.docstatus == 1:
				result.append({**dict(row), **dict(payment)})
	return result


def _summary_dict(doc: Any) -> dict[str, Any]:
	return {"summary": doc.name, "service_project": doc.service_project, **{field: doc.get(field) for field in _MONEY_FIELDS}, "source_fingerprint": doc.source_fingerprint, "last_recalculated_at": doc.last_recalculated_at}


def _project(service_project: str) -> Any:
	if not frappe.db.exists("Ferum Service Project", service_project):
		frappe.throw(_("Ferum Service Project не найден."), frappe.DoesNotExistError)
	return frappe.get_doc("Ferum Service Project", service_project)


def _require_role(roles: frozenset[str], operation: str) -> None:
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles(frappe.session.user)).intersection(roles):
		frappe.throw(_("Недостаточно прав: {0}.").format(operation), frappe.PermissionError)


def _savepoint(label: str) -> str:
	name = f"ca_finance_{label}_{frappe.generate_hash(length=8)}"
	frappe.db.savepoint(name)
	return name


def _with_flag(flag: str, value: Any, callback: Callable[[], _T]) -> _T:
	previous = frappe.flags.get(flag)
	frappe.flags[flag] = value
	try:
		return callback()
	finally:
		frappe.flags[flag] = previous


def _with_transition(
	writer_flag: str,
	transition_flag: str,
	target_status: str,
	callback: Callable[[], _T],
) -> _T:
	return _with_flag(
		writer_flag,
		True,
		lambda: _with_flag(transition_flag, target_status, callback),
	)
