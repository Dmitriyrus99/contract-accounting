"""Bench runtime acceptance tests for CA-07 finance read-model."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.tests.utils import FrappeTestCase

from contract_accounting.api.finance import (
    change_contractor_settlement_status,
    change_material_expense_status,
    create_contractor_settlement,
    create_material_expense,
    get_finance_reconciliation,
    get_finance_trace,
    get_portfolio_finance,
    recalculate_finance_summary,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
    _make_project,
)


class TestFerumProjectFinanceSummary(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.project = _make_project()
        self.project.contract_amount_with_vat = 120000
        self.project.contract_amount_without_vat = 120000
        self.project.save(ignore_permissions=True)
        self.supplier = self._make_supplier()
        self.item = self._make_item()
        self.warehouse = self._make_warehouse(self.project.company)
        self.sales_invoice = self._make_sales_invoice(120000)
        self.payment_entry = self._make_receive_payment(self.sales_invoice, 60000)
        self.other_purchase_invoice = self._make_purchase_invoice(6000)
        material = create_material_expense(
            self.project.name,
            str(date.today()),
            30000,
            amount_without_vat=30000,
            warehouse=self.warehouse,
            description="CA-07 material management cost",
        )
        self.material = material["material_expense"]
        change_material_expense_status(self.material, "Approved", "Verified material source")
        settlement = create_contractor_settlement(
            self.project.name,
            self.supplier,
            str(date.today()),
            str(date.today()),
            planned_amount=40000,
            approved_amount=40000,
        )
        self.settlement = settlement["contractor_settlement"]
        change_contractor_settlement_status(
            self.settlement, "Approved", "Commercial basis approved"
        )

    def tearDown(self) -> None:
        frappe.set_user(self._previous_user)
        super().tearDown()

    def test_rebuild_reconciles_standard_documents_and_exact_margin(self) -> None:
        result = recalculate_finance_summary(self.project.name)
        self.assertEqual(result["recognized_revenue_without_vat"], 120000)
        self.assertEqual(result["invoiced_with_vat"], 120000)
        self.assertEqual(result["paid_with_vat"], 60000)
        self.assertEqual(result["outstanding_with_vat"], 60000)
        self.assertEqual(result["overdue_ar_with_vat"], 60000)
        self.assertEqual(result["material_cost_without_vat"], 30000)
        self.assertEqual(result["contractor_cost_without_vat"], 40000)
        self.assertEqual(result["other_cost_without_vat"], 6000)
        self.assertEqual(result["total_cost_without_vat"], 76000)
        self.assertEqual(result["profit_without_vat"], 44000)
        self.assertAlmostEqual(result["profitability_percent"], 36.666667, places=5)

        trace = get_finance_trace(self.project.name)
        self.assertEqual(
            {row["name"] for row in trace["sales_invoices"]}, {self.sales_invoice.name}
        )
        self.assertEqual(
            {row["parent"] for row in trace["payment_entries"]}, {self.payment_entry.name}
        )
        self.assertEqual(
            trace["purchase_invoice_classification"][self.other_purchase_invoice.name][0],
            "Other",
        )
        self.assertTrue(get_finance_reconciliation(self.project.name)["is_reconciled"])

    def test_opening_invoice_changes_receivable_not_revenue(self) -> None:
        opening = self._make_sales_invoice(5000, is_opening=True, overdue=False)
        result = recalculate_finance_summary(self.project.name)
        self.assertEqual(result["recognized_revenue_without_vat"], 120000)
        self.assertEqual(result["invoiced_with_vat"], 120000)
        self.assertEqual(result["outstanding_with_vat"], 65000)
        opening.cancel()
        result = recalculate_finance_summary(self.project.name)
        self.assertEqual(result["outstanding_with_vat"], 60000)

    def test_purchase_invoice_has_exactly_one_active_cost_classification(self) -> None:
        invoice = self._make_purchase_invoice(10000)
        material = create_material_expense(
            self.project.name,
            str(date.today()),
            10000,
            amount_without_vat=10000,
            supplier=self.supplier,
            purchase_invoice=invoice.name,
        )["material_expense"]
        change_material_expense_status(material, "Approved", "Material classification")
        settlement = create_contractor_settlement(
            self.project.name,
            self.supplier,
            str(date.today()),
            str(date.today()),
            approved_amount=10000,
            purchase_invoice=invoice.name,
        )["contractor_settlement"]
        with self.assertRaises(frappe.ValidationError):
            change_contractor_settlement_status(settlement, "Approved", "Duplicate classification")
        self.assertEqual(
            frappe.db.get_value("Ferum Contractor Settlement", settlement, "status"), "Draft"
        )

        foreign = _make_project()
        foreign_invoice = self._make_purchase_invoice(5000, service_project=foreign.name)
        with self.assertRaises(frappe.ValidationError):
            create_material_expense(
                self.project.name,
                str(date.today()),
                5000,
                amount_without_vat=5000,
                purchase_invoice=foreign_invoice.name,
            )

    def test_material_expense_uses_standard_same_company_warehouse(self) -> None:
        self.assertEqual(
            frappe.db.get_value("Ferum Material Expense", self.material, "warehouse"),
            self.warehouse,
        )
        foreign = _make_project()
        foreign_warehouse = self._make_warehouse(foreign.company)
        with self.assertRaises(frappe.ValidationError):
            create_material_expense(
                self.project.name,
                str(date.today()),
                1000,
                amount_without_vat=1000,
                warehouse=foreign_warehouse,
            )

    def test_rebuild_is_idempotent_and_does_not_write_accounting_ledger(self) -> None:
        gl_before = frappe.db.count("GL Entry")
        invoice_count = frappe.db.count("Sales Invoice") + frappe.db.count("Purchase Invoice")
        first = recalculate_finance_summary(self.project.name)
        second = recalculate_finance_summary(self.project.name)
        self.assertEqual(first["source_fingerprint"], second["source_fingerprint"])
        self.assertEqual(frappe.db.count("GL Entry"), gl_before)
        self.assertEqual(
            frappe.db.count("Sales Invoice") + frappe.db.count("Purchase Invoice"), invoice_count
        )

        summary = frappe.get_doc("Ferum Project Finance Summary", first["summary"])
        summary.profit_without_vat = 1
        with self.assertRaises(frappe.PermissionError):
            summary.save(ignore_permissions=True)
        with self.assertRaises(frappe.PermissionError):
            summary.delete(ignore_permissions=True)

    def test_reconciliation_detects_stale_cache_and_portfolio_rolls_up_projects(self) -> None:
        result = recalculate_finance_summary(self.project.name)
        frappe.db.set_value(
            "Ferum Project Finance Summary",
            result["summary"],
            "profit_without_vat",
            1,
            update_modified=False,
        )
        reconciliation = get_finance_reconciliation(self.project.name)
        self.assertFalse(reconciliation["is_reconciled"])
        self.assertIn("profit_without_vat", reconciliation["differences"])
        recalculate_finance_summary(self.project.name)

        portfolio = get_portfolio_finance(company=self.project.company)
        self.assertEqual(portfolio["missing_summaries"], [])
        self.assertEqual(len(portfolio["groups"]), 1)
        group = portfolio["groups"][0]
        self.assertEqual(group["project_count"], 1)
        self.assertEqual(group["recognized_revenue_without_vat"], 120000)
        self.assertEqual(group["total_cost_without_vat"], 76000)
        self.assertEqual(group["profit_without_vat"], 44000)

    def test_cost_cancel_releases_purchase_invoice_and_settlement_is_guarded(self) -> None:
        invoice = self._make_purchase_invoice(10000)
        material = create_material_expense(
            self.project.name,
            str(date.today()),
            10000,
            amount_without_vat=10000,
            supplier=self.supplier,
            purchase_invoice=invoice.name,
        )["material_expense"]
        change_material_expense_status(material, "Approved", "Recognized")
        with self.assertRaises(frappe.ValidationError):
            invoice.cancel()
        invoice.reload()
        self.assertEqual(invoice.docstatus, 1)
        change_material_expense_status(material, "Cancelled", "Classification reversed")
        invoice.cancel()
        self.assertEqual(invoice.docstatus, 2)

        with self.assertRaises(frappe.ValidationError):
            change_contractor_settlement_status(self.settlement, "Settled", "No payment yet")
        self.assertEqual(
            frappe.db.get_value("Ferum Contractor Settlement", self.settlement, "status"),
            "Approved",
        )
        change_contractor_settlement_status(self.settlement, "Cancelled", "Commercial basis void")
        result = recalculate_finance_summary(self.project.name)
        self.assertEqual(result["contractor_cost_without_vat"], 0)

    def _make_sales_invoice(self, amount: float, *, is_opening: bool = False, overdue: bool = True):
        account_filters = (
            {"company": self.project.company, "account_type": "Temporary", "is_group": 0}
            if is_opening
            else {"company": self.project.company, "root_type": "Income", "is_group": 0}
        )
        income_account = frappe.db.get_value("Account", account_filters, "name")
        cost_center = frappe.db.get_value(
            "Cost Center", {"company": self.project.company, "is_group": 0}, "name"
        )
        posting_date = date.today() - timedelta(days=2) if overdue else date.today()
        due_date = (
            date.today() - timedelta(days=1) if overdue else date.today() + timedelta(days=30)
        )
        doc = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "company": self.project.company,
                "customer": self.project.customer,
                "set_posting_time": 1,
                "posting_date": posting_date,
                "due_date": due_date,
                "is_opening": "Yes" if is_opening else "No",
                "currency": self.project.currency,
                "conversion_rate": 1,
                "ferum_service_project": self.project.name,
                "items": [
                    {
                        "item_code": self.item,
                        "qty": 1,
                        "rate": amount,
                        "income_account": income_account,
                        "cost_center": cost_center,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        doc.submit()
        return doc

    def _make_purchase_invoice(self, amount: float, *, service_project: str | None = None):
        project_name = service_project or self.project.name
        company = frappe.db.get_value("Ferum Service Project", project_name, "company")
        expense_account = frappe.db.get_value(
            "Account", {"company": company, "root_type": "Expense", "is_group": 0}, "name"
        )
        cost_center = frappe.db.get_value(
            "Cost Center", {"company": company, "is_group": 0}, "name"
        )
        payable = frappe.db.get_value(
            "Account", {"company": company, "account_type": "Payable", "is_group": 0}, "name"
        )
        doc = frappe.get_doc(
            {
                "doctype": "Purchase Invoice",
                "company": company,
                "supplier": self.supplier,
                "posting_date": date.today(),
                "currency": "RUB",
                "conversion_rate": 1,
                "credit_to": payable,
                "ferum_service_project": project_name,
                "items": [
                    {
                        "item_code": self.item,
                        "qty": 1,
                        "rate": amount,
                        "expense_account": expense_account,
                        "cost_center": cost_center,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        doc.submit()
        return doc

    @staticmethod
    def _make_receive_payment(invoice, amount: float):
        payment = get_payment_entry("Sales Invoice", invoice.name)
        payment.paid_amount = amount
        payment.received_amount = amount
        for reference in payment.references:
            reference.allocated_amount = amount
        payment.reference_no = f"CA07-{uuid4().hex[:10]}"
        payment.reference_date = date.today()
        payment.insert(ignore_permissions=True)
        payment.submit()
        payment.reload()
        return payment

    @staticmethod
    def _make_supplier() -> str:
        name = f"CA-07 Supplier {uuid4().hex[:10]}"
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
    def _make_item() -> str:
        item_code = f"CA07-{uuid4().hex[:10]}"
        return (
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": item_code,
                    "item_name": item_code,
                    "item_group": "All Item Groups",
                    "stock_uom": "Nos",
                    "is_stock_item": 0,
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    @staticmethod
    def _make_warehouse(company: str) -> str:
        parent = frappe.db.get_value(
            "Warehouse",
            {"company": company, "is_group": 1, "parent_warehouse": ["is", "not set"]},
            "name",
        )
        if not parent:
            parent = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1}, "name")
        return (
            frappe.get_doc(
                {
                    "doctype": "Warehouse",
                    "warehouse_name": f"CA07 {uuid4().hex[:10]}",
                    "company": company,
                    "parent_warehouse": parent,
                    "is_group": 0,
                }
            )
            .insert(ignore_permissions=True)
            .name
        )
