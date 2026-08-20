"""Live, fail-closed FR-06 personnel readiness projection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from contract_accounting.domain.privacy import (
    ALLOWED_CREDENTIAL_TYPES,
    POLICY_HASH,
    POLICY_REFERENCE,
    credential_readiness,
)


@dataclass(frozen=True)
class ReadinessResult:
    status: str
    reason: str
    fingerprint: str


def parse_required_credential_types(value: str | list[str] | None) -> tuple[str, ...]:
    if not value:
        return ()
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError as exc:
        frappe.throw(_("required_credential_types должен быть JSON array."))
        raise AssertionError from exc
    if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
        frappe.throw(_("required_credential_types должен быть string array."))
    normalized = tuple(sorted(set(item.strip() for item in parsed if item.strip())))
    if set(normalized) - ALLOWED_CREDENTIAL_TYPES:
        frappe.throw(_("required_credential_types содержит значение вне FR-05 allowlist."))
    return normalized


def canonical_required_credential_types(value: str | list[str] | None) -> str:
    return json.dumps(
        parse_required_credential_types(value), ensure_ascii=False, separators=(",", ":")
    )


def evaluate_assignment(assignment: Any, *, as_of: date | None = None) -> ReadinessResult:
    as_of = as_of or getdate(today())
    enabled = cint(frappe.db.get_single_value("Ferum Privacy Settings", "enabled") or 0)
    policy_reference = frappe.db.get_single_value("Ferum Privacy Settings", "policy_reference")
    policy_hash = frappe.db.get_single_value("Ferum Privacy Settings", "policy_hash")
    if not enabled:
        return _result("Policy Inactive", "FR-05 policy is disabled", ())
    if policy_reference != POLICY_REFERENCE or policy_hash != POLICY_HASH:
        return _result("Policy Inactive", "FR-05 policy stamp mismatch", ())

    required = parse_required_credential_types(assignment.required_credential_types)
    if not required:
        return _result("Not Required", "No credential types configured", required)

    holder_type = "Employee"
    holder = assignment.employee
    if assignment.execution_mode == "Contractor":
        holder_type = "Ferum Contractor Worker"
        holder = assignment.contractor_worker
        if not holder:
            return _result("Missing Worker", "Contractor Worker is not assigned", required)
        worker = frappe.db.get_value(
            "Ferum Contractor Worker",
            holder,
            ("supplier", "status", "privacy_policy_reference", "privacy_policy_hash"),
            as_dict=True,
        )
        if (
            not worker
            or worker.supplier != assignment.supplier
            or worker.status != "Active"
            or worker.privacy_policy_reference != POLICY_REFERENCE
            or worker.privacy_policy_hash != POLICY_HASH
        ):
            return _result(
                "Missing Worker", "Worker is absent, inactive, mismatched, or unstamped", required
            )
    if not holder:
        return _result("Missing Worker", "Assignment holder is missing", required)

    credentials = frappe.get_all(
        "Ferum Personnel Credential",
        filters={
            "holder_type": holder_type,
            "holder": holder,
            "credential_type": ["in", list(required)],
            "retention_status": ["!=", "Metadata Only"],
        },
        fields=[
            "name",
            "credential_type",
            "verification_status",
            "data_owner_verified_by",
            "applicability_verified_by",
            "expires_on",
            "no_expiry",
            "modified",
        ],
        order_by="credential_type asc, modified desc, name asc",
        ignore_permissions=True,
    )
    evidence: list[tuple[str, str, str, str]] = []
    missing: list[str] = []
    pending: list[str] = []
    expired: list[str] = []
    for credential_type in required:
        matching = [row for row in credentials if row.credential_type == credential_type]
        states: list[str] = []
        for row in matching:
            state = credential_readiness(
                status=row.verification_status,
                data_owner_verified=bool(row.data_owner_verified_by),
                applicability_verified=bool(row.applicability_verified_by),
                expires_on=getdate(row.expires_on) if row.expires_on else None,
                no_expiry=bool(row.no_expiry),
                as_of=as_of,
            )
            states.append(state)
            evidence.append((credential_type, row.name, state, str(row.modified)))
        if "Ready" in states:
            continue
        if not states:
            missing.append(credential_type)
        elif "Pending Verification" in states:
            pending.append(credential_type)
        else:
            expired.append(credential_type)

    fingerprint_values: tuple[Any, ...] = (required, tuple(evidence), str(as_of))
    if missing:
        return _result("Missing Credential", ", ".join(missing), fingerprint_values)
    if pending:
        return _result("Pending Verification", ", ".join(pending), fingerprint_values)
    if expired:
        return _result("Expired", ", ".join(expired), fingerprint_values)
    return _result("Ready", "All required credentials are verified and current", fingerprint_values)


def assert_project_personnel_ready(service_project: str) -> None:
    settings_enabled = cint(frappe.db.get_single_value("Ferum Privacy Settings", "enabled") or 0)
    if not settings_enabled:
        frappe.throw(_("PERSONNEL READY заблокирован: FR-05 policy inactive."))
    requires_contractor = cint(
        frappe.db.get_value("Ferum Service Project", service_project, "requires_contractor") or 0
    )
    rows = frappe.get_all(
        "Ferum Contractor Assignment",
        filters={"service_project": service_project, "status": ["in", ["Approved", "Suspended"]]},
        fields=[
            "name",
            "execution_mode",
            "supplier",
            "employee",
            "contractor_worker",
            "required_credential_types",
            "readiness_confirmed_fingerprint",
        ],
        ignore_permissions=True,
    )
    if requires_contractor and not any(row.execution_mode == "Contractor" for row in rows):
        frappe.throw(_("PERSONNEL READY требует Approved Contractor Assignment."))
    relevant = [
        row
        for row in rows
        if row.execution_mode == "Contractor"
        or parse_required_credential_types(row.required_credential_types)
    ]
    for row in relevant:
        result = evaluate_assignment(row)
        if result.status not in {"Ready", "Not Required"}:
            frappe.throw(
                _("Assignment {0} personnel readiness: {1} ({2}).").format(
                    row.name, result.status, result.reason
                )
            )
        if row.readiness_confirmed_fingerprint != result.fingerprint:
            frappe.throw(
                _("Assignment {0} readiness требует актуальное PM confirmation.").format(row.name)
            )


def assert_personnel_not_applicable(service_project: str) -> None:
    requires_contractor = cint(
        frappe.db.get_value("Ferum Service Project", service_project, "requires_contractor") or 0
    )
    contractor_exists = frappe.db.exists(
        "Ferum Contractor Assignment",
        {
            "service_project": service_project,
            "execution_mode": "Contractor",
            "status": ["in", ["Approved", "Suspended"]],
        },
    )
    credential_requirements = frappe.get_all(
        "Ferum Contractor Assignment",
        filters={"service_project": service_project, "status": ["in", ["Approved", "Suspended"]]},
        pluck="required_credential_types",
        ignore_permissions=True,
    )
    if (
        requires_contractor
        or contractor_exists
        or any(parse_required_credential_types(value) for value in credential_requirements)
    ):
        frappe.throw(_("PERSONNEL READY нельзя обойти через Not Applicable."))


def _result(status: str, reason: str, values: tuple[Any, ...]) -> ReadinessResult:
    payload = json.dumps(
        values, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")
    )
    return ReadinessResult(
        status=status,
        reason=reason,
        fingerprint=hashlib.sha256(f"{status}|{reason}|{payload}".encode()).hexdigest(),
    )
