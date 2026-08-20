from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = ROOT / "contract_accounting" / "contract_accounting" / "doctype"


def schema(folder: str) -> dict[str, object]:
    return json.loads((DOCTYPE_ROOT / folder / f"{folder}.json").read_text(encoding="utf-8"))


def fields(document: dict[str, object]) -> dict[str, dict[str, object]]:
    return {row["fieldname"]: row for row in document["fields"]}


class BillingCycleSchemaTests(unittest.TestCase):
    def test_ca13_has_one_parent_cycle_and_no_accounting_ledger(self) -> None:
        cycle = schema("ferum_billing_cycle")
        self.assertEqual(cycle["name"], "Ferum Billing Cycle")
        self.assertNotEqual(cycle.get("istable"), 1)
        by_name = fields(cycle)
        self.assertEqual(by_name["service_project"]["options"], "Ferum Service Project")
        self.assertEqual(by_name["project_process"]["options"], "Ferum Project Process")
        self.assertEqual(
            by_name["status"]["options"].splitlines(),
            ["Open", "Completed", "Cancelled"],
        )
        self.assertFalse({"debit", "credit", "gl_entry", "paid_amount"}.intersection(by_name))

    def test_output_links_cycle_without_replacing_basis_or_invoice(self) -> None:
        output = fields(schema("ferum_billing_output"))
        self.assertEqual(output["billing_cycle"]["options"], "Ferum Billing Cycle")
        self.assertEqual(output["basis_items"]["options"], "Ferum Billing Basis Item")
        self.assertEqual(output["sales_invoice"]["options"], "Sales Invoice")

    def test_billing_runtime_fixture_uses_site_references_and_monotonic_dates(self) -> None:
        source = (DOCTYPE_ROOT / "ferum_billing_output" / "test_ferum_billing_output.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("from frappe.utils import getdate", source)
        self.assertIn("self.billing_date = getdate(self.obligation.effective_from)", source)
        self.assertIn('"effective_from": getdate(self.project_object.effective_from)', source)
        self.assertIn("work_date = getdate(self.obligation.effective_from)", source)
        self.assertIn("str(self.billing_date)", source)
        self.assertIn('"selling_price_list": "Standard Selling"', source)
        self.assertIn('"price_list_currency": self.project.currency', source)
        self.assertIn('"plc_conversion_rate": 1', source)

    def test_reference_graph_has_exact_nine_milestones(self) -> None:
        source = (ROOT / "contract_accounting" / "setup" / "billing_cycle_template.py").read_text(
            encoding="utf-8"
        )
        for code in (
            "WORK_COMPLETED",
            "EXECUTION_CONFIRMED",
            "ACT_PREPARED",
            "INVOICE_PREPARED",
            "UPD_OR_SF_PREPARED",
            "DOCUMENTS_APPROVED",
            "DOCUMENTS_SENT",
            "CUSTOMER_RECEIPT",
            "PAYMENT_RECEIVED",
        ):
            self.assertIn(f'"{code}"', source)
        self.assertIn('TEMPLATE_CODE: Final[str] = "FERUM-BILLING-CYCLE"', source)
        self.assertIn('"process_type": "Period Closing"', source)
        self.assertIn("never create cycle history", source)

    def test_api_has_projection_reverse_trace_and_legal_backfill_guard(self) -> None:
        source = (ROOT / "contract_accounting" / "api" / "billing_cycles.py").read_text(
            encoding="utf-8"
        )
        for command in (
            "create_billing_cycle",
            "get_billing_cycle_projection",
            "complete_billing_cycle",
            "get_billing_cycle_backfill_assessment",
            "backfill_billing_cycle_group",
            "resolve_billing_cycles_for_source",
        ):
            self.assertIn(f"def {command}(", source)
        self.assertIn("CONFIRM_UNAMBIGUOUS_BILLING_CYCLE_BACKFILL", source)
        self.assertIn("Issued/Signed/terminal Output", source)

    def test_cycle_deadline_is_in_timeline_and_control_center(self) -> None:
        deadlines = (ROOT / "contract_accounting" / "api" / "deadlines.py").read_text(
            encoding="utf-8"
        )
        control = (ROOT / "contract_accounting" / "api" / "contract_360.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('kind="Billing Cycle Due"', deadlines)
        self.assertIn('"Overdue Billing Cycle"', control)


if __name__ == "__main__":
    unittest.main()
