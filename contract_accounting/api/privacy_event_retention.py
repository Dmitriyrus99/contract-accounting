"""Three-year, hold-aware minimization for append-only privacy audit events."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Final
from uuid import uuid4

import frappe
from frappe import _
from frappe.utils import add_years, now_datetime, nowdate

from contract_accounting.infrastructure.privacy_target_lock import (
    lock_privacy_target,
    lock_privacy_targets,
)

EVENT_DOCTYPE: Final[str] = "Ferum Privacy Event"
BLOCKING_HOLD_STATUSES: Final[tuple[str, ...]] = ("Pending", "Active", "Release Pending")
PENDING_RECOVERY_GRACE_SECONDS: Final[int] = 3600
MAX_NATIVE_ARTIFACTS_PER_EVENT: Final[int] = 10_000

# Complete v15 structural inventory in scope. Communication Link is a child
# store; File is also traversed through matching Communication and ToDo parents.
NATIVE_REFERENCE_STORES: Final[tuple[tuple[str, str, str], ...]] = (
    ("Version", "ref_doctype", "docname"),
    ("Comment", "reference_doctype", "reference_name"),
    ("Activity Log", "reference_doctype", "reference_name"),
    ("Communication", "reference_doctype", "reference_name"),
    ("Communication Link", "link_doctype", "link_name"),
    ("ToDo", "reference_type", "reference_name"),
    ("File", "attached_to_doctype", "attached_to_name"),
    ("DocShare", "share_doctype", "share_name"),
)
DIRECT_REFERENCE_FIELDS: Final[dict[str, tuple[str, str]]] = {
    doctype: (doctype_field, name_field)
    for doctype, doctype_field, name_field in NATIVE_REFERENCE_STORES
}


def lock_privacy_event_artifact(doc: Any, method: str | None = None) -> None:
    """Serialize native references and reject missing/anonymized event targets."""

    event_names = set(_privacy_event_names_for_artifact(doc))
    if getattr(doc, "name", None) and not getattr(doc, "is_new", lambda: True)():
        # An update which removes or changes a protected reference must lock the
        # event found through the stored edge as well as the proposed edge.
        event_names.update(_event_names_for_target(str(doc.doctype), str(doc.name)))
    for event_name in sorted(event_names):
        if not lock_privacy_target(EVENT_DOCTYPE, event_name):
            frappe.throw(_("Privacy Event artifact target отсутствует."), frappe.PermissionError)
        if frappe.db.get_value(EVENT_DOCTYPE, event_name, "anonymized_at"):
            frappe.throw(
                _("Anonymized Privacy Event не принимает PII artifacts."),
                frappe.PermissionError,
            )


def anonymize_expired_privacy_events(*, limit: int = 100) -> int:
    """Irreversibly minimize expired events, one savepoint unit at a time."""

    recover_privacy_event_artifact_deletions()
    cutoff = add_years(nowdate(), -3)
    names = frappe.get_all(
        EVENT_DOCTYPE,
        filters={"occurred_at": ["<", cutoff], "anonymized_at": ["is", "not set"]},
        order_by="occurred_at asc, name asc",
        limit_page_length=max(1, min(int(limit), 1000)),
        pluck="name",
    )
    completed = 0
    physical_jobs: list[Path] = []
    for name in names:
        savepoint = f"privacy_event_retention_{completed}"
        frappe.db.savepoint(savepoint)
        try:
            minimized, physical_job = _anonymize_one(str(name), cutoff)
            if minimized:
                completed += 1
            if physical_job:
                physical_jobs.append(physical_job)
        except Exception:
            frappe.db.rollback(save_point=savepoint)
            frappe.log_error(
                title="Privacy Event retention failed",
                message=f"Privacy Event {name} could not be minimized; retry is required.",
            )
    _register_physical_deletion_callbacks(tuple(physical_jobs))
    return completed


def _anonymize_one(name: str, cutoff: str) -> tuple[bool, Path | None]:
    seed = frappe.db.get_value(
        EVENT_DOCTYPE,
        name,
        ("target_doctype", "target_name"),
        as_dict=True,
    )
    if not seed:
        return False, None
    targets = {(EVENT_DOCTYPE, name)}
    if seed.target_doctype and seed.target_name:
        targets.add((str(seed.target_doctype), str(seed.target_name)))
    locked = lock_privacy_targets(targets)
    if (EVENT_DOCTYPE, name) not in locked:
        return False, None
    row = frappe.db.get_value(
        EVENT_DOCTYPE,
        name,
        (
            "target_doctype",
            "target_name",
            "actor",
            "reason",
            "ticket",
            "payload_json",
            "occurred_at",
            "anonymized_at",
        ),
        as_dict=True,
        for_update=True,
    )
    if not row or row.anonymized_at or str(row.occurred_at) >= str(cutoff):
        return False, None

    inventory = _locked_native_artifact_inventory(name)
    file_targets = {("File", file_name) for file_name in inventory["File"]}
    if file_targets - lock_privacy_targets(file_targets):
        frappe.throw(_("Privacy Event File artifact изменён во время retention."))
    hold_targets = {(EVENT_DOCTYPE, name), *file_targets}
    if row.target_doctype and row.target_name:
        hold_targets.add((str(row.target_doctype), str(row.target_name)))
    if _has_blocking_hold(hold_targets):
        return False, None

    physical_entries = _physical_deletion_entries(inventory["File"])
    physical_job = (
        _publish_pending_physical_deletion(name, physical_entries) if physical_entries else None
    )
    try:
        digest = _irreversible_digest(row)
        _delete_native_artifacts(inventory)
        frappe.db.sql(
            """
            update `tabFerum Privacy Event`
               set target_name = null,
                   actor = null,
                   reason = null,
                   ticket = null,
                   payload_json = null,
                   anonymized_at = %s,
                   anonymization_hash = %s,
                   owner = 'Administrator',
                   modified_by = 'Administrator',
                   modified = %s
             where name = %s and anonymized_at is null
            """,
            (now_datetime(), digest, now_datetime(), name),
        )
    except Exception:
        if physical_job:
            _remove_quarantine_job(physical_job)
        raise
    return True, physical_job


def _privacy_event_names_for_artifact(doc: Any) -> frozenset[str]:
    names: set[str] = set()
    fields = DIRECT_REFERENCE_FIELDS.get(str(doc.doctype))
    if fields and doc.get(fields[0]) and doc.get(fields[1]):
        names.update(_event_names_for_target(str(doc.get(fields[0])), str(doc.get(fields[1]))))
    if doc.doctype == "Communication":
        for link in doc.get("timeline_links") or ():
            if link.link_doctype and link.link_name:
                names.update(_event_names_for_target(str(link.link_doctype), str(link.link_name)))
    return frozenset(names)


def _event_names_for_target(
    doctype: str,
    name: str,
    visited: frozenset[tuple[str, str]] = frozenset(),
) -> frozenset[str]:
    """Resolve an event through an arbitrary native-reference artifact chain."""

    target = (str(doctype or ""), str(name or ""))
    if not all(target) or target in visited:
        return frozenset()
    if target[0] == EVENT_DOCTYPE:
        return frozenset({target[1]})
    fields = DIRECT_REFERENCE_FIELDS.get(target[0])
    if not fields:
        return frozenset()
    row = frappe.db.get_value(target[0], target[1], fields, as_dict=True)
    if not row:
        return frozenset()
    next_visited = visited | {target}
    names: set[str] = set()
    if row.get(fields[0]) and row.get(fields[1]):
        names.update(
            _event_names_for_target(
                str(row.get(fields[0])),
                str(row.get(fields[1])),
                next_visited,
            )
        )
    if target[0] == "Communication":
        links = frappe.db.sql(
            """
            select link_doctype, link_name from `tabCommunication Link`
             where parent = %s and parenttype = 'Communication'
            """,
            target[1],
        )
        for link_doctype, link_name in links:
            if link_doctype and link_name:
                names.update(
                    _event_names_for_target(
                        str(link_doctype),
                        str(link_name),
                        next_visited,
                    )
                )
    return frozenset(names)


def _locked_native_artifact_inventory(event_name: str) -> dict[str, tuple[str, ...]]:
    inventory = _native_artifact_inventory(event_name)
    _lock_file_artifact_identities(inventory["File"])
    for doctype, names in sorted(inventory.items()):
        if doctype == "File":
            continue
        for artifact_name in names:
            frappe.db.get_value(doctype, artifact_name, "name", for_update=True)
    # A delete or legacy direct-SQL update does not use the typed hook. Refuse
    # minimization if the exact graph changed while its rows were acquired.
    if inventory != _native_artifact_inventory(event_name):
        frappe.throw(_("Privacy Event native artifact graph изменён во время retention."))
    return inventory


def _lock_file_artifact_identities(file_names: tuple[str, ...]) -> None:
    """Lock the complete File hash/path group in one primary-key order."""

    if not file_names:
        return
    placeholders = ", ".join(["%s"] * len(file_names))
    rows = frappe.db.sql(
        f"""
        select content_hash, file_url, thumbnail_url from `tabFile`
         where name in ({placeholders})
        """,  # nosec B608
        file_names,
    )
    hashes = sorted({str(content_hash) for content_hash, _url, _thumb in rows if content_hash})
    urls = sorted(
        {
            str(file_url)
            for _content_hash, url, thumbnail_url in rows
            for file_url in (url, thumbnail_url)
            if file_url
        }
    )
    conditions = [f"name in ({placeholders})"]
    parameters: list[str] = list(file_names)
    if hashes:
        conditions.append(f"content_hash in ({', '.join(['%s'] * len(hashes))})")
        parameters.extend(hashes)
    if urls:
        placeholders = ", ".join(["%s"] * len(urls))
        conditions.extend((f"file_url in ({placeholders})", f"thumbnail_url in ({placeholders})"))
        parameters.extend(urls)
        parameters.extend(urls)
    frappe.db.sql(
        f"select name from `tabFile` where {' or '.join(conditions)} order by name for update",  # nosec B608
        tuple(parameters),
    )


def _native_artifact_inventory(event_name: str) -> dict[str, tuple[str, ...]]:
    """Return the complete native-reference graph reachable from one event."""

    inventory: dict[str, set[str]] = {doctype: set() for doctype in DIRECT_REFERENCE_FIELDS}
    pending = {(EVENT_DOCTYPE, event_name)}
    visited: set[tuple[str, str]] = set()
    while pending:
        target_doctype, target_name = min(pending)
        pending.remove((target_doctype, target_name))
        if (target_doctype, target_name) in visited:
            continue
        visited.add((target_doctype, target_name))
        for doctype, doctype_field, name_field in NATIVE_REFERENCE_STORES:
            parent_select = ", parent" if doctype == "Communication Link" else ""
            rows = frappe.db.sql(
                f"""
                select name{parent_select} from `tab{doctype}`
                 where `{doctype_field}` = %s and `{name_field}` = %s
                 order by name
                """,  # nosec B608
                (target_doctype, target_name),
            )
            for row in rows:
                artifact_name = str(row[0])
                inventory[doctype].add(artifact_name)
                pending.add((doctype, artifact_name))
                if doctype == "Communication Link" and row[1]:
                    parent = str(row[1])
                    inventory["Communication"].add(parent)
                    pending.add(("Communication", parent))
        if target_doctype == "Communication":
            rows = frappe.db.sql(
                """
                select name from `tabCommunication Link`
                 where parent = %s and parenttype = 'Communication'
                 order by name
                """,
                target_name,
            )
            for row in rows:
                artifact_name = str(row[0])
                inventory["Communication Link"].add(artifact_name)
                pending.add(("Communication Link", artifact_name))
        if sum(map(len, inventory.values())) > MAX_NATIVE_ARTIFACTS_PER_EVENT:
            frappe.throw(_("Privacy Event native artifact graph превысил безопасный лимит."))
    return {doctype: tuple(sorted(names)) for doctype, names in inventory.items()}


def _has_blocking_hold(targets: set[tuple[str, str]]) -> bool:
    for target_doctype, target_name in sorted(targets):
        rows = frappe.db.sql(
            """
            select name from `tabFerum Privacy Legal Hold`
             where target_doctype = %s and target_name = %s
               and status in ('Pending', 'Active', 'Release Pending')
             order by name for update
            """,
            (target_doctype, target_name),
        )
        if rows:
            return True
    return False


def _irreversible_digest(row: Any) -> str:
    canonical = json.dumps(
        {
            "target_doctype": row.target_doctype,
            "target_name": row.target_name,
            "actor": row.actor,
            "reason": row.reason,
            "ticket": row.ticket,
            "payload_json": row.payload_json,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return hashlib.sha256(secrets.token_bytes(32) + canonical).hexdigest()


def _delete_native_artifacts(inventory: dict[str, tuple[str, ...]]) -> None:
    """Purge inventoried DB references without creating Deleted Document PII."""

    for doctype in (
        "Communication Link",
        "Version",
        "Comment",
        "Activity Log",
        "DocShare",
        "ToDo",
        "Communication",
        "File",
    ):
        names = inventory.get(doctype, ())
        if not names:
            continue
        frappe.db.delete(doctype, {"name": ["in", names]})
        frappe.db.delete("__global_search", {"doctype": doctype, "name": ["in", names]})
        if frappe.db.table_exists("Tag Link"):
            frappe.db.delete(
                "Tag Link",
                {"document_type": doctype, "document_name": ["in", names]},
            )


def _physical_deletion_entries(file_names: tuple[str, ...]) -> tuple[dict[str, str], ...]:
    if not file_names:
        return ()
    placeholders = ", ".join(["%s"] * len(file_names))
    rows = frappe.db.sql(
        f"""
        select name, file_url, thumbnail_url, is_folder from `tabFile`
         where name in ({placeholders}) order by name
        """,  # nosec B608
        file_names,
        as_dict=True,
    )
    purge_names = {str(row.name) for row in rows}
    local_urls = sorted(
        {
            str(file_url)
            for row in rows
            for file_url in (row.file_url, row.thumbnail_url)
            if file_url
        }
    )
    for file_url in local_urls:
        _local_file_path(file_url)
    identity_rows: tuple[tuple[str, str | None, str | None], ...] = ()
    if local_urls:
        placeholders = ", ".join(["%s"] * len(local_urls))
        identity_rows = tuple(
            frappe.db.sql(
                f"""
                select name, file_url, thumbnail_url
                  from `tabFile`
                 where file_url in ({placeholders})
                    or thumbnail_url in ({placeholders})
                 order by name for update
                """,  # nosec B608
                tuple(local_urls + local_urls),
            )
        )
    shared_urls = {
        str(file_url)
        for name, file_url, thumbnail_url in identity_rows
        if str(name) not in purge_names
        for file_url in (file_url, thumbnail_url)
        if file_url
    }
    entries: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.is_folder or not row.file_url:
            frappe.throw(_("Privacy Event File artifact не является локальным файлом."))
        for file_url in (row.file_url, row.thumbnail_url):
            if not file_url:
                continue
            path = _local_file_path(str(file_url))
            if str(file_url) in shared_urls:
                continue
            if not path.is_file():
                frappe.throw(_("Privacy Event File artifact bytes отсутствуют."))
            entries[str(path)] = {"path": str(path), "blob": f"{len(entries):04d}.blob"}
    return tuple(entries[path] for path in sorted(entries))


def _local_file_path(file_url: str) -> Path:
    if file_url.startswith("/private/files/"):
        root = Path(frappe.get_site_path("private", "files")).resolve()
    elif file_url.startswith("/files/"):
        root = Path(frappe.get_site_path("public", "files")).resolve()
    else:
        frappe.throw(_("Remote Privacy Event File требует отдельного retention подтверждения."))
    path = (root / Path(file_url).name).resolve()
    if path.parent != root:
        frappe.throw(_("Privacy Event File path вышел за пределы site."))
    return path


def _quarantine_root() -> Path:
    return Path(
        frappe.get_site_path("private", "files", ".privacy-event-retention-quarantine")
    ).resolve()


def _publish_pending_physical_deletion(
    event_name: str,
    entries: tuple[dict[str, str], ...],
) -> Path:
    root = _quarantine_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    job = root / f"{uuid4().hex}.pending"
    job.mkdir(mode=0o700)
    temporary = job / "manifest.json.tmp"
    manifest = job / "manifest.json"
    try:
        temporary.write_text(
            json.dumps(
                {"version": 1, "event": event_name, "created_at": time.time(), "entries": entries},
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        os.replace(temporary, manifest)
    except Exception:
        temporary.unlink(missing_ok=True)
        try:
            job.rmdir()
        except OSError:
            pass
        raise
    return job


def _register_physical_deletion_callbacks(jobs: tuple[Path, ...]) -> None:
    if not jobs:
        return
    frappe.db.after_rollback.add(lambda: _restore_or_remove_pending_jobs(jobs))
    frappe.db.before_commit.add(lambda: _stage_pending_jobs(jobs))
    frappe.db.after_commit.add(lambda: _commit_pending_jobs(jobs))


def _stage_pending_jobs(jobs: tuple[Path, ...]) -> None:
    staged: list[Path] = []
    try:
        for job in jobs:
            staged.append(job)
            _stage_pending_job(job)
    except Exception:
        for job in reversed(staged):
            _restore_pending_job(job)
        raise


def _stage_pending_job(job: Path) -> None:
    payload = _read_manifest(job)
    moved: list[tuple[Path, Path]] = []
    try:
        for entry in payload["entries"]:
            original = _validated_original(str(entry["path"]))
            blob = _validated_blob(job, str(entry["blob"]))
            if not original.is_file() or blob.exists():
                frappe.throw(_("Privacy Event artifact stage state недействителен."))
            os.replace(original, blob)
            moved.append((original, blob))
    except Exception:
        for original, blob in reversed(moved):
            if blob.exists() and not original.exists():
                os.replace(blob, original)
        raise


def _commit_pending_jobs(jobs: tuple[Path, ...]) -> None:
    for job in jobs:
        if not job.exists():
            continue
        committed = job.with_suffix(".committed")
        os.replace(job, committed)
        _finish_committed_job(committed)


def recover_privacy_event_artifact_deletions(*, force: bool = False) -> int:
    root = _quarantine_root()
    if not root.exists():
        return 0
    recovered = 0
    for job in sorted((*root.glob("*.pending"), *root.glob("*.committed"))):
        if job.name.endswith(".committed"):
            _finish_committed_job(job)
            recovered += 1
            continue
        payload = _read_manifest(job)
        if (
            not force
            and time.time() - float(payload["created_at"]) < PENDING_RECOVERY_GRACE_SECONDS
        ):
            continue
        event_name = str(payload["event"])
        if not lock_privacy_target(EVENT_DOCTYPE, event_name):
            frappe.throw(_("Privacy Event retention recovery target отсутствует."))
        event = frappe.db.get_value(
            EVENT_DOCTYPE,
            event_name,
            "anonymized_at",
            for_update=True,
        )
        if event:
            committed = job.with_suffix(".committed")
            os.replace(job, committed)
            _finish_committed_job(committed)
        else:
            inventory = _locked_native_artifact_inventory(event_name)
            file_targets = {("File", name) for name in inventory["File"]}
            if file_targets - lock_privacy_targets(file_targets):
                frappe.throw(_("Privacy Event recovery File set изменён."))
            _restore_pending_job(job)
        recovered += 1
    try:
        root.rmdir()
    except OSError:
        pass
    return recovered


def _restore_or_remove_pending_jobs(jobs: tuple[Path, ...]) -> None:
    for job in reversed(jobs):
        if job.exists():
            _restore_pending_job(job)


def _restore_pending_job(job: Path) -> None:
    if not job.exists():
        return
    payload = _read_manifest(job)
    for entry in reversed(payload["entries"]):
        original = _validated_original(str(entry["path"]))
        blob = _validated_blob(job, str(entry["blob"]))
        if blob.exists() and original.exists():
            frappe.throw(_("Privacy Event artifact rollback path уже занят."))
        if blob.exists():
            os.replace(blob, original)
    _remove_quarantine_job(job)


def _finish_committed_job(job: Path) -> None:
    payload = _read_manifest(job)
    for entry in payload["entries"]:
        _validated_blob(job, str(entry["blob"])).unlink(missing_ok=True)
    _remove_quarantine_job(job)


def _read_manifest(job: Path) -> dict[str, Any]:
    root = _quarantine_root()
    resolved = job.resolve()
    if resolved.parent != root or not resolved.name.endswith((".pending", ".committed")):
        frappe.throw(_("Privacy Event retention job path недействителен."))
    manifest = resolved / "manifest.json"
    if not manifest.is_file():
        frappe.throw(_("Privacy Event retention ledger повреждён."))
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if (
        payload.get("version") != 1
        or not payload.get("event")
        or not isinstance(payload.get("created_at"), int | float)
        or not isinstance(payload.get("entries"), list)
    ):
        frappe.throw(_("Privacy Event retention ledger version недействителен."))
    for entry in payload["entries"]:
        if not isinstance(entry, dict) or "path" not in entry or "blob" not in entry:
            frappe.throw(_("Privacy Event retention ledger entry недействителен."))
        _validated_original(str(entry["path"]))
        _validated_blob(resolved, str(entry["blob"]))
    return payload


def _validated_original(raw_path: str) -> Path:
    path = Path(raw_path).resolve()
    roots = (
        Path(frappe.get_site_path("public", "files")).resolve(),
        Path(frappe.get_site_path("private", "files")).resolve(),
    )
    if not any(path.parent == root for root in roots):
        frappe.throw(_("Privacy Event retention path вышел за пределы site files."))
    return path


def _validated_blob(job: Path, blob_name: str) -> Path:
    if not blob_name or Path(blob_name).name != blob_name:
        frappe.throw(_("Privacy Event retention blob path недействителен."))
    blob = (job.resolve() / blob_name).resolve()
    if blob.parent != job.resolve():
        frappe.throw(_("Privacy Event retention blob вышел за пределы job."))
    return blob


def _remove_quarantine_job(job: Path) -> None:
    (job / "manifest.json.tmp").unlink(missing_ok=True)
    (job / "manifest.json").unlink(missing_ok=True)
    job.rmdir()
