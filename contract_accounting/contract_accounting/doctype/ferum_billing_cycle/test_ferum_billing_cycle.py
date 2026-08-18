"""Bench runtime acceptance tests for CA-13 recurring period closing."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from contract_accounting.api.billing import (
    create_billing_output,
    issue_billing_output,
    register_billing_artifact,
    supersede_billing_output,
)
from contract_accounting.api.billing_cycles import (
    complete_billing_cycle,
    create_billing_cycle,
    get_billing_cycle_projection,
    resolve_billing_cycles_for_source,
)
from contract_accounting.api.contract_360 import get_contract_360
from contract_accounting.api.lifecycle import change_status
from contract_accounting.api.processes import (
    add_process_evidence,
    complete_project_stage,
    evaluate_stage_gate,
    transition_process_step,
    validate_process_evidence,
)
from contract_accounting.contract_accounting.doctype.ferum_billing_output import (
    test_ferum_billing_output as billing_output_fixture,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
    _make_project,
)
from contract_accounting.setup.billing_cycle_template import (
    STEPS,
    ensure_reference_billing_cycle_template,
)


class TestFerumBillingCycle(FrappeTestCase):
    _make_obligation = billing_output_fixture.TestFerumBillingOutput._make_obligation
    _make_accepted_visit = (
        billing_output_fixture.TestFerumBillingOutput._make_accepted_visit
    )
    _make_submitted_invoice = (
        billing_output_fixture.TestFerumBillingOutput._make_submitted_invoice
    )
    _save_file = staticmethod(billing_output_fixture.TestFerumBillingOutput._save_file)

    def setUp(self) -> None:
        super().setUp()
        self._previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.project = _make_project()
        self.project.project_manager = "Administrator"
        self.project.save(ignore_permissions=True)
        for legal_status in (
            "On Approval",
            "Approved",
            "Signing",
            "Signed",
            "In Force",
        ):
            change_status(self.project.name, target_legal_status=legal_status)
        change_status(self.project.name, target_execution_status="Launching")
        change_status(self.project.name, target_execution_status="Active")
        self.service_object = frappe.get_doc(
            {
                "doctype": "Ferum Service Object",
                "object_name": f"CA-13 Object {uuid4().hex[:10]}",
                "customer": self.project.customer,
                "address": "CA-13 runtime address",
            }
        ).insert(ignore_permissions=True)
        self.system = frappe.get_doc(
            {
                "doctype": "Ferum Object System",
                "service_object": self.service_object.name,
                "system_type": "APS",
                "system_name": f"CA-13 APS {uuid4().hex[:10]}",
                "equipment_count": 1,
            }
        ).insert(ignore_permissions=True)
        self.project_object = frappe.get_doc(
            {
                "doctype": "Ferum Project Object",
                "service_project": self.project.name,
                "service_object": self.service_object.name,
                "effective_from": getdate(),
            }
        ).insert(ignore_permissions=True)
        self.obligation = self._make_obligation()
        self.visit = self._make_accepted_visit()
        self.invoice = self._make_submitted_invoice()

    def tearDown(self) -> None:
        frappe.set_user(self._previous_user)
        super().tearDown()

    def test_reference_cycle_projection_and_correction_keep_exact_trace(self) -> None:
        first_template = ensure_reference_billing_cycle_template()
        self.assertEqual(first_template, ensure_reference_billing_cycle_template())
        template = frappe.get_doc("Ferum Process Template", first_template)
        self.assertEqual(
            (template.code, template.status), ("FERUM-BILLING-CYCLE", "Published")
        )
        stages = frappe.get_all(
            "Ferum Stage Template",
            filters={"process_template": template.name},
            pluck="name",
        )
        self.assertEqual(len(stages), 1)
        self.assertEqual(
            frappe.get_all(
                "Ferum Step Template",
                filters={"stage_template": stages[0]},
                pluck="step_code",
                order_by="sequence asc",
            ),
            [row[0] for row in STEPS],
        )

        result = self._create_cycle()
        repeated = self._create_cycle()
        self.assertTrue(result["created"])
        self.assertFalse(repeated["created"])
        self.assertEqual(result["billing_cycle"], repeated["billing_cycle"])
        self.assertEqual(result["work"]["expected_count"], 1)
        self.assertEqual(result["work"]["accepted_count"], 1)
        self.assertEqual(result["work"]["unbilled_count"], 1)
        card = get_contract_360(
            self.project.name,
            as_of=str(getdate() + timedelta(days=60)),
        )
        self.assertIn(
            "Overdue Billing Cycle",
            {row["rule"] for row in card["exceptions"]},
        )

        output = self._create_output(result["billing_cycle"])["billing_output"]
        final_file = self._save_file("Ferum Billing Output", output, "final.txt")
        register_billing_artifact(
            output,
            "Generated",
            final_file.name,
            "Final generated",
            generation_mode="Final",
        )
        issue_billing_output(output, f"ACT-{uuid4().hex[:8]}", "Issued")
        correction = supersede_billing_output(output, "Correct period package")
        old = frappe.get_doc("Ferum Billing Output", output)
        new = frappe.get_doc("Ferum Billing Output", correction["correction_output"])
        self.assertEqual(old.billing_cycle, result["billing_cycle"])
        self.assertEqual(new.billing_cycle, result["billing_cycle"])
        reverse = resolve_billing_cycles_for_source(
            "Ferum Maintenance Visit", self.visit.name
        )
        self.assertEqual(reverse["billing_cycles"], [result["billing_cycle"]])
        trace = get_billing_cycle_projection(result["billing_cycle"])
        self.assertEqual(trace["documents"]["output_count"], 2)
        self.assertEqual(trace["work"]["unbilled_count"], 0)

    def test_gate_requires_signed_output_and_standard_payment(self) -> None:
        cycle = self._create_cycle()["billing_cycle"]
        output = self._create_output(cycle)["billing_output"]
        final_file = self._save_file("Ferum Billing Output", output, "final.txt")
        generated = register_billing_artifact(
            output,
            "Generated",
            final_file.name,
            "Final generated",
            generation_mode="Final",
        )
        issue_billing_output(output, f"ACT-{uuid4().hex[:8]}", "Issued")
        generated_artifact = frappe.get_doc(
            "Ferum Billing Artifact", generated["artifact"]
        )
        signed_file = self._save_file("Ferum Billing Output", output, "signed.txt")
        signed = register_billing_artifact(
            output,
            "Signed Scan",
            signed_file.name,
            "Customer signed",
        )
        signed_artifact = frappe.get_doc("Ferum Billing Artifact", signed["artifact"])
        payment = self._make_payment()
        self.invoice.reload()
        self.assertEqual(float(self.invoice.outstanding_amount), 0)

        cycle_doc = frappe.get_doc("Ferum Billing Cycle", cycle)
        steps = frappe.get_all(
            "Ferum Project Process Step",
            filters={"project_process": cycle_doc.project_process},
            fields=["name", "template_step_code", "status"],
            order_by="creation asc, name asc",
        )
        by_code = {row.template_step_code: row for row in steps}
        sources = {
            "ACT_PREPARED": (
                "Document",
                "Ferum Project Document",
                generated_artifact.project_document,
            ),
            "INVOICE_PREPARED": ("ERP Document", "Sales Invoice", self.invoice.name),
            "DOCUMENTS_APPROVED": ("Approval", "User", "Administrator"),
            "DOCUMENTS_SENT": (
                "Outgoing Letter",
                "Ferum Project Document",
                signed_artifact.project_document,
            ),
            "CUSTOMER_RECEIPT": (
                "Incoming Letter",
                "Ferum Project Document",
                signed_artifact.project_document,
            ),
            "PAYMENT_RECEIVED": ("Payment", "Payment Entry", payment.name),
        }
        for code, _title, evidence_type, _step_type, _dependency in STEPS:
            row = by_code[code]
            if code == "UPD_OR_SF_PREPARED":
                transition_process_step(
                    row.name,
                    "Not Applicable",
                    not_applicable_reason="Act is the applicable closing document",
                )
                continue
            if row.status == "Planned":
                transition_process_step(row.name, "Ready")
            transition_process_step(row.name, "In Progress")
            if evidence_type == "Manual Confirmation":
                evidence = add_process_evidence(
                    row.name,
                    evidence_type,
                    snapshot={
                        "accepted_work": self.visit.name,
                        "period": str(getdate()),
                    },
                )
            else:
                typed, source_doctype, source_name = sources[code]
                self.assertEqual(typed, evidence_type)
                evidence = add_process_evidence(
                    row.name,
                    evidence_type,
                    source_doctype=source_doctype,
                    source_name=source_name,
                    snapshot={"billing_cycle": cycle},
                )
            validate_process_evidence(
                evidence["process_evidence"], "Validated", f"Validated {code}"
            )
            if code == "DOCUMENTS_APPROVED":
                transition_process_step(row.name, "Waiting Approval")
            transition_process_step(row.name, "Completed")

        stage = frappe.db.get_value(
            "Ferum Project Stage",
            {"project_process": cycle_doc.project_process},
            "name",
        )
        gate = evaluate_stage_gate(stage)
        self.assertEqual(gate["status"], "Passed")
        complete_project_stage(stage)
        completed = complete_billing_cycle(cycle)
        self.assertEqual(completed["status"], "Completed")
        self.assertTrue(completed["payment"]["all_invoices_paid"])
        self.assertTrue(completed["documents"]["all_active_outputs_signed"])
        payment_reverse = resolve_billing_cycles_for_source(
            "Payment Entry", payment.name
        )
        self.assertEqual(payment_reverse["billing_cycles"], [cycle])

        timeline = __import__(
            "contract_accounting.api.deadlines", fromlist=["get_deadline_timeline"]
        ).get_deadline_timeline(
            self.project.name,
            as_of=str(getdate() + timedelta(days=60)),
        )
        cycle_rows = [
            row
            for row in timeline["rows"]
            if row["source_doctype"] == "Ferum Billing Cycle"
        ]
        self.assertEqual(len(cycle_rows), 1)
        self.assertFalse(cycle_rows[0]["is_overdue"])

    def _create_cycle(self) -> dict:
        return create_billing_cycle(
            self.project.name,
            str(getdate()),
            str(getdate()),
            str(getdate() + timedelta(days=30)),
            f"ca13:{self.project.name}:{getdate().isoformat()}",
        )

    def _create_output(self, cycle: str) -> dict:
        return create_billing_output(
            self.project.name,
            self.invoice.name,
            "Act",
            str(getdate()),
            str(getdate()),
            str(getdate()),
            [
                {
                    "source_doctype": "Ferum Maintenance Visit",
                    "source_name": self.visit.name,
                }
            ],
            billing_cycle=cycle,
        )

    def _make_payment(self):
        payment = get_payment_entry("Sales Invoice", self.invoice.name)
        payment.paid_amount = self.invoice.outstanding_amount
        payment.received_amount = self.invoice.outstanding_amount
        for reference in payment.references:
            reference.allocated_amount = self.invoice.outstanding_amount
        payment.reference_no = f"CA13-{uuid4().hex[:10]}"
        payment.reference_date = getdate()
        payment.insert(ignore_permissions=True)
        payment.submit()
        payment.reload()
        return payment


if __name__ == "__main__":
    import unittest

    unittest.main()
