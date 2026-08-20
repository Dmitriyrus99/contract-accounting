"""Frappe runtime helpers shared by the demo/UAT entrypoints.

This module intentionally imports Frappe only inside functions.  Standalone
manifest tests therefore do not need a Bench environment.
"""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Mapping

from contract_accounting.demo_uat.manifest import entity_expected_values

_LOCAL_SITE_RE = re.compile(r"^[a-z0-9][a-z0-9.-]*\.localhost$")


class DemoUATRuntimeError(RuntimeError):
    """A fail-closed runtime precondition or drift failure."""


@contextmanager
def fresh_database_connection(frappe: Any):
    """Temporarily expose a separately connected database handle.

    Commit acknowledgement failures must not be reconciled through the
    connection that raised: its transaction and transport state are unknown.
    Request-local document caches are cleared at both swap boundaries so the
    durable-state probe cannot consume a cached pre- or post-commit document.
    """

    from frappe.database import get_db

    current_proxy = frappe.db
    current = (
        current_proxy._get_current_object()
        if hasattr(current_proxy, "_get_current_object")
        else current_proxy
    )
    fresh = get_db(
        host=current.host,
        user=current.user,
        password=current.password,
        port=current.port,
        cur_db_name=current.cur_db_name,
        socket=current.socket,
    )
    cache = getattr(frappe.local, "document_cache", None)
    if cache is not None:
        cache.clear()
    frappe.local.db = fresh
    try:
        fresh.sql("select 1")
        yield fresh
    finally:
        try:
            fresh.close()
        finally:
            frappe.local.db = current
            cache = getattr(frappe.local, "document_cache", None)
            if cache is not None:
                cache.clear()


_CREATE_WRITER_FLAGS: dict[str, tuple[str, ...]] = {
    "Ferum Project Process": ("ca11_process_writer",),
    "Ferum Project Stage": ("ca11_process_writer",),
    "Ferum Project Process Step": ("ca11_process_writer",),
    "Ferum Process Evidence": ("ca11_evidence_writer",),
    "Ferum Stage Gate": ("ca11_gate_writer",),
    "Ferum Billing Cycle": ("contract_accounting_billing_cycle_writer",),
    "Ferum Contractor Worker": ("contract_accounting_privacy_writer",),
    "Ferum Personnel Credential": ("contract_accounting_privacy_writer",),
    "Ferum Contractor Assignment": ("contract_accounting_assignment_writer",),
    "Ferum Material Expense": ("contract_accounting_material_expense_writer",),
    "Ferum Project Document Event": ("contract_accounting_project_document_event_writer",),
}

_SERVER_DERIVED_CREATE_FIELDS: dict[str, frozenset[str]] = {
    "Ferum Photo Evidence": frozenset({"content_hash"}),
}


def get_frappe():
    try:
        import frappe
    except ImportError as exc:  # pragma: no cover - exercised only outside Bench
        raise DemoUATRuntimeError("Frappe runtime is required for this entrypoint") from exc
    return frappe


def require_exact_token(provided: str | None, expected: str, operation: str) -> None:
    if provided != expected:
        raise DemoUATRuntimeError(
            f"{operation} refused: exact confirmation token required: {expected}"
        )


def require_local_site(frappe: Any) -> str:
    """Use only the already-active request context; never inspect site_config."""

    local = getattr(frappe, "local", None)
    site = getattr(local, "site", None) if local is not None else None
    if not isinstance(site, str) or not _LOCAL_SITE_RE.fullmatch(site):
        raise DemoUATRuntimeError(
            "operation refused: active frappe.local.site must be a plain *.localhost name"
        )
    return site


def require_administrator(frappe: Any) -> None:
    user = getattr(getattr(frappe, "session", None), "user", None)
    if user != "Administrator":
        raise DemoUATRuntimeError("operation refused: run the entrypoint as Administrator")


def parse_bindings(manifest: Mapping[str, Any], bindings: Any) -> dict[str, str]:
    frappe = get_frappe()
    if isinstance(bindings, str):
        try:
            bindings = frappe.parse_json(bindings)
        except Exception as exc:
            raise DemoUATRuntimeError("bindings must be a JSON object") from exc
    if not isinstance(bindings, dict):
        raise DemoUATRuntimeError("bindings must be an object of manifest key -> record name")
    required = set(manifest["required_bindings"])
    actual = set(bindings)
    if actual != required:
        raise DemoUATRuntimeError(
            f"binding keys mismatch: missing={sorted(required - actual)} extra={sorted(actual - required)}"
        )
    normalized: dict[str, str] = {}
    for key, value in bindings.items():
        if not isinstance(value, str) or not value.strip() or len(value) > 140:
            raise DemoUATRuntimeError(f"binding {key} must be a non-empty record name")
        normalized[str(key)] = value.strip()
    if normalized["own_engineer_user"] == normalized["foreign_engineer_user"]:
        raise DemoUATRuntimeError("own and foreign engineer bindings must be different users")
    return normalized


def validate_runtime_preflight(
    manifest: Mapping[str, Any], bindings: Mapping[str, str]
) -> dict[str, Any]:
    """Validate every runtime prerequisite before the installer makes a write."""

    frappe = get_frappe()
    validate_bindings(manifest, bindings)
    validate_ui_prerequisites(manifest)
    validate_timezone(manifest)

    entities = list(manifest["entities"])
    by_id = {str(entity["external_id"]): entity for entity in entities}
    for entity in entities:
        external_id = str(entity["external_id"])
        if entity["seed_support"] != "supported":
            raise DemoUATRuntimeError(f"unsupported entity blocks installation: {external_id}")
        doctype = str(entity["doctype"])
        if not frappe.db.exists("DocType", doctype):
            raise DemoUATRuntimeError(f"required DocType is not installed: {doctype}")
        meta = frappe.get_meta(doctype)
        for values in [entity["values"], *entity["transitions"]]:
            _validate_value_schema(
                meta,
                values,
                bindings=manifest["required_bindings"],
                entities=by_id,
                context=external_id,
            )
    return {
        "doctype_count": len({str(entity["doctype"]) for entity in entities}),
        "record_count": len(entities),
        "binding_count": len(bindings),
        "timezone": manifest["timezone"],
    }


def validate_bindings(manifest: Mapping[str, Any], bindings: Mapping[str, str]) -> None:
    frappe = get_frappe()
    specifications = manifest["required_bindings"]
    for key, specification in specifications.items():
        doctype = str(specification["doctype"])
        name = bindings[key]
        if not frappe.db.exists(doctype, name):
            raise DemoUATRuntimeError(f"binding does not exist: {key} -> {doctype} {name}")
        required_roles = set(specification.get("required_roles") or [])
        if required_roles:
            actual_roles = set(frappe.get_roles(name))
            missing = sorted(required_roles - actual_roles)
            if missing:
                raise DemoUATRuntimeError(f"binding {key} is missing roles: {missing}")
        customer_binding = specification.get("customer_binding")
        if customer_binding:
            customer = bindings[str(customer_binding)]
            linked = frappe.db.exists(
                "Dynamic Link",
                {
                    "parenttype": doctype,
                    "parent": name,
                    "link_doctype": "Customer",
                    "link_name": customer,
                },
            )
            if not linked:
                raise DemoUATRuntimeError(
                    f"binding {key} must be linked to Customer binding {customer_binding}"
                )


def validate_ui_prerequisites(manifest: Mapping[str, Any]) -> None:
    frappe = get_frappe()
    missing_roles = [
        role for role in manifest["ui_prerequisites"]["roles"] if not frappe.db.exists("Role", role)
    ]
    missing_pages = [
        page for page in manifest["ui_prerequisites"]["pages"] if not frappe.db.exists("Page", page)
    ]
    if missing_roles or missing_pages:
        raise DemoUATRuntimeError(
            f"UI prerequisites missing: roles={missing_roles} pages={missing_pages}"
        )


def validate_timezone(manifest: Mapping[str, Any]) -> None:
    frappe = get_frappe()
    timezone = frappe.db.get_single_value("System Settings", "time_zone")
    if timezone != manifest["timezone"]:
        raise DemoUATRuntimeError(
            f"timezone mismatch: expected={manifest['timezone']} actual={timezone!r}"
        )


def resolve_value(
    value: Any,
    *,
    entities: Mapping[str, Mapping[str, Any]],
    bindings: Mapping[str, str],
) -> Any:
    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            return str(entities[str(value["$ref"])]["record_name"])
        if set(value) == {"$binding"}:
            return bindings[str(value["$binding"])]
        return {
            str(key): resolve_value(child, entities=entities, bindings=bindings)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [resolve_value(child, entities=entities, bindings=bindings) for child in value]
    return value


def resolved_entity_values(
    entity: Mapping[str, Any],
    *,
    entities: Mapping[str, Mapping[str, Any]],
    bindings: Mapping[str, str],
    final: bool,
) -> dict[str, Any]:
    source = entity_expected_values(entity) if final else dict(entity["values"])
    return resolve_value(source, entities=entities, bindings=bindings)


def validate_document_matches(
    entity: Mapping[str, Any],
    *,
    entities: Mapping[str, Mapping[str, Any]],
    bindings: Mapping[str, str],
) -> None:
    frappe = get_frappe()
    doctype = str(entity["doctype"])
    name = str(entity["record_name"])
    if not frappe.db.exists(doctype, name):
        raise DemoUATRuntimeError(f"owned record is missing: {doctype} {name}")
    document = frappe.get_doc(doctype, name)
    meta = frappe.get_meta(doctype)
    expected = resolved_entity_values(entity, entities=entities, bindings=bindings, final=True)
    drift: list[str] = []
    for fieldname, expected_value in expected.items():
        field = meta.get_field(fieldname)
        actual_value = (
            document.get_password(fieldname, raise_exception=False)
            if field and field.fieldtype == "Password"
            else document.get(fieldname)
        )
        _compare_declared(expected_value, actual_value, fieldname, drift)
    if drift:
        raise DemoUATRuntimeError(f"record drift: {doctype} {name}: " + "; ".join(drift[:12]))


def create_entity(
    entity: Mapping[str, Any],
    *,
    entities: Mapping[str, Mapping[str, Any]],
    bindings: Mapping[str, str],
) -> str:
    frappe = get_frappe()
    doctype = str(entity["doctype"])
    name = str(entity["record_name"])
    values = resolved_entity_values(entity, entities=entities, bindings=bindings, final=False)
    values = _coerce_runtime_values(frappe, doctype, values)
    for fieldname in _SERVER_DERIVED_CREATE_FIELDS.get(doctype, frozenset()):
        values.pop(fieldname, None)
    if doctype == "Ferum Contractor Assignment":
        obligation = frappe.db.get_value(
            "Ferum Contract Obligation",
            values.get("contract_obligation"),
            ("project_object", "object_system", "work_type"),
            as_dict=True,
        )
        if not obligation:
            raise DemoUATRuntimeError("demo assignment obligation is missing")
        for fieldname in ("project_object", "object_system", "work_type"):
            if obligation.get(fieldname) and obligation.get(fieldname) != values.get(fieldname):
                raise DemoUATRuntimeError(
                    f"demo assignment scope drift at {fieldname}: "
                    f"obligation={obligation.get(fieldname)!r} assignment={values.get(fieldname)!r}"
                )
    document = frappe.get_doc({"doctype": doctype, **values})
    with _writer_context(frappe, doctype):
        document.insert(ignore_permissions=True, set_name=name)
    if document.name != name:
        raise DemoUATRuntimeError(
            f"deterministic name rejected by {doctype}: expected={name} actual={document.name}"
        )
    for transition in entity["transitions"]:
        patch = resolve_value(transition, entities=entities, bindings=bindings)
        for fieldname, value in patch.items():
            document.set(fieldname, value)
        with _writer_context(frappe, doctype, patch=patch):
            document.save(ignore_permissions=True, ignore_version=True)
    validate_document_matches(entity, entities=entities, bindings=bindings)
    return name


def _coerce_runtime_values(frappe: Any, doctype: str, values: Mapping[str, Any]) -> dict[str, Any]:
    """Match Frappe DB scalar types before controller cross-record comparisons."""

    meta = frappe.get_meta(doctype)
    coerced = dict(values)
    for fieldname, value in values.items():
        if value in (None, ""):
            continue
        field = meta.get_field(fieldname)
        if field is None:
            continue
        if field.fieldtype == "Date":
            coerced[fieldname] = frappe.utils.getdate(value)
        elif field.fieldtype == "Datetime":
            coerced[fieldname] = frappe.utils.get_datetime(value)
    return coerced


@contextmanager
def _writer_context(frappe: Any, doctype: str, *, patch: Mapping[str, Any] | None = None):
    """Set only the typed-writer flags required by deterministic demo creation."""

    values: dict[str, Any] = {flag: True for flag in _CREATE_WRITER_FLAGS.get(doctype, ())}
    if patch:
        if doctype == "Ferum Contractor Assignment" and "status" in patch:
            values["contract_accounting_assignment_transition"] = patch["status"]
        elif doctype == "Ferum Material Expense" and "status" in patch:
            values["contract_accounting_material_expense_transition"] = patch["status"]
        elif doctype == "Ferum Contractor Worker" and "status" in patch:
            values["contract_accounting_privacy_transition"] = patch["status"]
        elif doctype == "Ferum Personnel Credential" and "verification_status" in patch:
            values["contract_accounting_privacy_transition"] = patch["verification_status"]
        elif doctype == "Ferum Billing Cycle":
            values["contract_accounting_billing_cycle_update"] = True
    previous = {key: frappe.flags.get(key) for key in values}
    try:
        for key, value in values.items():
            frappe.flags[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                frappe.flags.pop(key, None)
            else:
                frappe.flags[key] = value


def _validate_value_schema(
    meta: Any,
    values: Mapping[str, Any],
    *,
    bindings: Mapping[str, Any],
    entities: Mapping[str, Mapping[str, Any]],
    context: str,
) -> None:
    frappe = get_frappe()
    for fieldname, value in values.items():
        field = meta.get_field(fieldname)
        if field is None:
            raise DemoUATRuntimeError(f"unknown field: {context}.{fieldname}")
        if field.fieldtype == "Table":
            if not isinstance(value, list):
                raise DemoUATRuntimeError(f"table field must be a list: {context}.{fieldname}")
            child_meta = frappe.get_meta(field.options)
            for index, child in enumerate(value):
                if not isinstance(child, dict):
                    raise DemoUATRuntimeError(
                        f"child row must be an object: {context}.{fieldname}[{index}]"
                    )
                _validate_value_schema(
                    child_meta,
                    child,
                    bindings=bindings,
                    entities=entities,
                    context=f"{context}.{fieldname}[{index}]",
                )
        if isinstance(value, dict) and set(value) == {"$ref"} and field.fieldtype == "Link":
            target = entities[str(value["$ref"])]
            if field.options != target["doctype"]:
                raise DemoUATRuntimeError(
                    f"Link target mismatch: {context}.{fieldname} -> {target['doctype']}"
                )
        if isinstance(value, dict) and set(value) == {"$binding"} and field.fieldtype == "Link":
            target = bindings[str(value["$binding"])]
            if field.options != target["doctype"]:
                raise DemoUATRuntimeError(
                    f"binding Link mismatch: {context}.{fieldname} -> {target['doctype']}"
                )
        if isinstance(value, dict) and set(value) == {"$ref"} and field.fieldtype == "Dynamic Link":
            selector = values.get(str(field.options))
            target = entities[str(value["$ref"])]
            if selector != target["doctype"]:
                raise DemoUATRuntimeError(
                    f"Dynamic Link target mismatch: {context}.{fieldname} -> {target['doctype']}"
                )
        if field.fieldtype == "Select" and isinstance(value, str):
            options = {part for part in str(field.options or "").splitlines() if part}
            if options and value not in options:
                raise DemoUATRuntimeError(
                    f"Select option mismatch: {context}.{fieldname}={value!r}"
                )


def _compare_declared(expected: Any, actual: Any, path: str, drift: list[str]) -> None:
    if isinstance(expected, list):
        actual_rows = list(actual or [])
        if len(actual_rows) != len(expected):
            drift.append(f"{path} count expected={len(expected)} actual={len(actual_rows)}")
            return
        for index, (expected_row, actual_row) in enumerate(zip(expected, actual_rows)):
            _compare_declared(expected_row, actual_row, f"{path}[{index}]", drift)
        return
    if isinstance(expected, dict):
        for key, expected_value in expected.items():
            if hasattr(actual, "get"):
                actual_value = actual.get(key)
            elif isinstance(actual, dict):
                actual_value = actual.get(key)
            else:
                drift.append(f"{path} expected object")
                return
            _compare_declared(expected_value, actual_value, f"{path}.{key}", drift)
        return
    normalized_actual = _normalize_scalar(actual)
    normalized_expected = _normalize_scalar(expected)
    if isinstance(normalized_expected, str) and _looks_like_json(normalized_expected):
        try:
            if json.loads(normalized_actual) == json.loads(normalized_expected):
                return
        except (TypeError, json.JSONDecodeError):
            pass
    if normalized_actual != normalized_expected:
        drift.append(f"{path} expected={normalized_expected!r} actual={normalized_actual!r}")


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return str(value)
    return value


def _looks_like_json(value: str) -> bool:
    stripped = value.strip()
    return (stripped.startswith("{") and stripped.endswith("}")) or (
        stripped.startswith("[") and stripped.endswith("]")
    )
