"""Run application file guards before Frappe unlinks physical content."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.core.doctype.file.file import File

from contract_accounting.api.privacy_event_retention import lock_privacy_event_artifact
from contract_accounting.infrastructure.privacy_file_guard import (
    is_credential_file_alias,
    preflight_new_file_alias,
    prevent_credential_file_delete,
    validate_credential_file_alias,
)
from contract_accounting.infrastructure.project_document_file_guard import (
    prevent_locked_file_delete,
)


class ContractAccountingFile(File):
    """Preserve protected binaries when a delete command is rejected."""

    def before_insert(self) -> None:
        # Event retention owns the parent lock; acquire it before the shared
        # hash/path alias locks used by the File preflight to keep one global
        # lock order for attachment creation versus event minimization.
        lock_privacy_event_artifact(self)
        preflight_new_file_alias(self)
        super().before_insert()
        validate_credential_file_alias(self)

    def validate(self) -> None:
        # Check the stored protected identity before Frappe can move a private
        # path into the public tree, then recheck the normalized final values.
        validate_credential_file_alias(self)
        super().validate()
        validate_credential_file_alias(self)

    def is_downloadable(self) -> bool:
        """Keep credential bytes behind the audited typed download command."""

        if is_credential_file_alias(self.name):
            return False
        return bool(super().is_downloadable())

    def make_thumbnail(self, *args, **kwargs):
        """Never materialize a public derivative of protected credential bytes."""

        if is_credential_file_alias(self.name):
            frappe.throw(
                _("Thumbnail для Credential File запрещён; используйте typed download."),
                frappe.PermissionError,
            )
        return super().make_thumbnail(*args, **kwargs)

    def on_trash(self) -> None:
        prevent_locked_file_delete(self)
        prevent_credential_file_delete(self)
        super().on_trash()
