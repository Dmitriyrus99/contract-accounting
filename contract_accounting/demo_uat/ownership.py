"""Private ownership registry and inbound-link safety checks for demo/UAT v1."""

from __future__ import annotations

import copy
import json
from datetime import timedelta
from typing import Any, Final, Mapping, Sequence
from urllib.parse import quote

from contract_accounting.demo_uat.manifest import canonical_sha256
from contract_accounting.demo_uat.runtime import DemoUATRuntimeError, get_frappe

REGISTRY_SCHEMA = "contract-accounting/demo-uat-ownership/v1"
REGISTRY_FILE_NAME = "contract-accounting-demo-uat-v1.ownership.json"
PINNED_USER_DELETE_DATA_EFFECTS: Final[tuple[str, ...]] = (
    "ToDo.allocated_to/delete",
    "ToDo.assigned_by/null",
    "Event.private-owner/delete",
    "DocShare.user/delete",
    "Communication.chat-notification/delete",
    "Contact.user/null",
    "Notification Settings/delete",
    "User Permission.user/delete",
    "OAuth Authorization Code.user/delete",
    "Token Cache.user/delete",
    "Energy Point Log.user/delete",
    "Workflow Action.user/null",
    "List Filter.for_user/delete",
    "Note Seen By.user/remove-and-save-parent",
    "User Invitation.email/unlink-and-save",
    "File.attached_to_User/delete-doc-attachment",
)


def registry_hash_payload(registry: Mapping[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(dict(registry))
    payload.pop("registry_sha256", None)
    return payload


def build_registry(
    manifest: Mapping[str, Any],
    *,
    bindings: Mapping[str, str],
    bootstrap_records: list[Mapping[str, Any]],
    privacy_policy: Mapping[str, Any],
    site: str,
) -> dict[str, Any]:
    frappe = get_frappe()
    registry: dict[str, Any] = {
        "schema": REGISTRY_SCHEMA,
        "dataset_id": manifest["dataset_id"],
        "manifest_sha256": manifest["integrity"]["canonical_sha256"],
        "site": site,
        "created_at": str(frappe.utils.now_datetime()),
        "created_by": str(frappe.session.user),
        "bindings": dict(sorted(bindings.items())),
        "bootstrap_records": [dict(row) for row in bootstrap_records],
        "privacy_policy": copy.deepcopy(dict(privacy_policy)),
        "records": [
            {
                "external_id": entity["external_id"],
                "project_key": entity["project_key"],
                "doctype": entity["doctype"],
                "name": entity["record_name"],
            }
            for entity in manifest["entities"]
        ],
    }
    registry["registry_sha256"] = canonical_sha256(registry_hash_payload(registry))
    return registry


def create_registry_file(registry: Mapping[str, Any]) -> str:
    frappe = get_frappe()
    if find_registry_file_names():
        raise DemoUATRuntimeError("ownership registry already exists")
    content = json.dumps(registry, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    document = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": REGISTRY_FILE_NAME,
            "is_private": 1,
            "content": content.encode("utf-8"),
        }
    ).insert(ignore_permissions=True)
    if not document.name:
        raise DemoUATRuntimeError("ownership registry File was not created")
    return str(document.name)


def find_registry_file_names() -> list[str]:
    frappe = get_frappe()
    return [
        str(name)
        for name in frappe.get_all(
            "File",
            filters={"file_name": REGISTRY_FILE_NAME, "is_private": 1},
            pluck="name",
            order_by="creation asc",
        )
    ]


def load_registry(
    manifest: Mapping[str, Any],
    *,
    site: str,
    required: bool = True,
) -> tuple[dict[str, Any] | None, str | None]:
    frappe = get_frappe()
    file_names = find_registry_file_names()
    if not file_names:
        if required:
            raise DemoUATRuntimeError("ownership registry is missing")
        return None, None
    if len(file_names) != 1:
        raise DemoUATRuntimeError(f"multiple ownership registries found: {file_names}")
    file_name = file_names[0]
    file_document = frappe.get_doc("File", file_name)
    try:
        raw = file_document.get_content()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        registry = json.loads(raw)
    except Exception as exc:
        raise DemoUATRuntimeError("ownership registry cannot be decoded") from exc
    validate_registry(registry, manifest=manifest, site=site)
    return registry, file_name


def validate_registry(
    registry: Any,
    *,
    manifest: Mapping[str, Any],
    site: str,
) -> None:
    if not isinstance(registry, dict):
        raise DemoUATRuntimeError("ownership registry root must be an object")
    required_keys = {
        "schema",
        "dataset_id",
        "manifest_sha256",
        "site",
        "created_at",
        "created_by",
        "bindings",
        "bootstrap_records",
        "privacy_policy",
        "records",
        "registry_sha256",
    }
    if set(registry) != required_keys:
        raise DemoUATRuntimeError("ownership registry keys have drifted")
    if registry["schema"] != REGISTRY_SCHEMA:
        raise DemoUATRuntimeError("ownership registry schema mismatch")
    if registry["dataset_id"] != manifest["dataset_id"]:
        raise DemoUATRuntimeError("ownership registry dataset mismatch")
    if registry["manifest_sha256"] != manifest["integrity"]["canonical_sha256"]:
        raise DemoUATRuntimeError("ownership registry manifest SHA mismatch")
    if registry["site"] != site:
        raise DemoUATRuntimeError("ownership registry belongs to another site")
    actual_sha = canonical_sha256(registry_hash_payload(registry))
    if registry["registry_sha256"] != actual_sha:
        raise DemoUATRuntimeError("ownership registry canonical SHA mismatch")
    expected_records = [
        {
            "external_id": entity["external_id"],
            "project_key": entity["project_key"],
            "doctype": entity["doctype"],
            "name": entity["record_name"],
        }
        for entity in manifest["entities"]
    ]
    if registry["records"] != expected_records:
        raise DemoUATRuntimeError("ownership registry record set has drifted")
    from contract_accounting.demo_uat.bootstrap import owned_record_rows

    if registry["bootstrap_records"] != owned_record_rows():
        raise DemoUATRuntimeError("ownership registry bootstrap record set has drifted")
    if not isinstance(registry["bindings"], dict):
        raise DemoUATRuntimeError("ownership registry bindings must be an object")
    _validate_privacy_policy_registry(registry["privacy_policy"])


def _validate_privacy_policy_registry(value: Any) -> None:
    from contract_accounting.demo_uat.bootstrap import (
        _PRIVACY_STATE_FIELDS,
        _privacy_state_fingerprint,
    )

    if not isinstance(value, dict) or set(value) != {
        "changed_by_demo",
        "prior_state",
        "prior_fingerprint",
        "demo_state",
        "demo_fingerprint",
    }:
        raise DemoUATRuntimeError("ownership registry privacy policy state has drifted")
    if not isinstance(value["changed_by_demo"], bool):
        raise DemoUATRuntimeError("ownership registry privacy policy ownership is invalid")
    for label in ("prior", "demo"):
        state = value[f"{label}_state"]
        if (
            not isinstance(state, dict)
            or set(state) != set(_PRIVACY_STATE_FIELDS)
            or value[f"{label}_fingerprint"] != _privacy_state_fingerprint(state)
        ):
            raise DemoUATRuntimeError(
                f"ownership registry privacy policy {label} fingerprint mismatch"
            )
    prior = value["prior_state"]
    demo = value["demo_state"]
    if value["changed_by_demo"]:
        if int(prior["enabled"]) or prior["activation_mode"] != "Disabled":
            raise DemoUATRuntimeError("demo-owned privacy prior state must be Disabled")
        if not int(demo["enabled"]) or demo["activation_mode"] != "Synthetic Test":
            raise DemoUATRuntimeError("demo-owned privacy active state must be Synthetic Test")
    elif prior != demo:
        raise DemoUATRuntimeError("preexisting privacy policy state must remain unchanged")


def manifest_record_presence(manifest: Mapping[str, Any]) -> list[dict[str, str]]:
    frappe = get_frappe()
    present: list[dict[str, str]] = []
    for entity in manifest["entities"]:
        doctype = str(entity["doctype"])
        name = str(entity["record_name"])
        if frappe.db.exists(doctype, name):
            present.append(
                {
                    "external_id": str(entity["external_id"]),
                    "doctype": doctype,
                    "name": name,
                }
            )
    return present


def deletion_plan(
    manifest: Mapping[str, Any],
    *,
    registry_file_name: str,
    bootstrap_records: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for entity in reversed(manifest["entities"]):
        plan.append(
            {
                "order": len(plan) + 1,
                "external_id": entity["external_id"],
                "doctype": entity["doctype"],
                "name": entity["record_name"],
            }
        )
    for record in sorted(bootstrap_records, key=lambda row: int(row["deletion_order"])):
        plan.append(
            {
                "order": len(plan) + 1,
                "external_id": record["external_id"],
                "doctype": record["doctype"],
                "name": record["name"],
            }
        )
    # The unattached registry has no graph dependency and is deliberately
    # removed last.  If an earlier domain delete fails, ownership evidence is
    # still physically available in addition to the database rollback.
    plan.append(
        {
            "order": len(plan) + 1,
            "external_id": "ownership-registry",
            "doctype": "File",
            "name": registry_file_name,
        }
    )
    return plan


def find_inbound_non_demo_links(
    *,
    registry_records: Sequence[Mapping[str, Any]],
    registry_file_name: str,
    bootstrap_records: Sequence[Mapping[str, Any]],
    bindings: Mapping[str, str],
    registry_created_at: Any,
    registry_created_by: str,
) -> list[dict[str, str]]:
    """Return every inbound Link/Dynamic Link whose owner is not demo-owned."""

    owned = {(str(record["doctype"]), str(record["name"])) for record in registry_records}
    owned.update((str(record["doctype"]), str(record["name"])) for record in bootstrap_records)
    owned.add(("File", registry_file_name))
    user_effects = inspect_user_on_trash_effects(
        registry_records=registry_records,
        bootstrap_records=bootstrap_records,
        registry_created_at=registry_created_at,
        registry_created_by=registry_created_by,
    )
    company_derived = _company_derived_keys(bindings=bindings)
    targets = owned | company_derived
    owned_versions, version_blockers = _classify_exact_version_sources(
        targets=targets,
        allowed_actors={
            str(registry_created_by),
            *(str(row["name"]) for row in bootstrap_records if str(row["doctype"]) == "User"),
        },
    )
    trusted_derived = _trusted_derived_source_keys(
        bindings=bindings,
        registry_records=registry_records,
        bootstrap_records=bootstrap_records,
        registry_created_at=registry_created_at,
        user_effect_keys={(str(row["doctype"]), str(row["name"])) for row in user_effects["owned"]},
    )
    source_allowlist = owned | trusted_derived | owned_versions
    blockers: list[dict[str, str]] = [*user_effects["blockers"], *version_blockers]
    blockers.extend(_scan_exact_file_attachments(targets, source_allowlist))
    # The private ownership registry and every exact ERPNext master generated
    # for the owned Company are normal inbound targets. An external File,
    # ToDo, Version, or Link to any of them must stop reset before hooks run.
    for target_doctype, target_name in sorted(targets):
        blockers.extend(_scan_direct_links(target_doctype, target_name, source_allowlist))
        blockers.extend(_scan_dynamic_links(target_doctype, target_name, source_allowlist))
    unique = {
        (
            row["target_doctype"],
            row["target_name"],
            row["source_doctype"],
            row["source_name"],
            row["fieldname"],
        ): row
        for row in blockers
    }
    return [unique[key] for key in sorted(unique)]


def _scan_exact_file_attachments(
    targets: set[tuple[str, str]],
    owned: set[tuple[str, str]],
) -> list[dict[str, str]]:
    """Scan File's structural attachment pair even when metadata is plain Data."""

    frappe = get_frappe()
    if not frappe.db.exists("DocType", "File"):
        return []
    blockers: list[dict[str, str]] = []
    for target_doctype, target_name in sorted(targets):
        for name in (
            frappe.get_all(
                "File",
                filters={
                    "attached_to_doctype": target_doctype,
                    "attached_to_name": target_name,
                },
                pluck="name",
            )
            or []
        ):
            if ("File", str(name)) in owned:
                continue
            blockers.append(
                {
                    "target_doctype": target_doctype,
                    "target_name": target_name,
                    "source_doctype": "File",
                    "source_name": str(name),
                    "fieldname": "attached_to_name",
                }
            )
    return blockers


def _trusted_derived_source_keys(
    *,
    bindings: Mapping[str, str],
    registry_records: Sequence[Mapping[str, Any]],
    bootstrap_records: Sequence[Mapping[str, Any]],
    registry_created_at: Any,
    user_effect_keys: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    """Return only standard rows necessarily derived from owned Company/User rows."""

    keys = _company_derived_keys(bindings=bindings)
    keys.update(user_effect_keys)
    keys.update(
        ("Comment", name)
        for name in owned_generated_comment_names(
            registry_records=registry_records,
            bootstrap_records=bootstrap_records,
        )
    )
    keys.update(
        ("Activity Log", name)
        for name in owned_activity_log_names(
            registry_records=registry_records,
            bootstrap_records=bootstrap_records,
            registry_created_at=registry_created_at,
        )
    )
    return keys


def _company_derived_keys(*, bindings: Mapping[str, str]) -> set[tuple[str, str]]:
    """Return exact current ERPNext rows whose Company hook owns lifecycle."""

    frappe = get_frappe()
    company = str(bindings["company"])
    keys: set[tuple[str, str]] = set()
    for doctype in (
        "Account",
        "Warehouse",
        "Cost Center",
        "Department",
        "Mode of Payment Account",
    ):
        if not frappe.db.exists("DocType", doctype):
            continue
        keys.update(
            (doctype, str(name))
            for name in (frappe.get_all(doctype, filters={"company": company}, pluck="name") or [])
        )
    return keys


def _classify_exact_version_sources(
    *,
    targets: set[tuple[str, str]],
    allowed_actors: set[str],
) -> tuple[set[tuple[str, str]], list[dict[str, str]]]:
    """Adopt only actor- and lifecycle-proven Versions; block every other one."""

    frappe = get_frappe()
    if not frappe.db.exists("DocType", "Version"):
        return set(), []
    scan_at = frappe.utils.now_datetime()
    owned: set[tuple[str, str]] = set()
    blockers: list[dict[str, str]] = []
    for target_doctype, target_name in sorted(targets):
        target_creation = frappe.db.get_value(target_doctype, target_name, "creation")
        if target_creation is None:
            continue
        created_at = frappe.utils.get_datetime(target_creation)
        for row in (
            frappe.get_all(
                "Version",
                filters={"ref_doctype": target_doctype, "docname": target_name},
                fields=["name", "owner", "creation"],
            )
            or []
        ):
            key = ("Version", str(row.name))
            if (
                str(row.owner or "") in allowed_actors
                and created_at <= frappe.utils.get_datetime(row.creation) <= scan_at
            ):
                owned.add(key)
                continue
            blockers.append(
                {
                    "target_doctype": target_doctype,
                    "target_name": target_name,
                    "source_doctype": "Version",
                    "source_name": str(row.name),
                    "fieldname": "docname",
                }
            )
    return owned, blockers


def inspect_user_on_trash_effects(
    *,
    registry_records: Sequence[Mapping[str, Any]],
    bootstrap_records: Sequence[Mapping[str, Any]],
    registry_created_at: Any,
    registry_created_by: str,
) -> dict[str, list[dict[str, Any]]]:
    """Classify every pinned Frappe v15 ``User.on_trash`` data effect.

    Only exact rows created inside the synthetic-user lifetime and structurally
    confined to owned targets are adopted. Rows that the pinned hook would
    delete or mutate without that provenance are returned as reset blockers.
    """

    frappe = get_frappe()
    users = sorted(str(row["name"]) for row in bootstrap_records if str(row["doctype"]) == "User")
    if not users:
        return {"owned": [], "blockers": []}
    targets = {
        (str(row["doctype"]), str(row["name"])) for row in [*registry_records, *bootstrap_records]
    }
    installed_at = frappe.utils.get_datetime(registry_created_at)
    scan_at = frappe.utils.now_datetime()
    user_created_at = {
        user: frappe.utils.get_datetime(frappe.db.get_value("User", user, "creation"))
        for user in users
    }
    actors = {*users, str(registry_created_by)}
    owned: dict[tuple[str, str], dict[str, Any]] = {}
    blockers: dict[tuple[str, str, str, str], dict[str, str]] = {}
    adopted_user_files: list[Any] = []

    def rows(doctype: str, filters: Mapping[str, Any], fields: Sequence[str]) -> list[Any]:
        if not frappe.db.exists("DocType", doctype):
            return []
        return list(frappe.get_all(doctype, filters=dict(filters), fields=["name", *fields]) or [])

    def in_window(value: Any, user: str, *, after_install: bool = True) -> bool:
        created = frappe.utils.get_datetime(value)
        lower = installed_at if after_install else user_created_at[user]
        return lower <= created <= scan_at

    def actor_is_owned(row: Any) -> bool:
        return str(row.get("owner") or "") in actors

    def target_is_owned(doctype: Any, name: Any, *, empty_ok: bool = True) -> bool:
        if not doctype and not name:
            return empty_ok
        return bool(doctype) and bool(name) and (str(doctype), str(name)) in targets

    def adopt(doctype: str, row: Any, reason: str, *, delete_before_user: bool = True) -> None:
        name = str(row.get("name"))
        owned[(doctype, name)] = {
            "doctype": doctype,
            "name": name,
            "reason": reason,
            "delete_before_user": delete_before_user,
        }

    def block(doctype: str, row: Any, fieldname: str, user: str) -> None:
        name = str(row.get("name"))
        blockers[(doctype, name, fieldname, user)] = {
            "target_doctype": "User",
            "target_name": user,
            "source_doctype": doctype,
            "source_name": name,
            "fieldname": fieldname,
        }

    for row in rows(
        "DocShare",
        {"user": ["in", users]},
        ["user", "share_doctype", "share_name", "owner", "creation"],
    ):
        user = str(row.user)
        if (
            in_window(row.creation, user, after_install=False)
            and actor_is_owned(row)
            and target_is_owned(row.share_doctype, row.share_name, empty_ok=False)
        ):
            adopt("DocShare", row, "exact synthetic-user share")
        else:
            block("DocShare", row, "user", user)

    todos = rows(
        "ToDo",
        {"allocated_to": ["in", users]},
        [
            "allocated_to",
            "assigned_by",
            "reference_type",
            "reference_name",
            "owner",
            "creation",
        ],
    )
    for row in todos:
        user = str(row.allocated_to)
        if (
            in_window(row.creation, user)
            and actor_is_owned(row)
            and str(row.assigned_by or "") in actors | {""}
            and target_is_owned(row.reference_type, row.reference_name)
        ):
            adopt("ToDo", row, "exact synthetic-user assignment")
        else:
            block("ToDo", row, "allocated_to", user)
    for row in rows(
        "ToDo",
        {"assigned_by": ["in", users]},
        ["allocated_to", "assigned_by", "reference_type", "reference_name"],
    ):
        if ("ToDo", str(row.name)) not in owned:
            block("ToDo", row, "assigned_by", str(row.assigned_by))

    for row in rows(
        "Event",
        {"owner": ["in", users], "event_type": "Private"},
        ["owner", "creation", "reference_doctype", "reference_docname"],
    ):
        user = str(row.owner)
        if in_window(row.creation, user) and target_is_owned(
            row.reference_doctype, row.reference_docname
        ):
            adopt("Event", row, "private synthetic-user event")
        else:
            block("Event", row, "owner", user)

    for row in rows(
        "Communication",
        {
            "communication_type": ["in", ["Chat", "Notification"]],
            "reference_doctype": "User",
        },
        ["communication_type", "reference_name", "owner", "creation"],
    ):
        affected = [
            user
            for user in users
            if str(row.reference_name or "") == user or str(row.owner) == user
        ]
        for user in affected:
            if (
                in_window(row.creation, user)
                and actor_is_owned(row)
                and str(row.reference_name or "") == user
            ):
                adopt("Communication", row, "synthetic-user notification")
            else:
                block("Communication", row, "reference_name", user)

    for row in rows(
        "Contact",
        {"user": ["in", users]},
        ["user", "email_id", "owner", "creation"],
    ):
        user = str(row.user)
        if (
            in_window(row.creation, user, after_install=False)
            and actor_is_owned(row)
            and str(row.email_id or "") == user
        ):
            adopt("Contact", row, "exact synthetic-user contact")
        else:
            block("Contact", row, "user", user)

    for row in rows(
        "Notification Settings",
        {"name": ["in", users]},
        ["user", "owner", "creation"],
    ):
        user = str(row.name)
        if (
            str(row.user or "") == str(registry_created_by)
            and user_created_at[user] - timedelta(seconds=5)
            <= frappe.utils.get_datetime(row.creation)
            <= installed_at
            and actor_is_owned(row)
        ):
            adopt(
                "Notification Settings",
                row,
                "exact bootstrap notification settings",
                delete_before_user=False,
            )
        else:
            block("Notification Settings", row, "user", user)

    for row in rows(
        "User Permission",
        {"user": ["in", users]},
        ["user", "allow", "for_value", "owner", "creation"],
    ):
        user = str(row.user)
        if (
            in_window(row.creation, user)
            and actor_is_owned(row)
            and target_is_owned(row.allow, row.for_value, empty_ok=False)
        ):
            adopt("User Permission", row, "exact owned-target permission")
        else:
            block("User Permission", row, "user", user)

    for doctype in ("OAuth Authorization Code", "Token Cache"):
        for row in rows(
            doctype,
            {"user": ["in", users]},
            ["user", "owner", "creation"],
        ):
            user = str(row.user)
            if in_window(row.creation, user) and actor_is_owned(row):
                adopt(doctype, row, "synthetic-user ephemeral authorization")
            else:
                block(doctype, row, "user", user)

    for row in rows(
        "Energy Point Log",
        {"user": ["in", users]},
        ["user", "reference_doctype", "reference_name", "owner", "creation"],
    ):
        user = str(row.user)
        if (
            in_window(row.creation, user)
            and actor_is_owned(row)
            and target_is_owned(row.reference_doctype, row.reference_name)
        ):
            adopt("Energy Point Log", row, "synthetic-user energy event")
        else:
            block("Energy Point Log", row, "user", user)

    for row in rows(
        "Workflow Action",
        {"user": ["in", users]},
        ["user", "reference_doctype", "reference_name", "owner", "creation"],
    ):
        user = str(row.user)
        if (
            in_window(row.creation, user)
            and actor_is_owned(row)
            and target_is_owned(row.reference_doctype, row.reference_name, empty_ok=False)
        ):
            adopt("Workflow Action", row, "owned-target synthetic workflow action")
        else:
            block("Workflow Action", row, "user", user)

    for row in rows(
        "List Filter",
        {"for_user": ["in", users]},
        ["for_user", "owner", "creation"],
    ):
        user = str(row.for_user)
        if in_window(row.creation, user) and actor_is_owned(row):
            adopt("List Filter", row, "synthetic-user list preference")
        else:
            block("List Filter", row, "for_user", user)

    for row in rows(
        "File",
        {
            "attached_to_doctype": "User",
            "attached_to_name": ["in", users],
        },
        [
            "attached_to_name",
            "file_name",
            "file_url",
            "is_private",
            "owner",
            "creation",
        ],
    ):
        user = str(row.attached_to_name)
        if (
            in_window(row.creation, user)
            and actor_is_owned(row)
            and bool(row.is_private)
            and str(row.file_url or "").startswith("/private/files/")
        ):
            adopt("File", row, "private synthetic-user attachment")
            adopted_user_files.append(row)
        else:
            block("File", row, "attached_to_name", user)

    if adopted_user_files:
        from frappe.utils import escape_html

        for file_row in adopted_user_files:
            file_url = quote(frappe.safe_encode(file_row.file_url), safe="/:")
            file_name = escape_html(file_row.file_name or file_row.file_url)
            expected_content = (
                f'<a href="{file_url}" target="_blank">{file_name}</a>'
                ' <i class="fa fa-lock text-warning"></i>'
            )
            for row in rows(
                "Comment",
                {
                    "comment_type": "Attachment",
                    "reference_doctype": "User",
                    "reference_name": str(file_row.attached_to_name),
                    "content": expected_content,
                    "owner": ["in", sorted(actors)],
                    "creation": [
                        "between",
                        [
                            frappe.utils.get_datetime(file_row.creation),
                            frappe.utils.get_datetime(file_row.creation) + timedelta(seconds=5),
                        ],
                    ],
                },
                ["owner", "creation"],
            ):
                adopt("Comment", row, "exact private user attachment feed")

    for row in rows(
        "Note Seen By",
        {"user": ["in", users]},
        ["user", "parent", "parenttype"],
    ):
        block("Note Seen By", row, "user", str(row.user))
    for row in rows(
        "User Invitation",
        {"email": ["in", users]},
        ["email", "user"],
    ):
        block("User Invitation", row, "email", str(row.email))

    return {
        "owned": [owned[key] for key in sorted(owned)],
        "blockers": [blockers[key] for key in sorted(blockers)],
    }


def owned_activity_log_names(
    *,
    registry_records: Sequence[Mapping[str, Any]],
    bootstrap_records: Sequence[Mapping[str, Any]],
    registry_created_at: Any,
) -> list[str]:
    """Return browser activity rows owned by synthetic users in this lifecycle.

    A matching user alone is insufficient: the row must point at an exact
    registry-owned synthetic User and its creation timestamp must fall between
    completion of dataset installation and the current reset/verify scan.
    Historical and future-dated rows therefore remain external blockers.
    """

    frappe = get_frappe()
    if not frappe.db.exists("DocType", "Activity Log"):
        return []
    users = sorted(str(row["name"]) for row in bootstrap_records if str(row["doctype"]) == "User")
    if not users:
        return []
    installed_at = frappe.utils.get_datetime(registry_created_at)
    lifecycle_end = frappe.utils.now_datetime()
    if installed_at > lifecycle_end:
        raise DemoUATRuntimeError("ownership registry created_at is in the future")
    owned_targets = {
        (str(row["doctype"]), str(row["name"])) for row in [*registry_records, *bootstrap_records]
    }
    rows = (
        frappe.get_all(
            "Activity Log",
            filters={
                "user": ["in", users],
                "creation": ["between", [installed_at, lifecycle_end]],
            },
            fields=[
                "name",
                "operation",
                "reference_doctype",
                "reference_name",
                "timeline_doctype",
                "timeline_name",
                "link_doctype",
                "link_name",
            ],
        )
        or []
    )
    owned: list[str] = []
    for row in rows:
        if str(row.operation or "") not in {"Login", "Logout"}:
            continue
        pairs = (
            (row.reference_doctype, row.reference_name),
            (row.timeline_doctype, row.timeline_name),
            (row.link_doctype, row.link_name),
        )
        if all(
            (not doctype and not name)
            or (bool(doctype) and bool(name) and (str(doctype), str(name)) in owned_targets)
            for doctype, name in pairs
        ):
            owned.append(str(row.name))
    return sorted(owned)


def owned_generated_comment_names(
    *,
    registry_records: Sequence[Mapping[str, Any]],
    bootstrap_records: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Resolve unambiguous Shared/Assigned feed rows from owned user actions.

    Attribution uses only structured rows: exact owned target, exact owned
    recipient/assignee, matching source/comment actor, comment type, and a
    narrow synchronous creation window. Ambiguous or unmatched comments remain
    external inbound blockers.
    """

    frappe = get_frappe()
    owned_targets = {
        (str(row["doctype"]), str(row["name"])) for row in [*registry_records, *bootstrap_records]
    }
    users = {str(row["name"]) for row in bootstrap_records if str(row["doctype"]) == "User"}
    sources: list[dict[str, Any]] = []
    for row in (
        frappe.get_all(
            "DocShare",
            filters={"user": ["in", sorted(users)]},
            fields=["name", "share_doctype", "share_name", "owner", "creation"],
        )
        or []
    ):
        target = (str(row.share_doctype), str(row.share_name))
        if target in owned_targets:
            sources.append(
                {
                    "reference_doctype": target[0],
                    "reference_name": target[1],
                    "comment_type": "Shared",
                    "actor": str(row.owner),
                    "creation": row.creation,
                }
            )
    for row in (
        frappe.get_all(
            "ToDo",
            filters={"allocated_to": ["in", sorted(users)]},
            fields=[
                "name",
                "reference_type",
                "reference_name",
                "owner",
                "assigned_by",
                "creation",
            ],
        )
        or []
    ):
        target = (str(row.reference_type or ""), str(row.reference_name or ""))
        if target in owned_targets:
            sources.append(
                {
                    "reference_doctype": target[0],
                    "reference_name": target[1],
                    "comment_type": "Assigned",
                    "actor": str(row.assigned_by or row.owner),
                    "creation": row.creation,
                }
            )

    attributed: set[str] = set()
    for source in sources:
        candidates = (
            frappe.get_all(
                "Comment",
                filters={
                    "reference_doctype": source["reference_doctype"],
                    "reference_name": source["reference_name"],
                    "comment_type": source["comment_type"],
                    "owner": source["actor"],
                    "creation": ["between", _creation_window(frappe, source["creation"])],
                },
                pluck="name",
            )
            or []
        )
        if len(candidates) == 1:
            attributed.add(str(candidates[0]))
    return sorted(attributed)


def _creation_window(frappe: Any, value: Any) -> list[Any]:
    from datetime import timedelta

    created = frappe.utils.get_datetime(value)
    return [created, created + timedelta(seconds=5)]


def _scan_direct_links(
    target_doctype: str,
    target_name: str,
    owned: set[tuple[str, str]],
) -> list[dict[str, str]]:
    frappe = get_frappe()
    sources: set[tuple[str, str]] = set()
    rows = frappe.get_all(
        "DocField",
        filters={"fieldtype": "Link", "options": target_doctype},
        fields=["parent as source_doctype", "fieldname"],
    )
    rows.extend(
        frappe.get_all(
            "Custom Field",
            filters={"fieldtype": "Link", "options": target_doctype},
            fields=["dt as source_doctype", "fieldname"],
        )
    )
    sources.update((str(row.source_doctype), str(row.fieldname)) for row in rows)
    blockers: list[dict[str, str]] = []
    for source_doctype, fieldname in sorted(sources):
        blockers.extend(
            _matching_source_rows(
                source_doctype,
                filters={fieldname: target_name},
                fieldname=fieldname,
                target_doctype=target_doctype,
                target_name=target_name,
                owned=owned,
            )
        )
    return blockers


def _scan_dynamic_links(
    target_doctype: str,
    target_name: str,
    owned: set[tuple[str, str]],
) -> list[dict[str, str]]:
    frappe = get_frappe()
    sources: set[tuple[str, str, str]] = set()
    rows = frappe.get_all(
        "DocField",
        filters={"fieldtype": "Dynamic Link"},
        fields=["parent as source_doctype", "fieldname", "options"],
    )
    rows.extend(
        frappe.get_all(
            "Custom Field",
            filters={"fieldtype": "Dynamic Link"},
            fields=["dt as source_doctype", "fieldname", "options"],
        )
    )
    sources.update(
        (str(row.source_doctype), str(row.fieldname), str(row.options))
        for row in rows
        if row.options
    )
    blockers: list[dict[str, str]] = []
    for source_doctype, fieldname, selector_field in sorted(sources):
        blockers.extend(
            _matching_source_rows(
                source_doctype,
                filters={selector_field: target_doctype, fieldname: target_name},
                fieldname=fieldname,
                target_doctype=target_doctype,
                target_name=target_name,
                owned=owned,
            )
        )
    return blockers


def _matching_source_rows(
    source_doctype: str,
    *,
    filters: Mapping[str, Any],
    fieldname: str,
    target_doctype: str,
    target_name: str,
    owned: set[tuple[str, str]],
) -> list[dict[str, str]]:
    frappe = get_frappe()
    meta = frappe.get_meta(source_doctype)
    if meta.issingle:
        document = frappe.get_single(source_doctype)
        if all(document.get(key) == value for key, value in filters.items()):
            rows = [{"name": source_doctype, "parent": None, "parenttype": None}]
        else:
            rows = []
    else:
        fields = ["name"]
        if meta.istable:
            fields.extend(["parent", "parenttype"])
        rows = frappe.get_all(source_doctype, filters=dict(filters), fields=fields) or []
    blockers: list[dict[str, str]] = []
    for row in rows:
        source_name = str(row.get("name"))
        if (source_doctype, source_name) in owned:
            continue
        if meta.istable:
            parenttype = str(row.get("parenttype") or "")
            parent = str(row.get("parent") or "")
            if (parenttype, parent) in owned:
                continue
            display_name = f"{parenttype}/{parent} child {source_name}"
        else:
            display_name = source_name
        blockers.append(
            {
                "target_doctype": target_doctype,
                "target_name": target_name,
                "source_doctype": source_doctype,
                "source_name": display_name,
                "fieldname": fieldname,
            }
        )
    return blockers
