"""Fail-closed Party Identity linkage over standard ERPNext masters."""

from __future__ import annotations

import re
from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

DOCTYPE: Final[str] = "Ferum Party Identity"
PARTY_LINKAGE_WRITE_FLAG: Final[str] = "contract_accounting_party_linkage_writer"
MASTER_LINK_FIELDS: Final[dict[str, str]] = {
    "customer": "Customer",
    "supplier": "Supplier",
    "company": "Company",
}
INN_LENGTHS: Final[dict[str, frozenset[int]]] = {
    "Legal Entity": frozenset({10}),
    "Government Body": frozenset({10}),
    "Individual Entrepreneur": frozenset({12}),
    "Self-Employed": frozenset({12}),
    "Individual": frozenset({12}),
    "Foreign Entity": frozenset({10, 12}),
}
INN_RE: Final[re.Pattern[str]] = re.compile(r"^\d+$")
KPP_RE: Final[re.Pattern[str]] = re.compile(r"^\d{9}$")
MAX_HEAD_DEPTH: Final[int] = 10


class FerumPartyIdentity(Document):
    def before_insert(self) -> None:
        authorized = frappe.flags.get(PARTY_LINKAGE_WRITE_FLAG)
        if isinstance(authorized, dict):
            # Document.insert() reapplies user defaults immediately before this hook.
            # Remove conventional-field defaults that the typed command did not request.
            for fieldname in MASTER_LINK_FIELDS:
                if fieldname not in authorized:
                    self.set(fieldname, None)

    def validate(self) -> None:
        self._validate_linkage_writer()
        self._validate_immutable_references()
        self._validate_inn()
        self._validate_tax_registrations()
        self._validate_head_party()
        self._validate_duplicate_reference()
        self._validate_unique_master_links()
        self._flag_duplicate_candidate()
        self.linkage_status = (
            "Linked" if any(self.get(field) for field in MASTER_LINK_FIELDS) else "Unlinked"
        )

    def on_trash(self) -> None:
        if any(self.get(field) for field in MASTER_LINK_FIELDS):
            frappe.throw(
                _("Linked Party Identity нельзя удалить; сначала выполните controlled unlink."),
                frappe.PermissionError,
            )

    def _validate_linkage_writer(self) -> None:
        before = self.get_doc_before_save()
        changed = [
            field
            for field in MASTER_LINK_FIELDS
            if self.get(field) != (before.get(field) if before else None)
        ]
        authorized = frappe.flags.get(PARTY_LINKAGE_WRITE_FLAG)
        if changed and not isinstance(authorized, dict):
            frappe.throw(
                _("Party Identity master links меняются только typed linkage command."),
                frappe.PermissionError,
            )
        if changed and any(field not in authorized for field in changed):
            frappe.throw(
                _("Typed linkage command attempted an unauthorized master link."),
                frappe.PermissionError,
            )

    def _validate_immutable_references(self) -> None:
        before = self.get_doc_before_save()
        if before is None:
            return
        for fieldname in ("provenance_doctype", "provenance_name", "external_reference"):
            old_value = before.get(fieldname)
            new_value = self.get(fieldname)
            if old_value and new_value != old_value:
                frappe.throw(
                    _("Party Identity {0} immutable; создайте reconciliation evidence.").format(
                        fieldname
                    )
                )

    def _validate_inn(self) -> None:
        inn = str(self.get("inn") or "").strip()
        if not inn:
            return
        if not INN_RE.fullmatch(inn):
            frappe.throw(_("INN должен состоять только из цифр."))
        allowed = INN_LENGTHS.get(self.party_type)
        if not allowed or len(inn) not in allowed:
            frappe.throw(_("Длина INN не соответствует Party Type."))
        self.inn = inn

    def _validate_tax_registrations(self) -> None:
        primary = 0
        for row in self.get("tax_registrations") or []:
            row.kpp = str(row.kpp or "").strip()
            if not KPP_RE.fullmatch(row.kpp):
                frappe.throw(_("KPP должен состоять ровно из 9 цифр."))
            if (
                row.valid_from
                and row.valid_until
                and getdate(row.valid_until) < getdate(row.valid_from)
            ):
                frappe.throw(_("Party Tax Registration valid_until раньше valid_from."))
            primary += int(bool(row.is_primary))
        if primary > 1:
            frappe.throw(_("У Party Identity может быть только один primary KPP."))

    def _validate_head_party(self) -> None:
        if self.is_branch and not self.head_party:
            frappe.throw(_("Branch Party Identity требует head_party."))
        if not self.head_party:
            return
        visited = {self.name} if self.name else set()
        current = self.head_party
        for _depth in range(MAX_HEAD_DEPTH):
            if not current:
                return
            if current in visited:
                frappe.throw(_("Party Identity head_party содержит цикл."))
            visited.add(current)
            current = frappe.db.get_value(DOCTYPE, current, "head_party")
        frappe.throw(_("Party Identity head_party превышает допустимую глубину."))

    def _validate_duplicate_reference(self) -> None:
        if self.name and self.possible_duplicate_of == self.name:
            frappe.throw(_("Party Identity не может ссылаться на себя как duplicate candidate."))

    def _validate_unique_master_links(self) -> None:
        if self.status != "Active":
            return
        for fieldname in MASTER_LINK_FIELDS:
            value = self.get(fieldname)
            if not value:
                continue
            existing = frappe.db.exists(
                DOCTYPE,
                {
                    fieldname: value,
                    "status": "Active",
                    "name": ["!=", self.name or ""],
                },
            )
            if existing:
                frappe.throw(
                    _("{0} уже связан с Active Party Identity {1}.").format(value, existing)
                )

    def _flag_duplicate_candidate(self) -> None:
        if not self.is_new() or self.possible_duplicate_of or not self.inn:
            return
        candidates = frappe.get_all(
            DOCTYPE,
            filters={"inn": self.inn, "name": ["!=", self.name or ""]},
            pluck="name",
            order_by="creation asc",
        )
        candidates = [name for name in candidates if name != self.head_party]
        if candidates:
            self.possible_duplicate_of = candidates[0]
            self.duplicate_review_status = "Not Reviewed"


def on_doctype_update() -> None:
    frappe.db.add_index(DOCTYPE, ["inn", "status"], "ca_party_inn_status_idx")
