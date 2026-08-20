"""Protected Contractor Worker lifecycle governed by FR05-PD-01."""

from __future__ import annotations

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document

from contract_accounting.api.privacy import (
    PRIVACY_RETENTION_FLAG,
    PRIVACY_TRANSITION_FLAG,
    PRIVACY_WRITE_FLAG,
    active_privacy_settings,
)
from contract_accounting.domain.privacy import POLICY_HASH, POLICY_REFERENCE

TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "Inactive": frozenset({"Active", "Archived"}),
    "Active": frozenset({"Inactive", "Archived"}),
    "Archived": frozenset({"Inactive"}),
}


class FerumContractorWorker(Document):
    def before_insert(self) -> None:
        self._require_writer()

    def validate(self) -> None:
        self._require_writer()
        settings = active_privacy_settings()
        if (
            self.privacy_policy_reference != POLICY_REFERENCE
            or self.privacy_policy_hash != POLICY_HASH
        ):
            frappe.throw(_("Contractor Worker policy stamp не совпадает с FR-05."))
        if (
            self.retention_status != "Anonymized"
            and settings.activation_mode == "Synthetic Test"
            and not str(self.privacy_basis_reference or "").startswith("TEST-")
        ):
            frappe.throw(_("Synthetic Worker требует TEST- basis."))
        if self.retention_status != "Anonymized" and (
            not self.supplier or not frappe.db.exists("Supplier", self.supplier)
        ):
            frappe.throw(_("Contractor Worker требует существующий Supplier."))
        if self.retention_status != "Anonymized" and (
            not self.privacy_basis_reference or not self.data_owner
        ):
            frappe.throw(_("Contractor Worker требует privacy basis и Data Owner."))
        if self.retention_status == "Anonymized" and any(
            (
                self.supplier,
                self.contact,
                self.position,
                self.privacy_basis_reference,
                self.data_owner,
            )
        ):
            frappe.throw(_("Anonymized Worker не должен сохранять Supplier/contact/basis/owner."))
        if self.contact and not self.work_contact_confirmed:
            frappe.throw(_("Contact разрешён только после подтверждения, что он рабочий."))
        self._validate_transition()
        self._freeze_identity()

    def on_trash(self) -> None:
        frappe.throw(
            _("Contractor Worker не удаляется напрямую; применяется retention."),
            frappe.PermissionError,
        )

    @staticmethod
    def _require_writer() -> None:
        if not frappe.flags.get(PRIVACY_WRITE_FLAG):
            frappe.throw(
                _("Contractor Worker изменяется только typed FR-06 command."),
                frappe.PermissionError,
            )

    def _validate_transition(self) -> None:
        before = self.get_doc_before_save()
        if before is None:
            if self.status != "Inactive":
                frappe.throw(_("Новый Contractor Worker создаётся в Inactive."))
            return
        if before.status == self.status:
            return
        if frappe.flags.get(PRIVACY_TRANSITION_FLAG) != self.status:
            frappe.throw(_("Contractor Worker transition context отсутствует."))
        if self.status not in TRANSITIONS.get(before.status, frozenset()):
            frappe.throw(_("Недопустимый Contractor Worker transition."))
        if before.status == "Archived" and len(str(self.transition_reason or "").strip()) < 10:
            frappe.throw(_("Возврат Archived Worker требует reason и повторную проверку."))

    def _freeze_identity(self) -> None:
        before = self.get_doc_before_save()
        if before is None:
            return
        for fieldname in (
            "supplier",
            "worker_external_id",
            "privacy_policy_reference",
            "privacy_policy_hash",
        ):
            if self.get(fieldname) != before.get(fieldname) and not (
                fieldname == "supplier" and frappe.flags.get(PRIVACY_RETENTION_FLAG)
            ):
                frappe.throw(_("Contractor Worker identity/policy stamp неизменяемы."))


def on_doctype_update() -> None:
    frappe.db.add_unique(
        "Ferum Contractor Worker", ["worker_external_id"], "ca_worker_external_id_uniq"
    )
    frappe.db.add_index("Ferum Contractor Worker", ["supplier", "status"])
