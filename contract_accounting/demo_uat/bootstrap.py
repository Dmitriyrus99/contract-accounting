"""Owned, synthetic-only ERPNext masters and actors for demo/UAT v1.

This module deliberately has no API for caller-supplied bindings.  It creates
or validates one fixed namespace and returns both the manifest bindings and a
deletion-safe ownership description.  The caller owns the outer transaction;
``bootstrap`` uses a savepoint but never commits.
"""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Final, Iterator, Mapping, Sequence

from contract_accounting.demo_uat.manifest import load_manifest
from contract_accounting.demo_uat.runtime import (
    DemoUATRuntimeError,
    get_frappe,
    require_administrator,
    require_exact_token,
    require_local_site,
)
from contract_accounting.domain.privacy import SYNTHETIC_ACTIVATION_CONFIRMATION

BOOTSTRAP_CONFIRMATION_TOKEN: Final[str] = "BOOTSTRAP_CONTRACT_ACCOUNTING_DEMO_UAT_V1"
NAMESPACE: Final[str] = "CA-DEMO-V1"

_BASE_BINDING_DOCTYPES: Final[dict[str, str]] = {
    "company": "Company",
    "customer": "Customer",
    "currency": "Currency",
    "own_address": "Address",
    "foreign_address": "Address",
    "own_engineer_user": "User",
    "foreign_engineer_user": "User",
}
_EXPANDED_BINDING_DOCTYPES: Final[dict[str, str]] = {
    **_BASE_BINDING_DOCTYPES,
    "own_supplier": "Supplier",
    "foreign_supplier": "Supplier",
    "process_template": "Ferum Process Template",
    "stage_template": "Ferum Stage Template",
    "step_template": "Ferum Step Template",
}

_SYNTHETIC_DOMAIN: Final[str] = "example.invalid"
_INSTALLER_CONTEXT_FLAG: Final[str] = "contract_accounting_demo_uat_installer"
_PRIVACY_STATE_FIELDS: Final[tuple[str, ...]] = (
    "enabled",
    "activation_mode",
    "activated_at",
    "activated_by",
    "approval_reference",
    "last_reason",
    "configuration_revision",
    "policy_reference",
    "policy_hash",
)


@dataclass(frozen=True)
class OwnedRecordSpec:
    external_id: str
    doctype: str
    name: str
    values: Mapping[str, Any]
    kind: str = "master"


@dataclass(frozen=True)
class BinaryFixtureSpec:
    fixture_id: str
    project_key: str
    record_name: str
    file_name: str
    attached_to_name: str
    content: bytes
    content_sha256: str
    frappe_content_hash_md5: str


_BINARY_FIXTURES: Final[tuple[BinaryFixtureSpec, ...]] = (
    BinaryFixtureSpec(
        fixture_id="ca.demo.v1.own.evidence_file",
        project_key="own",
        record_name=f"{NAMESPACE}-OWN-EVIDENCE-FILE",
        file_name="ca-demo-v1-own-evidence.txt",
        attached_to_name=f"{NAMESPACE}-OWN-INSPECTION",
        content=b"contract-accounting-demo-uat-v1 own synthetic evidence\n",
        content_sha256="3782a8e7eebf3dde0cb6c590e10abf472115b49871c94b48bcfaa22f63b03347",
        frappe_content_hash_md5="484b096263e621d81900f4388f286999",
    ),
    BinaryFixtureSpec(
        fixture_id="ca.demo.v1.foreign.evidence_file",
        project_key="foreign",
        record_name=f"{NAMESPACE}-FOREIGN-EVIDENCE-FILE",
        file_name="ca-demo-v1-foreign-evidence.txt",
        attached_to_name=f"{NAMESPACE}-FOREIGN-INSPECTION",
        content=b"contract-accounting-demo-uat-v1 foreign synthetic evidence\n",
        content_sha256="da08a901738bb98353a0ee622261d98639017003c8d200ca7e91df32939fdff0",
        frappe_content_hash_md5="c381bc7d36fcdb25fbc25a9baaa69a96",
    ),
)


def bootstrap(confirmation_token: str | None = None) -> dict[str, Any]:
    """Create prerequisites only inside the atomic installer transaction."""

    require_exact_token(confirmation_token, BOOTSTRAP_CONFIRMATION_TOKEN, "bootstrap")
    frappe = get_frappe()
    site = require_local_site(frappe)
    require_administrator(frappe)
    if not frappe.flags.get(_INSTALLER_CONTEXT_FLAG):
        raise DemoUATRuntimeError(
            "standalone bootstrap is prohibited; use demo_uat.installer.install"
        )
    manifest = load_manifest()
    _validate_manifest_binding_contract(manifest)
    specs = _owned_record_specs()
    _validate_preflight(frappe, specs)

    savepoint = "ca_demo_uat_v1_bootstrap"
    frappe.db.savepoint(savepoint)
    created: list[dict[str, str]] = []
    try:
        privacy_policy = _ensure_synthetic_privacy_policy(frappe)
        for spec in specs:
            if _create_or_validate(frappe, spec):
                created.append({"doctype": spec.doctype, "name": spec.name})
        for fixture in _BINARY_FIXTURES:
            if _create_or_validate_binary_fixture(frappe, fixture):
                created.append({"doctype": "File", "name": fixture.record_name})
        bindings, references = _resolve_bindings(frappe, manifest, specs, ensure_references=True)
        validate_bootstrap(manifest=manifest, bindings=bindings)
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise

    return {
        "status": "BOOTSTRAPPED_SYNTHETIC_DISABLED_MANUAL_UAT_REQUIRED",
        "site": site,
        "bindings": bindings,
        "owned_records": owned_record_rows(),
        "reference_records": references,
        "binary_fixtures": binary_fixture_descriptors(),
        "privacy_policy": privacy_policy,
        "created_count": len(created),
        "created_records": created,
    }


@contextmanager
def installer_bootstrap_context() -> Iterator[None]:
    """Authorize bootstrap only while the outer installer owns full rollback."""

    frappe = get_frappe()
    previous = frappe.flags.get(_INSTALLER_CONTEXT_FLAG)
    frappe.flags[_INSTALLER_CONTEXT_FLAG] = True
    try:
        yield
    finally:
        frappe.flags[_INSTALLER_CONTEXT_FLAG] = previous


def _privacy_state(settings: Any) -> dict[str, Any]:
    state: dict[str, Any] = {}
    for fieldname in _PRIVACY_STATE_FIELDS:
        value = settings.get(fieldname)
        if fieldname in {"enabled", "configuration_revision"}:
            value = int(value or 0)
        elif fieldname == "activated_at" and value:
            value = str(value)
        elif value == "":
            value = None
        state[fieldname] = value
    return state


def _privacy_state_fingerprint(state: Mapping[str, Any]) -> str:
    from contract_accounting.demo_uat.manifest import canonical_sha256

    return canonical_sha256(dict(state))


def _ensure_synthetic_privacy_policy(frappe: Any) -> dict[str, Any]:
    settings = frappe.get_single("Ferum Privacy Settings")
    prior_state = _privacy_state(settings)
    if settings.enabled:
        if settings.activation_mode != "Synthetic Test":
            raise DemoUATRuntimeError(
                "demo bootstrap requires Synthetic Test privacy mode; another mode is active"
            )
        changed_by_demo = False
    else:
        from contract_accounting.api.privacy import activate_privacy_policy

        activate_privacy_policy(
            activation_mode="Synthetic Test",
            confirmation=SYNTHETIC_ACTIVATION_CONFIRMATION,
            approval_reference="TEST-DEMO-UAT-V1-APPROVAL",
            reason="Synthetic-only local demo/UAT lifecycle activation",
        )
        settings = frappe.get_single("Ferum Privacy Settings")
        changed_by_demo = True
    demo_state = _privacy_state(settings)
    return {
        "changed_by_demo": changed_by_demo,
        "prior_state": prior_state,
        "prior_fingerprint": _privacy_state_fingerprint(prior_state),
        "demo_state": demo_state,
        "demo_fingerprint": _privacy_state_fingerprint(demo_state),
    }


def validate_bootstrap(
    *,
    manifest: Mapping[str, Any] | None = None,
    bindings: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Fail on any field, role, link, content, or binding drift; never write."""

    frappe = get_frappe()
    active_manifest = manifest or load_manifest()
    _validate_manifest_binding_contract(active_manifest)
    specs = _owned_record_specs()
    for spec in specs:
        if not frappe.db.exists(spec.doctype, spec.name):
            raise DemoUATRuntimeError(f"bootstrap record is missing: {spec.doctype} {spec.name}")
        _validate_record(frappe, spec)
    for fixture in _BINARY_FIXTURES:
        if not frappe.db.exists("File", fixture.record_name):
            raise DemoUATRuntimeError(f"bootstrap evidence File is missing: {fixture.record_name}")
        _validate_binary_fixture(frappe, fixture)
    expected_bindings, references = _resolve_bindings(
        frappe, active_manifest, specs, ensure_references=False
    )
    if bindings is not None and dict(bindings) != expected_bindings:
        raise DemoUATRuntimeError("bootstrap binding drift")
    return {
        "status": "BOOTSTRAP_STRUCTURAL_OK_MANUAL_UAT_REQUIRED",
        "bindings": expected_bindings,
        "owned_record_count": len(owned_record_rows()),
        "reference_records": references,
    }


def validate_privacy_policy_state(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the registered active policy fingerprint without mutating it."""

    frappe = get_frappe()
    current = _privacy_state(frappe.get_single("Ferum Privacy Settings"))
    if _privacy_state_fingerprint(current) != policy["demo_fingerprint"]:
        raise DemoUATRuntimeError("registered demo privacy policy state has external drift")
    return {
        "status": "PRIVACY_POLICY_STRUCTURAL_OK",
        "changed_by_demo": bool(policy["changed_by_demo"]),
        "activation_mode": current["activation_mode"],
    }


def owned_record_rows() -> list[dict[str, Any]]:
    """Return creation order plus explicit reverse deletion order for reset."""

    rows = [
        {
            "external_id": spec.external_id,
            "doctype": spec.doctype,
            "name": spec.name,
            "kind": spec.kind,
        }
        for spec in _owned_record_specs()
    ]
    rows.extend(
        {
            "external_id": fixture.fixture_id,
            "doctype": "File",
            "name": fixture.record_name,
            "kind": "private_fixture",
        }
        for fixture in _BINARY_FIXTURES
    )
    total = len(rows)
    return [
        {**row, "creation_order": index, "deletion_order": total - index + 1}
        for index, row in enumerate(rows, start=1)
    ]


def binary_fixture_descriptors() -> list[dict[str, Any]]:
    return [
        {
            "fixture_id": fixture.fixture_id,
            "project_key": fixture.project_key,
            "record_name": fixture.record_name,
            "file_name": fixture.file_name,
            "attached_to_external_id": f"ca.demo.v1.{fixture.project_key}.inspection",
            "is_private": 1,
            "content_encoding": "UTF-8 without BOM",
            "content_literal": fixture.content.decode("utf-8"),
            "content_sha256": fixture.content_sha256,
            "frappe_content_hash_md5": fixture.frappe_content_hash_md5,
            "materialization": "bootstrap-owned prerequisite",
        }
        for fixture in _BINARY_FIXTURES
    ]


def _owned_record_specs() -> tuple[OwnedRecordSpec, ...]:
    customer = f"{NAMESPACE}-CUSTOMER"
    currency = f"{NAMESPACE}-XTS"
    return (
        OwnedRecordSpec(
            "ca.demo.v1.bootstrap.currency",
            "Currency",
            currency,
            {"currency_name": currency, "enabled": 1, "symbol": "XTS"},
        ),
        OwnedRecordSpec(
            "ca.demo.v1.bootstrap.company",
            "Company",
            f"{NAMESPACE}-COMPANY",
            {
                "company_name": f"{NAMESPACE}-COMPANY",
                "abbr": "CADV1",
                "default_currency": currency,
                "country": "Russia",
            },
        ),
        OwnedRecordSpec(
            "ca.demo.v1.bootstrap.customer",
            "Customer",
            customer,
            {
                "customer_name": customer,
                "customer_type": "Company",
                "customer_group": "Commercial",
                "territory": "All Territories",
            },
        ),
        OwnedRecordSpec(
            "ca.demo.v1.bootstrap.own_supplier",
            "Supplier",
            f"{NAMESPACE}-OWN-SUPPLIER",
            {
                "supplier_name": f"{NAMESPACE}-OWN-SUPPLIER",
                "supplier_group": "Services",
                "supplier_type": "Company",
            },
        ),
        OwnedRecordSpec(
            "ca.demo.v1.bootstrap.foreign_supplier",
            "Supplier",
            f"{NAMESPACE}-FOREIGN-SUPPLIER",
            {
                "supplier_name": f"{NAMESPACE}-FOREIGN-SUPPLIER",
                "supplier_group": "Services",
                "supplier_type": "Company",
            },
        ),
        _address_spec("own", customer),
        _address_spec("foreign", customer),
        _user_spec("own-engineer", "Инженер"),
        _user_spec("foreign-engineer", "Инженер"),
        _user_spec("project-manager", "Руководитель проектов"),
        _user_spec("office-manager", "Офис-менеджер"),
    )


def _address_spec(project_key: str, customer: str) -> OwnedRecordSpec:
    upper = project_key.upper()
    return OwnedRecordSpec(
        f"ca.demo.v1.bootstrap.{project_key}_address",
        "Address",
        f"{NAMESPACE}-{upper}-ADDRESS",
        {
            "address_title": f"{NAMESPACE}-{upper}-SYNTHETIC-LOCATION",
            "address_type": "Other",
            "address_line1": f"{NAMESPACE} {upper} synthetic location; not a real address",
            "city": "Synthetic City",
            "country": "Russia",
            "links": [{"link_doctype": "Customer", "link_name": customer}],
        },
    )


def _user_spec(label: str, role: str) -> OwnedRecordSpec:
    email = f"ca-demo-v1-{label}@{_SYNTHETIC_DOMAIN}"
    return OwnedRecordSpec(
        f"ca.demo.v1.bootstrap.{label.replace('-', '_')}_user",
        "User",
        email,
        {
            "email": email,
            "first_name": f"CA Demo V1 {label.replace('-', ' ').title()}",
            "enabled": 0,
            "send_welcome_email": 0,
            "user_type": "System User",
            "roles": [{"role": role}],
        },
        kind="disabled_actor",
    )


def _validate_manifest_binding_contract(manifest: Mapping[str, Any]) -> None:
    raw = manifest.get("required_bindings")
    if not isinstance(raw, Mapping):
        raise DemoUATRuntimeError("manifest required_bindings must be an object")
    actual = {
        str(key): value.get("doctype") for key, value in raw.items() if isinstance(value, Mapping)
    }
    if actual not in (_BASE_BINDING_DOCTYPES, _EXPANDED_BINDING_DOCTYPES):
        raise DemoUATRuntimeError(f"unsupported demo/UAT binding contract: {actual}")
    business_graph = manifest.get("business_graph")
    if not isinstance(business_graph, Mapping):
        raise DemoUATRuntimeError("manifest business_graph must be an object")
    declared_fixtures = business_graph.get("binary_fixtures")
    if declared_fixtures is not None and declared_fixtures != binary_fixture_descriptors():
        raise DemoUATRuntimeError("manifest binary fixture contract has drifted")


def _validate_preflight(frappe: Any, specs: Sequence[OwnedRecordSpec]) -> None:
    doctypes = {spec.doctype for spec in specs} | {
        "File",
        "Ferum Process Template",
        "Ferum Stage Template",
        "Ferum Step Template",
    }
    missing_doctypes = sorted(
        doctype for doctype in doctypes if not frappe.db.exists("DocType", doctype)
    )
    roles = {
        str(row["role"]) for spec in specs if spec.doctype == "User" for row in spec.values["roles"]
    }
    missing_roles = sorted(role for role in roles if not frappe.db.exists("Role", role))
    if missing_doctypes or missing_roles:
        raise DemoUATRuntimeError(
            f"bootstrap prerequisites missing: doctypes={missing_doctypes} roles={missing_roles}"
        )


def _create_or_validate(frappe: Any, spec: OwnedRecordSpec) -> bool:
    if frappe.db.exists(spec.doctype, spec.name):
        _validate_record(frappe, spec)
        return False
    document = frappe.get_doc({"doctype": spec.doctype, **dict(spec.values)})
    document.insert(ignore_permissions=True, set_name=spec.name)
    if document.name != spec.name:
        raise DemoUATRuntimeError(
            f"bootstrap deterministic name rejected: {spec.doctype} {document.name!r}"
        )
    _validate_record(frappe, spec)
    return True


def _validate_record(frappe: Any, spec: OwnedRecordSpec) -> None:
    document = frappe.get_doc(spec.doctype, spec.name)
    drift: list[str] = []
    for fieldname, expected in spec.values.items():
        if fieldname == "send_welcome_email":
            # This is an insertion-only control in Frappe; disabled is the
            # durable no-delivery boundary validated below.
            continue
        if fieldname == "roles":
            actual_roles = sorted(str(row.role) for row in (document.get("roles") or []))
            expected_roles = sorted(str(row["role"]) for row in expected)
            if actual_roles != expected_roles:
                drift.append(f"roles expected={expected_roles!r} actual={actual_roles!r}")
            continue
        if fieldname == "links":
            actual_links = sorted(
                (str(row.link_doctype), str(row.link_name)) for row in (document.get("links") or [])
            )
            expected_links = sorted(
                (str(row["link_doctype"]), str(row["link_name"])) for row in expected
            )
            if actual_links != expected_links:
                drift.append(f"links expected={expected_links!r} actual={actual_links!r}")
            continue
        actual = document.get(fieldname)
        if _normalize(actual) != _normalize(expected):
            drift.append(f"{fieldname} expected={expected!r} actual={actual!r}")
    if spec.doctype == "User" and int(document.get("enabled") or 0) != 0:
        drift.append("enabled must remain 0")
    if drift:
        raise DemoUATRuntimeError(
            f"bootstrap record drift: {spec.doctype} {spec.name}: " + "; ".join(drift)
        )


def _create_or_validate_binary_fixture(frappe: Any, fixture: BinaryFixtureSpec) -> bool:
    _assert_fixture_hash(fixture)
    if frappe.db.exists("File", fixture.record_name):
        _validate_binary_fixture(frappe, fixture)
        return False
    document = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": fixture.file_name,
            "is_private": 1,
            "attached_to_doctype": "Ferum Inspection",
            "attached_to_name": fixture.attached_to_name,
            "content": fixture.content,
        }
    ).insert(ignore_permissions=True, set_name=fixture.record_name)
    if document.name != fixture.record_name:
        raise DemoUATRuntimeError(f"bootstrap deterministic File name rejected: {document.name!r}")
    _validate_binary_fixture(frappe, fixture)
    return True


def _validate_binary_fixture(frappe: Any, fixture: BinaryFixtureSpec) -> None:
    document = frappe.get_doc("File", fixture.record_name)
    expected = {
        "file_name": fixture.file_name,
        "is_private": 1,
        "attached_to_doctype": "Ferum Inspection",
        "attached_to_name": fixture.attached_to_name,
    }
    drift = [
        fieldname
        for fieldname, value in expected.items()
        if _normalize(document.get(fieldname)) != _normalize(value)
    ]
    try:
        content = document.get_content()
        if isinstance(content, str):
            content = content.encode("utf-8")
    except Exception as exc:
        raise DemoUATRuntimeError(
            f"bootstrap evidence File cannot be read: {fixture.record_name}"
        ) from exc
    if hashlib.sha256(content).hexdigest() != fixture.content_sha256:
        drift.append("content_sha256")
    if document.content_hash != fixture.frappe_content_hash_md5:
        drift.append("frappe_content_hash_md5")
    if drift:
        raise DemoUATRuntimeError(
            f"bootstrap evidence File drift: {fixture.record_name}: {sorted(drift)}"
        )


def _resolve_bindings(
    frappe: Any,
    manifest: Mapping[str, Any],
    specs: Sequence[OwnedRecordSpec],
    *,
    ensure_references: bool,
) -> tuple[dict[str, str], list[dict[str, str]]]:
    by_external = {spec.external_id: spec.name for spec in specs}
    bindings = {
        "company": by_external["ca.demo.v1.bootstrap.company"],
        "customer": by_external["ca.demo.v1.bootstrap.customer"],
        "currency": by_external["ca.demo.v1.bootstrap.currency"],
        "own_address": by_external["ca.demo.v1.bootstrap.own_address"],
        "foreign_address": by_external["ca.demo.v1.bootstrap.foreign_address"],
        "own_engineer_user": by_external["ca.demo.v1.bootstrap.own_engineer_user"],
        "foreign_engineer_user": by_external["ca.demo.v1.bootstrap.foreign_engineer_user"],
    }
    references: list[dict[str, str]] = []
    if set(manifest["required_bindings"]) == set(_EXPANDED_BINDING_DOCTYPES):
        bindings["own_supplier"] = by_external["ca.demo.v1.bootstrap.own_supplier"]
        bindings["foreign_supplier"] = by_external["ca.demo.v1.bootstrap.foreign_supplier"]
        reference_bindings = (
            _ensure_billing_cycle_reference_bindings(frappe)
            if ensure_references
            else _resolve_billing_cycle_reference_bindings(frappe)
        )
        bindings.update(reference_bindings)
        references = [
            {
                "binding": key,
                "doctype": _EXPANDED_BINDING_DOCTYPES[key],
                "name": value,
                "ownership": "source-controlled-reference-not-reset-owned",
            }
            for key, value in reference_bindings.items()
        ]
    return bindings, references


def _ensure_billing_cycle_reference_bindings(frappe: Any) -> dict[str, str]:
    from contract_accounting.setup.billing_cycle_template import (
        ensure_reference_billing_cycle_template,
    )

    ensure_reference_billing_cycle_template()
    return _resolve_billing_cycle_reference_bindings(frappe)


def _resolve_billing_cycle_reference_bindings(frappe: Any) -> dict[str, str]:
    """Resolve and validate the published reference graph without writing."""

    from contract_accounting.setup.billing_cycle_template import (
        STAGE_CODE,
        TEMPLATE_CODE,
        TEMPLATE_VERSION,
        _validate_existing,
    )

    existing = frappe.db.get_value(
        "Ferum Process Template",
        {"code": TEMPLATE_CODE, "version": TEMPLATE_VERSION},
        ("name", "status"),
        as_dict=True,
    )
    if not existing:
        raise DemoUATRuntimeError("billing-cycle reference template is missing")
    _validate_existing(str(existing.name), str(existing.status))
    template = str(existing.name)
    stage = frappe.db.get_value(
        "Ferum Stage Template",
        {"process_template": template, "stage_code": STAGE_CODE},
        "name",
    )
    step = frappe.db.get_value(
        "Ferum Step Template",
        {"stage_template": stage, "step_code": "WORK_COMPLETED"},
        "name",
    )
    if not stage or not step:
        raise DemoUATRuntimeError("billing-cycle reference binding graph is incomplete")
    return {
        "process_template": template,
        "stage_template": str(stage),
        "step_template": str(step),
    }


def _assert_fixture_hash(fixture: BinaryFixtureSpec) -> None:
    actual = hashlib.sha256(fixture.content).hexdigest()
    if actual != fixture.content_sha256:
        raise DemoUATRuntimeError(f"source fixture hash drift: {fixture.fixture_id}: {actual}")
    if (
        hashlib.md5(fixture.content, usedforsecurity=False).hexdigest()
        != fixture.frappe_content_hash_md5
    ):
        raise DemoUATRuntimeError(f"source fixture Frappe hash drift: {fixture.fixture_id}")


def _normalize(value: Any) -> Any:
    if value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    return value
