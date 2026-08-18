"""Bench runtime acceptance tests for CA-03 plan-to-fact execution."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from contract_accounting.api.execution import (
	accept_visit,
	change_visit_status,
	create_replacement_visit,
	generate_planned_visits,
	get_execution_trace,
	review_visit,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
	_make_project,
)


class TestFerumMaintenanceExecution(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		self._previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.project = _make_project()
		self.service_object = frappe.get_doc(
			{
				"doctype": "Ferum Service Object",
				"object_name": f"CA-03 Object {uuid4().hex[:10]}",
				"customer": self.project.customer,
				"address": "CA-03 runtime address",
			}
		).insert(ignore_permissions=True)
		self.system = self._make_system(self.service_object.name)
		self.project_object = frappe.get_doc(
			{
				"doctype": "Ferum Project Object",
				"service_project": self.project.name,
				"service_object": self.service_object.name,
				"effective_from": date.today(),
			}
		).insert(ignore_permissions=True)
		self.requirement = self._make_requirement()
		self.obligation = self._make_active_obligation()

	def tearDown(self) -> None:
		frappe.set_user(self._previous_user)
		super().tearDown()

	def test_generation_is_idempotent_with_exact_reverse_trace(self) -> None:
		first = self._generate_one_period()
		second = self._generate_one_period()
		self.assertEqual((first["created_schedules"], first["created_visits"]), (1, 1))
		self.assertEqual((second["created_schedules"], second["created_visits"]), (0, 0))
		self.assertEqual(first["items"], second["items"])
		self.assertEqual(
			frappe.db.count(
				"Ferum Maintenance Schedule", {"contract_obligation": self.obligation.name}
			),
			1,
		)
		self.assertEqual(
			frappe.db.count(
				"Ferum Maintenance Visit", {"contract_obligation": self.obligation.name}
			),
			1,
		)
		trace = get_execution_trace(first["items"][0]["schedule"])
		self.assertEqual(trace["contract_obligation"], self.obligation.name)
		self.assertEqual(trace["visits"][0]["name"], first["items"][0]["visit"])

	def test_cancelled_primary_is_not_silently_recreated(self) -> None:
		first = self._generate_one_period()
		visit_name = first["items"][0]["visit"]
		change_visit_status(
			visit_name,
			"Cancelled",
			cancellation_reason="Customer denied access",
		)
		rerun = self._generate_one_period()
		self.assertEqual(rerun["created_visits"], 0)
		self.assertEqual(rerun["items"][0]["visit"], visit_name)
		self.assertEqual(rerun["items"][0]["visit_status"], "Cancelled")

		first_replacement = create_replacement_visit(visit_name)
		second_replacement = create_replacement_visit(visit_name)
		self.assertEqual(first_replacement["created"], "1")
		self.assertEqual(second_replacement["created"], "0")
		self.assertEqual(first_replacement["replacement"], second_replacement["replacement"])
		self.assertEqual(
			frappe.db.count(
				"Ferum Maintenance Visit",
				{"maintenance_schedule": first["items"][0]["schedule"]},
			),
			2,
		)

	def test_acceptance_requires_reviewed_checklist_and_file_evidence(self) -> None:
		result = self._generate_one_period()
		visit_name = result["items"][0]["visit"]
		started_at = datetime.combine(date.today(), time(9, 0))
		change_visit_status(visit_name, "In Progress", actual_start=str(started_at))
		visit = frappe.get_doc("Ferum Maintenance Visit", visit_name)
		visit.work_result = "Completed"
		visit.visit_report = "Monthly APS maintenance completed"
		visit.save(ignore_permissions=True)
		change_visit_status(
			visit_name,
			"Completed",
			actual_end=str(started_at + timedelta(hours=2)),
		)
		with self.assertRaises(frappe.ValidationError):
			review_visit(visit_name, "Approved")

		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"ca03-{uuid4().hex[:10]}.jpg",
				"file_url": f"/private/files/ca03-{uuid4().hex[:10]}.jpg",
				"is_private": 1,
			}
		).insert(ignore_permissions=True)
		visit = frappe.get_doc("Ferum Maintenance Visit", visit_name)
		visit.append(
			"checklist",
			{
				"item_code": "APS-01",
				"description": "Inspect control panel",
				"is_completed": 1,
				"result": "Pass",
			},
		)
		visit.append(
			"evidence",
			{
				"evidence_type": "Photo",
				"file": file_doc.name,
				"captured_at": started_at + timedelta(hours=1),
				"captured_by": "Administrator",
			},
		)
		visit.save(ignore_permissions=True)
		review_visit(visit_name, "Approved")
		accepted = accept_visit(visit_name, "Accepted")
		self.assertEqual(accepted["acceptance_status"], "Accepted")
		visit.reload()
		self.assertEqual(visit.billing_eligible, 1)
		visit.visit_report = "Attempted silent rewrite"
		with self.assertRaises(frappe.ValidationError):
			visit.save(ignore_permissions=True)

	def test_service_request_is_unplanned_and_derives_customer_context(self) -> None:
		request = frappe.get_doc(
			{
				"doctype": "Ferum Service Request",
				"service_project": self.project.name,
				"project_object": self.project_object.name,
				"object_system": self.system.name,
				"source_type": "Customer",
				"request_type": "Emergency",
				"priority": "Critical",
				"requested_at": datetime.now(),
			}
		).insert(ignore_permissions=True)
		self.assertEqual(request.customer, self.project.customer)
		self.assertEqual(request.service_object, self.service_object.name)
		self.assertFalse(request.get("maintenance_schedule"))

		foreign_object = frappe.get_doc(
			{
				"doctype": "Ferum Service Object",
				"object_name": f"CA-03 Foreign {uuid4().hex[:10]}",
				"customer": self.project.customer,
				"address": "Foreign runtime address",
			}
		).insert(ignore_permissions=True)
		foreign_system = self._make_system(foreign_object.name)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Ferum Service Request",
					"service_project": self.project.name,
					"project_object": self.project_object.name,
					"object_system": foreign_system.name,
					"source_type": "Customer",
					"request_type": "Repair",
					"requested_at": datetime.now(),
				}
			).insert(ignore_permissions=True)

	def _generate_one_period(self) -> dict[str, object]:
		return generate_planned_visits(
			self.obligation.name,
			str(date.today()),
			str(date.today()),
		)

	def _make_requirement(self):
		document = frappe.get_doc(
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
			document.assessment_status = status
			document.save(ignore_permissions=True)
		return document

	def _make_active_obligation(self):
		document = frappe.get_doc(
			{
				"doctype": "Ferum Contract Obligation",
				"service_project": self.project.name,
				"requirement": self.requirement.name,
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
		document.status = "Active"
		document.save(ignore_permissions=True)
		return document

	@staticmethod
	def _make_system(service_object: str):
		return frappe.get_doc(
			{
				"doctype": "Ferum Object System",
				"service_object": service_object,
				"system_type": "APS",
				"system_name": f"CA-03 APS {uuid4().hex[:10]}",
				"equipment_count": 1,
			}
		).insert(ignore_permissions=True)
