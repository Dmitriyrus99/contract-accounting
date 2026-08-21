"""Prevent operational assignees from delegating project-wide visibility."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Final

import frappe
from frappe import _

ASSIGNMENT_MANAGER_ROLES: Final[frozenset[str]] = frozenset(
    {"Менеджер проектов", "Руководитель проектов", "System Manager"}
)


def guard_assignment_changes(doc: Any, fieldnames: Iterable[str]) -> None:
    before = doc.get_doc_before_save()
    if before is None:
        changed = [
            fieldname
            for fieldname in fieldnames
            if doc.get(fieldname) not in (None, "", frappe.session.user)
        ]
    else:
        changed = [
            fieldname for fieldname in fieldnames if doc.get(fieldname) != before.get(fieldname)
        ]
    if not changed or frappe.session.user == "Administrator":
        return
    if set(frappe.get_roles(frappe.session.user)).intersection(ASSIGNMENT_MANAGER_ROLES):
        return
    frappe.throw(
        _("Назначение изменяет project-wide access и доступно только руководителю: {0}.").format(
            ", ".join(changed)
        ),
        frappe.PermissionError,
    )
