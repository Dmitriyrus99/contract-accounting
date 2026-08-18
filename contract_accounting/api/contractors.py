"""CA-08 operational assignment and commercial-basis commands."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final, TypeVar

import frappe
from frappe import _
from frappe.utils import now_datetime

from contract_accounting.contract_accounting.doctype.ferum_contractor_assignment.ferum_contractor_assignment import (
	ASSIGNMENT_TRANSITION_FLAG,
	ASSIGNMENT_WRITER_FLAG,
)
from contract_accounting.contract_accounting.doctype.ferum_contractor_assignment.ferum_contractor_assignment import (
	DOCTYPE as ASSIGNMENT_DOCTYPE,
)
from contract_accounting.contract_accounting.doctype.ferum_contractor_commercial_terms.ferum_contractor_commercial_terms import (
	DOCTYPE as TERMS_DOCTYPE,
)
from contract_accounting.contract_accounting.doctype.ferum_contractor_commercial_terms.ferum_contractor_commercial_terms import (
	TERMS_TRANSITION_FLAG,
	TERMS_WRITER_FLAG,
)

_T = TypeVar("_T")
_ASSIGNMENT_CREATE_ROLES: Final[frozenset[str]] = frozenset(
	{"Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_ASSIGNMENT_APPROVE_ROLES: Final[frozenset[str]] = frozenset(
	{"Руководитель проектов", "System Manager"}
)
_TERMS_ROLES: Final[frozenset[str]] = frozenset(
	{"Бухгалтер", "Руководитель проектов", "System Manager"}
)


@frappe.whitelist(methods=["POST"])
def create_contractor_assignment(
	service_project: str,
	execution_mode: str,
	project_object: str,
	work_type: str,
	responsibility: str,
	effective_from: str,
	effective_to: str | None = None,
	supplier: str | None = None,
	employee: str | None = None,
	contractor_worker: str | None = None,
	object_system: str | None = None,
	contract_obligation: str | None = None,
) -> dict[str, str]:
	_require_role(_ASSIGNMENT_CREATE_ROLES, "create Contractor Assignment")
	_project(service_project).check_permission("read")
	doc = frappe.get_doc(
		{
			"doctype": ASSIGNMENT_DOCTYPE,
			"service_project": service_project,
			"execution_mode": execution_mode,
			"supplier": supplier,
			"employee": employee,
			"contractor_worker": contractor_worker,
			"project_object": project_object,
			"object_system": object_system,
			"contract_obligation": contract_obligation,
			"work_type": work_type,
			"responsibility": responsibility,
			"effective_from": effective_from,
			"effective_to": effective_to,
		}
	)
	_with_flag(ASSIGNMENT_WRITER_FLAG, True, lambda: doc.insert(ignore_permissions=True))
	return {"contractor_assignment": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def change_contractor_assignment_status(name: str, target_status: str, reason: str) -> dict[str, str]:
	_require_role(_ASSIGNMENT_APPROVE_ROLES, "Contractor Assignment transition")
	if target_status not in {"Approved", "Suspended", "Completed", "Cancelled"}:
		frappe.throw(_("Contractor Assignment target status не разрешён."))
	if not str(reason or "").strip():
		frappe.throw(_("Contractor Assignment transition требует reason."))
	save_point = _savepoint("assignment")
	try:
		frappe.db.get_value(ASSIGNMENT_DOCTYPE, name, "name", for_update=True)
		doc = frappe.get_doc(ASSIGNMENT_DOCTYPE, name)
		doc.check_permission("write")
		doc.status = target_status
		doc.status_reason = reason.strip()
		if target_status == "Approved":
			doc.approved_at = now_datetime()
			doc.approved_by = frappe.session.user
		elif target_status == "Completed":
			doc.completed_at = now_datetime()
			doc.completed_by = frappe.session.user
		elif target_status == "Cancelled":
			doc.cancelled_at = now_datetime()
			doc.cancelled_by = frappe.session.user
		_with_transition(
			ASSIGNMENT_WRITER_FLAG,
			ASSIGNMENT_TRANSITION_FLAG,
			target_status,
			lambda: doc.save(ignore_permissions=True),
		)
		return {"contractor_assignment": doc.name, "status": doc.status}
	except Exception:
		frappe.db.rollback(save_point=save_point)
		raise


@frappe.whitelist(methods=["POST"])
def create_contractor_commercial_terms(
	contractor_assignment: str,
	effective_from: str,
	client_price: float,
	contractor_cost: float,
	effective_to: str | None = None,
) -> dict[str, str]:
	_require_role(_TERMS_ROLES, "create Contractor Commercial Terms")
	assignment = frappe.get_doc(ASSIGNMENT_DOCTYPE, contractor_assignment)
	assignment.check_permission("read")
	doc = frappe.get_doc(
		{
			"doctype": TERMS_DOCTYPE,
			"contractor_assignment": contractor_assignment,
			"effective_from": effective_from,
			"effective_to": effective_to,
			"client_price": client_price,
			"contractor_cost": contractor_cost,
		}
	)
	_with_flag(TERMS_WRITER_FLAG, True, lambda: doc.insert(ignore_permissions=True))
	return {"commercial_terms": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def change_contractor_commercial_terms_status(
	name: str, target_status: str, reason: str
) -> dict[str, str]:
	_require_role(_TERMS_ROLES, "Contractor Commercial Terms transition")
	if target_status not in {"Approved", "Cancelled"}:
		frappe.throw(_("Commercial Terms target status не разрешён."))
	if not str(reason or "").strip():
		frappe.throw(_("Commercial Terms transition требует reason."))
	save_point = _savepoint("terms")
	try:
		frappe.db.get_value(TERMS_DOCTYPE, name, "name", for_update=True)
		doc = frappe.get_doc(TERMS_DOCTYPE, name)
		doc.check_permission("write")
		doc.status = target_status
		doc.status_reason = reason.strip()
		if target_status == "Approved":
			doc.approved_at = now_datetime()
			doc.approved_by = frappe.session.user
		else:
			if frappe.db.exists(
				"Ferum Contractor Settlement",
				{"commercial_terms": doc.name, "status": ["in", ["Approved", "Settled"]]},
			):
				frappe.throw(_("Commercial Terms используются признанным Contractor Settlement."))
			doc.cancelled_at = now_datetime()
			doc.cancelled_by = frappe.session.user
		_with_transition(
			TERMS_WRITER_FLAG,
			TERMS_TRANSITION_FLAG,
			target_status,
			lambda: doc.save(ignore_permissions=True),
		)
		_link_terms(doc.contractor_assignment, doc.name if target_status == "Approved" else None)
		return {"commercial_terms": doc.name, "status": doc.status}
	except Exception:
		frappe.db.rollback(save_point=save_point)
		raise


@frappe.whitelist()
def get_contractor_assignment_trace(name: str) -> dict[str, Any]:
	doc = frappe.get_doc(ASSIGNMENT_DOCTYPE, name)
	doc.check_permission("read")
	terms = (
		frappe.db.get_value(
			TERMS_DOCTYPE,
			doc.commercial_terms,
			("name", "status", "currency", "client_price", "contractor_cost", "margin_amount", "margin_percent"),
			as_dict=True,
		)
		if doc.commercial_terms
		else None
	)
	return {
		"assignment": doc.as_dict(),
		"commercial_terms": dict(terms) if terms else None,
		"settlements": frappe.get_all(
			"Ferum Contractor Settlement",
			filters={"contractor_assignment": doc.name},
			fields=["name", "status", "period_start", "period_end", "approved_amount", "paid_amount", "payable_amount"],
			order_by="period_end asc, name asc",
		),
		"material_expenses": frappe.get_all(
			"Ferum Material Expense",
			filters={"contractor_assignment": doc.name},
			fields=["name", "status", "expense_date", "amount_without_vat"],
			order_by="expense_date asc, name asc",
		),
		"personnel_readiness": {
			"enabled": False,
			"reason": "MG-CA-015 is open",
		},
	}


def _link_terms(assignment_name: str, terms_name: str | None) -> None:
	frappe.db.get_value(ASSIGNMENT_DOCTYPE, assignment_name, "name", for_update=True)
	assignment = frappe.get_doc(ASSIGNMENT_DOCTYPE, assignment_name)
	assignment.commercial_terms = terms_name
	_with_flag(ASSIGNMENT_WRITER_FLAG, True, lambda: assignment.save(ignore_permissions=True))


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
	name = f"ca_contractor_{label}_{frappe.generate_hash(length=8)}"
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
