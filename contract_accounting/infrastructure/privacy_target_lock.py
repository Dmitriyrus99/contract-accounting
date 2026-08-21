"""Shared row locks for privacy retention, holds and active assignments."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

import frappe

LOCKABLE_PRIVACY_TARGETS: Final[frozenset[str]] = frozenset(
    {
        "Employee",
        "Ferum Contractor Worker",
        "Ferum Personnel Credential",
        "Ferum Privacy Event",
        "File",
    }
)


def lock_privacy_target(target_doctype: str, target_name: str) -> bool:
    """Lock one exact privacy target and return whether it still exists.

    Every workflow capable of creating a retention blocker or a new active
    assignment must acquire this same row lock before changing state.
    """

    if target_doctype not in LOCKABLE_PRIVACY_TARGETS or not target_name:
        return False
    return bool(
        frappe.db.get_value(
            target_doctype,
            target_name,
            "name",
            for_update=True,
        )
    )


def lock_privacy_targets(targets: Iterable[tuple[str, str]]) -> frozenset[tuple[str, str]]:
    """Acquire exact target locks in one deterministic global order."""

    normalized = sorted(
        {
            (str(doctype), str(name))
            for doctype, name in targets
            if doctype in LOCKABLE_PRIVACY_TARGETS and name
        }
    )
    return frozenset(target for target in normalized if lock_privacy_target(*target))


def lock_file_content_hash_aliases(
    content_hash: str,
    *,
    canonical_file: str | None = None,
    file_url: str | None = None,
) -> tuple[str, ...]:
    """Serialize File/Credential creation for one existing blob identity.

    A content hash cannot be locked directly because it is not its own row. Both
    competing flows therefore discover the existing File rows for the hash and
    lock their exact primary keys in the same order. Credential creation also
    supplies its canonical File, making an empty or concurrently changed hash a
    fail-closed error instead of silently validating a different blob.
    """

    normalized_hash = str(content_hash or "").strip()
    normalized_canonical = str(canonical_file or "").strip()
    normalized_url = str(file_url or "").strip()
    if not normalized_url.startswith(("/files/", "/private/files/")):
        normalized_url = ""
    if not normalized_hash and not normalized_url:
        return ()

    names: set[str] = set()
    if normalized_hash:
        names.update(
            str(name)
            for name in frappe.get_all(
                "File",
                filters={"content_hash": normalized_hash},
                pluck="name",
                order_by="name asc",
            )
        )
    if normalized_url:
        names.update(
            str(name)
            for name in frappe.get_all(
                "File",
                filters={"file_url": normalized_url},
                pluck="name",
                order_by="name asc",
            )
        )
    if normalized_canonical:
        names.add(normalized_canonical)
    locked = tuple(name for name in sorted(names) if lock_privacy_target("File", name))

    if normalized_canonical:
        current = frappe.db.get_value(
            "File",
            normalized_canonical,
            ("content_hash", "file_url"),
            as_dict=True,
            for_update=True,
        )
        if not current or (normalized_hash and str(current.content_hash or "") != normalized_hash):
            frappe.throw("Credential canonical File отсутствует или изменён во время проверки.")
        if normalized_url and str(current.file_url or "") != normalized_url:
            frappe.throw("Credential canonical File path изменён во время проверки.")
    return locked


def lock_assignment_privacy_target(doc: object, method: str | None = None) -> None:
    """Serialize a proposed active assignment before controller validation."""

    if getattr(doc, "status", None) not in {"Approved", "Suspended"}:
        return
    if getattr(doc, "execution_mode", None) == "Contractor" and getattr(
        doc,
        "contractor_worker",
        None,
    ):
        lock_privacy_target("Ferum Contractor Worker", doc.contractor_worker)
    elif getattr(doc, "execution_mode", None) == "Internal" and getattr(
        doc,
        "employee",
        None,
    ):
        lock_privacy_target("Employee", doc.employee)
