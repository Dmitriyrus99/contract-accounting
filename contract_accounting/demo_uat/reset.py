"""Dry-run-first reverse reset for the owned demo/UAT graph."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Final, Mapping, Sequence

from contract_accounting.demo_uat.bootstrap import owned_record_rows
from contract_accounting.demo_uat.file_safety import FileRecoverySet
from contract_accounting.demo_uat.installer import CommitState
from contract_accounting.demo_uat.manifest import RESET_CONFIRMATION_TOKEN, load_manifest
from contract_accounting.demo_uat.ownership import (
    deletion_plan,
    find_inbound_non_demo_links,
    find_registry_file_names,
    inspect_user_on_trash_effects,
    load_registry,
    manifest_record_presence,
    owned_activity_log_names,
    owned_generated_comment_names,
)
from contract_accounting.demo_uat.runtime import (
    DemoUATRuntimeError,
    fresh_database_connection,
    get_frappe,
    require_administrator,
    require_exact_token,
    require_local_site,
    validate_runtime_preflight,
)

_GUARDED_CUSTOM_DELETE_BYPASS: Final[frozenset[str]] = frozenset(
    {
        "Ferum Billing Cycle",
        "Ferum Contract Obligation",
        "Ferum Contract Requirement",
        "Ferum Contractor Assignment",
        "Ferum Contractor Worker",
        "Ferum Finding",
        "Ferum Inspection",
        "Ferum Maintenance Schedule",
        "Ferum Maintenance Visit",
        "Ferum Material Expense",
        "Ferum Personnel Credential",
        "Ferum Photo Evidence",
        "Ferum Process Evidence",
        "Ferum Project Document",
        "Ferum Project Document Event",
        "Ferum Project Object",
        "Ferum Project Process",
        "Ferum Project Process Step",
        "Ferum Project Stage",
        "Ferum Service Request",
        "Ferum Stage Gate",
    }
)
_COMPANY_DERIVED_DOCTYPES: Final[tuple[str, ...]] = (
    "Account",
    "Warehouse",
    "Cost Center",
    "Department",
    "Mode of Payment Account",
)
_RESET_AUDIT_DOCTYPES: Final[tuple[str, ...]] = (
    "Comment",
    "Deleted Document",
    "Version",
)
_RESET_COMMIT_TARGETS_FLAG: Final[str] = "contract_accounting_demo_reset_commit_targets"


def reset(
    confirmation_token: str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Bench entrypoint; ``dry_run=True`` is the immutable safe default."""

    require_exact_token(confirmation_token, RESET_CONFIRMATION_TOKEN, "reset")
    if not isinstance(dry_run, bool):
        raise DemoUATRuntimeError("dry_run must be a JSON boolean")
    frappe = get_frappe()
    site = require_local_site(frappe)
    require_administrator(frappe)
    manifest = load_manifest()
    registry, registry_file_name = load_registry(manifest, site=site, required=False)
    if registry is None:
        residue = manifest_record_presence(manifest)
        bootstrap_rows = owned_record_rows()
        bootstrap_residue = [
            row for row in bootstrap_rows if frappe.db.exists(str(row["doctype"]), str(row["name"]))
        ]
        company = next(
            str(row["name"]) for row in bootstrap_rows if str(row["doctype"]) == "Company"
        )
        derived_residue = find_derived_residue(
            registry_records=[
                {"doctype": entity["doctype"], "name": entity["record_name"]}
                for entity in manifest["entities"]
            ],
            bootstrap_records=bootstrap_rows,
            bindings={"company": company},
        )
        if residue or bootstrap_residue or derived_residue or find_registry_file_names():
            raise DemoUATRuntimeError(
                "reset refused: owned-looking records exist without registry: "
                + repr((residue + bootstrap_residue + derived_residue)[:10])
            )
        return {
            "status": "RESET_COMPLETE_NOT_A_UAT_RESULT",
            "dry_run": dry_run,
            "site": site,
            "delete_count": 0,
            "deleted": [],
            "plan": [],
            "blockers": [],
        }
    assert registry is not None and registry_file_name is not None
    bindings = registry["bindings"]
    validate_runtime_preflight(manifest, bindings)
    missing_owned = [
        row
        for row in [*registry["records"], *registry["bootstrap_records"]]
        if not frappe.db.exists(str(row["doctype"]), str(row["name"]))
    ]
    if missing_owned:
        raise DemoUATRuntimeError(
            "reset refused: registry-owned records are missing: " + repr(missing_owned[:10])
        )

    plan = deletion_plan(
        manifest,
        registry_file_name=registry_file_name,
        bootstrap_records=registry["bootstrap_records"],
    )
    generated_comment_names = owned_generated_comment_names(
        registry_records=registry["records"],
        bootstrap_records=registry["bootstrap_records"],
    )
    activity_log_names = owned_activity_log_names(
        registry_records=registry["records"],
        bootstrap_records=registry["bootstrap_records"],
        registry_created_at=registry["created_at"],
    )
    user_effects = inspect_user_on_trash_effects(
        registry_records=registry["records"],
        bootstrap_records=registry["bootstrap_records"],
        registry_created_at=registry["created_at"],
        registry_created_by=registry["created_by"],
    )
    audit_targets = {
        (str(row["doctype"]), str(row["name"]))
        for row in [*registry["records"], *registry["bootstrap_records"]]
    }
    audit_targets.add(("File", registry_file_name))
    audit_targets.update(("Comment", name) for name in generated_comment_names)
    audit_targets.update(("Activity Log", name) for name in activity_log_names)
    audit_targets.update((str(row["doctype"]), str(row["name"])) for row in user_effects["owned"])
    # Company.on_trash removes generated ERP masters internally. Capture their
    # exact current names before deletion so every delete-feed/history row can
    # be attributed without any namespace substring heuristic.
    audit_targets.update(_current_company_derived_targets(frappe, bindings))
    privacy_target: tuple[str, str] | None = None
    if registry["privacy_policy"]["changed_by_demo"]:
        privacy_target = ("Ferum Privacy Settings", "Ferum Privacy Settings")
        audit_targets.add(privacy_target)
    audit_targets.update(
        ("Notification Settings", str(row["name"]))
        for row in registry["bootstrap_records"]
        if str(row["doctype"]) == "User"
    )
    audit_actors = {
        str(registry["created_by"]),
        *(
            str(row["name"])
            for row in registry["bootstrap_records"]
            if str(row["doctype"]) == "User"
        ),
    }
    current_audit_rows = find_reset_audit_artifacts(audit_targets, allowed_actors=audit_actors)
    audit_scan_at = frappe.utils.now_datetime()
    target_created_at = {
        target: frappe.utils.get_datetime(frappe.db.get_value(target[0], target[1], "creation"))
        for target in audit_targets
        if frappe.db.exists(target[0], target[1])
    }
    if privacy_target is not None:
        # The singleton predates the dataset. The signed registry carries the
        # exact timestamp at which this installer activated the demo policy.
        target_created_at[privacy_target] = frappe.utils.get_datetime(
            registry["privacy_policy"]["demo_state"]["activated_at"]
        )
    audit_owned = [
        row
        for row in current_audit_rows
        if (str(row["target_doctype"]), str(row["target_name"])) in target_created_at
        and target_created_at[(str(row["target_doctype"]), str(row["target_name"]))]
        <= frappe.utils.get_datetime(row["creation"])
        <= audit_scan_at
    ]
    audit_external = [
        row
        for row in current_audit_rows
        if row not in audit_owned
        and (
            privacy_target is None
            or (str(row["target_doctype"]), str(row["target_name"])) != privacy_target
        )
    ]
    audit_snapshot = _reset_audit_snapshot(frappe)
    derived_plan = (
        [
            {
                "order": 0,
                "external_id": f"derived.comment.{name}",
                "doctype": "Comment",
                "name": name,
            }
            for name in generated_comment_names
        ]
        + [
            {
                "order": 0,
                "external_id": f"derived.activity-log.{name}",
                "doctype": "Activity Log",
                "name": name,
            }
            for name in activity_log_names
        ]
        + [
            {
                "order": 0,
                "external_id": f"derived.user-effect.{row['doctype']}.{row['name']}",
                "doctype": str(row["doctype"]),
                "name": str(row["name"]),
            }
            for row in user_effects["owned"]
            if bool(row["delete_before_user"])
        ]
        + [
            {
                "order": 0,
                "external_id": f"derived.reset-audit.{row['doctype']}.{row['name']}",
                "doctype": str(row["doctype"]),
                "name": str(row["name"]),
            }
            for row in audit_owned
        ]
    )
    if derived_plan:
        plan = [
            *derived_plan,
            *plan,
        ]
        for order, item in enumerate(plan, start=1):
            item["order"] = order
    expected_audit_snapshot = {
        doctype: names
        - {str(row["name"]) for row in audit_owned if str(row["doctype"]) == doctype}
        - {str(item["name"]) for item in plan if str(item["doctype"]) == doctype}
        for doctype, names in audit_snapshot.items()
    }
    inbound = find_inbound_non_demo_links(
        registry_records=registry["records"],
        registry_file_name=registry_file_name,
        bootstrap_records=registry["bootstrap_records"],
        bindings=bindings,
        registry_created_at=registry["created_at"],
        registry_created_by=registry["created_by"],
    )
    inbound.extend(
        {
            "target_doctype": str(row["target_doctype"]),
            "target_name": str(row["target_name"]),
            "source_doctype": str(row["doctype"]),
            "source_name": str(row["name"]),
            "fieldname": str(row["fieldname"]),
        }
        for row in audit_external
    )
    inbound = [
        {key: str(value) for key, value in row.items()}
        for _, row in sorted(
            {
                (
                    row["target_doctype"],
                    row["target_name"],
                    row["source_doctype"],
                    row["source_name"],
                    row["fieldname"],
                ): row
                for row in inbound
            }.items()
        )
    ]
    if inbound:
        if dry_run:
            return {
                "status": "RESET_BLOCKED_BY_INBOUND_NON_DEMO_LINKS",
                "dry_run": True,
                "site": site,
                "delete_count": 0,
                "plan": plan,
                "blockers": inbound,
            }
        raise DemoUATRuntimeError(
            "reset refused: inbound non-demo links exist: " + repr(inbound[:10])
        )
    if dry_run:
        return {
            "status": "RESET_DRY_RUN_ONLY",
            "dry_run": True,
            "site": site,
            "delete_count": 0,
            "plan": plan,
            "blockers": [],
        }

    prior_privacy_state = _prepare_privacy_restore(frappe, registry["privacy_policy"])
    file_snapshots = _snapshot_file_blobs(frappe, plan)
    session_ids = _owned_session_ids(frappe, registry["bootstrap_records"])
    savepoint = "ca_demo_uat_v1_reset"
    frappe.db.savepoint(savepoint)
    try:
        if session_ids:
            frappe.db.delete("Sessions", {"sid": ["in", session_ids]})
        for item in plan:
            external_id = str(item["external_id"])
            if external_id.startswith("derived.reset-audit.") or external_id.startswith(
                "derived.user-effect.DocShare."
            ):
                # These are exact owned rows whose Frappe hooks only produce
                # additional feed residue. Existing Shared comments have their
                # own exact plan entries.
                frappe.db.delete(item["doctype"], {"name": item["name"]})
            else:
                if item["doctype"] == "File" and external_id.startswith(
                    "derived.user-effect.File."
                ):
                    # Its exact Attachment feed is already in the owned plan.
                    # Detach before File.on_trash so reset cannot create a new
                    # "Attachment Removed" feed row for the soon-deleted User.
                    frappe.db.set_value(
                        "File",
                        item["name"],
                        {
                            "attached_to_doctype": None,
                            "attached_to_name": None,
                            "attached_to_field": None,
                        },
                        update_modified=False,
                    )
                frappe.delete_doc(
                    item["doctype"],
                    item["name"],
                    ignore_permissions=True,
                    force=True,
                    # Only explicitly enumerated immutable Ferum controllers are
                    # bypassed. ERPNext Company/User hooks must clean their own
                    # Accounts, Warehouses, Cost Centers, permissions and sessions.
                    ignore_on_trash=item["doctype"] in _GUARDED_CUSTOM_DELETE_BYPASS,
                    # Parent deletion may already remove an owned attachment.
                    # Presence was checked against the registry before the plan.
                    ignore_missing=True,
                    delete_permanently=True,
                )
        if prior_privacy_state is not None:
            _restore_privacy_state(frappe, prior_privacy_state)
        cleanup_targets = (
            audit_targets
            | {(str(item["doctype"]), str(item["name"])) for item in plan}
            | {("Ferum Privacy Settings", "Ferum Privacy Settings")}
        )
        _cleanup_reset_audit_delta(
            frappe,
            expected_snapshot=expected_audit_snapshot,
            allowed_targets=cleanup_targets,
            allowed_actors=audit_actors,
        )
        remaining = manifest_record_presence(manifest)
        remaining_bootstrap = [
            row
            for row in registry["bootstrap_records"]
            if frappe.db.exists(str(row["doctype"]), str(row["name"]))
        ]
        remaining_registries = find_registry_file_names()
        remaining_generated_comments = [
            name for name in generated_comment_names if frappe.db.exists("Comment", name)
        ]
        remaining_activity_logs = [
            name for name in activity_log_names if frappe.db.exists("Activity Log", name)
        ]
        remaining_derived = find_derived_residue(
            registry_records=registry["records"],
            bootstrap_records=registry["bootstrap_records"],
            bindings=bindings,
            registry_created_at=registry["created_at"],
        )
        remaining_audit_delta = _reset_audit_delta(frappe, expected_audit_snapshot)
        if (
            remaining
            or remaining_bootstrap
            or remaining_registries
            or remaining_generated_comments
            or remaining_activity_logs
            or remaining_derived
            or remaining_audit_delta
        ):
            raise DemoUATRuntimeError(
                "reset postcondition failed: "
                f"records={remaining} bootstrap={remaining_bootstrap} "
                f"registries={remaining_registries} "
                f"generated_comments={remaining_generated_comments} "
                f"activity_logs={remaining_activity_logs} derived={remaining_derived}"
                f" audit_delta={remaining_audit_delta}"
            )
    except Exception as operation_error:
        _recover_reset_files(
            frappe,
            file_snapshots,
            operation_error=operation_error,
            savepoint=savepoint,
        )
        raise
    commit_targets = frozenset(cleanup_targets)
    setattr(frappe.flags, _RESET_COMMIT_TARGETS_FLAG, commit_targets)
    expected_audit_fingerprints = _reset_audit_fingerprints(frappe)

    # Run after callbacks registered by the reset itself. It turns any
    # successful same-transaction audit mutation into an ambiguous commit
    # exception, which is then reconciled only from durable state.
    def audit_watchdog() -> None:
        callbacks = getattr(frappe.db.after_commit, "_functions", ())
        if callbacks:
            # A callback ahead of us may enqueue more work behind us. Requeue
            # the watchdog until it is genuinely the final callback, then
            # fingerprint the durable audit graph.
            callbacks.append(audit_watchdog)
            return
        _assert_reset_audit_fingerprints(frappe, expected_audit_fingerprints)

    frappe.db.after_commit.add(audit_watchdog)
    try:
        frappe.db.commit()
    except Exception as commit_error:
        commit_state = _reset_commit_state(
            frappe,
            manifest=manifest,
            registry=registry,
            expected_audit_snapshot=expected_audit_snapshot,
            file_snapshots=file_snapshots,
            expected_audit_fingerprints=expected_audit_fingerprints,
        )
        if commit_state is CommitState.NOT_COMMITTED:
            _recover_reset_files(
                frappe,
                file_snapshots,
                operation_error=commit_error,
                savepoint=None,
            )
            raise
        if commit_state is CommitState.UNKNOWN:
            raise DemoUATRuntimeError(
                "reset commit outcome is UNKNOWN; destructive File recovery refused; "
                f"quarantine retained at {file_snapshots['recovery'].directory}"
            ) from commit_error
        # The reset transaction is durably committed, but an after_commit
        # callback may have opened a new transaction before raising.  Clear
        # that callback transaction so its audit mutation cannot leak into the
        # request or be committed by a later operation.
        try:
            frappe.db.rollback()
        except Exception as rollback_error:
            raise DemoUATRuntimeError(
                "reset committed, but the failed after_commit callback transaction "
                "could not be rolled back; discard this database connection"
            ) from rollback_error
    finally:
        # An earlier after_commit callback may raise before the watchdog is
        # reached. Frappe then leaves the unexecuted callbacks in its deque;
        # remove only our exact callback so it cannot poison a later request.
        callbacks = getattr(frappe.db.after_commit, "_functions", ())
        try:
            callbacks.remove(audit_watchdog)
        except ValueError:
            pass
        setattr(frappe.flags, _RESET_COMMIT_TARGETS_FLAG, None)
    file_snapshots["recovery"].discard()
    for sid in session_ids:
        frappe.cache.hdel("session", sid)
        frappe.cache.hdel("last_db_session_update", sid)
    return {
        "status": "RESET_COMPLETE_NOT_A_UAT_RESULT",
        "dry_run": False,
        "site": site,
        "delete_count": len(plan),
        "deleted": plan,
    }


def prevent_reset_commit_artifact(doc: Any, method: str | None = None) -> None:
    """Block audit rows created by callbacks after the reset final check."""

    targets = getattr(get_frappe().flags, _RESET_COMMIT_TARGETS_FLAG, None)
    if not targets:
        return
    target = (str(doc.get("ref_doctype") or ""), str(doc.get("docname") or ""))
    if target in targets:
        raise DemoUATRuntimeError(
            f"reset commit callback attempted to create Version for {target[0]}/{target[1]}"
        )


def _reset_commit_state(
    frappe: Any,
    *,
    manifest: dict[str, Any],
    registry: Mapping[str, Any],
    expected_audit_snapshot: Mapping[str, set[str]],
    file_snapshots: Mapping[str, Any],
    expected_audit_fingerprints: Mapping[str, Mapping[str, str]],
) -> CommitState:
    """Resolve an ambiguous reset commit exception from durable postconditions."""

    try:
        with fresh_database_connection(frappe):
            if manifest_record_presence(manifest) or find_registry_file_names():
                all_owned = all(
                    frappe.db.exists(str(row["doctype"]), str(row["name"]))
                    for row in [*registry["records"], *registry["bootstrap_records"]]
                )
                return CommitState.NOT_COMMITTED if all_owned else CommitState.UNKNOWN
            if any(
                frappe.db.exists(str(row["doctype"]), str(row["name"]))
                for row in registry["bootstrap_records"]
            ):
                return CommitState.UNKNOWN
            if find_derived_residue(
                registry_records=registry["records"],
                bootstrap_records=registry["bootstrap_records"],
                bindings=registry["bindings"],
                registry_created_at=registry["created_at"],
            ):
                return CommitState.UNKNOWN
            if _reset_audit_delta(frappe, expected_audit_snapshot):
                return CommitState.UNKNOWN
            if _reset_audit_fingerprints(frappe) != expected_audit_fingerprints:
                return CommitState.UNKNOWN
            if any(Path(row["path"]).exists() for row in file_snapshots["rows"]):
                return CommitState.UNKNOWN
            return CommitState.COMMITTED
    except Exception:
        return CommitState.UNKNOWN


def find_reset_audit_artifacts(
    targets: set[tuple[str, str]],
    *,
    allowed_actors: set[str],
) -> list[dict[str, Any]]:
    """Return exact Frappe delete-feed/history rows for deterministic targets."""

    frappe = get_frappe()
    artifacts: list[dict[str, Any]] = []
    for target_doctype, target_name in sorted(targets):
        if frappe.db.exists("DocType", "Deleted Document"):
            for row in (
                frappe.get_all(
                    "Deleted Document",
                    filters={
                        "deleted_doctype": target_doctype,
                        "deleted_name": target_name,
                        "owner": ["in", sorted(allowed_actors)],
                    },
                    fields=["name", "creation"],
                )
                or []
            ):
                artifacts.append(
                    {
                        "doctype": "Deleted Document",
                        "name": str(row.name),
                        "creation": row.creation,
                        "target_doctype": target_doctype,
                        "target_name": target_name,
                        "fieldname": "deleted_name",
                    }
                )
        if frappe.db.exists("DocType", "Version"):
            for row in (
                frappe.get_all(
                    "Version",
                    filters={
                        "ref_doctype": target_doctype,
                        "docname": target_name,
                        "owner": ["in", sorted(allowed_actors)],
                    },
                    fields=["name", "creation"],
                )
                or []
            ):
                artifacts.append(
                    {
                        "doctype": "Version",
                        "name": str(row.name),
                        "creation": row.creation,
                        "target_doctype": target_doctype,
                        "target_name": target_name,
                        "fieldname": "docname",
                    }
                )
        if frappe.db.exists("DocType", "Comment"):
            for row in (
                frappe.get_all(
                    "Comment",
                    filters={
                        "comment_type": "Deleted",
                        "reference_doctype": target_doctype,
                        "subject": ["like", f"% {target_name}"],
                        "owner": ["in", sorted(allowed_actors)],
                    },
                    fields=["name", "subject", "creation"],
                )
                or []
            ):
                if str(row.subject or "").endswith(f" {target_name}"):
                    artifacts.append(
                        {
                            "doctype": "Comment",
                            "name": str(row.name),
                            "creation": row.creation,
                            "target_doctype": target_doctype,
                            "target_name": target_name,
                            "fieldname": "subject",
                        }
                    )
    unique = {(row["doctype"], row["name"]): row for row in artifacts}
    return [unique[key] for key in sorted(unique)]


def _reset_audit_snapshot(frappe: Any) -> dict[str, set[str]]:
    return {
        doctype: (
            {str(name) for name in (frappe.get_all(doctype, pluck="name") or [])}
            if frappe.db.exists("DocType", doctype)
            else set()
        )
        for doctype in _RESET_AUDIT_DOCTYPES
    }


def _reset_audit_fingerprints(frappe: Any) -> dict[str, dict[str, str]]:
    """Fingerprint complete audit documents, including same-name mutations."""

    result: dict[str, dict[str, str]] = {}
    for doctype in _RESET_AUDIT_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            result[doctype] = {}
            continue
        rows: dict[str, str] = {}
        for name in frappe.get_all(doctype, pluck="name") or []:
            document = frappe.get_doc(doctype, name).as_dict(no_nulls=False)
            canonical = json.dumps(document, sort_keys=True, default=str, ensure_ascii=False)
            rows[str(name)] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        result[doctype] = rows
    return result


def _assert_reset_audit_fingerprints(
    frappe: Any, expected: Mapping[str, Mapping[str, str]]
) -> None:
    actual = _reset_audit_fingerprints(frappe)
    if actual != expected:
        raise DemoUATRuntimeError("reset after_commit changed external audit history")


def _current_company_derived_targets(
    frappe: Any, bindings: Mapping[str, str]
) -> set[tuple[str, str]]:
    company = str(bindings["company"])
    targets: set[tuple[str, str]] = set()
    for doctype in _COMPANY_DERIVED_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue
        targets.update(
            (doctype, str(name))
            for name in (frappe.get_all(doctype, filters={"company": company}, pluck="name") or [])
        )
    return targets


def _reset_audit_delta(
    frappe: Any,
    expected_snapshot: Mapping[str, set[str]],
) -> list[dict[str, str]]:
    current = _reset_audit_snapshot(frappe)
    delta: list[dict[str, str]] = []
    for doctype in _RESET_AUDIT_DOCTYPES:
        for name in sorted(current[doctype] - expected_snapshot[doctype]):
            delta.append({"doctype": doctype, "name": name, "change": "added"})
        for name in sorted(expected_snapshot[doctype] - current[doctype]):
            delta.append({"doctype": doctype, "name": name, "change": "removed-external"})
    return delta


def _cleanup_reset_audit_delta(
    frappe: Any,
    *,
    expected_snapshot: Mapping[str, set[str]],
    allowed_targets: set[tuple[str, str]],
    allowed_actors: set[str],
) -> None:
    delta = _reset_audit_delta(frappe, expected_snapshot)
    removed_external = [row for row in delta if row["change"] == "removed-external"]
    if removed_external:
        raise DemoUATRuntimeError(
            "reset changed preexisting audit history: " + repr(removed_external[:10])
        )
    added = {(row["doctype"], row["name"]) for row in delta if row["change"] == "added"}
    exact = {
        (str(row["doctype"]), str(row["name"]))
        for row in find_reset_audit_artifacts(allowed_targets, allowed_actors=allowed_actors)
    }
    unmatched = sorted(added - exact)
    if unmatched:
        raise DemoUATRuntimeError(
            "reset created unattributed audit residue: " + repr(unmatched[:10])
        )
    for doctype, name in sorted(added):
        frappe.db.delete(doctype, {"name": name})


def _audit_residue_rows(
    registry_records: Sequence[Mapping[str, Any]],
    bootstrap_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    targets = {
        (str(row["doctype"]), str(row["name"])) for row in [*registry_records, *bootstrap_records]
    }
    targets.update(
        ("Notification Settings", str(row["name"]))
        for row in bootstrap_records
        if str(row["doctype"]) == "User"
    )
    actors = {str(row["name"]) for row in bootstrap_records if str(row["doctype"]) == "User"} | {
        "Administrator"
    }
    exact = find_reset_audit_artifacts(targets, allowed_actors=actors)
    residue = [
        {
            "doctype": str(row["doctype"]),
            "name": str(row["name"]),
            "reason": (f"reset audit residue for {row['target_doctype']}/{row['target_name']}"),
        }
        for row in exact
    ]
    # A deleted Activity Log has a generated hash name, so after a lost
    # registry its exact target cannot be reconstructed. Fail closed only for
    # rows in the same actor/time cluster as deterministic demo delete-feed
    # artifacts; reset never auto-deletes in this no-registry branch.
    if exact:
        frappe = get_frappe()
        created = [frappe.utils.get_datetime(row["creation"]) for row in exact]
        from datetime import timedelta

        window = [min(created) - timedelta(seconds=2), max(created) + timedelta(seconds=2)]
        for row in (
            frappe.get_all(
                "Comment",
                filters={
                    "comment_type": "Deleted",
                    "reference_doctype": "Activity Log",
                    "creation": ["between", window],
                    "owner": ["in", sorted(actors)],
                },
                fields=["name", "subject"],
            )
            or []
        ):
            if str(row.subject or "").startswith("Activity Log "):
                residue.append(
                    {
                        "doctype": "Comment",
                        "name": str(row.name),
                        "reason": "orphan Activity Log delete-feed in demo reset cluster",
                    }
                )
    unique = {(row["doctype"], row["name"], row["reason"]): row for row in residue}
    return [unique[key] for key in sorted(unique)]


def find_derived_residue(
    *,
    registry_records: Sequence[Mapping[str, Any]],
    bootstrap_records: Sequence[Mapping[str, Any]],
    bindings: Mapping[str, str],
    registry_created_at: Any | None = None,
) -> list[dict[str, str]]:
    """Find standard Frappe/ERPNext rows derived from owned Company/User data."""

    frappe = get_frappe()
    owned = {
        (str(row["doctype"]), str(row["name"])) for row in [*registry_records, *bootstrap_records]
    }
    users = sorted(name for doctype, name in owned if doctype == "User")
    company = str(bindings["company"])
    residue: list[dict[str, str]] = []
    residue.extend(_audit_residue_rows(registry_records, bootstrap_records))

    def collect(doctype: str, filters: Mapping[str, Any], reason: str) -> None:
        if not frappe.db.exists("DocType", doctype):
            return
        for name in frappe.get_all(doctype, filters=dict(filters), pluck="name") or []:
            residue.append({"doctype": doctype, "name": str(name), "reason": reason})

    for doctype in _COMPANY_DERIVED_DOCTYPES:
        collect(doctype, {"company": company}, f"company={company}")
    if users:
        collect("User Permission", {"user": ["in", users]}, "owned synthetic user")
        collect("ToDo", {"allocated_to": ["in", users]}, "owned synthetic assignee")
        collect("DocShare", {"user": ["in", users]}, "owned synthetic share user")
        collect("Token Cache", {"user": ["in", users]}, "owned synthetic token user")
        collect("Token", {"user": ["in", users]}, "owned synthetic token user")
        collect("Contact", {"user": ["in", users]}, "owned synthetic user contact")
        collect(
            "Comment",
            {"reference_doctype": "User", "reference_name": ["in", users]},
            "owned synthetic user comment",
        )
        if registry_created_at is not None:
            for name in owned_activity_log_names(
                registry_records=registry_records,
                bootstrap_records=bootstrap_records,
                registry_created_at=registry_created_at,
            ):
                residue.append(
                    {
                        "doctype": "Activity Log",
                        "name": name,
                        "reason": "owned synthetic user activity within dataset lifecycle",
                    }
                )
        else:
            # Without a registry there is no safe lifecycle timestamp. Any
            # Activity Log owned by a deterministic bootstrap user is residue
            # and must make the zero-delete result fail closed.
            collect(
                "Activity Log",
                {"user": ["in", users]},
                "deterministic synthetic user activity without registry",
            )
    for doctype, name in sorted(owned):
        collect(
            "User Permission",
            {"allow": doctype, "for_value": name},
            f"owned target {doctype}/{name}",
        )
        collect(
            "ToDo",
            {"reference_type": doctype, "reference_name": name},
            f"owned target {doctype}/{name}",
        )
        collect(
            "DocShare",
            {"share_doctype": doctype, "share_name": name},
            f"owned target {doctype}/{name}",
        )
    if users:
        placeholders = ", ".join(["%s"] * len(users))
        sessions = frappe.db.sql(
            f"select sid as name, user from `tabSessions` where user in ({placeholders})",
            tuple(users),
            as_dict=True,
        )
        residue.extend(
            {
                "doctype": "Sessions",
                "name": str(row.name),
                "reason": f"owned synthetic session user={row.user}",
            }
            for row in sessions
        )
    unique = {(row["doctype"], row["name"], row["reason"]): row for row in residue}
    return [unique[key] for key in sorted(unique)]


def _owned_session_ids(frappe: Any, bootstrap_records: Sequence[Mapping[str, Any]]) -> list[str]:
    users = sorted(str(row["name"]) for row in bootstrap_records if str(row["doctype"]) == "User")
    if not users:
        return []
    placeholders = ", ".join(["%s"] * len(users))
    return [
        str(row.sid)
        for row in frappe.db.sql(
            f"select sid from `tabSessions` where user in ({placeholders})",
            tuple(users),
            as_dict=True,
        )
    ]


def _prepare_privacy_restore(frappe: Any, policy: Mapping[str, Any]) -> dict[str, Any] | None:
    if not policy["changed_by_demo"]:
        return None
    from contract_accounting.demo_uat.bootstrap import (
        _privacy_state,
        _privacy_state_fingerprint,
    )

    current = _privacy_state(frappe.get_single("Ferum Privacy Settings"))
    if _privacy_state_fingerprint(current) != policy["demo_fingerprint"]:
        raise DemoUATRuntimeError(
            "reset refused: demo-owned privacy policy state has external drift"
        )
    return dict(policy["prior_state"])


def _restore_privacy_state(frappe: Any, prior_state: Mapping[str, Any]) -> None:
    from contract_accounting.contract_accounting.doctype.ferum_privacy_settings.ferum_privacy_settings import (
        PRIVACY_SETTINGS_WRITE_FLAG,
    )
    from contract_accounting.demo_uat.bootstrap import (
        _privacy_state,
        _privacy_state_fingerprint,
    )

    previous = frappe.flags.get(PRIVACY_SETTINGS_WRITE_FLAG)
    frappe.flags[PRIVACY_SETTINGS_WRITE_FLAG] = True
    try:
        settings = frappe.get_single("Ferum Privacy Settings")
        for fieldname, value in prior_state.items():
            settings.set(fieldname, value)
        settings.save(ignore_permissions=True)
        restored = _privacy_state(frappe.get_single("Ferum Privacy Settings"))
        if _privacy_state_fingerprint(restored) != _privacy_state_fingerprint(prior_state):
            raise DemoUATRuntimeError("privacy policy prior state restore postcondition failed")
    finally:
        frappe.flags[PRIVACY_SETTINGS_WRITE_FLAG] = previous


def _snapshot_file_blobs(frappe: Any, plan: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    paths: list[Path] = []
    names: list[str] = []
    for item in plan:
        if item["doctype"] != "File" or not frappe.db.exists("File", item["name"]):
            continue
        document = frappe.get_doc("File", item["name"])
        if not str(document.file_url or "").startswith("/private/files/"):
            raise DemoUATRuntimeError(
                f"reset refuses non-private or external owned File path: {document.name}"
            )
        path = Path(document.get_full_path()).resolve()
        content = path.read_bytes()
        names.append(str(document.name))
        paths.append(path)
        rows.append(
            {
                "name": str(document.name),
                "file_url": str(document.file_url),
                "path": path,
                "sha256": hashlib.sha256(content).hexdigest(),
                "content_hash": str(document.content_hash or ""),
                "file_name": str(document.file_name or ""),
                "is_private": int(document.is_private or 0),
                "attached_to_doctype": str(document.attached_to_doctype or ""),
                "attached_to_name": str(document.attached_to_name or ""),
                "attached_to_field": str(document.attached_to_field or ""),
            }
        )
    recovery = FileRecoverySet(frappe, paths, operation="reset")
    recovery.track_file_documents(names)
    return {"rows": rows, "recovery": recovery}


def _restore_file_blobs(frappe: Any, snapshots: Mapping[str, Any]) -> None:
    recovery = snapshots["recovery"]
    recovery.restore()
    for snapshot in snapshots["rows"]:
        name = str(snapshot["name"])
        if not frappe.db.exists("File", name):
            raise DemoUATRuntimeError(
                f"reset rollback did not restore File database row: {name}; "
                f"quarantine retained at {recovery.directory}"
            )
        document = frappe.get_doc("File", name)
        actual = {
            "file_url": str(document.file_url),
            "content_hash": str(document.content_hash or ""),
            "file_name": str(document.file_name or ""),
            "is_private": int(document.is_private or 0),
            "attached_to_doctype": str(document.attached_to_doctype or ""),
            "attached_to_name": str(document.attached_to_name or ""),
            "attached_to_field": str(document.attached_to_field or ""),
        }
        expected = {key: snapshot[key] for key in actual}
        if actual != expected:
            raise DemoUATRuntimeError(
                f"reset rollback File database row drift: {name}; "
                f"quarantine retained at {recovery.directory}"
            )
        path = Path(document.get_full_path()).resolve()
        if path != Path(snapshot["path"]) or not path.is_file():
            raise DemoUATRuntimeError(
                f"reset rollback File path drift: {name}; quarantine retained at "
                f"{recovery.directory}"
            )
        if hashlib.sha256(path.read_bytes()).hexdigest() != snapshot["sha256"]:
            raise DemoUATRuntimeError(
                f"reset rollback could not restore File bytes: {name}; quarantine retained at "
                f"{recovery.directory}"
            )


def _recover_reset_files(
    frappe: Any,
    snapshots: Mapping[str, Any],
    *,
    operation_error: Exception,
    savepoint: str | None,
) -> None:
    recovery = snapshots["recovery"]
    try:
        if savepoint is None:
            frappe.db.rollback()
        else:
            frappe.db.rollback(save_point=savepoint)
        _restore_file_blobs(frappe, snapshots)
        recovery.discard()
    except Exception as recovery_error:
        raise DemoUATRuntimeError(
            "reset failed and exact database/File recovery is incomplete; "
            f"quarantine retained at {recovery.directory}; original error: "
            f"{type(operation_error).__name__}"
        ) from recovery_error
