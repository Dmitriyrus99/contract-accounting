"""Serialize generic Attach/Attach Image/Link(File) references with credential retention."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from contract_accounting.infrastructure.privacy_file_guard import (
    _credential_for_file,
    _credential_for_identity,
)
from contract_accounting.infrastructure.privacy_target_lock import (
    lock_file_content_hash_aliases,
    lock_privacy_target,
)


def lock_credential_attachment_references(doc: Any, method: str | None = None) -> None:
    """Close new-business-reference versus retention races for standard file fields."""

    values: set[str] = set()
    for field in doc.meta.fields:
        if field.fieldtype in {"Attach", "Attach Image"} or (
            field.fieldtype == "Link" and field.options == "File"
        ):
            value = str(doc.get(field.fieldname) or "").strip()
            if value:
                values.add(value)
    for value in sorted(values):
        row = frappe.db.get_value(
            "File",
            {"file_url": value} if value.startswith(("/files/", "/private/files/")) else value,
            ("name", "content_hash", "file_url"),
            as_dict=True,
        )
        if not row:
            continue
        credential = _credential_for_file(str(row.name)) or _credential_for_identity(
            str(row.content_hash or ""), str(row.file_url or "")
        )
        if not credential:
            continue
        lock_privacy_target("Ferum Personnel Credential", credential)
        lock_file_content_hash_aliases(
            str(row.content_hash or ""),
            canonical_file=str(row.name),
            file_url=str(row.file_url or ""),
        )
        current = frappe.db.get_value(
            "File",
            row.name,
            ("content_hash", "file_url"),
            as_dict=True,
            for_update=True,
        )
        if (
            not current
            or (
                _credential_for_file(str(row.name))
                or _credential_for_identity(
                    str(current.content_hash or ""), str(current.file_url or ""), for_update=True
                )
            )
            != credential
        ):
            frappe.throw(
                _("Credential attachment source изменился во время business reference save."),
                frappe.PermissionError,
            )
