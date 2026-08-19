"""Bench runtime acceptance tests for CA-06 execution-to-billing traceability."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from contract_accounting.api.billing import (
    cancel_billing_output,
    create_billing_output,
    get_billing_trace,
    get_unbilled_accepted_work,
    issue_billing_output,
    register_billing_artifact,
    supersede_billing_output,
)
from contract_accounting.api.execution import (
    accept_visit,
    change_visit_status,
    generate_planned_visits,
    review_visit,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
    _make_address,
    _make_project,
)


class TestFerumBillingOutput(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.project = _make_project()
        self.service_object = frappe.get_doc(
            {
                "doctype": "Ferum Service Object",
                "object_name": f"CA-06 Object {uuid4().hex[:10]}",
                "customer": self.project.customer,
                "address": _make_address(self.project.customer, "CA-06 runtime address"),
            }
        ).insert(ignore_permissions=True)
        self.system = frappe.get_doc(
            {
                "doctype": "Ferum Object System",
                "service_object": self.service_object.name,
                "system_type": "APS",
                "system_name": f"CA-06 APS {uuid4().hex[:10]}",
                "equipment_count": 1,
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
        self.obligation = self._make_obligation()
        self.visit = self._make_accepted_visit()
        self.invoice = self._make_submitted_invoice()

    def tearDown(self) -> None:
        frappe.set_user(self._previous_user)
        super().tearDown()

    def test_selector_and_basis_snapshot_claim_exact_accepted_sources(self) -> None:
        request = self._make_resolved_request()
        candidates = get_unbilled_accepted_work(
            self.project.name, str(date.today()), str(date.today())
        )
        candidate_keys = {(row["source_doctype"], row["source_name"]) for row in candidates}
        self.assertIn(("Ferum Maintenance Visit", self.visit.name), candidate_keys)
        self.assertIn(("Ferum Service Request", request.name), candidate_keys)

        result = self._create_output(
            [
                {"source_doctype": "Ferum Maintenance Visit", "source_name": self.visit.name},
                {"source_doctype": "Ferum Service Request", "source_name": request.name},
            ]
        )
        output = frappe.get_doc("Ferum Billing Output", result["billing_output"])
        self.assertEqual(len(output.basis_items), 2)
        self.assertEqual(output.sales_invoice, self.invoice.name)
        self.assertEqual(output.invoice_grand_total_snapshot, self.invoice.grand_total)
        self.assertTrue(output.basis_hash)
        self.assertTrue(all(row.source_hash for row in output.basis_items))
        remaining = get_unbilled_accepted_work(
            self.project.name, str(date.today()), str(date.today())
        )
        remaining_keys = {(row["source_doctype"], row["source_name"]) for row in remaining}
        self.assertNotIn(("Ferum Maintenance Visit", self.visit.name), remaining_keys)
        self.assertNotIn(("Ferum Service Request", request.name), remaining_keys)
        with self.assertRaises(frappe.UniqueValidationError):
            self._create_output()

    def test_final_and_signed_artifacts_project_to_active_document_registry(self) -> None:
        output_name = self._create_output()["billing_output"]
        final_file = self._save_file("Ferum Billing Output", output_name, "final.txt")
        generated = register_billing_artifact(
            output_name,
            "Generated",
            final_file.name,
            "Final generated",
            generation_mode="Final",
        )
        self.assertEqual(generated["status"], "Generated")
        issued = issue_billing_output(output_name, f"ACT-{uuid4().hex[:8]}", "Act issued")
        self.assertEqual(issued["status"], "Issued")
        generated_artifact = frappe.get_doc("Ferum Billing Artifact", generated["artifact"])
        self.assertTrue(generated_artifact.project_document)
        generated_document = frappe.get_doc(
            "Ferum Project Document", generated_artifact.project_document
        )
        self.assertEqual(generated_document.status, "Active")
        self.assertEqual(generated_document.digital_copy_status, "Verified")
        self.assertEqual(generated_document.file, final_file.name)

        signed_file = self._save_file("Ferum Billing Output", output_name, "signed.txt")
        signed = register_billing_artifact(
            output_name,
            "Signed Scan",
            signed_file.name,
            "Customer signed",
        )
        self.assertEqual(signed["status"], "Signed")
        signed_artifact = frappe.get_doc("Ferum Billing Artifact", signed["artifact"])
        signed_document = frappe.get_doc("Ferum Project Document", signed_artifact.project_document)
        self.assertEqual(signed_document.digital_copy_status, "Signed")
        self.assertEqual(signed_document.billing_reference_name, signed_artifact.name)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc("File", signed_file.name).delete(ignore_permissions=True)
        trace = get_billing_trace(output_name)
        self.assertEqual(
            [event["event_type"] for event in trace["events"]],
            ["Created", "Generated", "Issued", "Signed"],
        )

    def test_issue_and_direct_mutation_fail_closed(self) -> None:
        output_name = self._create_output()["billing_output"]
        with self.assertRaises(frappe.ValidationError):
            issue_billing_output(output_name, "ACT-NO-FILE", "Premature issue")
        output = frappe.get_doc("Ferum Billing Output", output_name)
        output.status = "Issued"
        with self.assertRaises(frappe.PermissionError):
            output.save(ignore_permissions=True)
        file_doc = self._save_file("Ferum Billing Output", output_name, "final.txt")
        register_billing_artifact(
            output_name,
            "Generated",
            file_doc.name,
            "Final generated",
            generation_mode="Final",
        )
        issue_billing_output(output_name, f"ACT-{uuid4().hex[:8]}", "Issued")
        output.reload()
        output.basis_items[0].source_hash = "tampered"
        with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
            output.save(ignore_permissions=True)
        event = frappe.get_last_doc("Ferum Billing Event", {"billing_output": output_name})
        event.reason = "tampered"
        with self.assertRaises(frappe.PermissionError):
            event.save(ignore_permissions=True)

    def test_output_does_not_write_ledger_and_guards_invoice_cancel(self) -> None:
        gl_before = frappe.db.count("GL Entry", {"voucher_no": self.invoice.name})
        output_name = self._create_output()["billing_output"]
        self.assertEqual(frappe.db.count("GL Entry", {"voucher_no": self.invoice.name}), gl_before)
        with self.assertRaises(frappe.ValidationError):
            self.invoice.cancel()
        cancelled = cancel_billing_output(output_name, "Invoice will be amended")
        self.assertEqual(cancelled["status"], "Cancelled")
        self.invoice.reload()
        self.invoice.cancel()
        self.assertEqual(self.invoice.docstatus, 2)
        candidates = get_unbilled_accepted_work(
            self.project.name, str(date.today()), str(date.today())
        )
        self.assertIn(self.visit.name, {row["source_name"] for row in candidates})

    def test_supersede_preserves_old_basis_and_claims_correction(self) -> None:
        output_name = self._issued_output()
        old = frappe.get_doc("Ferum Billing Output", output_name)
        old_hash = old.basis_hash
        result = supersede_billing_output(output_name, "Correct accepted work package")
        old.reload()
        new = frappe.get_doc("Ferum Billing Output", result["correction_output"])
        self.assertEqual(old.status, "Superseded")
        self.assertEqual(old.superseded_by, new.name)
        self.assertEqual(old.basis_hash, old_hash)
        self.assertEqual(old.basis_items[0].inclusion_state, "Reversed")
        self.assertFalse(old.basis_items[0].active_claim_key)
        self.assertEqual(new.status, "Draft")
        self.assertEqual(new.supersedes, old.name)
        self.assertEqual(new.basis_items[0].inclusion_state, "Included")
        self.assertTrue(new.basis_items[0].active_claim_key)
        self.assertEqual(old.basis_items[0].source_hash, new.basis_items[0].source_hash)
        candidates = get_unbilled_accepted_work(
            self.project.name, str(date.today()), str(date.today())
        )
        self.assertNotIn(self.visit.name, {row["source_name"] for row in candidates})

    def test_artifact_versions_are_current_without_overwriting_history(self) -> None:
        output_name = self._create_output()["billing_output"]
        first_file = self._save_file("Ferum Billing Output", output_name, "preview-1.txt")
        first = register_billing_artifact(
            output_name,
            "Generated",
            first_file.name,
            "First preview",
            generation_mode="Preview",
        )
        second_file = self._save_file("Ferum Billing Output", output_name, "preview-2.txt")
        second = register_billing_artifact(
            output_name,
            "Generated",
            second_file.name,
            "Second preview",
            generation_mode="Preview",
        )
        first_artifact = frappe.get_doc("Ferum Billing Artifact", first["artifact"])
        second_artifact = frappe.get_doc("Ferum Billing Artifact", second["artifact"])
        self.assertEqual((first_artifact.version, first_artifact.is_current), (1, 0))
        self.assertEqual((second_artifact.version, second_artifact.is_current), (2, 1))
        self.assertEqual(second_artifact.supersedes_artifact, first_artifact.name)
        with self.assertRaises(frappe.PermissionError):
            first_artifact.delete(ignore_permissions=True)

    def _create_output(self, refs=None):
        return create_billing_output(
            self.project.name,
            self.invoice.name,
            "Act",
            str(date.today()),
            str(date.today()),
            str(date.today()),
            refs
            or [
                {
                    "source_doctype": "Ferum Maintenance Visit",
                    "source_name": self.visit.name,
                }
            ],
        )

    def _issued_output(self) -> str:
        output_name = self._create_output()["billing_output"]
        file_doc = self._save_file("Ferum Billing Output", output_name, "final.txt")
        register_billing_artifact(
            output_name,
            "Generated",
            file_doc.name,
            "Final generated",
            generation_mode="Final",
        )
        issue_billing_output(output_name, f"ACT-{uuid4().hex[:8]}", "Issued")
        return output_name

    def _make_obligation(self):
        requirement = frappe.get_doc(
            {
                "doctype": "Ferum Contract Requirement",
                "service_project": self.project.name,
                "requirement_type": "Work",
                "requirement_source": "Contract",
                "source_document_reference": f"Contract/{uuid4().hex[:10]}",
                "source_clause": "6.1",
                "description": "Monthly billable maintenance",
                "applicability": "Applicable",
                "routing_decision": "Recurring Obligation",
            }
        ).insert(ignore_permissions=True)
        for status in ("Assessed", "Approved"):
            requirement.assessment_status = status
            requirement.save(ignore_permissions=True)
        obligation = frappe.get_doc(
            {
                "doctype": "Ferum Contract Obligation",
                "service_project": self.project.name,
                "requirement": requirement.name,
                "project_object": self.project_object.name,
                "object_system": self.system.name,
                "work_type": "Monthly APS maintenance",
                "obligation_type": "Maintenance",
                "recurrence": [
                    {
                        "frequency": "Monthly",
                        "interval": 1,
                        "period_anchor": "Contract Start",
                        "window_before_days": 0,
                        "window_after_days": 0,
                        "due_offset_days": 0,
                        "calendar_type": "Calendar Days",
                        "generation_horizon_days": 365,
                    }
                ],
                "deadline_rule": {},
                "quantity": 1,
                "uom": "Nos",
                "currency": self.project.currency,
                "price_component": 1200,
                "effective_from": date.today(),
            }
        ).insert(ignore_permissions=True)
        obligation.status = "Active"
        obligation.save(ignore_permissions=True)
        return obligation

    def _make_accepted_visit(self):
        result = generate_planned_visits(self.obligation.name, str(date.today()), str(date.today()))
        visit_name = result["items"][0]["visit"]
        started_at = datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=9)
        change_visit_status(visit_name, "In Progress", actual_start=str(started_at))
        visit = frappe.get_doc("Ferum Maintenance Visit", visit_name)
        visit.work_result = "Completed"
        visit.visit_report = "Monthly service completed"
        visit.save(ignore_permissions=True)
        change_visit_status(
            visit_name, "Completed", actual_end=str(started_at + timedelta(hours=2))
        )
        file_doc = self._save_file("Ferum Maintenance Visit", visit_name, "visit.txt")
        visit.reload()
        visit.append(
            "checklist",
            {
                "item_code": "APS-01",
                "description": "Inspect panel",
                "is_completed": 1,
                "result": "Pass",
            },
        )
        visit.append(
            "evidence",
            {
                "evidence_type": "Report",
                "file": file_doc.name,
                "captured_at": started_at + timedelta(hours=1),
                "captured_by": "Administrator",
            },
        )
        visit.save(ignore_permissions=True)
        review_visit(visit_name, "Approved")
        accept_visit(visit_name, "Accepted")
        return frappe.get_doc("Ferum Maintenance Visit", visit_name)

    def _make_resolved_request(self):
        request = frappe.get_doc(
            {
                "doctype": "Ferum Service Request",
                "service_project": self.project.name,
                "project_object": self.project_object.name,
                "object_system": self.system.name,
                "subject": "Billing output request fixture",
                "description": "Resolved request used as an exact billing basis source.",
                "source_type": "Customer",
                "request_type": "Repair",
                "requested_at": datetime.now(),
                "contract_obligation": self.obligation.name,
            }
        ).insert(ignore_permissions=True)
        request.status = "In Progress"
        request.actual_start = datetime.now()
        request.save(ignore_permissions=True)
        file_doc = self._save_file("Ferum Service Request", request.name, "request.txt")
        request.append(
            "evidence",
            {
                "evidence_type": "Report",
                "file": file_doc.name,
                "captured_at": datetime.now(),
                "captured_by": "Administrator",
            },
        )
        request.actual_end = datetime.now()
        request.work_result = "Completed"
        request.resolution = "Repair completed"
        request.status = "Resolved"
        request.save(ignore_permissions=True)
        return request

    def _make_submitted_invoice(self):
        item_code = f"CA06-{uuid4().hex[:10]}"
        frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "item_group": "All Item Groups",
                "stock_uom": "Nos",
                "is_stock_item": 0,
            }
        ).insert(ignore_permissions=True)
        income_account = frappe.db.get_value(
            "Account",
            {"company": self.project.company, "root_type": "Income", "is_group": 0},
            "name",
        )
        cost_center = frappe.db.get_value(
            "Cost Center",
            {"company": self.project.company, "is_group": 0},
            "name",
        )
        invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "company": self.project.company,
                "customer": self.project.customer,
                "posting_date": date.today(),
                "due_date": date.today() + timedelta(days=30),
                "currency": self.project.currency,
                "conversion_rate": 1,
                "ferum_service_project": self.project.name,
                "items": [
                    {
                        "item_code": item_code,
                        "qty": 1,
                        "rate": 1200,
                        "income_account": income_account,
                        "cost_center": cost_center,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        invoice.submit()
        return invoice

    @staticmethod
    def _save_file(doctype: str, name: str, suffix: str):
        filename = f"ca06-{uuid4().hex[:10]}-{suffix}"
        return save_file(
            filename,
            f"CA-06 immutable evidence: {filename}".encode(),
            doctype,
            name,
            is_private=1,
        )
