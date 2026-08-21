"""Bench acceptance for DP-05 Company/Contract selection and primary sources."""

from __future__ import annotations

import json
from datetime import date
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from contract_accounting.api.calendars import (
    assign_calendar,
    create_customer_response_deadline,
    set_signature_deadline,
)
from contract_accounting.api.deadlines import get_deadline_timeline
from contract_accounting.infrastructure.calendar_registry import (
    calendar_day_counts,
    calendar_from_document,
)


class TestProductionCalendar(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.company, self.customer, self.project, self.contact, self.document = _make_context()
        self.sent_evidence = save_file(
            f"ca17-{uuid4().hex[:8]}-sent.txt",
            b"customer request delivery evidence",
            "Ferum Project Document",
            self.document.name,
            is_private=1,
        )

    def tearDown(self) -> None:
        frappe.set_user(self._previous_user)
        super().tearDown()

    def test_versioned_fixture_hash_and_exact_counts_are_runtime_verified(self) -> None:
        revision = frappe.get_doc("Ferum Calendar Revision", "RU-5D-2026-v1")
        calendar = calendar_from_document(revision)
        self.assertEqual(calendar_day_counts(calendar), (247, 118, 4))
        self.assertEqual(len(revision.calendar_hash), 64)
        self.assertEqual(calendar.calendar_hash, revision.calendar_hash)
        with self.assertRaises(frappe.PermissionError):
            revision.title = "silent mutation"
            revision.save(ignore_permissions=True)

    def test_company_calendar_signature_deadline_is_guarded_and_idempotent(self) -> None:
        assignment = self._assign_company()
        result = set_signature_deadline(
            project_document=self.document.name,
            triggered_at="2026-04-30 18:01:00",
            offset_days=0,
            offset_unit="Business Days",
            warning_days=3,
            escalation_days=1,
            reason="Contract signature control",
        )
        self.assertEqual(result["calendar_scope"], "Company")
        self.assertTrue(result["due_at"].startswith("2026-05-04T19:00:00"))
        document = frappe.get_doc("Ferum Project Document", self.document.name)
        calculation = frappe.get_doc(
            "Ferum Deadline Calculation", document.signature_deadline_calculation
        )
        snapshot = json.loads(calculation.calendar_snapshot_json)
        self.assertEqual(calculation.calendar_assignment, assignment["calendar_assignment"])
        self.assertEqual(snapshot["source"]["normalized_anchor_at"][:16], "2026-05-04T08:00")
        self.assertEqual(snapshot["algorithm_version"], "dp05-v1")

        repeated = set_signature_deadline(
            project_document=self.document.name,
            triggered_at="2026-04-30 18:01:00",
            offset_days=0,
            offset_unit="Business Days",
            warning_days=3,
            escalation_days=1,
            reason="Idempotent retry",
        )
        self.assertFalse(repeated["created"])
        document.signature_due_at = "2026-05-05 19:00:00"
        with self.assertRaises(frappe.PermissionError):
            document.save(ignore_permissions=True)

    def test_contract_override_recalculation_retains_old_snapshot(self) -> None:
        self._assign_company()
        initial = set_signature_deadline(
            project_document=self.document.name,
            triggered_at="2026-06-11 17:00:00",
            offset_days=1,
            offset_unit="Business Days",
            reason="Initial Company calculation",
        )
        old = frappe.get_doc("Ferum Deadline Calculation", initial["deadline_calculation"])
        old_snapshot = old.calendar_snapshot_json
        contract_assignment = assign_calendar(
            scope_type="Contract",
            company=self.company.name,
            service_project=self.project.name,
            calendar_revision="RU-5D-2026-v1",
            contract_basis="Contract clause 7.4 explicitly selects the production calendar",
            evidence_document=self.document.name,
            reason="Activate explicit contract precedence",
        )
        recalculated = set_signature_deadline(
            project_document=self.document.name,
            triggered_at="2026-06-11 17:00:00",
            offset_days=1,
            offset_unit="Business Days",
            reason="Authorized manual recalculation after Contract Calendar assignment",
            manual_recalculation=1,
        )
        self.assertEqual(recalculated["calendar_scope"], "Contract")
        new = frappe.get_doc("Ferum Deadline Calculation", recalculated["deadline_calculation"])
        self.assertEqual(new.supersedes, old.name)
        self.assertEqual(new.calendar_assignment, contract_assignment["calendar_assignment"])
        self.assertEqual(
            frappe.db.get_value(old.doctype, old.name, "calendar_snapshot_json"), old_snapshot
        )
        with self.assertRaises(frappe.PermissionError):
            old.reason = "rewrite history"
            old.save(ignore_permissions=True)

    def test_customer_response_is_structured_and_visible_in_timeline(self) -> None:
        self._assign_company()
        assign_calendar(
            scope_type="Contract",
            company=self.company.name,
            service_project=self.project.name,
            calendar_revision="RU-5D-2026-v1",
            contract_basis="Contract clause 7.4 explicitly selects the production calendar",
            evidence_document=self.document.name,
            reason="Contract calendar for customer response",
        )
        result = create_customer_response_deadline(
            service_project=self.project.name,
            source_doctype="Ferum Service Project",
            source_name=self.project.name,
            contact=self.contact.name,
            sent_item="Approval request for work schedule",
            channel="Email",
            sent_at="2026-06-11 18:01:00",
            sent_evidence=self.sent_evidence.name,
            expected_result="Written approval or reasoned objections",
            internal_owner="Administrator",
            offset_days=0,
            offset_unit="Business Days",
            reason="Contractual customer response control",
            timeout_action="Escalate to Project Head without assuming approval",
        )
        self.assertEqual(result["calendar_scope"], "Contract")
        self.assertTrue(result["due_at"].startswith("2026-06-15T19:00:00"))
        dependency = frappe.get_doc("Ferum External Dependency", result["external_dependency"])
        self.assertEqual(dependency.customer, self.customer.name)
        self.assertEqual(dependency.status, "Waiting External")
        timeline = get_deadline_timeline(self.project.name, as_of="2026-06-16 09:00:00")
        row = next(
            item
            for item in timeline["rows"]
            if item["source_doctype"] == "Ferum External Dependency"
        )
        self.assertEqual(row["kind"], "Customer Response Due")
        self.assertTrue(row["is_overdue"])
        self.assertEqual(row["deadline_calculation"], dependency.deadline_calculation)

    def _assign_company(self) -> dict[str, object]:
        return assign_calendar(
            scope_type="Company",
            company=self.company.name,
            calendar_revision="RU-5D-2026-v1",
            reason="Official Russian production calendar for 2026",
        )


def _make_context():
    suffix = uuid4().hex[:10]
    company = frappe.get_doc(
        {
            "doctype": "Company",
            "company_name": f"CA-17 Company {suffix}",
            "abbr": uuid4().hex[:5].upper(),
            "default_currency": "RUB",
            "country": "Russia",
        }
    ).insert(ignore_permissions=True)
    customer = frappe.get_doc(
        {
            "doctype": "Customer",
            "customer_name": f"CA-17 Customer {suffix}",
            "customer_type": "Company",
            "customer_group": "Commercial",
            "territory": "Russia",
        }
    ).insert(ignore_permissions=True)
    contact = frappe.get_doc(
        {
            "doctype": "Contact",
            "first_name": f"CA17 {suffix}",
            "links": [{"link_doctype": "Customer", "link_name": customer.name}],
        }
    ).insert(ignore_permissions=True)
    project = frappe.get_doc(
        {
            "doctype": "Ferum Service Project",
            "project_name": f"CA-17 project {suffix}",
            "company": company.name,
            "customer": customer.name,
            "contract_number": f"CA17-{suffix}",
            "contract_date": date(2026, 1, 15),
            "contract_subject": "DP-05 runtime acceptance",
            "effective_from": date(2026, 1, 15),
            "effective_to": date(2026, 12, 31),
            "currency": "RUB",
            "project_manager": "Administrator",
        }
    ).insert(ignore_permissions=True)
    document = frappe.get_doc(
        {
            "doctype": "Ferum Project Document",
            "source_doctype": "Ferum Service Project",
            "source_name": project.name,
            "document_type": "Contract",
            "document_number": f"CA17-DOC-{suffix}",
            "document_date": date(2026, 1, 15),
            "version": "1",
            "owner_user": "Administrator",
        }
    ).insert(ignore_permissions=True)
    return company, customer, project, contact, document
