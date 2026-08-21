"""FR-06 break-glass and legal-hold controls."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from contract_accounting.api.privacy import active_privacy_settings, record_privacy_event
from contract_accounting.contract_accounting.doctype.ferum_privacy_break_glass.ferum_privacy_break_glass import (
    ALLOWED_ACTIONS,
    ALLOWED_TARGETS,
    BREAK_GLASS_WRITE_FLAG,
)
from contract_accounting.contract_accounting.doctype.ferum_privacy_legal_hold.ferum_privacy_legal_hold import (
    ALLOWED_TARGETS as LEGAL_HOLD_TARGETS,
)
from contract_accounting.contract_accounting.doctype.ferum_privacy_legal_hold.ferum_privacy_legal_hold import (
    LEGAL_HOLD_WRITE_FLAG,
)
from contract_accounting.domain.privacy import (
    POLICY_HASH,
    POLICY_REFERENCE,
    PrivacyRuleError,
    break_glass_expiry,
    validate_break_glass_minutes,
)
from contract_accounting.infrastructure.privacy_file_guard import credential_file_aliases
from contract_accounting.infrastructure.privacy_target_lock import (
    lock_privacy_target,
    lock_privacy_targets,
)

SECURITY_ROLES = frozenset({"Ответственный за ИБ"})
DPO_ROLES = frozenset({"Ответственный за ПДн", "Юрист"})
PRODUCT_OWNER_ROLES = frozenset({"Генеральный директор"})
DATA_OWNER_ROLES = frozenset({"Менеджер персональных данных", "Офис-менеджер"})


@frappe.whitelist(methods=["POST"])
def request_break_glass(
    ticket: str,
    reason: str,
    target_doctype: str,
    target_name: str,
    action: str,
    requested_minutes: int | str,
) -> dict[str, Any]:
    _require_roles(frozenset({"System Manager"}) | SECURITY_ROLES, "request break-glass")
    active_privacy_settings()
    if target_doctype not in ALLOWED_TARGETS or action not in ALLOWED_ACTIONS:
        frappe.throw(_("Break-glass target/action не входит в allowlist."))
    if not _lock_protected_target_context(target_doctype, target_name):
        frappe.throw(_("Break-glass exact target не найден."))
    try:
        minutes = validate_break_glass_minutes(int(requested_minutes))
    except (PrivacyRuleError, TypeError, ValueError) as exc:
        frappe.throw(_(str(exc)))
    doc = frappe.get_doc(
        {
            "doctype": "Ferum Privacy Break Glass",
            "requester": frappe.session.user,
            "requester_is_security": int(
                bool(set(frappe.get_roles(frappe.session.user)).intersection(SECURITY_ROLES))
            ),
            "ticket": _required(ticket, "ticket", 3),
            "reason": _required(reason, "reason", 10),
            "target_doctype": target_doctype,
            "target_name": target_name,
            "action": action,
            "requested_minutes": minutes,
            "status": "Requested",
            "policy_reference": POLICY_REFERENCE,
            "policy_hash": POLICY_HASH,
        }
    )
    with _flag(BREAK_GLASS_WRITE_FLAG):
        doc.insert(ignore_permissions=True)
    record_privacy_event(
        "Break Glass Requested",
        doc.doctype,
        doc.name,
        reason,
        {"target_doctype": target_doctype, "target_name": target_name, "action": action},
        ticket=ticket,
    )
    return _break_glass_result(doc)


@frappe.whitelist(methods=["POST"])
def approve_break_glass(name: str, approval_kind: str, reason: str) -> dict[str, Any]:
    active_privacy_settings()
    reason = _required(reason, "reason", 10)
    doc = _lock_break_glass_doc(name)
    if doc.status not in {"Requested", "Partially Approved"}:
        frappe.throw(_("Break-glass уже не ожидает approvals."))
    if doc.requester == frappe.session.user:
        frappe.throw(_("Requester не может одобрить собственный break-glass."))

    requester_is_security = bool(doc.requester_is_security)
    now = now_datetime()
    if approval_kind == "DPO":
        _require_explicit_roles(DPO_ROLES, "DPO break-glass approval")
        if doc.dpo_approved_by:
            frappe.throw(_("DPO approval уже зафиксирован."))
        _require_distinct_actor(
            frappe.session.user,
            doc.requester,
            doc.security_approved_by,
            doc.product_owner_approved_by,
        )
        doc.dpo_approved_by = frappe.session.user
        doc.dpo_approved_at = now
    elif approval_kind == "Security" and not requester_is_security:
        _require_explicit_roles(SECURITY_ROLES, "Security break-glass approval")
        if doc.security_approved_by:
            frappe.throw(_("Security approval уже зафиксирован."))
        _require_distinct_actor(
            frappe.session.user,
            doc.requester,
            doc.dpo_approved_by,
            doc.product_owner_approved_by,
        )
        doc.security_approved_by = frappe.session.user
        doc.security_approved_at = now
    elif approval_kind == "Product Owner" and requester_is_security:
        _require_explicit_roles(PRODUCT_OWNER_ROLES, "Product Owner break-glass approval")
        if doc.product_owner_approved_by:
            frappe.throw(_("Product Owner approval уже зафиксирован."))
        _require_distinct_actor(
            frappe.session.user,
            doc.requester,
            doc.dpo_approved_by,
            doc.security_approved_by,
        )
        doc.product_owner_approved_by = frappe.session.user
        doc.product_owner_approved_at = now
    else:
        frappe.throw(_("Approval kind не соответствует requester separation rule."))

    complete = bool(doc.dpo_approved_by) and bool(
        doc.product_owner_approved_by if requester_is_security else doc.security_approved_by
    )
    if complete:
        doc.status = "Active"
        doc.activated_at = now
        doc.expires_at = break_glass_expiry(now, int(doc.requested_minutes))
    else:
        doc.status = "Partially Approved"
    with _flag(BREAK_GLASS_WRITE_FLAG):
        doc.save(ignore_permissions=True)
    record_privacy_event(
        "Break Glass Approved",
        doc.doctype,
        doc.name,
        reason,
        {"approval_kind": approval_kind, "status": doc.status},
        ticket=doc.ticket,
    )
    return _break_glass_result(doc)


@frappe.whitelist(methods=["POST"])
def revoke_break_glass(name: str, reason: str) -> dict[str, Any]:
    _require_roles(
        frozenset({"System Manager"}) | SECURITY_ROLES | DPO_ROLES | PRODUCT_OWNER_ROLES,
        "revoke break-glass",
    )
    doc = _lock_break_glass_doc(name)
    if doc.status not in {"Requested", "Partially Approved", "Active"}:
        frappe.throw(_("Break-glass уже terminal."))
    with _flag(BREAK_GLASS_WRITE_FLAG):
        doc.status = "Revoked"
        doc.revoked_at = now_datetime()
        doc.revoked_by = frappe.session.user
        doc.save(ignore_permissions=True)
    record_privacy_event(
        "Break Glass Revoked",
        doc.doctype,
        doc.name,
        _required(reason, "reason", 10),
        {"status": doc.status},
        ticket=doc.ticket,
    )
    return _break_glass_result(doc)


def expire_break_glass() -> int:
    """Idempotently revoke elapsed grants; safe for the 15-minute scheduler."""

    now = now_datetime()
    expired = frappe.get_all(
        "Ferum Privacy Break Glass",
        filters={"status": "Active", "expires_at": ["<=", now]},
        pluck="name",
    )
    expired_count = 0
    for name in expired:
        doc = _lock_break_glass_doc(name)
        if doc.status != "Active" or not doc.expires_at or doc.expires_at > now:
            continue
        with _flag(BREAK_GLASS_WRITE_FLAG):
            doc.status = "Expired"
            doc.revoked_at = now
            doc.revoked_by = "Administrator"
            doc.save(ignore_permissions=True)
        record_privacy_event(
            "Break Glass Expired",
            doc.doctype,
            doc.name,
            "Automatic expiry after approved duration",
            {"status": "Expired"},
            ticket=doc.ticket,
        )
        expired_count += 1
    return expired_count


def has_active_break_glass(
    user: str, target_doctype: str, target_name: str, action: str = "Read"
) -> bool:
    if action not in ALLOWED_ACTIONS:
        return False
    return bool(
        frappe.db.exists(
            "Ferum Privacy Break Glass",
            {
                "requester": user,
                "target_doctype": target_doctype,
                "target_name": target_name,
                "action": action,
                "status": "Active",
                "expires_at": [">", now_datetime()],
            },
        )
    )


def lock_active_read_grant(user: str, target_doctype: str, target_name: str) -> str | None:
    """Lock and current-validate one exact typed Read grant."""

    names = frappe.db.sql(
        """
        select name
          from `tabFerum Privacy Break Glass`
         where requester = %s
           and target_doctype = %s
           and target_name = %s
           and action = 'Read'
           and status = 'Active'
         order by name
        """,
        (user, target_doctype, target_name),
        pluck=True,
    )
    for name in names:
        doc = _lock_break_glass_doc(str(name))
        if _is_current_read_grant(doc, user, target_doctype, target_name):
            return str(doc.name)
    return None


def is_locked_read_grant_current(
    name: str, user: str, target_doctype: str, target_name: str
) -> bool:
    return _is_current_read_grant(
        frappe.get_doc("Ferum Privacy Break Glass", name),
        user,
        target_doctype,
        target_name,
    )


def _is_current_read_grant(doc: Any, user: str, target_doctype: str, target_name: str) -> bool:
    return bool(
        doc.requester == user
        and doc.target_doctype == target_doctype
        and doc.target_name == target_name
        and doc.action == "Read"
        and doc.status == "Active"
        and doc.expires_at
        and doc.expires_at > now_datetime()
    )


def lock_active_download_grant(user: str, file_aliases: set[str]) -> str | None:
    """Lock and return one current exact-target Download grant."""

    aliases = sorted({str(name) for name in file_aliases if name})
    if not aliases:
        return None
    placeholders = ", ".join(["%s"] * len(aliases))
    names = frappe.db.sql(
        f"""
        select name
          from `tabFerum Privacy Break Glass`
         where requester = %s
           and target_doctype = 'File'
           and target_name in ({placeholders})
           and action = 'Download'
           and status = 'Active'
         order by name
        """,  # nosec: only the number of parameter placeholders is dynamic.
        (user, *aliases),
        pluck=True,
    )
    for name in names:
        doc = _lock_break_glass_doc(str(name))
        if _is_current_download_grant(doc, user, set(aliases)):
            return str(doc.name)
    return None


def is_locked_download_grant_current(
    name: str,
    user: str,
    file_aliases: set[str],
) -> bool:
    """Recheck a previously locked grant immediately before response."""

    doc = frappe.get_doc("Ferum Privacy Break Glass", name)
    return _is_current_download_grant(doc, user, file_aliases)


def _is_current_download_grant(doc: Any, user: str, aliases: set[str]) -> bool:
    return bool(
        doc.requester == user
        and doc.target_doctype == "File"
        and doc.target_name in aliases
        and doc.action == "Download"
        and doc.status == "Active"
        and doc.expires_at
        and doc.expires_at > now_datetime()
    )


@frappe.whitelist(methods=["POST"])
def request_legal_hold(
    target_doctype: str, target_name: str, reason: str, review_on: str
) -> dict[str, Any]:
    _require_explicit_roles(
        DPO_ROLES | PRODUCT_OWNER_ROLES | DATA_OWNER_ROLES, "request legal hold"
    )
    active_privacy_settings()
    if target_doctype not in LEGAL_HOLD_TARGETS:
        frappe.throw(_("Legal hold target не входит в allowlist."))
    if not _lock_protected_target_context(target_doctype, target_name):
        frappe.throw(_("Legal hold exact target не найден."))
    if get_datetime(review_on).date() <= now_datetime().date():
        frappe.throw(_("Legal hold review_on должен быть в будущем."))
    doc = frappe.get_doc(
        {
            "doctype": "Ferum Privacy Legal Hold",
            "target_doctype": target_doctype,
            "target_name": target_name,
            "reason": _required(reason, "reason", 10),
            "review_on": review_on,
            "status": "Pending",
            "requested_by": frappe.session.user,
            "requested_at": now_datetime(),
            "policy_reference": POLICY_REFERENCE,
            "policy_hash": POLICY_HASH,
        }
    )
    with _flag(LEGAL_HOLD_WRITE_FLAG):
        doc.insert(ignore_permissions=True)
    record_privacy_event(
        "Legal Hold Requested", doc.doctype, doc.name, reason, {"review_on": review_on}
    )
    return _legal_hold_result(doc)


@frappe.whitelist(methods=["POST"])
def approve_legal_hold(name: str, approval_kind: str, reason: str) -> dict[str, Any]:
    active_privacy_settings()
    doc = _lock_legal_hold_doc(name)
    if doc.status != "Pending":
        frappe.throw(_("Legal hold уже не ожидает activation approvals."))
    now = now_datetime()
    if approval_kind == "Legal":
        _require_explicit_roles(DPO_ROLES, "Legal hold Legal approval")
        if doc.legal_approved_by:
            frappe.throw(_("Legal hold Legal approval уже зафиксирован."))
        _require_distinct_actor(
            frappe.session.user, doc.requested_by, doc.product_owner_approved_by
        )
        doc.legal_approved_by = frappe.session.user
        doc.legal_approved_at = now
    elif approval_kind == "Product Owner":
        _require_explicit_roles(PRODUCT_OWNER_ROLES, "Legal hold Product Owner approval")
        if doc.product_owner_approved_by:
            frappe.throw(_("Legal hold Product Owner approval уже зафиксирован."))
        _require_distinct_actor(frappe.session.user, doc.requested_by, doc.legal_approved_by)
        doc.product_owner_approved_by = frappe.session.user
        doc.product_owner_approved_at = now
    else:
        frappe.throw(_("Legal hold approval_kind не поддерживается."))
    if doc.legal_approved_by and doc.product_owner_approved_by:
        doc.status = "Active"
    with _flag(LEGAL_HOLD_WRITE_FLAG):
        doc.save(ignore_permissions=True)
    record_privacy_event(
        "Legal Hold Approved",
        doc.doctype,
        doc.name,
        _required(reason, "reason", 10),
        {"approval_kind": approval_kind, "status": doc.status},
    )
    return _legal_hold_result(doc)


@frappe.whitelist(methods=["POST"])
def request_legal_hold_release(name: str, reason: str) -> dict[str, Any]:
    _require_explicit_roles(DPO_ROLES | PRODUCT_OWNER_ROLES, "request legal hold release")
    doc = _lock_legal_hold_doc(name)
    if doc.status != "Active":
        frappe.throw(_("Release разрешён только для Active legal hold."))
    with _flag(LEGAL_HOLD_WRITE_FLAG):
        doc.status = "Release Pending"
        doc.release_reason = _required(reason, "reason", 10)
        doc.release_requested_by = frappe.session.user
        doc.release_requested_at = now_datetime()
        doc.save(ignore_permissions=True)
    record_privacy_event(
        "Legal Hold Release Requested", doc.doctype, doc.name, reason, {"status": doc.status}
    )
    return _legal_hold_result(doc)


@frappe.whitelist(methods=["POST"])
def approve_legal_hold_release(name: str, approval_kind: str, reason: str) -> dict[str, Any]:
    active_privacy_settings()
    doc = _lock_legal_hold_doc(name)
    if doc.status != "Release Pending":
        frappe.throw(_("Legal hold не ожидает release approvals."))
    now = now_datetime()
    if approval_kind == "Legal":
        _require_explicit_roles(DPO_ROLES, "Legal hold release Legal approval")
        if doc.release_legal_approved_by:
            frappe.throw(_("Legal hold release Legal approval уже зафиксирован."))
        _require_distinct_actor(
            frappe.session.user,
            doc.release_requested_by,
            doc.release_product_owner_approved_by,
        )
        doc.release_legal_approved_by = frappe.session.user
        doc.release_legal_approved_at = now
    elif approval_kind == "Product Owner":
        _require_explicit_roles(PRODUCT_OWNER_ROLES, "Legal hold release Product Owner approval")
        if doc.release_product_owner_approved_by:
            frappe.throw(_("Legal hold release Product Owner approval уже зафиксирован."))
        _require_distinct_actor(
            frappe.session.user,
            doc.release_requested_by,
            doc.release_legal_approved_by,
        )
        doc.release_product_owner_approved_by = frappe.session.user
        doc.release_product_owner_approved_at = now
    else:
        frappe.throw(_("Legal hold release approval_kind не поддерживается."))
    if doc.release_legal_approved_by and doc.release_product_owner_approved_by:
        doc.status = "Released"
        doc.released_at = now
    with _flag(LEGAL_HOLD_WRITE_FLAG):
        doc.save(ignore_permissions=True)
    record_privacy_event(
        "Legal Hold Release Approved",
        doc.doctype,
        doc.name,
        _required(reason, "reason", 10),
        {"approval_kind": approval_kind, "status": doc.status},
    )
    return _legal_hold_result(doc)


def has_active_legal_hold(target_doctype: str, target_name: str) -> bool:
    return bool(
        frappe.db.exists(
            "Ferum Privacy Legal Hold",
            {"target_doctype": target_doctype, "target_name": target_name, "status": "Active"},
        )
    )


def _lock_break_glass_doc(name: str) -> Any:
    seed = frappe.db.get_value(
        "Ferum Privacy Break Glass",
        name,
        ("target_doctype", "target_name"),
        as_dict=True,
    )
    if not seed or not _lock_protected_target_context(seed.target_doctype, seed.target_name):
        frappe.throw(_("Break-glass exact target не найден."))
    if not frappe.db.get_value("Ferum Privacy Break Glass", name, "name", for_update=True):
        frappe.throw(_("Break-glass не найден."))
    doc = frappe.get_doc("Ferum Privacy Break Glass", name)
    if (doc.target_doctype, doc.target_name) != (seed.target_doctype, seed.target_name):
        frappe.throw(_("Break-glass target изменён во время блокировки."))
    return doc


def _lock_legal_hold_doc(name: str) -> Any:
    seed = frappe.db.get_value(
        "Ferum Privacy Legal Hold",
        name,
        ("target_doctype", "target_name"),
        as_dict=True,
    )
    if not seed or not _lock_protected_target_context(seed.target_doctype, seed.target_name):
        frappe.throw(_("Legal hold exact target не найден."))
    if not frappe.db.get_value("Ferum Privacy Legal Hold", name, "name", for_update=True):
        frappe.throw(_("Legal hold не найден."))
    doc = frappe.get_doc("Ferum Privacy Legal Hold", name)
    if (doc.target_doctype, doc.target_name) != (seed.target_doctype, seed.target_name):
        frappe.throw(_("Legal hold target изменён во время блокировки."))
    return doc


def _lock_protected_target_context(target_doctype: str, target_name: str) -> bool:
    """Lock target -> hash aliases before any grant/hold row."""

    target_doctype = str(target_doctype or "")
    target_name = str(target_name or "")
    credential = target_name if target_doctype == "Ferum Personnel Credential" else None
    if target_doctype == "File":
        rows = frappe.db.sql(
            """
            select credential.name
              from `tabFerum Personnel Credential` credential
              join `tabFile` canonical on canonical.name = credential.document
             join `tabFile` candidate on candidate.name = %s
             where candidate.name = canonical.name
                or (ifnull(candidate.content_hash, '') != ''
                    and candidate.content_hash = canonical.content_hash)
                or (
                    (
                        canonical.file_url like '/files/%%'
                        or canonical.file_url like '/private/files/%%'
                    )
                    and candidate.file_url = canonical.file_url
                )
             order by credential.name
             limit 1
            """,
            (target_name,),
        )
        credential = str(rows[0][0]) if rows else None
    if credential:
        if not lock_privacy_target("Ferum Personnel Credential", credential):
            return False
        document = frappe.db.get_value("Ferum Personnel Credential", credential, "document")
        aliases = credential_file_aliases(str(document or ""), for_update=True)
        alias_targets = {("File", str(row.name)) for row in aliases}
        if alias_targets - lock_privacy_targets(alias_targets):
            return False
        if target_doctype == "File" and ("File", target_name) not in alias_targets:
            return False
        return True
    return lock_privacy_target(target_doctype, target_name)


def _break_glass_result(doc: Any) -> dict[str, Any]:
    return {
        "break_glass": doc.name,
        "status": doc.status,
        "target_doctype": doc.target_doctype,
        "target_name": doc.target_name,
        "action": doc.action,
        "expires_at": str(doc.expires_at) if doc.expires_at else None,
    }


def _legal_hold_result(doc: Any) -> dict[str, Any]:
    return {
        "legal_hold": doc.name,
        "status": doc.status,
        "target_doctype": doc.target_doctype,
        "target_name": doc.target_name,
        "review_on": str(doc.review_on),
    }


def _require_roles(roles: frozenset[str], operation: str) -> None:
    if frappe.session.user == "Administrator":
        return
    if not set(frappe.get_roles(frappe.session.user)).intersection(roles):
        frappe.throw(_("Недостаточно прав: {0}.").format(operation), frappe.PermissionError)


def _require_explicit_roles(roles: frozenset[str], operation: str) -> None:
    """Require an assigned business role; Administrator is not an approval role."""

    if frappe.session.user == "Administrator" or not set(
        frappe.get_roles(frappe.session.user)
    ).intersection(roles):
        frappe.throw(_("Недостаточно прав: {0}.").format(operation), frappe.PermissionError)


def _require_distinct_actor(actor: str, *other_actors: str | None) -> None:
    if actor in {value for value in other_actors if value}:
        frappe.throw(
            _("Requester и каждый approver должны быть разными пользователями."),
            frappe.PermissionError,
        )


def _required(value: str | None, label: str, minimum: int) -> str:
    normalized = str(value or "").strip()
    if len(normalized) < minimum:
        frappe.throw(_("{0} должен содержать не менее {1} символов.").format(label, minimum))
    return normalized


@contextmanager
def _flag(name: str, value: Any = True) -> Iterator[None]:
    previous = frappe.flags.get(name)
    frappe.flags[name] = value
    try:
        yield
    finally:
        frappe.flags[name] = previous
