"""Supplier-isolated read boundary for Contractor Assignment."""

from __future__ import annotations

from typing import Any, Final

import frappe

from contract_accounting.infrastructure.project_graph_permissions import (
	contractor_assignment_query,
	has_project_graph_permission,
)

DOCTYPE: Final[str] = "Ferum Contractor Assignment"
CONTRACTOR_ROLE: Final[str] = "Подрядчик"


def get_permission_query_conditions(user: str | None = None, doctype: str | None = None) -> str:
	user = user or frappe.session.user
	conditions: list[str] = []
	project_condition = contractor_assignment_query(user)
	if project_condition:
		conditions.append(project_condition)
	if user != "Administrator" and CONTRACTOR_ROLE in frappe.get_roles(user):
		suppliers = allowed_suppliers(user)
		if not suppliers:
			return "1=0"
		escaped = ", ".join(frappe.db.escape(value) for value in suppliers)
		conditions.append(f"`tab{DOCTYPE}`.`supplier` in ({escaped})")
	return " and ".join(f"({condition})" for condition in conditions)


def has_permission(
	doc: Any,
	ptype: str | None = None,
	user: str | None = None,
	debug: bool = False,
) -> bool | None:
	user = user or frappe.session.user
	project_result = has_project_graph_permission(doc, ptype, user, debug)
	if project_result is False:
		return False
	if user == "Administrator" or CONTRACTOR_ROLE not in frappe.get_roles(user):
		return project_result
	if ptype not in {None, "read", "select"}:
		return False
	return bool(doc.supplier and doc.supplier in allowed_suppliers(user))


def allowed_suppliers(user: str) -> tuple[str, ...]:
	rows = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "Supplier", "is_default": ["in", [0, 1]]},
		fields=["for_value", "applicable_for"],
		order_by="for_value asc",
	)
	return tuple(
		str(row.for_value)
		for row in rows
		if not row.applicable_for or row.applicable_for == DOCTYPE
	)
