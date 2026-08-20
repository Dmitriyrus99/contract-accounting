"""Typed FR-06 commands for protected personnel data."""

from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from pathlib import PurePosixPath
from typing import Any, Final, Iterator

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import cint, getdate, now_datetime, today

from contract_accounting.contract_accounting.doctype.ferum_privacy_event.ferum_privacy_event import (
    PRIVACY_EVENT_WRITE_FLAG,
)
from contract_accounting.contract_accounting.doctype.ferum_privacy_settings.ferum_privacy_settings import (
    PRIVACY_SETTINGS_WRITE_FLAG,
)
from contract_accounting.domain.privacy import (
    ALLOWED_ATTACHMENT_SUFFIXES,
    ALLOWED_CREDENTIAL_TYPES,
    ALLOWED_HOLDER_TYPES,
    MAX_ATTACHMENT_SIZE,
    POLICY_HASH,
    POLICY_REFERENCE,
    PRODUCTION_ACTIVATION_CONFIRMATION,
    SYNTHETIC_ACTIVATION_CONFIRMATION,
)
from contract_accounting.infrastructure.privacy_file_guard import credential_file_aliases
from contract_accounting.infrastructure.privacy_target_lock import (
    lock_privacy_target,
    lock_privacy_targets,
)

PRIVACY_WRITE_FLAG: Final[str] = "contract_accounting_privacy_writer"
PRIVACY_TRANSITION_FLAG: Final[str] = "contract_accounting_privacy_transition"
PRIVACY_RETENTION_FLAG: Final[str] = "contract_accounting_privacy_retention"

WORKER_DOCTYPE: Final[str] = "Ferum Contractor Worker"
CREDENTIAL_DOCTYPE: Final[str] = "Ferum Personnel Credential"

DATA_OWNER_ROLES: Final[frozenset[str]] = frozenset(
    {"Менеджер персональных данных", "Офис-менеджер"}
)
DPO_ROLES: Final[frozenset[str]] = frozenset({"Ответственный за ПДн", "Юрист"})
VERIFIER_ROLES: Final[frozenset[str]] = frozenset(
    {"Проверяющий допуски", "Руководитель проектов", "Менеджер проектов"}
)
PRODUCT_OWNER_ROLES: Final[frozenset[str]] = frozenset({"Генеральный директор"})
TENDER_ROLES: Final[frozenset[str]] = frozenset({"Тендерный специалист"})


@frappe.whitelist(methods=["POST"])
def activate_privacy_policy(
    activation_mode: str,
    confirmation: str,
    approval_reference: str,
    reason: str,
) -> dict[str, Any]:
    """Activate synthetic or production processing with separate exact tokens."""

    _require_product_owner("activate FR-05 privacy policy")
    approval_reference = _required(approval_reference, "approval_reference", 5)
    reason = _required(reason, "reason", 10)
    expected = {
        "Synthetic Test": SYNTHETIC_ACTIVATION_CONFIRMATION,
        "Production": PRODUCTION_ACTIVATION_CONFIRMATION,
    }.get(activation_mode)
    if expected is None or confirmation != expected:
        frappe.throw(_("Privacy activation confirmation не совпадает с выбранным mode."))
    if activation_mode == "Synthetic Test" and not cint(frappe.conf.get("developer_mode")):
        frappe.throw(_("Synthetic Test activation разрешён только на developer site."))

    settings = frappe.get_single("Ferum Privacy Settings")
    if settings.enabled:
        frappe.throw(_("Privacy policy уже активирована."))
    with _flag(PRIVACY_SETTINGS_WRITE_FLAG):
        settings.enabled = 1
        settings.activation_mode = activation_mode
        settings.activated_at = now_datetime()
        settings.activated_by = frappe.session.user
        settings.approval_reference = approval_reference
        settings.last_reason = reason
        settings.configuration_revision = cint(settings.configuration_revision) + 1
        settings.policy_reference = POLICY_REFERENCE
        settings.policy_hash = POLICY_HASH
        settings.save(ignore_permissions=True)
    return _settings_result(settings)


@frappe.whitelist(methods=["POST"])
def deactivate_privacy_policy(reason: str) -> dict[str, Any]:
    _require_product_owner("deactivate FR-05 privacy policy")
    settings = frappe.get_single("Ferum Privacy Settings")
    if not settings.enabled:
        frappe.throw(_("Privacy policy уже выключена."))
    with _flag(PRIVACY_SETTINGS_WRITE_FLAG):
        settings.enabled = 0
        settings.activation_mode = "Disabled"
        settings.last_reason = _required(reason, "reason", 10)
        settings.configuration_revision = cint(settings.configuration_revision) + 1
        settings.policy_reference = POLICY_REFERENCE
        settings.policy_hash = POLICY_HASH
        settings.save(ignore_permissions=True)
    return _settings_result(settings)


@frappe.whitelist()
def get_privacy_policy_status() -> dict[str, Any]:
    settings = frappe.get_single("Ferum Privacy Settings")
    settings.check_permission("read")
    return _settings_result(settings)


@frappe.whitelist(methods=["POST"])
def create_contractor_worker(
    supplier: str,
    display_name: str,
    privacy_basis_reference: str,
    data_owner: str,
    position: str | None = None,
    contact: str | None = None,
    work_contact_confirmed: int | str = 0,
) -> dict[str, Any]:
    _require_roles(DATA_OWNER_ROLES, "create Contractor Worker")
    settings = _active_settings()
    basis = _basis(privacy_basis_reference, settings.activation_mode)
    doc = frappe.get_doc(
        {
            "doctype": WORKER_DOCTYPE,
            "supplier": supplier,
            "worker_external_id": _worker_external_id(supplier),
            "display_name": _required(display_name, "display_name", 2),
            "position": position,
            "contact": contact,
            "work_contact_confirmed": cint(work_contact_confirmed),
            "status": "Inactive",
            "privacy_basis_reference": basis,
            "data_owner": data_owner,
            "privacy_policy_reference": POLICY_REFERENCE,
            "privacy_policy_hash": POLICY_HASH,
        }
    )
    with _flag(PRIVACY_WRITE_FLAG):
        doc.insert(ignore_permissions=True)
    _event("Worker Created", doc, "Approved source registered", {"status": doc.status})
    return _worker_result(doc)


@frappe.whitelist(methods=["POST"])
def transition_contractor_worker(name: str, target_status: str, reason: str) -> dict[str, Any]:
    _require_roles(DATA_OWNER_ROLES | DPO_ROLES, "transition Contractor Worker")
    _active_settings()
    reason = _required(reason, "reason", 10)
    frappe.db.get_value(WORKER_DOCTYPE, name, "name", for_update=True)
    doc = frappe.get_doc(WORKER_DOCTYPE, name)
    with _flag(PRIVACY_WRITE_FLAG), _flag(PRIVACY_TRANSITION_FLAG, target_status):
        doc.status = target_status
        doc.transition_reason = reason
        if target_status == "Archived":
            doc.archived_at = now_datetime()
            doc.archived_by = frappe.session.user
        elif target_status == "Inactive" and doc.get_doc_before_save() is None:
            pass
        doc.save(ignore_permissions=True)
    _event("Worker Status Changed", doc, reason, {"status": target_status})
    return _worker_result(doc)


@frappe.whitelist(methods=["POST"])
def create_personnel_credential(
    holder_type: str,
    holder: str,
    credential_type: str,
    credential_number: str,
    privacy_basis_reference: str,
    issued_on: str | None = None,
    expires_on: str | None = None,
    no_expiry: int | str = 0,
    issuer: str | None = None,
    document: str | None = None,
) -> dict[str, Any]:
    _require_roles(DATA_OWNER_ROLES, "create Personnel Credential")
    settings = _active_settings()
    if holder_type not in ALLOWED_HOLDER_TYPES:
        frappe.throw(_("Credential holder_type не входит в approved allowlist."))
    if credential_type not in ALLOWED_CREDENTIAL_TYPES:
        frappe.throw(_("Credential type не входит в approved allowlist."))
    if not frappe.db.exists(holder_type, holder):
        frappe.throw(_("Credential holder не найден."))
    if document:
        _validate_private_file(document)
    doc = frappe.get_doc(
        {
            "doctype": CREDENTIAL_DOCTYPE,
            "holder_type": holder_type,
            "holder": holder,
            "credential_type": credential_type,
            "credential_number": _required(credential_number, "credential_number", 1),
            "issued_on": issued_on,
            "expires_on": expires_on,
            "no_expiry": cint(no_expiry),
            "issuer": issuer,
            "document": document,
            "malware_status": "Pending" if document else "Not Applicable",
            "verification_status": "Draft",
            "privacy_basis_reference": _basis(privacy_basis_reference, settings.activation_mode),
            "privacy_policy_reference": POLICY_REFERENCE,
            "privacy_policy_hash": POLICY_HASH,
            "retention_status": "Active",
        }
    )
    with _flag(PRIVACY_WRITE_FLAG):
        doc.insert(ignore_permissions=True)
    _event(
        "Credential Created", doc, "Approved source registered", {"status": doc.verification_status}
    )
    return _credential_result(doc, mask_number=True)


@frappe.whitelist(methods=["POST"])
def record_credential_scan_result(
    name: str, result: str, scan_reference: str, reason: str
) -> dict[str, Any]:
    _require_roles(frozenset({"Ответственный за ИБ"}), "record credential malware scan")
    _active_settings()
    if result not in {"Clean", "Rejected"}:
        frappe.throw(_("Malware result должен быть Clean или Rejected."))
    doc = frappe.get_doc(CREDENTIAL_DOCTYPE, name)
    if not doc.document:
        frappe.throw(_("Credential не содержит attachment."))
    if doc.malware_status == "Rejected" and result == "Clean":
        frappe.throw(
            _("Rejected attachment нельзя повторно пометить Clean; создайте новую Credential.")
        )
    file_doc = _validate_private_file(doc.document, require_read_permission=False)
    file_hash = _sha256_content(file_doc.get_content())
    transition = "Rejected" if result == "Rejected" else None
    with _flag(PRIVACY_WRITE_FLAG), _flag(PRIVACY_TRANSITION_FLAG, transition):
        doc.malware_status = result
        doc.malware_scan_reference = _required(scan_reference, "scan_reference", 5)
        doc.scanned_file_hash = file_hash
        doc.scanned_at = now_datetime()
        doc.scanned_by = frappe.session.user
        if result == "Rejected":
            doc.verification_status = "Rejected"
        doc.transition_reason = _required(reason, "reason", 10)
        doc.save(ignore_permissions=True)
    _event(
        "Credential Malware Scan",
        doc,
        reason,
        {"result": result, "file_hash": file_hash, "recorded_by": frappe.session.user},
    )
    return {
        "credential": doc.name,
        "malware_status": doc.malware_status,
        "verification_status": doc.verification_status,
    }


@frappe.whitelist(methods=["POST"])
def verify_credential_source(name: str, reason: str) -> dict[str, Any]:
    _require_roles(DATA_OWNER_ROLES, "verify credential source")
    return _verify_credential(name, reason, "data_owner")


@frappe.whitelist(methods=["POST"])
def verify_credential_applicability(name: str, reason: str) -> dict[str, Any]:
    _require_roles(VERIFIER_ROLES, "verify credential applicability")
    return _verify_credential(name, reason, "applicability")


@frappe.whitelist(methods=["POST"])
def revoke_or_reject_credential(name: str, target_status: str, reason: str) -> dict[str, Any]:
    _require_roles(DATA_OWNER_ROLES | DPO_ROLES | VERIFIER_ROLES, "reject or revoke credential")
    _active_settings()
    if target_status not in {"Rejected", "Revoked"}:
        frappe.throw(_("Credential target status должен быть Rejected или Revoked."))
    doc, _aliases = _lock_credential_alias_context(name)
    _require_scoped_verifier_access(doc)
    with _flag(PRIVACY_WRITE_FLAG), _flag(PRIVACY_TRANSITION_FLAG, target_status):
        doc.verification_status = target_status
        doc.transition_reason = _required(reason, "reason", 10)
        doc.save(ignore_permissions=True)
    _event("Credential Status Changed", doc, reason, {"status": target_status})
    return _credential_result(doc, mask_number=True)


@frappe.whitelist(methods=["POST"])
def get_personnel_credential(name: str, reason: str | None = None) -> dict[str, Any]:
    _active_settings()
    typed_reason = _required(reason, "reason", 10)
    lock_privacy_target(CREDENTIAL_DOCTYPE, name)
    doc = frappe.get_doc(CREDENTIAL_DOCTYPE, name)
    roles = set(frappe.get_roles(frappe.session.user))
    full = bool(roles.intersection(DATA_OWNER_ROLES | DPO_ROLES | PRODUCT_OWNER_ROLES))
    regular_allowed = bool(doc.has_permission("read"))
    locked_grant = None if regular_allowed else _lock_typed_read_grant(doc.doctype, doc.name)
    if not regular_allowed and not locked_grant:
        return _record_denied_read(doc, typed_reason, "Credential Read Denied")
    if full:
        _event("Credential Read", doc, typed_reason, {"full_number": True})
    elif locked_grant:
        if not _is_typed_read_grant_current(locked_grant, doc.doctype, doc.name):
            return _record_denied_read(doc, typed_reason, "Credential Read Denied")
        _event(
            "Credential Break Glass Read",
            doc,
            typed_reason,
            {"full_number": False, "access": "allowed"},
        )
    result = _credential_result(doc, mask_number=not full)
    if not full and not roles.intersection(VERIFIER_ROLES):
        result.pop("credential_number", None)
    return result


@frappe.whitelist(methods=["POST"])
def get_contractor_worker(name: str, reason: str) -> dict[str, Any]:
    """Return a minimal Worker projection through an audited typed read only."""

    _active_settings()
    reason = _required(reason, "reason", 10)
    lock_privacy_target(WORKER_DOCTYPE, name)
    doc = frappe.get_doc(WORKER_DOCTYPE, name)
    regular_allowed = bool(doc.has_permission("read"))
    locked_grant = None if regular_allowed else _lock_typed_read_grant(doc.doctype, doc.name)
    if not regular_allowed and not locked_grant:
        return _record_denied_read(doc, reason, "Worker Read Denied")
    if locked_grant and not _is_typed_read_grant_current(locked_grant, doc.doctype, doc.name):
        return _record_denied_read(doc, reason, "Worker Read Denied")
    _event(
        "Worker Typed Read",
        doc,
        reason,
        {"access": "break_glass" if locked_grant else "role", "projection": "minimal"},
    )
    return {
        "worker": doc.name,
        "worker_external_id": doc.worker_external_id,
        "status": doc.status,
    }


@frappe.whitelist(methods=["POST"])
def download_credential_attachment(name: str, reason: str) -> dict[str, Any] | None:
    """Stream one approved private attachment; never expose a reusable public URL."""

    _active_settings()
    reason = _required(reason, "reason", 10)
    doc, alias_names = _lock_credential_alias_context(name)
    roles = set(frappe.get_roles(frappe.session.user))
    full_roles = DATA_OWNER_ROLES | DPO_ROLES | PRODUCT_OWNER_ROLES
    allowed = bool(roles.intersection(full_roles))
    if not allowed and roles.intersection(VERIFIER_ROLES):
        allowed = bool(doc.has_permission("read"))
    locked_grant = None
    if not allowed:
        from contract_accounting.api.privacy_controls import lock_active_download_grant

        locked_grant = lock_active_download_grant(frappe.session.user, alias_names)
        allowed = bool(locked_grant)
    if not allowed:
        return _record_denied_read(doc, reason, "Credential Attachment Download Denied")
    if (
        not doc.document
        or doc.malware_status != "Clean"
        or doc.verification_status in {"Rejected", "Revoked", "Expired"}
        or (not doc.no_expiry and doc.expires_on and getdate(doc.expires_on) < getdate(today()))
    ):
        frappe.throw(_("Credential attachment отсутствует или не имеет Clean scan."))
    file_doc = _validate_private_file(doc.document, require_read_permission=False)
    content = file_doc.get_content()
    actual_hash = _sha256_content(content)
    if not doc.scanned_file_hash or actual_hash != doc.scanned_file_hash:
        frappe.throw(_("Credential attachment изменён после malware scan."), frappe.PermissionError)
    current = frappe.get_doc(CREDENTIAL_DOCTYPE, name)
    if (
        current.document != doc.document
        or current.malware_status != "Clean"
        or current.verification_status in {"Rejected", "Revoked", "Expired"}
        or (
            not current.no_expiry
            and current.expires_on
            and getdate(current.expires_on) < getdate(today())
        )
        or current.scanned_file_hash != actual_hash
    ):
        frappe.throw(_("Credential attachment state изменён во время download."))
    if locked_grant:
        from contract_accounting.api.privacy_controls import (
            is_locked_download_grant_current,
        )

        if not is_locked_download_grant_current(
            locked_grant,
            frappe.session.user,
            alias_names,
        ):
            frappe.throw(_("Credential attachment download grant истёк."), frappe.PermissionError)
    _event(
        "Credential Attachment Downloaded",
        doc,
        reason,
        {"file": file_doc.name, "file_hash": actual_hash},
    )
    frappe.local.response.filename = file_doc.file_name
    frappe.local.response.filecontent = content
    frappe.local.response.type = "download"


def _record_denied_read(doc: Any, reason: str, event_type: str) -> dict[str, Any]:
    """Return a non-exception 403 so Frappe commits the denial audit normally."""

    _event(event_type, doc, reason, {"access": "denied"})
    frappe.local.response.http_status_code = 403
    return {"ok": False, "error": "permission_denied"}


def _lock_typed_read_grant(target_doctype: str, target_name: str) -> str | None:
    from contract_accounting.api.privacy_controls import lock_active_read_grant

    return lock_active_read_grant(frappe.session.user, target_doctype, target_name)


def _is_typed_read_grant_current(grant: str, target_doctype: str, target_name: str) -> bool:
    from contract_accounting.api.privacy_controls import is_locked_read_grant_current

    return is_locked_read_grant_current(
        grant,
        frappe.session.user,
        target_doctype,
        target_name,
    )


@frappe.whitelist(methods=["POST"])
def get_supplier_qualification_summary(supplier: str, reason: str) -> dict[str, Any]:
    """Return only aggregated qualification counts; never reveal holders or numbers."""

    _require_roles(
        TENDER_ROLES | DATA_OWNER_ROLES | DPO_ROLES | PRODUCT_OWNER_ROLES,
        "read anonymized Supplier qualification summary",
    )
    _active_settings()
    reason = _required(reason, "reason", 10)
    if not frappe.db.exists("Supplier", supplier):
        frappe.throw(_("Supplier не найден."))
    rows = frappe.db.sql(
        """
        select credential.credential_type,
               count(*) as total_count,
               sum(
                 credential.verification_status = 'Verified'
                 and (credential.no_expiry = 1 or credential.expires_on >= %(as_of)s)
               ) as valid_count
        from `tabFerum Personnel Credential` credential
        join `tabFerum Contractor Worker` worker
          on credential.holder_type = 'Ferum Contractor Worker'
         and credential.holder = worker.name
        where worker.supplier = %(supplier)s
          and worker.status = 'Active'
          and credential.retention_status != 'Metadata Only'
        group by credential.credential_type
        order by credential.credential_type asc
        """,
        {"supplier": supplier, "as_of": getdate(today())},
        as_dict=True,
    )
    summary = [
        {
            "credential_type": row.credential_type,
            "total_count": cint(row.total_count),
            "valid_count": cint(row.valid_count),
        }
        for row in rows
    ]
    record_privacy_event(
        "Supplier Qualification Summary Read",
        "Supplier",
        supplier,
        reason,
        {"credential_types": len(summary)},
    )
    return {"supplier": supplier, "as_of": today(), "qualifications": summary}


def expire_personnel_credentials() -> int:
    """Persist elapsed Verified credentials; disabled policy performs no writes."""

    if not cint(frappe.db.get_single_value("Ferum Privacy Settings", "enabled") or 0):
        return 0
    if (
        frappe.db.get_single_value("Ferum Privacy Settings", "policy_reference") != POLICY_REFERENCE
        or frappe.db.get_single_value("Ferum Privacy Settings", "policy_hash") != POLICY_HASH
    ):
        return 0
    names = frappe.get_all(
        CREDENTIAL_DOCTYPE,
        filters={
            "verification_status": "Verified",
            "no_expiry": 0,
            "expires_on": ["<", getdate(today())],
        },
        pluck="name",
    )
    expired_count = 0
    for name in names:
        try:
            doc, _aliases = _lock_credential_alias_context(name)
        except frappe.DoesNotExistError:
            continue
        if (
            doc.verification_status != "Verified"
            or doc.no_expiry
            or not doc.expires_on
            or getdate(doc.expires_on) >= getdate(today())
        ):
            continue
        with _flag(PRIVACY_WRITE_FLAG), _flag(PRIVACY_TRANSITION_FLAG, "Expired"):
            doc.verification_status = "Expired"
            doc.transition_reason = "Automatic expiry after credential expires_on"
            doc.save(ignore_permissions=True)
        _event(
            "Credential Automatically Expired",
            doc,
            doc.transition_reason,
            {"expires_on": str(doc.expires_on)},
        )
        expired_count += 1
    return expired_count


def _verify_credential(name: str, reason: str, dimension: str) -> dict[str, Any]:
    _active_settings()
    reason = _required(reason, "reason", 10)
    frappe.db.get_value(CREDENTIAL_DOCTYPE, name, "name", for_update=True)
    doc = frappe.get_doc(CREDENTIAL_DOCTYPE, name)
    if dimension == "applicability":
        _require_scoped_verifier_access(doc)
    if doc.verification_status not in {"Draft", "Verified"}:
        frappe.throw(_("Credential нельзя проверить в текущем status."))
    if doc.document and doc.malware_status != "Clean":
        frappe.throw(_("Credential attachment недоступен до Clean malware result."))
    other_verifier = (
        doc.applicability_verified_by if dimension == "data_owner" else doc.data_owner_verified_by
    )
    if other_verifier == frappe.session.user:
        frappe.throw(_("Source и applicability должны подтвердить разные пользователи."))
    now = now_datetime()
    transition = (
        "Verified"
        if (
            (dimension == "data_owner" and doc.applicability_verified_by)
            or (dimension == "applicability" and doc.data_owner_verified_by)
        )
        else None
    )
    with _flag(PRIVACY_WRITE_FLAG), _flag(PRIVACY_TRANSITION_FLAG, transition):
        if dimension == "data_owner":
            doc.data_owner_verified_by = frappe.session.user
            doc.data_owner_verified_at = now
        else:
            doc.applicability_verified_by = frappe.session.user
            doc.applicability_verified_at = now
        if doc.data_owner_verified_by and doc.applicability_verified_by:
            doc.verification_status = "Verified"
            doc.verified_by = frappe.session.user
            doc.verified_on = now
        doc.transition_reason = reason
        doc.save(ignore_permissions=True)
    _event(
        "Credential Verification",
        doc,
        reason,
        {"dimension": dimension, "status": doc.verification_status},
    )
    return _credential_result(doc, mask_number=True)


def _require_scoped_verifier_access(doc: Any) -> None:
    roles = set(frappe.get_roles(frappe.session.user))
    if roles.intersection(VERIFIER_ROLES) and not roles.intersection(DATA_OWNER_ROLES | DPO_ROLES):
        doc.check_permission("read")


def active_privacy_settings() -> Any:
    """Public fail-closed settings resolver used by DocType controllers."""

    return _active_settings()


def record_privacy_event(
    event_type: str,
    target_doctype: str,
    target_name: str,
    reason: str,
    payload: dict[str, Any] | None = None,
    *,
    ticket: str | None = None,
) -> str:
    target = frappe.get_doc(target_doctype, target_name)
    return _event(event_type, target, reason, payload or {}, ticket=ticket)


def _active_settings() -> Any:
    settings = frappe.get_single("Ferum Privacy Settings")
    if not settings.enabled:
        frappe.throw(
            _("Protected personnel data заблокированы: FR-05 policy не активирована."),
            frappe.PermissionError,
        )
    if settings.policy_reference != POLICY_REFERENCE or settings.policy_hash != POLICY_HASH:
        frappe.throw(_("Active privacy policy stamp не прошёл проверку."), frappe.PermissionError)
    return settings


def _event(
    event_type: str,
    target: Any,
    reason: str,
    payload: dict[str, Any],
    *,
    ticket: str | None = None,
) -> str:
    occurred_at = now_datetime()
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    correlation = hashlib.sha256(
        f"{event_type}|{target.doctype}|{target.name}|{frappe.session.user}|{occurred_at}|{canonical}".encode()
    ).hexdigest()
    doc = frappe.get_doc(
        {
            "doctype": "Ferum Privacy Event",
            "event_type": event_type,
            "target_doctype": target.doctype,
            "target_name": target.name,
            "actor": frappe.session.user,
            "reason": _required(reason, "reason", 5),
            "ticket": ticket,
            "occurred_at": occurred_at,
            "policy_reference": POLICY_REFERENCE,
            "policy_hash": POLICY_HASH,
            "payload_json": canonical,
            "correlation_key": correlation,
        }
    )
    with _flag(PRIVACY_EVENT_WRITE_FLAG):
        doc.insert(ignore_permissions=True)
    return doc.name


def _worker_external_id(supplier: str) -> str:
    if not frappe.db.exists("Supplier", supplier):
        frappe.throw(_("Supplier не найден."))
    code = re.sub(r"[^A-Z0-9]", "", supplier.upper())[:8] or "SUPPLIER"
    return make_autoname(f"CW-{code}-.#####")


def _basis(value: str, activation_mode: str) -> str:
    basis = _required(value, "privacy_basis_reference", 5)
    if activation_mode == "Synthetic Test" and not basis.startswith("TEST-"):
        frappe.throw(_("Synthetic Test records требуют basis с префиксом TEST-."))
    return basis


def _validate_private_file(name: str, *, require_read_permission: bool = True) -> Any:
    file_doc = frappe.get_doc("File", name)
    if require_read_permission:
        file_doc.check_permission("read")
    if not cint(file_doc.is_private):
        frappe.throw(_("Credential attachment должен быть private."))
    suffix = PurePosixPath(str(file_doc.file_name or "").lower()).suffix
    if suffix not in ALLOWED_ATTACHMENT_SUFFIXES:
        frappe.throw(_("Credential attachment type не входит в allowlist PDF/JPEG/PNG."))
    if cint(file_doc.file_size) > MAX_ATTACHMENT_SIZE:
        frappe.throw(_("Credential attachment превышает 10 MB."))
    return file_doc


def _lock_credential_alias_context(name: str) -> tuple[Any, set[str]]:
    """Lock Credential -> complete alias set and return current state."""

    if not lock_privacy_target(CREDENTIAL_DOCTYPE, name):
        raise frappe.DoesNotExistError(CREDENTIAL_DOCTYPE, name)
    doc = frappe.get_doc(CREDENTIAL_DOCTYPE, name)
    aliases = (
        credential_file_aliases(str(doc.document or ""), for_update=True) if doc.document else ()
    )
    alias_targets = {("File", str(row.name)) for row in aliases}
    if alias_targets - lock_privacy_targets(alias_targets):
        frappe.throw(_("Credential attachment alias set изменён во время блокировки."))
    current = frappe.get_doc(CREDENTIAL_DOCTYPE, name)
    if current.document != doc.document:
        frappe.throw(_("Credential attachment изменён во время блокировки."))
    current_aliases = (
        credential_file_aliases(str(current.document or ""), for_update=True)
        if current.document
        else ()
    )
    current_names = {str(row.name) for row in current_aliases}
    if current_names != {name for _doctype, name in alias_targets}:
        frappe.throw(_("Credential attachment alias set изменён во время блокировки."))
    return current, current_names


def _credential_result(doc: Any, *, mask_number: bool) -> dict[str, Any]:
    number = doc.credential_number_masked if mask_number else doc.get_password("credential_number")
    return {
        "credential": doc.name,
        "holder_type": doc.holder_type,
        "holder": doc.holder,
        "credential_type": doc.credential_type,
        "credential_number": number,
        "verification_status": doc.verification_status,
        "expires_on": str(doc.expires_on) if doc.expires_on else None,
        "no_expiry": bool(doc.no_expiry),
        "malware_status": doc.malware_status,
    }


def _sha256_content(content: bytes | str) -> str:
    payload = content.encode() if isinstance(content, str) else bytes(content)
    return hashlib.sha256(payload).hexdigest()


def _worker_result(doc: Any) -> dict[str, Any]:
    return {
        "worker": doc.name,
        "worker_external_id": doc.worker_external_id,
        "supplier": doc.supplier,
        "display_name": doc.display_name,
        "status": doc.status,
    }


def _settings_result(settings: Any) -> dict[str, Any]:
    return {
        "enabled": bool(settings.enabled),
        "activation_mode": settings.activation_mode,
        "activated_at": str(settings.activated_at) if settings.activated_at else None,
        "activated_by": settings.activated_by,
        "approval_reference": settings.approval_reference,
        "configuration_revision": cint(settings.configuration_revision),
        "policy_reference": settings.policy_reference,
        "policy_hash": settings.policy_hash,
    }


def _require_product_owner(operation: str) -> None:
    _require_roles(PRODUCT_OWNER_ROLES, operation)


def _require_roles(roles: frozenset[str], operation: str) -> None:
    if frappe.session.user == "Administrator":
        return
    if not set(frappe.get_roles(frappe.session.user)).intersection(roles):
        frappe.throw(_("Недостаточно прав: {0}.").format(operation), frappe.PermissionError)


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
