"""Typed, idempotent Party Identity linkage commands."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final, TypeVar

import frappe
from frappe import _
from frappe.utils import now_datetime

from contract_accounting.contract_accounting.doctype.ferum_party_identity.ferum_party_identity import (
    DOCTYPE,
    MASTER_LINK_FIELDS,
    PARTY_LINKAGE_WRITE_FLAG,
)

_T = TypeVar("_T")
_LINK_ROLES: Final[frozenset[str]] = frozenset(
    {"System Manager", "Бухгалтер", "Юрист", "Офис-менеджер"}
)


@frappe.whitelist(methods=["POST"])
def link_party_identity(
    party_type: str,
    full_name: str,
    reason: str,
    customer: str | None = None,
    supplier: str | None = None,
    company: str | None = None,
    party_identity: str | None = None,
    inn: str | None = None,
    provenance_doctype: str | None = None,
    provenance_name: str | None = None,
    external_reference: str | None = None,
) -> dict[str, str]:
    """Create or extend one linkage without copying ERPNext business fields."""

    _require_link_role()
    party_type = _required(party_type, "party_type")
    full_name = _required(full_name, "full_name")
    reason = _required(reason, "reason")
    links = {"customer": customer, "supplier": supplier, "company": company}
    links = {field: _clean(value) for field, value in links.items() if _clean(value)}
    if not links:
        frappe.throw(_("Party Identity linkage требует Customer, Supplier или Company."))
    if bool(provenance_doctype) != bool(provenance_name):
        frappe.throw(_("Provenance DocType и record должны быть указаны вместе."))

    save_point = f"ca_party_link_{frappe.generate_hash(length=8)}"
    frappe.db.savepoint(save_point)
    try:
        for fieldname, name in sorted(links.items()):
            master_doctype = MASTER_LINK_FIELDS[fieldname]
            if not frappe.db.get_value(master_doctype, name, "name", for_update=True):
                frappe.throw(_("{0} {1} не найден.").format(master_doctype, name))

        candidates: set[str] = set()
        for fieldname, name in links.items():
            candidates.update(
                frappe.get_all(
                    DOCTYPE,
                    filters={fieldname: name, "status": "Active"},
                    pluck="name",
                )
            )
        if party_identity:
            candidates.add(party_identity)
        if len(candidates) > 1:
            frappe.throw(
                _("ERPNext masters указывают на разные Party Identity; требуется reconciliation.")
            )

        if candidates:
            name = next(iter(candidates))
            frappe.db.get_value(DOCTYPE, name, "name", for_update=True)
            doc = frappe.get_doc(DOCTYPE, name)
            doc.check_permission("write")
            _assert_identity_unchanged(doc, party_type, full_name, inn)
        else:
            doc = frappe.new_doc(DOCTYPE)
            # Frappe may inject user defaults into conventional fieldnames such as
            # ``company``. A typed command must derive links only from its input.
            for fieldname in MASTER_LINK_FIELDS:
                doc.set(fieldname, None)
            doc.party_type = party_type
            doc.full_name = full_name
            doc.inn = _clean(inn)

        for fieldname, value in links.items():
            current = doc.get(fieldname)
            if current and current != value:
                frappe.throw(_("Party Identity уже связан с другим {0}.").format(fieldname))
            doc.set(fieldname, value)
        if provenance_doctype:
            if doc.provenance_name and (
                doc.provenance_doctype != provenance_doctype
                or doc.provenance_name != provenance_name
            ):
                frappe.throw(
                    _("Party Identity provenance immutable; создайте reconciliation evidence.")
                )
            doc.provenance_doctype = provenance_doctype
            doc.provenance_name = provenance_name
        if external_reference:
            if doc.external_reference and doc.external_reference != external_reference:
                frappe.throw(
                    _("Party Identity external_reference нельзя перезаписать linkage command.")
                )
            doc.external_reference = external_reference
        doc.linkage_reason = reason
        doc.linkage_updated_by = frappe.session.user
        doc.linkage_updated_at = now_datetime()

        if doc.is_new():
            _with_flag(links, lambda: doc.insert(ignore_permissions=True))
        else:
            _with_flag(links, lambda: doc.save(ignore_permissions=True))
        return {
            "party_identity": doc.name,
            "linkage_status": doc.linkage_status,
            "customer": doc.customer or "",
            "supplier": doc.supplier or "",
            "company": doc.company or "",
        }
    except Exception:
        frappe.db.rollback(save_point=save_point)
        raise


def _assert_identity_unchanged(doc: Any, party_type: str, full_name: str, inn: str | None) -> None:
    expected_inn = _clean(inn)
    if doc.party_type != party_type or doc.full_name != full_name:
        frappe.throw(_("Linkage command не синхронизирует Party Identity business fields."))
    if expected_inn and doc.inn and doc.inn != expected_inn:
        frappe.throw(_("Linkage command не может заменить INN существующей Party Identity."))


def _with_flag(authorized_links: dict[str, str], callback: Callable[[], _T]) -> _T:
    previous = frappe.flags.get(PARTY_LINKAGE_WRITE_FLAG)
    frappe.flags[PARTY_LINKAGE_WRITE_FLAG] = dict(authorized_links)
    try:
        return callback()
    finally:
        frappe.flags[PARTY_LINKAGE_WRITE_FLAG] = previous


def _require_link_role() -> None:
    if frappe.session.user == "Administrator":
        return
    if not set(frappe.get_roles(frappe.session.user)).intersection(_LINK_ROLES):
        frappe.throw(_("Недостаточно прав для Party Identity linkage."), frappe.PermissionError)


def _required(value: str | None, fieldname: str) -> str:
    cleaned = _clean(value)
    if not cleaned:
        frappe.throw(_("{0} обязательно.").format(fieldname))
    return cleaned


def _clean(value: str | None) -> str:
    return str(value or "").strip()
