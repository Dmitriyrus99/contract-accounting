"""Read-only structural verifier for the demo/UAT dataset.

Structural verification deliberately never returns ``PASS``: cross-role UI,
accounting, legal/finance acceptance, and sign-off remain separate gates.
"""

from __future__ import annotations

from typing import Any, Mapping

from contract_accounting.demo_uat.bootstrap import (
    validate_bootstrap,
    validate_privacy_policy_state,
)
from contract_accounting.demo_uat.manifest import (
    VERIFY_CONFIRMATION_TOKEN,
    load_manifest,
)
from contract_accounting.demo_uat.ownership import (
    find_inbound_non_demo_links,
    load_registry,
)
from contract_accounting.demo_uat.runtime import (
    DemoUATRuntimeError,
    get_frappe,
    require_exact_token,
    require_local_site,
    validate_document_matches,
    validate_runtime_preflight,
)


def verify(confirmation_token: str | None = None) -> dict[str, Any]:
    """Bench entrypoint: validate the owned core graph without mutating it."""

    require_exact_token(confirmation_token, VERIFY_CONFIRMATION_TOKEN, "verify")
    frappe = get_frappe()
    site = require_local_site(frappe)
    manifest = load_manifest()
    registry, registry_file_name = load_registry(manifest, site=site, required=True)
    assert registry is not None and registry_file_name is not None
    return verify_registered_dataset(
        manifest,
        registry=registry,
        registry_file_name=registry_file_name,
        site=site,
    )


def verify_registered_dataset(
    manifest: Mapping[str, Any],
    *,
    registry: Mapping[str, Any],
    registry_file_name: str,
    site: str,
) -> dict[str, Any]:
    bindings = registry["bindings"]
    bootstrap = validate_bootstrap(manifest=manifest, bindings=bindings)
    privacy_policy = validate_privacy_policy_state(registry["privacy_policy"])
    preflight = validate_runtime_preflight(manifest, bindings)
    entities = {str(row["external_id"]): row for row in manifest["entities"]}
    for entity in manifest["entities"]:
        validate_document_matches(entity, entities=entities, bindings=bindings)
    inbound = find_inbound_non_demo_links(
        registry_records=registry["records"],
        registry_file_name=registry_file_name,
        bootstrap_records=registry["bootstrap_records"],
        bindings=bindings,
        registry_created_at=registry["created_at"],
        registry_created_by=registry["created_by"],
    )
    if inbound:
        raise DemoUATRuntimeError(
            "non-demo inbound links contaminate the dataset: " + repr(inbound[:10])
        )
    return {
        "status": "STRUCTURAL_OK_MANUAL_UAT_REQUIRED",
        "site": site,
        "dataset_id": manifest["dataset_id"],
        "manifest_sha256": manifest["integrity"]["canonical_sha256"],
        "registry_sha256": registry["registry_sha256"],
        "record_count": len(manifest["entities"]),
        "project_counts": manifest["expected"]["counts"]["by_project"],
        "expected_link_count": manifest["expected"]["links"]["count"],
        "preflight": preflight,
        "bootstrap": bootstrap,
        "privacy_policy": privacy_policy,
        "unsupported": manifest["unsupported"],
        "manual_uat": manifest["ui_prerequisites"]["manual_checks"],
    }
