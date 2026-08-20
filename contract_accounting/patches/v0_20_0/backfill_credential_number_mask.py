"""Backfill the non-sensitive last-four projection used by scoped reviewers."""

from __future__ import annotations

import frappe

from contract_accounting.domain.privacy import mask_credential_number


def execute() -> None:
    for name, number in frappe.get_all(
        "Ferum Personnel Credential",
        fields=["name", "credential_number"],
        as_list=True,
    ):
        frappe.db.set_value(
            "Ferum Personnel Credential",
            name,
            "credential_number_masked",
            mask_credential_number(number),
            update_modified=False,
        )
