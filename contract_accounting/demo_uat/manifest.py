"""Strict loader and canonical integrity contract for demo/UAT manifest v1."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Final, Iterable, Mapping

MANIFEST_PATH: Final[Path] = Path(__file__).with_name("manifest_v1.json")
SCHEMA_ID: Final[str] = "contract-accounting/demo-uat-manifest/v1"
DATASET_ID: Final[str] = "contract-accounting-demo-uat-v1"
INSTALL_CONFIRMATION_TOKEN: Final[str] = "INSTALL_CONTRACT_ACCOUNTING_DEMO_UAT_V1"
VERIFY_CONFIRMATION_TOKEN: Final[str] = "VERIFY_CONTRACT_ACCOUNTING_DEMO_UAT_V1"
RESET_CONFIRMATION_TOKEN: Final[str] = "RESET_CONTRACT_ACCOUNTING_DEMO_UAT_V1"

_TOP_LEVEL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema",
        "manifest_version",
        "dataset_id",
        "released_at",
        "qualification_status",
        "timezone",
        "site_policy",
        "confirmation_tokens",
        "integrity",
        "required_bindings",
        "projects",
        "role_scenarios",
        "ui_prerequisites",
        "business_graph",
        "entities",
        "expected",
        "unsupported",
    }
)
_ENTITY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "external_id",
        "record_name",
        "project_key",
        "doctype",
        "seed_support",
        "values",
        "transitions",
    }
)
_EXTERNAL_ID_RE: Final[re.Pattern[str]] = re.compile(
    r"^ca\.demo\.v1\.(own|foreign)\.[a-z][a-z0-9_]*$"
)
_RECORD_NAME_RE: Final[re.Pattern[str]] = re.compile(
    r"^CA-DEMO-V1-(OWN|FOREIGN)-[A-Z0-9][A-Z0-9-]*$"
)


class ManifestValidationError(ValueError):
    """Raised when a manifest is incomplete, ambiguous, or has drifted."""


def canonical_json(value: Any) -> str:
    """Return the UTF-8 canonical form used by every manifest/registry hash."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def manifest_hash_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return the manifest with the self-referential digest field removed."""

    payload = copy.deepcopy(dict(manifest))
    integrity = payload.get("integrity")
    if isinstance(integrity, dict):
        integrity.pop("canonical_sha256", None)
    return payload


def compute_manifest_sha256(manifest: Mapping[str, Any]) -> str:
    return canonical_sha256(manifest_hash_payload(manifest))


def load_manifest(path: str | Path | None = None) -> dict[str, Any]:
    manifest_path = Path(path) if path is not None else MANIFEST_PATH
    try:
        raw = manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestValidationError(f"manifest cannot be read: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ManifestValidationError("manifest root must be an object")
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    _require_exact_keys(manifest, _TOP_LEVEL_KEYS, "manifest")
    if manifest["schema"] != SCHEMA_ID or manifest["manifest_version"] != 1:
        raise ManifestValidationError("only demo/UAT manifest schema v1 is supported")
    if manifest["dataset_id"] != DATASET_ID:
        raise ManifestValidationError("unexpected dataset_id")
    if manifest["timezone"] != "Europe/Moscow":
        raise ManifestValidationError("v1 timezone must be Europe/Moscow")
    if manifest["qualification_status"] != "FULL_SYNTHETIC_GRAPH_MANUAL_UAT_REQUIRED":
        raise ManifestValidationError("manifest must not claim PASS or release readiness")
    _validate_site_policy(manifest["site_policy"])
    _validate_tokens(manifest["confirmation_tokens"])
    _validate_integrity(manifest)

    bindings = _require_mapping(manifest["required_bindings"], "required_bindings")
    projects = _require_list(manifest["projects"], "projects")
    if {row.get("key") for row in projects if isinstance(row, dict)} != {"own", "foreign"}:
        raise ManifestValidationError("projects must contain exactly own and foreign")

    entities = _require_list(manifest["entities"], "entities")
    if not entities:
        raise ManifestValidationError("entities must not be empty")
    by_id: dict[str, Mapping[str, Any]] = {}
    record_names: set[str] = set()
    for index, raw_entity in enumerate(entities):
        entity = _require_mapping(raw_entity, f"entities[{index}]")
        _require_exact_keys(entity, _ENTITY_KEYS, f"entities[{index}]")
        external_id = _require_string(entity["external_id"], "external_id")
        record_name = _require_string(entity["record_name"], "record_name")
        project_key = entity["project_key"]
        if not _EXTERNAL_ID_RE.fullmatch(external_id):
            raise ManifestValidationError(f"unstable external_id: {external_id}")
        if external_id in by_id:
            raise ManifestValidationError(f"duplicate external_id: {external_id}")
        if not _RECORD_NAME_RE.fullmatch(record_name) or len(record_name) > 140:
            raise ManifestValidationError(f"unsafe deterministic record_name: {record_name}")
        if record_name in record_names:
            raise ManifestValidationError(f"duplicate record_name: {record_name}")
        if project_key not in {"own", "foreign"}:
            raise ManifestValidationError(f"unknown project_key: {project_key}")
        expected_prefix = f"ca.demo.v1.{project_key}."
        if not external_id.startswith(expected_prefix):
            raise ManifestValidationError(f"external_id/project mismatch: {external_id}")
        if entity["seed_support"] not in {"supported", "unsupported"}:
            raise ManifestValidationError(f"invalid seed_support: {external_id}")
        _require_mapping(entity["values"], f"{external_id}.values")
        transitions = _require_list(entity["transitions"], f"{external_id}.transitions")
        for transition in transitions:
            patch = _require_mapping(transition, f"{external_id}.transition")
            if not patch:
                raise ManifestValidationError(f"empty transition: {external_id}")
        by_id[external_id] = entity
        record_names.add(record_name)

    _validate_references(entities, by_id, bindings)
    _validate_project_roots(projects, by_id)
    _validate_role_scenarios(manifest["role_scenarios"], bindings)
    _validate_expected(manifest["expected"], entities)
    unsupported = _require_list(manifest["unsupported"], "unsupported")
    if not unsupported:
        raise ManifestValidationError("unsupported boundaries must be explicit")
    for row in unsupported:
        item = _require_mapping(row, "unsupported item")
        if set(item) != {"area", "reason", "effect"} or not all(
            isinstance(value, str) and value.strip() for value in item.values()
        ):
            raise ManifestValidationError("unsupported entries require area/reason/effect")


def entity_expected_values(entity: Mapping[str, Any]) -> dict[str, Any]:
    values = copy.deepcopy(dict(entity["values"]))
    for transition in entity.get("transitions", []):
        values.update(copy.deepcopy(dict(transition)))
    return values


def iter_references(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    """Yield ``(field_path, external_id)`` pairs from nested manifest values."""

    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            yield path, str(value["$ref"])
            return
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from iter_references(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_references(child, f"{path}[{index}]")


def expected_link_rows(entities: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entity in entities:
        for field, target in iter_references(entity_expected_values(entity)):
            rows.append({"from": str(entity["external_id"]), "field": field, "to": target})
    return sorted(rows, key=lambda row: (row["from"], row["field"], row["to"]))


def expected_count_summary(entities: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(entities)
    by_project = Counter(str(row["project_key"]) for row in rows)
    by_doctype = Counter(str(row["doctype"]) for row in rows)
    return {
        "by_project": dict(sorted(by_project.items())),
        "by_doctype": dict(sorted(by_doctype.items())),
    }


def expected_link_summary(entities: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = expected_link_rows(entities)
    return {
        "count": len(rows),
        "cross_project_count": sum(
            1 for row in rows if row["from"].split(".")[3] != row["to"].split(".")[3]
        ),
        "canonical_sha256": canonical_sha256(rows),
    }


def _validate_site_policy(value: Any) -> None:
    policy = _require_mapping(value, "site_policy")
    if policy != {
        "allowed_suffix": ".localhost",
        "source": "frappe.local.site",
        "read_site_config": False,
    }:
        raise ManifestValidationError("site_policy must be the exact local-only policy")


def _validate_tokens(value: Any) -> None:
    tokens = _require_mapping(value, "confirmation_tokens")
    expected = {
        "install": INSTALL_CONFIRMATION_TOKEN,
        "verify": VERIFY_CONFIRMATION_TOKEN,
        "reset": RESET_CONFIRMATION_TOKEN,
    }
    if tokens != expected or len(set(tokens.values())) != 3:
        raise ManifestValidationError("confirmation tokens do not match v1 contract")


def _validate_integrity(manifest: Mapping[str, Any]) -> None:
    integrity = _require_mapping(manifest["integrity"], "integrity")
    expected_keys = {"algorithm", "canonicalization", "scope", "canonical_sha256"}
    _require_exact_keys(integrity, frozenset(expected_keys), "integrity")
    if integrity["algorithm"] != "SHA-256":
        raise ManifestValidationError("integrity algorithm must be SHA-256")
    if integrity["canonicalization"] != "RFC8785-compatible sorted UTF-8 JSON":
        raise ManifestValidationError("unexpected canonicalization contract")
    if integrity["scope"] != "manifest excluding integrity.canonical_sha256":
        raise ManifestValidationError("unexpected hash scope")
    declared = integrity["canonical_sha256"]
    actual = compute_manifest_sha256(manifest)
    if not isinstance(declared, str) or not re.fullmatch(r"[0-9a-f]{64}", declared):
        raise ManifestValidationError("canonical_sha256 must be 64 lowercase hex characters")
    if declared != actual:
        raise ManifestValidationError(
            f"manifest canonical SHA drift: declared={declared} actual={actual}"
        )


def _validate_references(
    entities: list[Any],
    by_id: Mapping[str, Mapping[str, Any]],
    bindings: Mapping[str, Any],
) -> None:
    seen: set[str] = set()
    for raw_entity in entities:
        entity = _require_mapping(raw_entity, "entity")
        external_id = str(entity["external_id"])
        values = entity_expected_values(entity)
        for field, target in iter_references(values):
            if target not in by_id:
                raise ManifestValidationError(f"unknown $ref {target} at {external_id}.{field}")
            if target not in seen:
                raise ManifestValidationError(
                    f"$ref must point to an earlier entity: {external_id}.{field} -> {target}"
                )
            if by_id[target]["project_key"] != entity["project_key"]:
                raise ManifestValidationError(
                    f"cross-project reference forbidden: {external_id}.{field} -> {target}"
                )
        for field, binding in _iter_bindings(values):
            if binding not in bindings:
                raise ManifestValidationError(
                    f"unknown $binding {binding} at {external_id}.{field}"
                )
        seen.add(external_id)


def _validate_project_roots(projects: list[Any], by_id: Mapping[str, Mapping[str, Any]]) -> None:
    for raw_project in projects:
        project = _require_mapping(raw_project, "project")
        required = {"key", "kind", "root_external_id", "engineer_binding", "description"}
        _require_exact_keys(project, frozenset(required), "project")
        root = project["root_external_id"]
        if root not in by_id or by_id[root]["doctype"] != "Ferum Service Project":
            raise ManifestValidationError(f"invalid project root: {root}")
        if by_id[root]["project_key"] != project["key"]:
            raise ManifestValidationError(f"root scope mismatch: {root}")


def _validate_role_scenarios(value: Any, bindings: Mapping[str, Any]) -> None:
    scenarios = _require_list(value, "role_scenarios")
    ids: set[str] = set()
    for raw in scenarios:
        scenario = _require_mapping(raw, "role scenario")
        required = {"id", "role", "user_binding", "can_see", "must_not_see", "manual_gate"}
        _require_exact_keys(scenario, frozenset(required), "role scenario")
        scenario_id = _require_string(scenario["id"], "role scenario id")
        if scenario_id in ids:
            raise ManifestValidationError(f"duplicate role scenario: {scenario_id}")
        ids.add(scenario_id)
        binding = scenario["user_binding"]
        if binding is not None and binding not in bindings:
            raise ManifestValidationError(f"unknown scenario binding: {binding}")
        visible = set(_require_list(scenario["can_see"], "can_see"))
        hidden = set(_require_list(scenario["must_not_see"], "must_not_see"))
        if visible.intersection(hidden) or not visible.union(hidden).issubset({"own", "foreign"}):
            raise ManifestValidationError(f"invalid visibility scenario: {scenario_id}")
        if scenario["manual_gate"] is not True:
            raise ManifestValidationError("role visibility is always a manual UAT gate")


def _validate_expected(value: Any, entities: list[Any]) -> None:
    expected = _require_mapping(value, "expected")
    _require_exact_keys(expected, frozenset({"total_records", "counts", "links"}), "expected")
    if expected["total_records"] != len(entities):
        raise ManifestValidationError("expected.total_records drift")
    actual_counts = expected_count_summary(entities)
    if expected["counts"] != actual_counts:
        raise ManifestValidationError("expected.counts drift")
    if expected["links"] != expected_link_summary(entities):
        raise ManifestValidationError("expected.links drift")


def _iter_bindings(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        if set(value) == {"$binding"}:
            yield path, str(value["$binding"])
            return
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from _iter_bindings(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_bindings(child, f"{path}[{index}]")


def _require_exact_keys(value: Mapping[str, Any], keys: frozenset[str], label: str) -> None:
    actual = set(value)
    if actual != set(keys):
        missing = sorted(set(keys) - actual)
        extra = sorted(actual - set(keys))
        raise ManifestValidationError(f"{label} keys mismatch: missing={missing} extra={extra}")


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ManifestValidationError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ManifestValidationError(f"{label} must be an array")
    return value


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{label} must be a non-empty string")
    return value
