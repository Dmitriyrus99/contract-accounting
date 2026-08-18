"""Bench runtime acceptance tests for CA-02 requirement/obligation routing."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from contract_accounting.contract_accounting.doctype.ferum_contract_obligation.ferum_contract_obligation import (
	preview_obligation,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
	_make_project,
)


class TestFerumContractObligation(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		self._previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.project = _make_project()
		self.service_object = frappe.get_doc(
			{
				"doctype": "Ferum Service Object",
				"object_name": f"CA-02 Object {uuid4().hex[:10]}",
				"customer": self.project.customer,
				"address": "CA-02 runtime address",
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

	def tearDown(self) -> None:
		frappe.set_user(self._previous_user)
		super().tearDown()

	def test_approved_requirement_routes_to_active_obligation_and_pure_preview(self) -> None:
		requirement = self._make_approved_requirement("Recurring Obligation")
		obligation = self._make_obligation(requirement.name)
		obligation.status = "Active"
		obligation.save(ignore_permissions=True)

		count_before = frappe.db.count(
			"Ferum Contract Obligation", {"service_project": self.project.name}
		)
		first = preview_obligation(
			obligation.name,
			str(date.today()),
			str(date.today() + timedelta(days=100)),
		)
		second = preview_obligation(
			obligation.name,
			str(date.today()),
			str(date.today() + timedelta(days=100)),
		)
		self.assertEqual(first, second)
		self.assertEqual(first[0]["period_key"], str(date.today()))
		self.assertEqual(first[0]["due_date"], str(date.today() + timedelta(days=5)))
		self.assertEqual(
			frappe.db.count(
				"Ferum Contract Obligation", {"service_project": self.project.name}
			),
			count_before,
		)

	def test_one_time_requirement_cannot_become_recurring_obligation(self) -> None:
		requirement = self._make_approved_requirement("One-time Process Step")
		with self.assertRaises(frappe.ValidationError):
			self._make_obligation(requirement.name)

	def test_object_system_and_project_membership_are_consistent(self) -> None:
		requirement = self._make_approved_requirement("Recurring Obligation")
		foreign_object = frappe.get_doc(
			{
				"doctype": "Ferum Service Object",
				"object_name": f"CA-02 Foreign {uuid4().hex[:10]}",
				"customer": self.project.customer,
				"address": "Foreign runtime address",
			}
		).insert(ignore_permissions=True)
		foreign_system = self._make_system(foreign_object.name)
		with self.assertRaises(frappe.ValidationError):
			self._make_obligation(requirement.name, object_system=foreign_system.name)

	def test_active_versions_cannot_overlap_and_identity_is_frozen(self) -> None:
		requirement = self._make_approved_requirement("Recurring Obligation")
		first = self._make_obligation(
			requirement.name,
			effective_to=date.today() + timedelta(days=30),
		)
		first.status = "Active"
		first.save(ignore_permissions=True)

		overlap = self._make_obligation_document(
			requirement.name,
			effective_from=date.today() + timedelta(days=30),
		)
		overlap.insert(ignore_permissions=True)
		overlap.status = "Active"
		with self.assertRaises(frappe.ValidationError):
			overlap.save(ignore_permissions=True)

		first.reload()
		first.work_type = "Changed after activation"
		with self.assertRaises(frappe.ValidationError):
			first.save(ignore_permissions=True)
		first.reload()
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Ferum Contract Obligation", first.name, ignore_permissions=True)

	def _make_approved_requirement(self, routing_decision: str):
		requirement = frappe.get_doc(
			{
				"doctype": "Ferum Contract Requirement",
				"service_project": self.project.name,
				"requirement_type": "Work",
				"requirement_source": "Contract",
				"source_document_reference": f"Contract/{uuid4().hex[:10]}",
				"source_clause": "3.2",
				"description": "Perform monthly maintenance",
				"applicability": "Applicable",
				"routing_decision": routing_decision,
			}
		).insert(ignore_permissions=True)
		for status in ("Assessed", "Approved"):
			requirement.assessment_status = status
			requirement.save(ignore_permissions=True)
		return requirement

	def _make_obligation(self, requirement: str, **overrides: object):
		document = self._make_obligation_document(requirement, **overrides)
		document.insert(ignore_permissions=True)
		return document

	def _make_obligation_document(self, requirement: str, **overrides: object):
		values: dict[str, object] = {
			"doctype": "Ferum Contract Obligation",
			"service_project": self.project.name,
			"requirement": requirement,
			"project_object": self.project_object.name,
			"object_system": self.system.name,
			"work_type": "Monthly APS maintenance",
			"obligation_type": "Maintenance",
			"recurrence": [
				{
					"frequency": "Monthly",
					"interval": 1,
					"period_anchor": "Contract Start",
					"due_offset_days": 5,
					"calendar_type": "Calendar Days",
					"generation_horizon_days": 365,
				}
			],
			"deadline_rule": {},
			"acceptance_rule": {},
			"evidence_rule": {},
			"currency": self.project.currency,
			"effective_from": date.today(),
		}
		values.update(overrides)
		return frappe.get_doc(values)

	@staticmethod
	def _make_system(service_object: str):
		return frappe.get_doc(
			{
				"doctype": "Ferum Object System",
				"service_object": service_object,
				"system_type": "APS",
				"system_name": f"CA-02 APS {uuid4().hex[:10]}",
				"equipment_count": 1,
			}
		).insert(ignore_permissions=True)
