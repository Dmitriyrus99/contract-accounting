"""Transactional, create-or-validate installer for demo/UAT manifest v1."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from contract_accounting.demo_uat.bootstrap import (
    BOOTSTRAP_CONFIRMATION_TOKEN,
    binary_fixture_descriptors,
    bootstrap,
    installer_bootstrap_context,
    owned_record_rows,
    validate_bootstrap,
)
from contract_accounting.demo_uat.file_safety import FileRecoverySet, exact_private_path
from contract_accounting.demo_uat.manifest import (
    INSTALL_CONFIRMATION_TOKEN,
    load_manifest,
)
from contract_accounting.demo_uat.ownership import (
    REGISTRY_FILE_NAME,
    build_registry,
    create_registry_file,
    find_registry_file_names,
    load_registry,
    manifest_record_presence,
)
from contract_accounting.demo_uat.runtime import (
    DemoUATRuntimeError,
    create_entity,
    fresh_database_connection,
    get_frappe,
    require_administrator,
    require_exact_token,
    require_local_site,
    validate_runtime_preflight,
)
from contract_accounting.demo_uat.verifier import verify_registered_dataset


class CommitState(Enum):
    """Durable outcome of a commit whose caller observed an exception."""

    COMMITTED = "committed"
    NOT_COMMITTED = "not-committed"
    UNKNOWN = "unknown"


def install(
    confirmation_token: str | None = None,
) -> dict[str, Any]:
    """Bench entrypoint for a local-only all-or-nothing installation."""

    require_exact_token(confirmation_token, INSTALL_CONFIRMATION_TOKEN, "install")
    frappe = get_frappe()
    site = require_local_site(frappe)
    require_administrator(frappe)
    manifest = load_manifest()

    registry, registry_file_name = load_registry(manifest, site=site, required=False)
    if registry is not None:
        validate_bootstrap(manifest=manifest, bindings=registry["bindings"])
        preflight = validate_runtime_preflight(manifest, registry["bindings"])
        assert registry_file_name is not None
        result = verify_registered_dataset(
            manifest,
            registry=registry,
            registry_file_name=registry_file_name,
            site=site,
        )
        return {
            **result,
            "status": "ALREADY_INSTALLED_STRUCTURAL_OK_MANUAL_UAT_REQUIRED",
            "created_count": 0,
            "preflight": preflight,
        }

    unowned = manifest_record_presence(manifest)
    bootstrap_residue = [
        row
        for row in owned_record_rows()
        if frappe.db.exists(str(row["doctype"]), str(row["name"]))
    ]
    # A lost registry must not allow a new install to adopt historical rows
    # associated with the deterministic Company/User names.  Reuse reset's
    # conservative, zero-delete residue detector so both entrypoints have the
    # same fail-closed boundary.
    from contract_accounting.demo_uat.reset import find_derived_residue

    company = next(
        str(row["name"]) for row in owned_record_rows() if str(row["doctype"]) == "Company"
    )
    derived_residue = find_derived_residue(
        registry_records=[
            {"doctype": entity["doctype"], "name": entity["record_name"]}
            for entity in manifest["entities"]
        ],
        bootstrap_records=owned_record_rows(),
        bindings={"company": company},
    )
    if unowned or bootstrap_residue or derived_residue:
        raise DemoUATRuntimeError(
            "deterministic demo names exist without an ownership registry: "
            + repr([*unowned, *bootstrap_residue, *derived_residue])
        )

    entities = {str(row["external_id"]): row for row in manifest["entities"]}
    created: list[str] = []
    file_names = [str(row["record_name"]) for row in binary_fixture_descriptors()]
    candidate_paths = [
        exact_private_path(frappe, str(row["file_name"])) for row in binary_fixture_descriptors()
    ]
    candidate_paths.append(exact_private_path(frappe, REGISTRY_FILE_NAME))
    _remove_recoverable_install_file_orphans(frappe, manifest=manifest)
    file_recovery = FileRecoverySet(frappe, candidate_paths, operation="install")
    try:
        with installer_bootstrap_context():
            bootstrap_result = bootstrap(BOOTSTRAP_CONFIRMATION_TOKEN)
        normalized_bindings = bootstrap_result["bindings"]
        preflight = validate_runtime_preflight(manifest, normalized_bindings)
        for entity in manifest["entities"]:
            created.append(
                create_entity(
                    entity,
                    entities=entities,
                    bindings=normalized_bindings,
                )
            )
        registry = build_registry(
            manifest,
            bindings=normalized_bindings,
            bootstrap_records=bootstrap_result["owned_records"],
            privacy_policy=bootstrap_result["privacy_policy"],
            site=site,
        )
        registry_file_name = create_registry_file(registry)
        file_names.append(registry_file_name)
        result = verify_registered_dataset(
            manifest,
            registry=registry,
            registry_file_name=registry_file_name,
            site=site,
        )
        file_recovery.track_file_documents(file_names)
    except Exception as operation_error:
        # A full transaction rollback is intentional: Frappe's File rollback
        # watchers are not invoked for savepoint-only rollback.
        _recover_install_files(
            frappe,
            file_recovery,
            file_names=file_names,
            manifest=manifest,
            operation_error=operation_error,
        )
        raise
    try:
        frappe.db.commit()
    except Exception as commit_error:
        commit_state = _install_commit_state(frappe, manifest, site=site)
        if commit_state is CommitState.NOT_COMMITTED:
            _recover_install_files(
                frappe,
                file_recovery,
                file_names=file_names,
                manifest=manifest,
                operation_error=commit_error,
            )
            raise
        if commit_state is CommitState.UNKNOWN:
            raise DemoUATRuntimeError(
                "installer commit outcome is UNKNOWN; destructive File recovery refused; "
                f"quarantine retained at {file_recovery.directory}"
            ) from commit_error
    file_recovery.discard()
    return {
        **result,
        "status": "INSTALLED_STRUCTURAL_OK_MANUAL_UAT_REQUIRED",
        "created_count": len(created),
        "created_names": created,
        "preflight": preflight,
    }


def _install_commit_state(frappe: Any, manifest: dict[str, Any], *, site: str) -> CommitState:
    """Resolve an ambiguous commit without treating an unavailable probe as rollback proof."""

    try:
        with fresh_database_connection(frappe):
            registry, registry_file_name = load_registry(manifest, site=site, required=False)
            if registry is None or registry_file_name is None:
                any_domain = bool(manifest_record_presence(manifest))
                any_bootstrap = any(
                    frappe.db.exists(str(row["doctype"]), str(row["name"]))
                    for row in owned_record_rows()
                )
                return (
                    CommitState.UNKNOWN
                    if any_domain or any_bootstrap
                    else CommitState.NOT_COMMITTED
                )
            validate_bootstrap(manifest=manifest, bindings=registry["bindings"])
            verify_registered_dataset(
                manifest,
                registry=registry,
                registry_file_name=registry_file_name,
                site=site,
            )
            return CommitState.COMMITTED
    except Exception:
        return CommitState.UNKNOWN


def _remove_recoverable_install_file_orphans(frappe: Any, *, manifest: dict[str, Any]) -> None:
    """Remove exact disk-only demo leftovers before deterministic File insert."""

    for fixture in binary_fixture_descriptors():
        if frappe.db.exists("File", str(fixture["record_name"])):
            continue
        path = exact_private_path(frappe, str(fixture["file_name"]))
        if not path.exists():
            continue
        actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_sha256 != fixture["content_sha256"]:
            raise DemoUATRuntimeError(
                "recoverable demo fixture orphan has unexpected bytes: "
                f"{fixture['file_name']} {actual_sha256}"
            )
        path.unlink()

    if find_registry_file_names():
        return
    registry_path = exact_private_path(frappe, REGISTRY_FILE_NAME)
    if not registry_path.exists():
        return
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DemoUATRuntimeError("recoverable demo registry orphan is not valid JSON") from exc
    if (
        registry.get("schema") != "contract-accounting/demo-uat-ownership/v1"
        or registry.get("dataset_id") != manifest["dataset_id"]
        or registry.get("manifest_sha256") != manifest["integrity"]["canonical_sha256"]
    ):
        raise DemoUATRuntimeError("recoverable demo registry orphan does not match manifest")
    registry_path.unlink()


def _recover_install_files(
    frappe: Any,
    recovery: FileRecoverySet,
    *,
    file_names: list[str],
    manifest: dict[str, Any],
    operation_error: Exception,
) -> None:
    try:
        recovery.track_file_documents(file_names)
        frappe.db.rollback()
        recovery.restore()
        residue = manifest_record_presence(manifest)
        residue.extend(
            {
                "doctype": str(row["doctype"]),
                "name": str(row["name"]),
            }
            for row in owned_record_rows()
            if frappe.db.exists(str(row["doctype"]), str(row["name"]))
        )
        residue.extend({"doctype": "File", "name": name} for name in find_registry_file_names())
        if residue:
            raise DemoUATRuntimeError(
                "installer rollback left database residue: " + repr(residue[:10])
            )
        recovery.discard()
    except Exception as recovery_error:
        raise DemoUATRuntimeError(
            "installer failed and exact database/File recovery is incomplete; "
            f"quarantine retained at {recovery.directory}; original error: "
            f"{type(operation_error).__name__}"
        ) from recovery_error
