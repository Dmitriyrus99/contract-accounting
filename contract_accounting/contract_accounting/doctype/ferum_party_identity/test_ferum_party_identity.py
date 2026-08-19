"""Bench runtime acceptance for the ERPNext master-data boundary."""

from __future__ import annotations

from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from contract_accounting.api.master_data import link_party_identity
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
    _make_customer,
)


class TestFerumPartyIdentity(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.customer = _make_customer(f"CA Party Customer {uuid4().hex[:10]}")
        self.inn = f"77{uuid4().int % 100_000_000:08d}"

    def tearDown(self) -> None:
        frappe.set_user(self._previous_user)
        super().tearDown()

    def test_linkage_is_idempotent_and_does_not_copy_business_fields(self) -> None:
        customer_name = frappe.db.get_value("Customer", self.customer, "customer_name")
        first = self._link(customer=self.customer)
        second = self._link(customer=self.customer, reason="Idempotent retry")
        self.assertEqual(second["party_identity"], first["party_identity"])
        self.assertEqual(
            frappe.db.count("Ferum Party Identity", {"customer": self.customer}),
            1,
        )
        self.assertEqual(
            frappe.db.get_value("Customer", self.customer, "customer_name"),
            customer_name,
        )

    def test_existing_identity_can_add_supplier_without_ambiguous_merge(self) -> None:
        first = self._link(customer=self.customer)
        supplier = self._make_supplier()
        supplier_name = frappe.db.get_value("Supplier", supplier, "supplier_name")
        result = self._link(
            party_identity=first["party_identity"],
            supplier=supplier,
            reason="Approved cross-master linkage",
        )
        self.assertEqual(result["party_identity"], first["party_identity"])
        self.assertEqual(result["supplier"], supplier)
        self.assertEqual(frappe.db.get_value("Supplier", supplier, "supplier_name"), supplier_name)

    def test_conflicting_master_links_fail_closed(self) -> None:
        first = self._link(customer=self.customer)
        other_customer = _make_customer(f"CA Other Party {uuid4().hex[:10]}")
        second = self._link(customer=other_customer)
        with self.assertRaises(frappe.ValidationError):
            self._link(
                party_identity=first["party_identity"],
                customer=other_customer,
                reason="Must not merge automatically",
            )
        self.assertNotEqual(first["party_identity"], second["party_identity"])

    def test_direct_master_link_edit_and_linked_delete_are_rejected(self) -> None:
        result = self._link(customer=self.customer)
        doc = frappe.get_doc("Ferum Party Identity", result["party_identity"])
        doc.customer = _make_customer(f"CA Direct Edit {uuid4().hex[:10]}")
        with self.assertRaises(frappe.PermissionError):
            doc.save(ignore_permissions=True)
        doc.reload()
        with self.assertRaises(frappe.PermissionError):
            doc.delete(ignore_permissions=True)

    def test_same_inn_creates_review_candidate_without_auto_merge(self) -> None:
        first = self._link(customer=self.customer)
        other_customer = _make_customer(f"CA Duplicate Candidate {uuid4().hex[:10]}")
        second = self._link(customer=other_customer)
        self.assertNotEqual(first["party_identity"], second["party_identity"])
        candidate = frappe.get_doc("Ferum Party Identity", second["party_identity"])
        self.assertEqual(candidate.possible_duplicate_of, first["party_identity"])
        self.assertEqual(candidate.duplicate_review_status, "Not Reviewed")

    def test_invalid_inn_kpp_and_branch_cycle_are_rejected(self) -> None:
        with self.assertRaises(frappe.ValidationError):
            self._link(customer=self.customer, inn="770123456X")
        identity = self._link(customer=self.customer)
        doc = frappe.get_doc("Ferum Party Identity", identity["party_identity"])
        doc.append("tax_registrations", {"kpp": "123"})
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

        head = frappe.get_doc("Ferum Party Identity", identity["party_identity"])
        other_customer = _make_customer(f"CA Branch Party {uuid4().hex[:10]}")
        branch_identity = self._link(customer=other_customer)
        branch = frappe.get_doc("Ferum Party Identity", branch_identity["party_identity"])
        branch.is_branch = 1
        branch.head_party = head.name
        branch.save(ignore_permissions=True)
        head.is_branch = 1
        head.head_party = branch.name
        with self.assertRaises(frappe.ValidationError):
            head.save(ignore_permissions=True)

    def test_provenance_and_external_reference_are_immutable(self) -> None:
        result = self._link(
            customer=self.customer,
            provenance_doctype="Customer",
            provenance_name=self.customer,
            external_reference="MDM-001",
        )
        doc = frappe.get_doc("Ferum Party Identity", result["party_identity"])
        doc.external_reference = "MDM-002"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

    def _link(self, **overrides: object) -> dict[str, str]:
        values: dict[str, object] = {
            "party_type": "Legal Entity",
            "full_name": "ООО Тестовая организация",
            "reason": "Verified master-data linkage",
            "inn": self.inn,
        }
        values.update(overrides)
        return link_party_identity(**values)  # type: ignore[arg-type]

    @staticmethod
    def _make_supplier() -> str:
        name = f"CA Party Supplier {uuid4().hex[:10]}"
        return (
            frappe.get_doc(
                {
                    "doctype": "Supplier",
                    "supplier_name": name,
                    "supplier_group": frappe.db.get_value(
                        "Supplier Group", {"is_group": 0}, "name"
                    ),
                }
            )
            .insert(ignore_permissions=True)
            .name
        )
