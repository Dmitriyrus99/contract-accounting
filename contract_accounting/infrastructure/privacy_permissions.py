"""Row-level FR-05 boundaries for Worker and Credential records."""

from __future__ import annotations

from typing import Any, Final

import frappe

WORKER_DOCTYPE: Final[str] = "Ferum Contractor Worker"
CREDENTIAL_DOCTYPE: Final[str] = "Ferum Personnel Credential"
PRIVILEGED_ROLES: Final[frozenset[str]] = frozenset(
    {"Менеджер персональных данных", "Ответственный за ПДн", "Генеральный директор"}
)
PROJECT_ROLES: Final[frozenset[str]] = frozenset(
    {"Руководитель проектов", "Менеджер проектов", "Проверяющий допуски", "Инженер"}
)


def get_worker_permission_query_conditions(
    user: str | None = None, doctype: str | None = None
) -> str:
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if roles.intersection(PRIVILEGED_ROLES) or "Офис-менеджер" in roles:
        return ""
    names: set[str] = set()
    if roles.intersection(PROJECT_ROLES):
        names.update(_project_workers(user))
    return _names_condition(WORKER_DOCTYPE, names)


def get_credential_permission_query_conditions(
    user: str | None = None, doctype: str | None = None
) -> str:
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if roles.intersection(PRIVILEGED_ROLES) or "Офис-менеджер" in roles:
        return ""
    names: set[str] = set()
    if roles.intersection(PROJECT_ROLES):
        names.update(_project_credentials(user))
    return _names_condition(CREDENTIAL_DOCTYPE, names)


def has_worker_permission(
    doc: Any,
    ptype: str | None = None,
    user: str | None = None,
    debug: bool = False,
) -> bool | None:
    user = user or frappe.session.user
    if ptype not in {None, "read", "select", "report"}:
        return False
    roles = set(frappe.get_roles(user))
    if roles.intersection(PRIVILEGED_ROLES) or "Офис-менеджер" in roles:
        return True
    return bool(roles.intersection(PROJECT_ROLES) and doc.name in _project_workers(user))


def has_credential_permission(
    doc: Any,
    ptype: str | None = None,
    user: str | None = None,
    debug: bool = False,
) -> bool | None:
    user = user or frappe.session.user
    if ptype not in {None, "read", "select", "report"}:
        return False
    roles = set(frappe.get_roles(user))
    if roles.intersection(PRIVILEGED_ROLES) or "Офис-менеджер" in roles:
        return True
    return bool(roles.intersection(PROJECT_ROLES) and doc.name in _project_credentials(user))


def _project_workers(user: str) -> set[str]:
    return {
        str(row[0])
        for row in frappe.db.sql(
            """
            select distinct contractor.contractor_worker
            from `tabFerum Contractor Assignment` contractor
            join `tabFerum Service Project` project on project.name = contractor.service_project
            where contractor.contractor_worker is not null
              and contractor.contractor_worker != ''
              and contractor.status in ('Approved', 'Suspended')
              and (
                project.project_manager = %(user)s
                or exists (
                  select 1
                  from `tabFerum Contractor Assignment` own_assignment
                  join `tabEmployee` employee on employee.name = own_assignment.employee
                  where own_assignment.service_project = contractor.service_project
                    and own_assignment.project_object = contractor.project_object
                    and own_assignment.status in ('Approved', 'Suspended')
                    and employee.user_id = %(user)s
                )
              )
            """,
            {"user": user},
        )
    }


def _project_credentials(user: str) -> set[str]:
    workers = _project_workers(user)
    names: set[str] = set()
    if workers:
        names.update(
            frappe.get_all(
                CREDENTIAL_DOCTYPE,
                filters={"holder_type": WORKER_DOCTYPE, "holder": ["in", sorted(workers)]},
                pluck="name",
                ignore_permissions=True,
            )
        )
    employee_rows = frappe.db.sql(
        """
        select distinct credential.name
        from `tabFerum Personnel Credential` credential
        join `tabFerum Contractor Assignment` assigned
          on credential.holder_type = 'Employee' and credential.holder = assigned.employee
        join `tabFerum Service Project` project on project.name = assigned.service_project
        where assigned.status in ('Approved', 'Suspended')
          and project.project_manager = %(user)s
        """,
        {"user": user},
    )
    names.update(str(row[0]) for row in employee_rows)
    return names


def _names_condition(doctype: str, names: set[str]) -> str:
    if not names:
        return "1=0"
    escaped = ", ".join(frappe.db.escape(name) for name in sorted(names))
    return f"`tab{doctype}`.`name` in ({escaped})"
