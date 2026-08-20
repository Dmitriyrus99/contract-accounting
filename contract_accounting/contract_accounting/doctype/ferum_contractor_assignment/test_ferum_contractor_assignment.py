"""Bench runtime acceptance tests for CA-08 assignment and privacy boundary."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from contract_accounting.api.contractors import (
    change_contractor_assignment_status,
    change_contractor_commercial_terms_status,
    create_contractor_assignment,
    create_contractor_commercial_terms,
    get_contractor_assignment_trace,
)
from contract_accounting.api.finance import (
    change_contractor_settlement_status,
    change_material_expense_status,
    create_contractor_settlement,
    create_material_expense,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
    _make_address,
    _make_project,
)


class TestFerumContractorAssignment(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.project = _make_project()
        self.service_object = frappe.get_doc(
            {
                "doctype": "Ferum Service Object",
                "object_name": f"CA-08 Object {uuid4().hex[:10]}",
                "customer": self.project.customer,
                "address": _make_address(self.project.customer, "CA-08 runtime address"),
            }
        ).insert(ignore_permissions=True)
        self.project_object = frappe.get_doc(
            {
                "doctype": "Ferum Project Object",
                "service_project": self.project.name,
                "service_object": self.service_object.name,
                "effective_from": date.today(),
            }
        ).insert(ignore_permissions=True)
        self.system = frappe.get_doc(
            {
                "doctype": "Ferum Object System",
                "service_object": self.service_object.name,
                "system_type": "APS",
                "system_name": f"CA-08 APS {uuid4().hex[:10]}",
                "equipment_count": 1,
            }
        ).insert(ignore_permissions=True)
        self.supplier = self._make_supplier()
        self.other_supplier = self._make_supplier()
        self.assignment = self._make_assignment(self.supplier)
        change_contractor_assignment_status(self.assignment, "Approved", "Approved for CA-08 test")

    def tearDown(self) -> None:
        frappe.set_user(self._previous_user)
        super().tearDown()

    def test_assignment_is_responsibility_only_and_overlap_fails_closed(self) -> None:
        doc = frappe.get_doc("Ferum Contractor Assignment", self.assignment)
        self.assertEqual(doc.execution_mode, "Contractor")
        self.assertEqual(doc.supplier, self.supplier)
        self.assertEqual(doc.project_object, self.project_object.name)
        self.assertEqual(doc.object_system, self.system.name)
        privacy_enabled = bool(frappe.db.get_single_value("Ferum Privacy Settings", "enabled"))
        self.assertEqual(
            doc.credentials_readiness,
            "Not Required" if privacy_enabled else "Policy Inactive",
        )
        self.assertFalse(doc.commercial_terms)

        overlap = self._make_assignment(self.supplier)
        with self.assertRaises(frappe.ValidationError):
            change_contractor_assignment_status(overlap, "Approved", "Must overlap")
        self.assertEqual(
            frappe.db.get_value("Ferum Contractor Assignment", overlap, "status"), "Draft"
        )

        other = self._make_assignment(self.other_supplier)
        change_contractor_assignment_status(other, "Approved", "Different supplier is valid")
        self.assertEqual(
            frappe.db.get_value("Ferum Contractor Assignment", other, "status"), "Approved"
        )

        doc.responsibility = "Direct mutation"
        with self.assertRaises(frappe.PermissionError):
            doc.save(ignore_permissions=True)

    def test_scope_mismatch_and_executor_xor_are_rejected(self) -> None:
        with self.assertRaises(frappe.ValidationError):
            create_contractor_assignment(
                self.project.name,
                "Contractor",
                self.project_object.name,
                "APS maintenance",
                "Invalid executor",
                str(date.today()),
            )

        foreign_object = frappe.get_doc(
            {
                "doctype": "Ferum Service Object",
                "object_name": f"CA-08 Foreign {uuid4().hex[:10]}",
                "customer": self.project.customer,
                "address": _make_address(self.project.customer, "CA-08 foreign address"),
            }
        ).insert(ignore_permissions=True)
        foreign_system = frappe.get_doc(
            {
                "doctype": "Ferum Object System",
                "service_object": foreign_object.name,
                "system_type": "CCTV",
                "system_name": f"CA-08 Foreign System {uuid4().hex[:8]}",
            }
        ).insert(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            self._make_assignment(self.other_supplier, object_system=foreign_system.name)

    def test_commercial_terms_link_later_and_margin_is_separate(self) -> None:
        terms = create_contractor_commercial_terms(
            self.assignment,
            str(date.today()),
            100000,
            60000,
        )["commercial_terms"]
        self.assertFalse(
            frappe.db.get_value("Ferum Contractor Assignment", self.assignment, "commercial_terms")
        )
        change_contractor_commercial_terms_status(terms, "Approved", "Commercial approval")
        row = frappe.db.get_value(
            "Ferum Contractor Commercial Terms",
            terms,
            ("margin_amount", "margin_percent", "status"),
            as_dict=True,
        )
        self.assertEqual(row.margin_amount, 40000)
        self.assertEqual(row.margin_percent, 40)
        self.assertEqual(row.status, "Approved")
        self.assertEqual(
            frappe.db.get_value("Ferum Contractor Assignment", self.assignment, "commercial_terms"),
            terms,
        )
        trace = get_contractor_assignment_trace(self.assignment)
        self.assertEqual(trace["commercial_terms"]["margin_amount"], 40000)
        self.assertEqual(
            bool(trace["personnel_readiness"]["enabled"]),
            bool(frappe.db.get_single_value("Ferum Privacy Settings", "enabled")),
        )

        change_contractor_commercial_terms_status(terms, "Cancelled", "Commercial basis void")
        self.assertFalse(
            frappe.db.get_value("Ferum Contractor Assignment", self.assignment, "commercial_terms")
        )

    def test_settlement_and_material_keep_assignment_and_commercial_basis(self) -> None:
        terms = self._approved_terms()
        settlement = create_contractor_settlement(
            self.project.name,
            self.supplier,
            str(date.today()),
            str(date.today() + timedelta(days=30)),
            planned_amount=60000,
            approved_amount=60000,
            project_object=self.project_object.name,
            contractor_assignment=self.assignment,
            commercial_terms=terms,
        )["contractor_settlement"]
        change_contractor_settlement_status(settlement, "Approved", "Accepted contractor work")

        material = create_material_expense(
            self.project.name,
            str(date.today()),
            10000,
            amount_without_vat=10000,
            project_object=self.project_object.name,
            contractor_assignment=self.assignment,
            supplier=self.supplier,
            description="Contractor-provided material",
        )["material_expense"]
        change_material_expense_status(material, "Approved", "Material accepted")

        trace = get_contractor_assignment_trace(self.assignment)
        self.assertEqual({row["name"] for row in trace["settlements"]}, {settlement})
        self.assertEqual({row["name"] for row in trace["material_expenses"]}, {material})

    def test_worker_and_credential_direct_writes_are_blocked_by_privacy_gate(self) -> None:
        before_workers = frappe.db.count("Ferum Contractor Worker")
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc(
                {
                    "doctype": "Ferum Contractor Worker",
                    "supplier": self.supplier,
                    "worker_external_id": uuid4().hex,
                    "display_name": "Blocked Worker",
                }
            ).insert(ignore_permissions=True)
        self.assertEqual(frappe.db.count("Ferum Contractor Worker"), before_workers)

        before_credentials = frappe.db.count("Ferum Personnel Credential")
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc(
                {
                    "doctype": "Ferum Personnel Credential",
                    "holder_type": "Customer",
                    "holder": self.project.customer,
                    "credential_type": "Other",
                    "credential_number": uuid4().hex,
                }
            ).insert(ignore_permissions=True)
        self.assertEqual(frappe.db.count("Ferum Personnel Credential"), before_credentials)

    def test_supplier_user_permission_isolates_contractor_assignments(self) -> None:
        other = self._make_assignment(self.other_supplier)
        change_contractor_assignment_status(other, "Approved", "Other supplier assignment")
        user = self._make_contractor_user(self.supplier)
        frappe.set_user(user)
        rows = frappe.get_list(
            "Ferum Contractor Assignment",
            fields=["name", "supplier"],
            order_by="name asc",
        )
        self.assertEqual({row.name for row in rows}, {self.assignment})
        self.assertEqual({row.supplier for row in rows}, {self.supplier})
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc("Ferum Contractor Assignment", other).check_permission("read")

    def _make_assignment(self, supplier: str, *, object_system: str | None = None) -> str:
        return create_contractor_assignment(
            self.project.name,
            "Contractor",
            self.project_object.name,
            "APS maintenance",
            "Execute scoped preventive maintenance",
            str(date.today()),
            effective_to=str(date.today() + timedelta(days=90)),
            supplier=supplier,
            object_system=object_system or self.system.name,
        )["contractor_assignment"]

    def _approved_terms(self) -> str:
        terms = create_contractor_commercial_terms(
            self.assignment,
            str(date.today()),
            100000,
            60000,
        )["commercial_terms"]
        change_contractor_commercial_terms_status(terms, "Approved", "Commercial approval")
        return terms

    @staticmethod
    def _make_supplier() -> str:
        name = f"CA-08 Supplier {uuid4().hex[:10]}"
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

    @staticmethod
    def _make_contractor_user(supplier: str) -> str:
        email = f"ca08-{uuid4().hex[:12]}@example.test"
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "CA-08 Contractor",
                "send_welcome_email": 0,
                "roles": [{"role": "Подрядчик"}],
            }
        ).insert(ignore_permissions=True)
        frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": user.name,
                "allow": "Supplier",
                "for_value": supplier,
            }
        ).insert(ignore_permissions=True)
        return user.name
