"""Bench runtime acceptance tests for the CA-04 independent Finding lifecycle."""

from __future__ import annotations

from base64 import b64decode
from datetime import date, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from contract_accounting.api.execution import generate_planned_visits
from contract_accounting.api.findings import (
    change_finding_status,
    create_service_request_from_finding,
    get_finding_exception_report,
    link_finding_execution,
    review_photo_evidence,
    triage_finding,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
    _make_address,
    _make_project,
)


class TestFerumFinding(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.project = _make_project()
        self.service_object = frappe.get_doc(
            {
                "doctype": "Ferum Service Object",
                "object_name": f"CA-04 Object {uuid4().hex[:10]}",
                "customer": self.project.customer,
                "address": _make_address(self.project.customer, "CA-04 runtime address"),
            }
        ).insert(ignore_permissions=True)
        self.system = frappe.get_doc(
            {
                "doctype": "Ferum Object System",
                "service_object": self.service_object.name,
                "system_type": "APS",
                "system_name": f"CA-04 APS {uuid4().hex[:10]}",
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
        self.visit = self._make_visit()

    def tearDown(self) -> None:
        frappe.set_user(self._previous_user)
        super().tearDown()

    def test_visit_finding_is_independent_and_source_snapshot_is_immutable(self) -> None:
        before_requests = frappe.db.count("Ferum Service Request")
        finding = self._make_finding()
        self.assertEqual(frappe.db.count("Ferum Service Request"), before_requests)
        self.assertEqual(finding.source_doctype, "Ferum Maintenance Visit")
        self.assertEqual(finding.service_project, self.project.name)
        self.assertEqual(finding.project_object, self.project_object.name)
        self.assertEqual(finding.service_object, self.service_object.name)
        self.assertEqual(finding.object_system, self.system.name)
        self.assertIn(self.visit.name, finding.detected_context_snapshot)
        finding.source_doctype = "Ferum Service Request"
        with self.assertRaises(frappe.ValidationError):
            finding.save(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Ferum Finding",
                    "source_doctype": "Ferum Inspection",
                    "source_name": "MISSING-INSPECTION",
                    "category": "Observation",
                    "severity": "Low",
                    "title": "Future source",
                    "description": "Inspection is intentionally not installed before CA-12",
                }
            ).insert(ignore_permissions=True)

    def test_triage_and_exception_report_use_derived_flags(self) -> None:
        finding = self._make_finding(severity="Critical")
        with self.assertRaises(frappe.ValidationError):
            triage_finding(finding.name, "Confirmed")
        due = frappe.utils.get_datetime(finding.found_at) + timedelta(minutes=5)
        triage_finding(
            finding.name,
            "Confirmed",
            decision="Fix Under Contract",
            responsible="Administrator",
            due_date=str(due),
        )
        with patch(
            "contract_accounting.api.findings.now_datetime",
            return_value=due + timedelta(days=1),
        ):
            report = get_finding_exception_report(self.project.name)
        row = next(item for item in report["items"] if item["name"] == finding.name)
        self.assertTrue(row["open_critical"])
        self.assertTrue(row["overdue"])
        self.assertFalse(row["without_decision"])

    def test_resolution_and_close_require_evidence_and_become_immutable(self) -> None:
        finding = self._make_confirmed_finding()
        change_finding_status(finding.name, "In Resolution")
        with self.assertRaises(frappe.ValidationError):
            change_finding_status(
                finding.name,
                "Resolved",
                resolution_class="Eliminated",
                resolution="Control panel repaired",
            )
        finding.reload()
        file_doc = self._save_evidence_file(finding.name)
        photo = frappe.get_doc(
            {
                "doctype": "Ferum Photo Evidence",
                "source_doctype": "Ferum Finding",
                "source_name": finding.name,
                "category": "After",
                "file": file_doc.name,
            }
        ).insert(ignore_permissions=True)
        self.assertEqual(photo.content_hash, file_doc.content_hash)
        with self.assertRaises(frappe.ValidationError):
            change_finding_status(
                finding.name,
                "Resolved",
                resolution_class="Eliminated",
                resolution="Control panel repaired",
            )
        review_photo_evidence(photo.name, "Accepted")
        resolved = change_finding_status(
            finding.name,
            "Resolved",
            resolution_class="Eliminated",
            resolution="Control panel repaired",
        )
        self.assertTrue(resolved["resolved_at"])
        closed = change_finding_status(finding.name, "Closed")
        self.assertTrue(closed["closed_at"])
        finding.reload()
        finding.comment = "attempted silent rewrite"
        with self.assertRaises(frappe.ValidationError):
            finding.save(ignore_permissions=True)
        photo.reload()
        photo.comment = "attempted photo rewrite"
        with self.assertRaises(frappe.ValidationError):
            photo.save(ignore_permissions=True)

    def test_explicit_request_creation_is_idempotent_and_preserves_source(self) -> None:
        finding = self._make_confirmed_finding(decision="Additional Work")
        source_before = (
            finding.source_doctype,
            finding.source_name,
            finding.detected_context_snapshot,
        )
        first = create_service_request_from_finding(finding.name, "ca04:create-request:1")
        second = create_service_request_from_finding(finding.name, "ca04:create-request:1")
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["service_request"], second["service_request"])
        request = frappe.get_doc("Ferum Service Request", first["service_request"])
        self.assertEqual(request.source_type, "Finding")
        self.assertEqual(request.source_reference, finding.name)
        finding.reload()
        self.assertEqual(
            (finding.source_doctype, finding.source_name, finding.detected_context_snapshot),
            source_before,
        )
        self.assertEqual(len(finding.execution_links), 1)

    def test_execution_link_rejects_foreign_context_and_disallowed_doctype(self) -> None:
        finding = self._make_confirmed_finding()
        request = self._make_request(self.project.name, self.project_object.name, self.system.name)
        first = link_finding_execution(
            finding.name,
            "Ferum Service Request",
            request.name,
            "Execution",
            "ca04:link:1",
        )
        second = link_finding_execution(
            finding.name,
            "Ferum Service Request",
            request.name,
            "Execution",
            "ca04:link:1",
        )
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        with self.assertRaises(frappe.ValidationError):
            link_finding_execution(
                finding.name,
                "Sales Order",
                "MISSING",
                "Execution",
                "ca04:link:blocked",
            )
        foreign_project = _make_project()
        foreign_object = frappe.get_doc(
            {
                "doctype": "Ferum Service Object",
                "object_name": f"CA-04 Foreign {uuid4().hex[:10]}",
                "customer": foreign_project.customer,
                "address": _make_address(foreign_project.customer, "Foreign runtime address"),
            }
        ).insert(ignore_permissions=True)
        foreign_membership = frappe.get_doc(
            {
                "doctype": "Ferum Project Object",
                "service_project": foreign_project.name,
                "service_object": foreign_object.name,
                "effective_from": date.today(),
            }
        ).insert(ignore_permissions=True)
        foreign_request = self._make_request(
            foreign_project.name,
            foreign_membership.name,
            None,
        )
        with self.assertRaises(frappe.ValidationError):
            link_finding_execution(
                finding.name,
                "Ferum Service Request",
                foreign_request.name,
                "Execution",
                "ca04:link:foreign",
            )

    def _make_finding(self, *, severity: str = "High"):
        return frappe.get_doc(
            {
                "doctype": "Ferum Finding",
                "source_doctype": "Ferum Maintenance Visit",
                "source_name": self.visit.name,
                "category": "Defect",
                "severity": severity,
                "title": "APS control panel fault",
                "description": "Control panel reports an intermittent power fault",
            }
        ).insert(ignore_permissions=True)

    def _make_confirmed_finding(self, *, decision: str = "Fix Under Contract"):
        finding = self._make_finding()
        triage_finding(
            finding.name,
            "Confirmed",
            decision=decision,
            responsible="Administrator",
            due_date=str(frappe.utils.get_datetime(finding.found_at) + timedelta(days=2)),
        )
        finding.reload()
        return finding

    def _make_visit(self):
        requirement = frappe.get_doc(
            {
                "doctype": "Ferum Contract Requirement",
                "service_project": self.project.name,
                "requirement_type": "Work",
                "requirement_source": "Contract",
                "source_document_reference": f"Contract/{uuid4().hex[:10]}",
                "source_clause": "4.1",
                "description": "Monthly maintenance visit",
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
                        "window_before_days": 1,
                        "window_after_days": 2,
                        "due_offset_days": 3,
                        "calendar_type": "Calendar Days",
                        "generation_horizon_days": 365,
                    }
                ],
                "deadline_rule": {},
                "currency": self.project.currency,
                "effective_from": date.today(),
            }
        ).insert(ignore_permissions=True)
        obligation.status = "Active"
        obligation.save(ignore_permissions=True)
        result = generate_planned_visits(obligation.name, str(date.today()), str(date.today()))
        return frappe.get_doc("Ferum Maintenance Visit", result["items"][0]["visit"])

    def _make_request(
        self,
        service_project: str,
        project_object: str,
        object_system: str | None,
    ):
        return frappe.get_doc(
            {
                "doctype": "Ferum Service Request",
                "service_project": service_project,
                "project_object": project_object,
                "object_system": object_system,
                "subject": "Finding request fixture",
                "description": "Independent request used to validate Finding provenance boundaries.",
                "source_type": "Customer",
                "request_type": "Repair",
                "priority": "High",
                "requested_at": datetime.now(),
            }
        ).insert(ignore_permissions=True)

    @staticmethod
    def _save_evidence_file(finding_name: str):
        return save_file(
            f"ca04-{uuid4().hex[:10]}.png",
            b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
                "+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ),
            "Ferum Finding",
            finding_name,
            is_private=1,
        )
