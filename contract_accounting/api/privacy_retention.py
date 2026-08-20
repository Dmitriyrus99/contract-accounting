"""Explicit dry-run-first FR-05 retention execution."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime

from contract_accounting.api.privacy import (
    PRIVACY_RETENTION_FLAG,
    PRIVACY_TRANSITION_FLAG,
    PRIVACY_WRITE_FLAG,
    active_privacy_settings,
    record_privacy_event,
)
from contract_accounting.api.privacy_controls import has_active_legal_hold
from contract_accounting.domain.privacy import (
    PRODUCTION_RETENTION_CONFIRMATION,
    SYNTHETIC_RETENTION_CONFIRMATION,
    PrivacyRuleError,
    retention_due,
)
from contract_accounting.infrastructure.privacy_file_guard import (
    RETENTION_FILE_DELETE_FLAG,
    credential_file_aliases,
)
from contract_accounting.infrastructure.privacy_target_lock import (
    lock_privacy_target,
    lock_privacy_targets,
)

RETENTION_ROLES = frozenset(
    {"Ответственный за ПДн", "Юрист", "Генеральный директор", "Менеджер персональных данных"}
)
PENDING_RECOVERY_GRACE_SECONDS = 3600


@frappe.whitelist()
def get_privacy_retention_plan(as_of: str) -> dict[str, Any]:
    _require_roles(RETENTION_ROLES, "view privacy retention plan")
    active_privacy_settings()
    plan_date = getdate(as_of)
    return {"as_of": str(plan_date), "dry_run": True, "actions": _build_plan(plan_date)}


@frappe.whitelist(methods=["POST"])
def execute_privacy_retention(as_of: str, confirmation: str, reason: str) -> dict[str, Any]:
    _require_roles(RETENTION_ROLES, "execute privacy retention")
    settings = active_privacy_settings()
    expected = (
        SYNTHETIC_RETENTION_CONFIRMATION
        if settings.activation_mode == "Synthetic Test"
        else PRODUCTION_RETENTION_CONFIRMATION
    )
    if confirmation != expected:
        frappe.throw(_("Retention confirmation не совпадает с activation mode."))
    reason = _required(reason, "reason", 10)
    retry_committed_physical_deletions()
    plan_date = getdate(as_of)
    actions = _build_plan(plan_date)
    executed: list[dict[str, Any]] = []
    physical_jobs: list[Path] = []
    for action in actions:
        if action["blocked_by_legal_hold"]:
            continue
        current = _lock_and_revalidate_action(action, plan_date)
        if current is None:
            continue
        physical_job = _execute_action(current, reason)
        if physical_job:
            physical_jobs.append(physical_job)
        executed.append(current)
    _register_physical_deletion_commit_callbacks(tuple(physical_jobs))
    return {
        "as_of": str(plan_date),
        "dry_run": False,
        "planned": len(actions),
        "executed": len(executed),
        "skipped_after_recheck": len(actions) - len(executed),
        "actions": executed,
    }


def _build_plan(as_of: date) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for worker in frappe.get_all(
        "Ferum Contractor Worker",
        fields=["name", "creation", "contact", "retention_status"],
        order_by="name asc",
        ignore_permissions=True,
    ):
        base = _holder_base_date(
            "Ferum Contractor Worker", worker.name, getdate(worker.creation), as_of
        )
        if base is None:
            continue
        try:
            due = retention_due(base_date=base, as_of=as_of)
        except PrivacyRuleError:
            continue
        if due.contact and worker.contact and worker.retention_status == "Active":
            actions.append(
                _action("Clear Worker Contact", "Ferum Contractor Worker", worker.name, base)
            )
        if due.metadata and worker.retention_status != "Anonymized":
            actions.append(
                _action("Anonymize Worker", "Ferum Contractor Worker", worker.name, base)
            )

    for credential in frappe.get_all(
        "Ferum Personnel Credential",
        fields=[
            "name",
            "creation",
            "holder_type",
            "holder",
            "issued_on",
            "expires_on",
            "document",
            "retention_status",
        ],
        order_by="name asc",
        ignore_permissions=True,
    ):
        fallback = getdate(credential.expires_on or credential.issued_on or credential.creation)
        base = _holder_base_date(credential.holder_type, credential.holder, fallback, as_of)
        if base is None:
            continue
        if credential.expires_on:
            base = max(base, getdate(credential.expires_on))
        try:
            due = retention_due(base_date=base, as_of=as_of)
        except PrivacyRuleError:
            continue
        if due.attachment and credential.document and credential.retention_status == "Active":
            actions.append(
                _action(
                    "Delete Credential File",
                    "Ferum Personnel Credential",
                    credential.name,
                    base,
                    file_name=credential.document,
                )
            )
        if due.metadata and credential.retention_status != "Metadata Only":
            actions.append(
                _action(
                    "Minimize Credential Metadata",
                    "Ferum Personnel Credential",
                    credential.name,
                    base,
                )
            )
    return actions


def _holder_base_date(holder_type: str, holder: str, fallback: date, as_of: date) -> date | None:
    rows = _holder_assignments(holder_type, holder)
    if rows is None:
        return fallback
    return _base_date_from_assignments(rows, fallback, as_of)


def _base_date_from_assignments(rows: tuple[Any, ...], fallback: date, as_of: date) -> date | None:
    if any(
        row.status in {"Approved", "Suspended"}
        and (not row.effective_to or getdate(row.effective_to) >= as_of)
        for row in rows
    ):
        return None
    ends = [getdate(row.effective_to) for row in rows if row.effective_to]
    return max([fallback, *ends])


def _action(
    action: str,
    target_doctype: str,
    target_name: str,
    base_date: date,
    *,
    file_name: str | None = None,
) -> dict[str, Any]:
    held = has_active_legal_hold(target_doctype, target_name)
    file_aliases: list[str] = []
    if file_name:
        aliases = credential_file_aliases(file_name)
        file_aliases = [str(row.name) for row in aliases]
        held = held or any(has_active_legal_hold("File", name) for name in file_aliases)
        held = held or any(
            has_active_legal_hold(doctype, name)
            for doctype, name, _fieldname in _blob_business_references(
                aliases,
                target_name,
                allowed_targets=_credential_holder_targets(target_name),
                for_update=False,
            )
        )
    return {
        "action": action,
        "target_doctype": target_doctype,
        "target_name": target_name,
        "file": file_name,
        "file_aliases": file_aliases,
        "base_date": str(base_date),
        "blocked_by_legal_hold": held,
    }


def _holder_assignments(
    holder_type: str,
    holder: str,
    *,
    for_update: bool = False,
) -> tuple[Any, ...] | None:
    fieldname = {
        "Ferum Contractor Worker": "contractor_worker",
        "Employee": "employee",
    }.get(holder_type)
    if not fieldname:
        return None
    lock_clause = " for update" if for_update else ""
    return tuple(
        frappe.db.sql(
            f"""
            select name, status, effective_from, effective_to
              from `tabFerum Contractor Assignment`
             where `{fieldname}` = %s
             order by name
             {lock_clause}
            """,  # nosec: fieldname and lock_clause come from closed constants above.
            (holder,),
            as_dict=True,
        )
    )


def _lock_hold_rows(targets: set[tuple[str, str]]) -> tuple[Any, ...]:
    if not targets:
        return ()
    ordered = sorted(targets)
    conditions = " or ".join("(target_doctype = %s and target_name = %s)" for _target in ordered)
    parameters = tuple(value for target in ordered for value in target)
    return tuple(
        frappe.db.sql(
            f"""
            select name, target_doctype, target_name, status
              from `tabFerum Privacy Legal Hold`
             where {conditions}
             order by target_doctype, target_name, name
             for update
            """,  # nosec: only the number of parameterized predicates is dynamic.
            parameters,
            as_dict=True,
        )
    )


def _has_locked_active_hold(targets: set[tuple[str, str]]) -> bool:
    return any(row.status == "Active" for row in _lock_hold_rows(targets))


def _lock_and_revalidate_action(action: dict[str, Any], as_of: date) -> dict[str, Any] | None:
    if action["target_doctype"] == "Ferum Contractor Worker":
        return _revalidate_worker_action(action, as_of)
    if action["target_doctype"] == "Ferum Personnel Credential":
        return _revalidate_credential_action(action, as_of)
    return None


def _revalidate_worker_action(action: dict[str, Any], as_of: date) -> dict[str, Any] | None:
    name = str(action["target_name"])
    if not lock_privacy_target("Ferum Contractor Worker", name):
        return None
    assignments = _holder_assignments(
        "Ferum Contractor Worker",
        name,
        for_update=True,
    )
    targets = {("Ferum Contractor Worker", name)}
    if _has_locked_active_hold(targets):
        return None
    worker = frappe.get_doc("Ferum Contractor Worker", name)
    base = _base_date_from_assignments(assignments or (), getdate(worker.creation), as_of)
    if base is None:
        return None
    try:
        due = retention_due(base_date=base, as_of=as_of)
    except PrivacyRuleError:
        return None
    if action["action"] == "Clear Worker Contact":
        eligible = due.contact and worker.contact and worker.retention_status == "Active"
    elif action["action"] == "Anonymize Worker":
        eligible = due.metadata and worker.retention_status != "Anonymized"
    else:
        return None
    return _action(action["action"], worker.doctype, worker.name, base) if eligible else None


def _revalidate_credential_action(
    action: dict[str, Any],
    as_of: date,
) -> dict[str, Any] | None:
    name = str(action["target_name"])
    seed = frappe.db.get_value(
        "Ferum Personnel Credential",
        name,
        ("holder_type", "holder"),
        as_dict=True,
    )
    if not seed:
        return None
    targets = {("Ferum Personnel Credential", name)}
    if seed.holder_type in {"Ferum Contractor Worker", "Employee"}:
        targets.add((str(seed.holder_type), str(seed.holder)))
    locked = lock_privacy_targets(targets)
    if ("Ferum Personnel Credential", name) not in locked:
        return None

    credential = frappe.get_doc("Ferum Personnel Credential", name)
    assignments = _holder_assignments(
        credential.holder_type,
        credential.holder,
        for_update=True,
    )
    aliases = (
        credential_file_aliases(credential.document, for_update=True) if credential.document else ()
    )
    alias_targets = {("File", str(row.name)) for row in aliases}
    if alias_targets - lock_privacy_targets(alias_targets):
        return None
    # Credential is locked, so compliant File creation cannot add an alias
    # between this second resolution and the destructive operation.
    aliases = (
        credential_file_aliases(credential.document, for_update=True) if credential.document else ()
    )
    alias_targets = {("File", str(row.name)) for row in aliases}
    hold_targets = {("Ferum Personnel Credential", name)}
    if action["action"] == "Delete Credential File":
        hold_targets.update(alias_targets)
    if _has_locked_active_hold(hold_targets):
        return None
    if action["action"] == "Delete Credential File" and _blob_business_references(
        aliases,
        credential.name,
        allowed_targets={(str(credential.holder_type), str(credential.holder))},
        for_update=True,
    ):
        # A content hash/path can be shared by another Credential or a normal
        # business artifact. Retention must never delete that owner's bytes.
        return None

    fallback = getdate(credential.expires_on or credential.issued_on or credential.creation)
    base = _base_date_from_assignments(assignments or (), fallback, as_of)
    if base is None:
        return None
    if credential.expires_on:
        base = max(base, getdate(credential.expires_on))
    try:
        due = retention_due(base_date=base, as_of=as_of)
    except PrivacyRuleError:
        return None
    if action["action"] == "Delete Credential File":
        eligible = (
            due.attachment
            and credential.document
            and aliases
            and credential.retention_status == "Active"
        )
        return (
            _action(
                action["action"],
                credential.doctype,
                credential.name,
                base,
                file_name=credential.document,
            )
            if eligible
            else None
        )
    if action["action"] == "Minimize Credential Metadata":
        eligible = due.metadata and credential.retention_status != "Metadata Only"
        return (
            _action(action["action"], credential.doctype, credential.name, base)
            if eligible
            else None
        )
    return None


def _execute_action(action: dict[str, Any], reason: str) -> Path | None:
    if action["target_doctype"] == "Ferum Contractor Worker":
        doc = frappe.get_doc(action["target_doctype"], action["target_name"])
        with _flag(PRIVACY_WRITE_FLAG), _flag(PRIVACY_RETENTION_FLAG):
            if action["action"] == "Clear Worker Contact":
                doc.contact = None
                doc.work_contact_confirmed = 0
                doc.retention_status = "Contact Removed"
            else:
                with _flag(PRIVACY_TRANSITION_FLAG, "Archived"):
                    doc.status = "Archived"
                    doc.archived_at = now_datetime()
                    doc.archived_by = frappe.session.user
                    doc.display_name = doc.worker_external_id
                    doc.supplier = None
                    doc.position = None
                    doc.contact = None
                    doc.work_contact_confirmed = 0
                    doc.privacy_basis_reference = None
                    doc.data_owner = None
                    doc.retention_status = "Anonymized"
                    doc.transition_reason = reason
                    doc.save(ignore_permissions=True)
                    record_privacy_event(
                        action["action"], doc.doctype, doc.name, reason, {"retention": "3 years"}
                    )
                    return None
            doc.save(ignore_permissions=True)
        record_privacy_event(
            action["action"], doc.doctype, doc.name, reason, {"retention": "90 days"}
        )
        return None

    doc = frappe.get_doc(action["target_doctype"], action["target_name"])
    if action["action"] == "Delete Credential File":
        file_name = str(doc.document or "")
        aliases = credential_file_aliases(file_name)
        alias_names = tuple(str(row.name) for row in aliases)
        content_hashes = {str(row.content_hash) for row in aliases if row.content_hash}
        alias_documents = [frappe.get_doc("File", name) for name in alias_names]
        if _blob_business_references(
            aliases,
            doc.name,
            allowed_targets={(str(doc.holder_type), str(doc.holder))},
            for_update=True,
        ):
            frappe.throw(
                _("Credential blob используется другим документом; physical retention запрещён."),
                frappe.PermissionError,
            )
        physical_deletions = _physical_deletion_entries(alias_documents)
        with _flag(PRIVACY_WRITE_FLAG), _flag(PRIVACY_RETENTION_FLAG):
            doc.document = None
            doc.malware_status = "Not Applicable"
            doc.malware_scan_reference = None
            doc.scanned_file_hash = None
            doc.scanned_at = None
            doc.scanned_by = None
            doc.retention_status = "File Removed"
            doc.save(ignore_permissions=True)
        with _flag(RETENTION_FILE_DELETE_FLAG, frozenset(alias_names)):
            for name in alias_names:
                frappe.delete_doc(
                    "File",
                    name,
                    ignore_permissions=True,
                    force=True,
                    ignore_on_trash=True,
                )
        # Physical bytes remain untouched while actions run. A durable pending
        # intent is published before commit; the final before-commit callback
        # moves paths under the retained DB locks, and after-commit unlinks only
        # quarantined bytes. Any staged fault restores synchronously.
        remaining_names = [name for name in alias_names if frappe.db.exists("File", name)]
        remaining_hashes = [
            content_hash
            for content_hash in content_hashes
            if frappe.db.exists("File", {"content_hash": content_hash})
        ]
        missing_paths = [
            str(entry["path"])
            for entry in physical_deletions
            if not os.path.isfile(str(entry["path"]))
        ]
        if remaining_names or remaining_hashes or missing_paths:
            frappe.throw(
                _("Credential retention physical/database postcondition не выполнен."),
                frappe.ValidationError,
            )
        record_privacy_event(
            action["action"],
            doc.doctype,
            doc.name,
            reason,
            {
                "file_deleted": bool(file_name),
                "file_aliases_deleted": len(alias_names),
                "physical_paths_scheduled": len(physical_deletions),
            },
        )
        return _schedule_physical_deletions(physical_deletions, str(doc.name))
    with _flag(PRIVACY_WRITE_FLAG), _flag(PRIVACY_RETENTION_FLAG):
        doc.credential_number = None
        doc.credential_number_masked = None
        doc.issuer = None
        doc.retention_status = "Metadata Only"
        doc.save(ignore_permissions=True)
    record_privacy_event(action["action"], doc.doctype, doc.name, reason, {"retention": "3 years"})
    return None


def _physical_deletion_entries(alias_documents: list[Any]) -> tuple[dict[str, Any], ...]:
    entries: dict[str, dict[str, Any]] = {}
    for alias in alias_documents:
        path = str(Path(alias.get_full_path()).resolve())
        entry = entries.setdefault(
            path,
            {"path": path, "file_urls": set(), "content_hashes": set()},
        )
        if alias.file_url:
            entry["file_urls"].add(str(alias.file_url))
        if alias.content_hash:
            entry["content_hashes"].add(str(alias.content_hash))
        thumbnail_url = str(alias.get("thumbnail_url") or "").strip()
        if thumbnail_url:
            thumbnail_path = _strict_local_file_path(thumbnail_url)
            thumbnail_entry = entries.setdefault(
                str(thumbnail_path),
                {"path": str(thumbnail_path), "file_urls": set(), "content_hashes": set()},
            )
            thumbnail_entry["file_urls"].add(thumbnail_url)
    return tuple(
        {
            "path": path,
            "file_urls": sorted(entry["file_urls"]),
            "content_hashes": sorted(entry["content_hashes"]),
            "size": Path(path).stat().st_size,
            "sha256": _sha256_file(Path(path)),
        }
        for path, entry in sorted(entries.items())
    )


def _blob_business_references(
    aliases: tuple[Any, ...],
    credential_name: str,
    *,
    allowed_targets: set[tuple[str, str]] | None = None,
    for_update: bool,
) -> tuple[tuple[str, str, str], ...]:
    """Inventory every standard File/Attach reference to the complete blob identity."""

    alias_names = {str(row.name) for row in aliases}
    alias_urls = {str(row.file_url) for row in aliases if row.file_url}
    values = sorted(alias_names | alias_urls)
    if not values:
        return ()
    references: set[tuple[str, str, str]] = set()
    allowed = set(allowed_targets or ())
    allowed.add(("Ferum Personnel Credential", credential_name))
    for row in aliases:
        attached_doctype = str(row.get("attached_to_doctype") or "")
        attached_name = str(row.get("attached_to_name") or "")
        if attached_doctype and attached_name and (attached_doctype, attached_name) not in allowed:
            references.add((attached_doctype, attached_name, "File.attached_to"))

    fields = list(
        frappe.db.sql(
            """
            select parent, fieldname, fieldtype
              from `tabDocField`
             where fieldtype in ('Attach', 'Attach Image')
                or (fieldtype = 'Link' and options = 'File')
            union all
            select dt as parent, fieldname, fieldtype
              from `tabCustom Field`
             where fieldtype in ('Attach', 'Attach Image')
                or (fieldtype = 'Link' and options = 'File')
             order by parent, fieldname
            """,
            as_dict=True,
        )
    )
    placeholders = ", ".join(["%s"] * len(values))
    lock_clause = " for update" if for_update else ""
    for field in fields:
        doctype = str(field.parent)
        fieldname = str(field.fieldname)
        if not re.fullmatch(r"[A-Za-z0-9 _-]+", doctype) or not re.fullmatch(
            r"[A-Za-z0-9_]+", fieldname
        ):
            frappe.throw(_("Небезопасная File reference metadata; retention остановлен."))
        if not frappe.db.table_exists(doctype):
            continue
        rows = frappe.db.sql(
            f"select name from `tab{doctype}` where `{fieldname}` in ({placeholders})"
            f" order by name{lock_clause}",  # nosec B608: identifiers come from validated metadata.
            tuple(values),
        )
        for (name,) in rows:
            if (doctype, str(name)) in allowed:
                continue
            references.add((doctype, str(name), fieldname))
    return tuple(sorted(references))


def _credential_holder_targets(credential_name: str) -> set[tuple[str, str]]:
    row = frappe.db.get_value(
        "Ferum Personnel Credential",
        credential_name,
        ("holder_type", "holder"),
        as_dict=True,
    )
    return {(str(row.holder_type), str(row.holder))} if row and row.holder else set()


def _strict_local_file_path(file_url: str) -> Path:
    """Resolve only Frappe's two local file namespaces."""

    normalized = str(file_url or "").strip()
    if normalized.startswith("/private/files/"):
        root = Path(frappe.get_site_path("private", "files")).resolve()
        relative = normalized.removeprefix("/private/files/")
    elif normalized.startswith("/files/"):
        root = Path(frappe.get_site_path("public", "files")).resolve()
        relative = normalized.removeprefix("/files/")
    else:
        frappe.throw(_("Credential derivative path не является local File path."))
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root) or not relative:
        frappe.throw(_("Credential derivative path вышел за пределы files root."))
    return resolved


def _schedule_physical_deletions(
    entries: tuple[dict[str, Any], ...],
    credential_name: str,
) -> Path:
    """Publish intent before commit; move bytes while DB row locks are held."""

    job = _publish_pending_physical_deletion(entries, credential_name)
    frappe.db.after_rollback.add(lambda: _recover_pending_physical_deletion(job, force=True))
    return job


def _register_physical_deletion_commit_callbacks(jobs: tuple[Path, ...]) -> None:
    if not jobs:
        return
    frappe.db.before_commit.add(lambda: _stage_pending_jobs_for_commit(jobs))
    frappe.db.after_commit.add(lambda: _commit_pending_jobs(jobs))


def _stage_pending_jobs_for_commit(jobs: tuple[Path, ...]) -> None:
    staged: list[Path] = []
    try:
        for job in jobs:
            staged.append(job)
            _stage_pending_physical_deletion(job)
        # frappe.db.commit() cleared rollback callbacks before entering this
        # callback. Re-register restoration now so an SQL COMMIT exception and
        # the request rollback restore bytes in the same failure path.
        frappe.db.after_rollback.add(lambda: _restore_staged_pending_jobs(jobs))
    except Exception:
        for job in reversed(staged):
            _restore_staged_pending_physical_deletion(job)
        raise


def _restore_staged_pending_jobs(jobs: tuple[Path, ...]) -> None:
    for job in reversed(jobs):
        _restore_staged_pending_physical_deletion(job)


def _commit_pending_jobs(jobs: tuple[Path, ...]) -> None:
    for job in jobs:
        _commit_pending_physical_deletion(job)


def _restore_staged_pending_physical_deletion(job: Path) -> None:
    if not job.exists():
        return
    payload = _read_quarantine_manifest(job)
    for entry in reversed(payload["entries"]):
        original = _validated_original_path(str(entry["path"]))
        blob = _validated_blob_path(job, str(entry["blob"]))
        if blob.exists() and original.exists():
            frappe.throw(
                _("Credential retention staged rollback path уже занят."),
                frappe.ValidationError,
            )
        if blob.exists():
            _validate_physical_content(blob, entry)
            os.replace(blob, original)
    _remove_quarantine_job(job)


def _quarantine_root() -> Path:
    return Path(frappe.get_site_path("private", "files", ".privacy-retention-quarantine")).resolve()


def _publish_pending_physical_deletion(
    entries: tuple[dict[str, Any], ...],
    credential_name: str,
) -> Path:
    root = _quarantine_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    job = root / f"{uuid4().hex}.pending"
    job.mkdir(mode=0o700)
    manifest_entries = []
    for index, entry in enumerate(entries):
        original = _validated_original_path(str(entry["path"]))
        manifest_entries.append(
            {
                "path": str(original),
                "file_urls": sorted({str(value) for value in entry.get("file_urls", ())}),
                "content_hashes": sorted({str(value) for value in entry.get("content_hashes", ())}),
                "size": int(entry.get("size", original.stat().st_size)),
                "sha256": str(entry.get("sha256") or _sha256_file(original)),
                "blob": f"{index:04d}.blob",
            }
        )
    temporary_manifest = job / "manifest.json.tmp"
    manifest = job / "manifest.json"
    try:
        _write_json_durable(
            temporary_manifest,
            {
                "version": 1,
                "credential": str(credential_name),
                "created_at": time.time(),
                "entries": manifest_entries,
            },
        )
        os.replace(temporary_manifest, manifest)
        _fsync_directory(job)
        _fsync_directory(root)
    except Exception:
        temporary_manifest.unlink(missing_ok=True)
        try:
            job.rmdir()
        except OSError:
            pass
        raise
    return job


def retry_committed_physical_deletions(*, force: bool = False) -> int:
    """Recover pending rollbacks and finish interrupted committed cleanup."""

    root = _quarantine_root()
    if not root.exists():
        return 0
    completed = 0
    for job in sorted((*root.glob("*.pending"), *root.glob("*.committed"))):
        try:
            if job.name.endswith(".pending"):
                if not _recover_pending_physical_deletion(job, force=force):
                    continue
            else:
                _finish_committed_physical_deletion(job)
            completed += 1
        except Exception as exc:
            _mark_quarantine_job_error(job, exc)
    try:
        root.rmdir()
    except OSError:
        pass
    return completed


def _stage_pending_physical_deletion(job: Path) -> None:
    payload = _read_quarantine_manifest(job)
    moved: list[tuple[Path, Path]] = []
    try:
        for entry in payload["entries"]:
            original = _validated_original_path(str(entry["path"]))
            blob = _validated_blob_path(job, str(entry["blob"]))
            if not original.is_file() or blob.exists():
                frappe.throw(
                    _("Credential retention source/quarantine state недействителен."),
                    frappe.ValidationError,
                )
            _validate_physical_content(original, entry)
            os.replace(original, blob)
            moved.append((original, blob))
        _fsync_directory(job)
        for directory in {original.parent for original, _blob in moved}:
            _fsync_directory(directory)
    except Exception:
        for original, blob in reversed(moved):
            if blob.exists() and not original.exists():
                os.replace(blob, original)
        _remove_quarantine_job(job)
        raise


def _commit_pending_physical_deletion(job: Path) -> None:
    if not job.exists():
        return
    committed = job.with_suffix(".committed")
    os.replace(job, committed)
    _fsync_directory(committed.parent)
    _finish_committed_physical_deletion(committed)


def _recover_pending_physical_deletion(job: Path, *, force: bool = False) -> bool:
    if not job.exists():
        return False
    payload = _read_quarantine_manifest(job)
    if not force and time.time() - float(payload["created_at"]) < PENDING_RECOVERY_GRACE_SECONDS:
        return False
    credential, locked_alias_names = _lock_pending_recovery_context(payload)
    committed = not credential or (
        not credential.document and credential.retention_status in {"File Removed", "Metadata Only"}
    )
    if committed:
        committed_job = job.with_suffix(".committed")
        os.replace(job, committed_job)
        _finish_committed_physical_deletion(committed_job)
        return True
    _recheck_pending_recovery_context(payload, credential, locked_alias_names)
    for entry in reversed(payload["entries"]):
        original = _validated_original_path(str(entry["path"]))
        blob = _validated_blob_path(job, str(entry["blob"]))
        if blob.exists() and original.exists():
            frappe.throw(
                _("Credential retention rollback path уже занят."),
                frappe.ValidationError,
            )
        if blob.exists():
            _validate_physical_content(blob, entry)
            os.replace(blob, original)
            _fsync_directory(original.parent)
    _remove_quarantine_job(job)
    return True


def _lock_pending_recovery_context(
    payload: dict[str, Any],
) -> tuple[Any | None, frozenset[str]]:
    credential_name = str(payload["credential"])
    if not lock_privacy_target("Ferum Personnel Credential", credential_name):
        return None, frozenset()
    credential = frappe.get_doc("Ferum Personnel Credential", credential_name)
    aliases = (
        credential_file_aliases(str(credential.document), for_update=True)
        if credential.document
        else ()
    )
    alias_targets = {("File", str(row.name)) for row in aliases}
    if alias_targets - lock_privacy_targets(alias_targets):
        frappe.throw(
            _("Credential retention recovery alias set изменён во время блокировки."),
            frappe.ValidationError,
        )
    locked_names = frozenset(name for _doctype, name in alias_targets)
    _recheck_pending_recovery_context(payload, credential, locked_names)
    return frappe.get_doc("Ferum Personnel Credential", credential_name), locked_names


def _recheck_pending_recovery_context(
    payload: dict[str, Any],
    expected_credential: Any,
    expected_alias_names: frozenset[str],
) -> None:
    current = frappe.get_doc("Ferum Personnel Credential", str(payload["credential"]))
    if (
        current.document != expected_credential.document
        or current.retention_status != expected_credential.retention_status
    ):
        frappe.throw(
            _("Credential retention recovery state изменён во время блокировки."),
            frappe.ValidationError,
        )
    aliases = (
        credential_file_aliases(str(current.document), for_update=True) if current.document else ()
    )
    current_names = frozenset(str(row.name) for row in aliases)
    if current_names != expected_alias_names:
        frappe.throw(
            _("Credential retention recovery alias set изменён после блокировки."),
            frappe.ValidationError,
        )
    if current.document:
        alias_paths = {
            str(Path(frappe.get_doc("File", name).get_full_path()).resolve())
            for name in current_names
        }
        manifest_paths = {
            str(_validated_original_path(str(entry["path"]))) for entry in payload["entries"]
        }
        if not manifest_paths.issubset(alias_paths):
            frappe.throw(
                _("Credential retention recovery manifest не совпадает с alias paths."),
                frappe.ValidationError,
            )


def _finish_committed_physical_deletion(job: Path) -> None:
    payload = _read_quarantine_manifest(job)
    for entry in payload["entries"]:
        blob = _validated_blob_path(job, str(entry["blob"]))
        if blob.exists():
            _validate_physical_content(blob, entry)
        blob.unlink(missing_ok=True)
    _fsync_directory(job)
    _remove_quarantine_job(job)


def _read_quarantine_manifest(job: Path) -> dict[str, Any]:
    root = _quarantine_root()
    resolved_job = job.resolve()
    if resolved_job.parent != root or not resolved_job.name.endswith((".pending", ".committed")):
        frappe.throw(
            _("Credential retention quarantine job path недействителен."),
            frappe.ValidationError,
        )
    manifest = resolved_job / "manifest.json"
    if not manifest.is_file():
        frappe.throw(
            _("Credential retention quarantine ledger повреждён."),
            frappe.ValidationError,
        )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if (
        payload.get("version") != 1
        or not payload.get("credential")
        or not isinstance(payload.get("created_at"), int | float)
        or not isinstance(payload.get("entries"), list)
    ):
        frappe.throw(
            _("Credential retention quarantine ledger version не поддерживается."),
            frappe.ValidationError,
        )
    for entry in payload["entries"]:
        if (
            not isinstance(entry, dict)
            or "path" not in entry
            or "blob" not in entry
            or not isinstance(entry.get("size"), int)
            or int(entry["size"]) < 0
            or not isinstance(entry.get("sha256"), str)
            or len(str(entry["sha256"])) != 64
        ):
            frappe.throw(
                _("Credential retention quarantine entry недействителен."),
                frappe.ValidationError,
            )
        _validated_original_path(str(entry["path"]))
        _validated_blob_path(resolved_job, str(entry["blob"]))
    return payload


def _validated_original_path(raw_path: str) -> Path:
    original = Path(raw_path).resolve()
    allowed_roots = (
        Path(frappe.get_site_path("public", "files")).resolve(),
        Path(frappe.get_site_path("private", "files")).resolve(),
    )
    if not any(original.is_relative_to(root) for root in allowed_roots):
        frappe.throw(
            _("Credential retention path вышел за пределы public/private files."),
            frappe.ValidationError,
        )
    return original


def _validated_blob_path(job: Path, blob_name: str) -> Path:
    if not blob_name or Path(blob_name).name != blob_name:
        frappe.throw(
            _("Credential retention quarantine blob path недействителен."),
            frappe.ValidationError,
        )
    blob = (job.resolve() / blob_name).resolve()
    if not blob.is_relative_to(job.resolve()):
        frappe.throw(
            _("Credential retention quarantine blob вышел за пределы job."),
            frappe.ValidationError,
        )
    return blob


def _remove_quarantine_job(job: Path) -> None:
    (job / "manifest.json.tmp").unlink(missing_ok=True)
    (job / "manifest.json").unlink(missing_ok=True)
    job.rmdir()
    _fsync_directory(job.parent)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_physical_content(path: Path, entry: dict[str, Any]) -> None:
    if path.stat().st_size != int(entry["size"]) or _sha256_file(path) != str(entry["sha256"]):
        frappe.throw(
            _("Credential retention quarantine content hash/size не совпадает."),
            frappe.ValidationError,
        )


def _write_json_durable(path: Path, payload: dict[str, Any]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _mark_quarantine_job_error(job: Path, exc: Exception) -> None:
    try:
        root = _quarantine_root()
        resolved = job.resolve()
        if resolved.parent != root or not resolved.name.endswith((".pending", ".committed")):
            _log_quarantine_error(
                "Privacy retention quarantine job rejected",
                f"unsafe job reference: {type(exc).__name__}",
            )
            return
        error_job = resolved.with_suffix(".error")
        if error_job.exists():
            error_job = root / f"{resolved.stem}-{uuid4().hex}.error"
        os.replace(resolved, error_job)
        _write_json_durable(
            error_job / "error.json",
            {
                "version": 1,
                "failed_at": time.time(),
                "source_job": resolved.name,
                "error_type": type(exc).__name__,
            },
        )
        _fsync_directory(error_job)
        _fsync_directory(root)
        _log_quarantine_error(
            "Privacy retention quarantine job isolated",
            f"job={error_job.name}; error={type(exc).__name__}",
        )
    except Exception as isolation_exc:
        _log_quarantine_error(
            "Privacy retention quarantine isolation failed",
            f"job={job.name}; error={type(exc).__name__}; isolation={type(isolation_exc).__name__}",
        )


def _log_quarantine_error(title: str, message: str) -> None:
    try:
        frappe.log_error(title=title, message=message)
    except Exception:
        pass


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
