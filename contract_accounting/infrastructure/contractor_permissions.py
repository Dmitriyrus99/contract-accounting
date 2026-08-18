"""Supplier-isolated read boundary for Contractor Assignment."""

from __future__ import annotations

from typing import Any, Final

import frappe

DOCTYPE: Final[str] = "Ferum Contractor Assignment"
CONTRACTOR_ROLE: Final[str] = "Подрядчик"


def get_permission_query_conditions(user: str | None = None, doctype: str | None = None) -> str:
	user = user or frappe.session.user
	if user == "Administrator" or CONTRACTOR_ROLE not in frappe.get_roles(user):
		return ""
	suppliers = _allowed_suppliers(user)
	if not suppliers:
		return "1=0"
	escaped = ", ".join(frappe.db.escape(value) for value in suppliers)
	return f"`tab{DOCTYPE}`.`supplier` in ({escaped})"


def has_permission(
	doc: Any,
	ptype: str | None = None,
	user: str | None = None,
	debug: bool = False,
) -> bool | None:
	user = user or frappe.session.user
	if user == "Administrator" or CONTRACTOR_ROLE not in frappe.get_roles(user):
		return None
	if ptype not in {None, "read", "select"}:
		return False
	return bool(doc.supplier and doc.supplier in _allowed_suppliers(user))


def _allowed_suppliers(user: str) -> tuple[str, ...]:
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
