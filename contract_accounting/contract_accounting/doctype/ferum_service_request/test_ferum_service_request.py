"""Bench runtime acceptance for Service Request disposition and exception branches."""

from __future__ import annotations

from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime, today
from frappe.utils.file_manager import save_file

from contract_accounting.api.requests import (
	create_paid_work_request,
	get_request_successors,
	partial_close_request,
	register_customer_approval_evidence,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
	_make_project,
)


class TestFerumServiceRequestDisposition(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		self.previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.project = _make_project()
		self.service_object = frappe.get_doc(
			{
				"doctype": "Ferum Service Object",
				"object_name": f"CA-15 Request Object {uuid4().hex[:10]}",
				"customer": self.project.customer,
				"address": "CA-15 request disposition fixture",
			}
		).insert(ignore_permissions=True)
		self.project_object = frappe.get_doc(
			{
				"doctype": "Ferum Project Object",
				"service_project": self.project.name,
				"service_object": self.service_object.name,
				"effective_from": today(),
			}
		).insert(ignore_permissions=True)
		self.source = self._make_request()

	def tearDown(self) -> None:
		frappe.set_user(self.previous_user)
		super().tearDown()

	def test_subject_description_and_typed_source_are_fail_closed(self) -> None:
		missing_text = self._request_values()
		missing_text.pop("subject")
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(missing_text).insert(ignore_permissions=True)

		inspection = frappe.get_doc(
			{
				"doctype": "Ferum Inspection",
				"project_object": self.project_object.name,
				"inspection_type": "Initial",
				"planned_date": today(),
				"lead_inspector": "Administrator",
				"idempotency_key": f"ca15-request-{uuid4().hex}",
			}
		).insert(ignore_permissions=True)
		finding = frappe.get_doc(
			{
				"doctype": "Ferum Finding",
				"source_doctype": "Ferum Inspection",
				"source_name": inspection.name,
				"category": "Defect",
				"severity": "High",
				"title": "Typed source finding",
				"description": "Typed source fixture",
			}
		).insert(ignore_permissions=True)
		typed = self._request_values(
			source_type="Finding",
			source_doctype="Ferum Finding",
			source_name=finding.name,
		)
		request = frappe.get_doc(typed).insert(ignore_permissions=True)
		self.assertEqual(request.source_reference, finding.name)

		wrong_type = self._request_values(
			source_type="Finding",
			source_doctype="Ferum Maintenance Visit",
			source_name=finding.name,
		)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(wrong_type).insert(ignore_permissions=True)

	def test_successors_and_customer_approval_are_idempotent(self) -> None:
		paid_first = create_paid_work_request(self.source.name)
		paid_second = create_paid_work_request(self.source.name)
		self.assertTrue(paid_first["created"])
		self.assertFalse(paid_second["created"])
		self.assertEqual(paid_first["successor"], paid_second["successor"])
		paid = frappe.get_doc("Ferum Service Request", paid_first["successor"])
		self.assertEqual(paid.exception_key, f"paid:{self.source.name}")

		paid.status = "Assigned"
		paid.assigned_engineer = "Administrator"
		paid.save(ignore_permissions=True)
		paid.status = "In Progress"
		paid.actual_start = now_datetime()
		with self.assertRaises(frappe.ValidationError):
			paid.save(ignore_permissions=True)

		approval_file = self._save_file(paid.name, "customer-approval.txt")
		approval_first = register_customer_approval_evidence(paid.name, approval_file.name)
		approval_second = register_customer_approval_evidence(paid.name, approval_file.name)
		self.assertTrue(approval_first["created"])
		self.assertFalse(approval_second["created"])
		self.assertEqual(approval_first["project_document"], approval_second["project_document"])
		paid.reload()
		paid.status = "In Progress"
		paid.actual_start = now_datetime()
		paid.save(ignore_permissions=True)

		self.source.status = "In Progress"
		self.source.actual_start = now_datetime()
		self.source.save(ignore_permissions=True)
		evidence_file = self._save_file(self.source.name, "partial-work.txt")
		self.source.append(
			"evidence",
			{
				"evidence_type": "Report",
				"file": evidence_file.name,
				"captured_at": now_datetime(),
				"captured_by": "Administrator",
			},
		)
		self.source.actual_end = now_datetime()
		self.source.work_result = "Partially Completed"
		self.source.resolution = "Accepted completed part only"
		self.source.status = "Resolved"
		self.source.save(ignore_permissions=True)
		remaining_first = partial_close_request(
			self.source.name,
			"Remaining repair",
			"Complete the explicitly remaining work.",
		)
		remaining_second = partial_close_request(
			self.source.name,
			"Ignored retry",
			"Ignored retry description.",
		)
		self.assertEqual(remaining_first["successor"], remaining_second["successor"])
		self.assertEqual(
			frappe.db.get_value("Ferum Service Request", self.source.name, "status"),
			"Closed",
		)
		derived = get_request_successors(self.source.name)
		self.assertEqual(
			{row["successor_kind"] for row in derived["successors"]},
			{"Paid Work", "Remaining"},
		)

	def _make_request(self):
		return frappe.get_doc(self._request_values()).insert(ignore_permissions=True)

	def _request_values(self, **updates):
		values = {
			"doctype": "Ferum Service Request",
			"service_project": self.project.name,
			"project_object": self.project_object.name,
			"subject": "Repair customer request",
			"description": "Repair the failed equipment and record exact evidence.",
			"source_type": "Customer",
			"request_type": "Repair",
			"priority": "High",
			"requested_at": now_datetime(),
		}
		values.update(updates)
		return values

	@staticmethod
	def _save_file(request: str, suffix: str):
		filename = f"ca15-{uuid4().hex[:10]}-{suffix}"
		return save_file(
			filename,
			f"CA-15 Service Request evidence: {filename}".encode(),
			"Ferum Service Request",
			request,
			is_private=1,
		)


if __name__ == "__main__":
	import unittest

	unittest.main()
