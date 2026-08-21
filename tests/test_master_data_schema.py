from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = ROOT / "contract_accounting" / "contract_accounting" / "doctype"


def schema(name: str) -> dict[str, object]:
    return json.loads((DOCTYPE_ROOT / name / f"{name}.json").read_text(encoding="utf-8"))


def fields(document: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        field["fieldname"]: field
        for field in document["fields"]  # type: ignore[index,union-attr]
    }


class TestMasterDataBoundary(unittest.TestCase):
    def test_party_identity_links_standard_erpnext_masters_without_replacing_them(self) -> None:
        party = fields(schema("ferum_party_identity"))
        for fieldname, target in {
            "customer": "Customer",
            "supplier": "Supplier",
            "company": "Company",
        }.items():
            with self.subTest(fieldname=fieldname):
                self.assertEqual(party[fieldname]["fieldtype"], "Link")
                self.assertEqual(party[fieldname]["options"], target)
                self.assertEqual(party[fieldname]["unique"], 1)
        self.assertEqual(party["provenance_name"]["fieldtype"], "Dynamic Link")
        self.assertEqual(party["provenance_name"]["options"], "provenance_doctype")
        for fieldname in (
            "linkage_status",
            "linkage_reason",
            "linkage_updated_by",
            "linkage_updated_at",
        ):
            self.assertEqual(party[fieldname]["read_only"], 1)

    def test_party_tax_registration_reuses_standard_address(self) -> None:
        party = fields(schema("ferum_party_identity"))
        self.assertEqual(party["tax_registrations"]["options"], "Ferum Party Tax Registration")
        registration = schema("ferum_party_tax_registration")
        self.assertEqual(registration["istable"], 1)
        address = fields(registration)["address"]
        self.assertEqual(address["fieldtype"], "Link")
        self.assertEqual(address["options"], "Address")

    def test_service_object_reuses_customer_address_and_contact(self) -> None:
        service_object = fields(schema("ferum_service_object"))
        for fieldname, target in {
            "customer": "Customer",
            "address": "Address",
            "main_contact": "Contact",
        }.items():
            with self.subTest(fieldname=fieldname):
                self.assertEqual(service_object[fieldname]["fieldtype"], "Link")
                self.assertEqual(service_object[fieldname]["options"], target)

    def test_material_expense_reuses_standard_warehouse(self) -> None:
        warehouse = fields(schema("ferum_material_expense"))["warehouse"]
        self.assertEqual(warehouse["fieldtype"], "Link")
        self.assertEqual(warehouse["options"], "Warehouse")
        self.assertEqual(warehouse["read_only"], 1)

    def test_linkage_is_post_only_and_has_no_business_field_sync(self) -> None:
        source = (ROOT / "contract_accounting" / "api" / "master_data.py").read_text(
            encoding="utf-8"
        )
        self.assertEqual(source.count('@frappe.whitelist(methods=["POST"])'), 1)
        for business_field in ("customer_name", "supplier_name", "company_name"):
            self.assertNotIn(business_field, source)
        self.assertIn("for_update=True", source)
        self.assertIn("PARTY_LINKAGE_WRITE_FLAG", source)

    def test_no_second_ssot_for_standard_erpnext_masters(self) -> None:
        for folder in (
            "ferum_customer",
            "ferum_supplier",
            "ferum_company",
            "ferum_address",
            "ferum_contact",
            "ferum_warehouse",
            "ferum_project",
            "ferum_task",
            "ferum_issue",
            "ferum_asset",
            "ferum_workflow",
            "ferum_communication",
        ):
            with self.subTest(folder=folder):
                self.assertFalse((DOCTYPE_ROOT / folder).exists())


if __name__ == "__main__":
    unittest.main()
