"""Assigned-project read boundary for operational Desk roles."""

from __future__ import annotations

from typing import Any, Final

import frappe

DOCTYPE: Final[str] = "Ferum Service Project"
SCOPED_ROLES: Final[frozenset[str]] = frozenset({"Инженер", "Офис-менеджер"})
UNRESTRICTED_ROLES: Final[frozenset[str]] = frozenset(
	{
		"System Manager",
		"Генеральный директор",
		"Руководитель проектов",
		"Менеджер проектов",
		"Юрист",
		"Бухгалтер",
	}
)


def get_permission_query_conditions(user: str | None = None, doctype: str | None = None) -> str:
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or roles.intersection(UNRESTRICTED_ROLES):
		return ""
	scoped_roles = roles.intersection(SCOPED_ROLES)
	if not scoped_roles:
		return "1=0"
	return _project_condition(user, scoped_roles)


def has_permission(
	doc: Any,
	ptype: str | None = None,
	user: str | None = None,
	debug: bool = False,
) -> bool | None:
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or roles.intersection(UNRESTRICTED_ROLES):
		return None
	if not roles.intersection(SCOPED_ROLES):
		return False
	if ptype not in {None, "read", "select", "report"}:
		return False
	return _is_assigned_project(str(doc.name), user, roles)


def _project_condition(user: str, roles: set[str]) -> str:
	escaped_user = frappe.db.escape(user)
	conditions = [
		f"exists (select 1 from `tabFerum Project Process Step` step where step.service_project = `tab{DOCTYPE}`.name and step.responsible_user = {escaped_user})"
	]
	if "Инженер" in roles:
		conditions.extend(
			[
				f"exists (select 1 from `tabFerum Project Object` obj where obj.service_project = `tab{DOCTYPE}`.name and obj.responsible_engineer = {escaped_user})",
				f"exists (select 1 from `tabFerum Service Request` req where req.service_project = `tab{DOCTYPE}`.name and req.assigned_engineer = {escaped_user})",
				f"exists (select 1 from `tabFerum Maintenance Visit` visit where visit.service_project = `tab{DOCTYPE}`.name and visit.assigned_engineer = {escaped_user})",
				f"exists (select 1 from `tabFerum Project Process Step` step where step.service_project = `tab{DOCTYPE}`.name and step.responsible_role = 'Инженер' and ifnull(step.responsible_user, '') = '')",
			]
		)
	if "Офис-менеджер" in roles:
		conditions.extend(
			[
				f"exists (select 1 from `tabFerum Project Document` doc where doc.service_project = `tab{DOCTYPE}`.name and doc.owner_user = {escaped_user})",
				f"exists (select 1 from `tabFerum Project Process Step` step where step.service_project = `tab{DOCTYPE}`.name and step.responsible_role = 'Офис-менеджер' and ifnull(step.responsible_user, '') = '')",
			]
		)
	return "(" + " or ".join(conditions) + ")"


def _is_assigned_project(project: str, user: str, roles: set[str]) -> bool:
	if frappe.db.exists(
		"Ferum Project Process Step",
		{"service_project": project, "responsible_user": user},
	):
		return True
	if "Инженер" in roles:
		for doctype, fieldname in (
			("Ferum Project Object", "responsible_engineer"),
			("Ferum Service Request", "assigned_engineer"),
			("Ferum Maintenance Visit", "assigned_engineer"),
		):
			if frappe.db.exists(doctype, {"service_project": project, fieldname: user}):
				return True
		if frappe.db.exists(
			"Ferum Project Process Step",
			{
				"service_project": project,
				"responsible_role": "Инженер",
				"responsible_user": ["is", "not set"],
			},
		):
			return True
	if "Офис-менеджер" in roles:
		if frappe.db.exists(
			"Ferum Project Document",
			{"service_project": project, "owner_user": user},
		):
			return True
		if frappe.db.exists(
			"Ferum Project Process Step",
			{
				"service_project": project,
				"responsible_role": "Офис-менеджер",
				"responsible_user": ["is", "not set"],
			},
		):
			return True
	return False
