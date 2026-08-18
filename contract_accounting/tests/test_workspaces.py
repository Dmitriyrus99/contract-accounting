"""Bench runtime acceptance for CA-14 read-only work queues and Launch UI data."""

from __future__ import annotations

from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from contract_accounting.api.launch import (
	CONFIRMATION_TOKEN,
	generate_reference_launch_process,
)
from contract_accounting.api.lifecycle import change_status
from contract_accounting.api.processes import (
	evaluate_stage_gate,
	transition_process_step,
)
from contract_accounting.api.workspaces import (
	get_launch_projects,
	get_my_actions,
	get_project_launch_view,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
	_make_project,
)
from contract_accounting.setup.launch_template import ensure_reference_launch_template


class TestWorkspaces(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		self.previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.project = _make_project()
		self.project.project_manager = "Administrator"
		self.project.save(ignore_permissions=True)
		for status in ("On Approval", "Approved"):
			change_status(self.project.name, target_legal_status=status)
		self.requirement = frappe.get_doc(
			{
				"doctype": "Ferum Contract Requirement",
				"service_project": self.project.name,
				"requirement_type": "Other",
				"requirement_source": "Contract",
				"source_document_reference": f"CA14-{uuid4().hex[:10]}",
				"source_clause": "launch-assessment",
				"description": "CA-14 requirement assessment fixture",
				"applicability": "Applicable",
				"routing_decision": "Informational",
			}
		).insert(ignore_permissions=True)
		self.requirement.assessment_status = "Assessed"
		self.requirement.save(ignore_permissions=True)
		self.requirement.assessment_status = "Approved"
		self.requirement.save(ignore_permissions=True)
		ensure_reference_launch_template()
		self.generated = generate_reference_launch_process(
			self.project.name,
			f"ca14:{self.project.name}",
			self.requirement.name,
			CONFIRMATION_TOKEN,
		)

	def tearDown(self) -> None:
		frappe.set_user(self.previous_user)
		super().tearDown()

	def test_my_actions_deduplicates_process_step_and_todo_delivery(self) -> None:
		payload = get_my_actions(as_of="2026-08-18 12:00:00")
		process_rows = [
			row
			for row in payload["actions"]
			if row["source_type"] == "Ferum Project Process Step"
			and row["service_project"] == self.project.name
		]
		self.assertEqual(len(process_rows), 4)
		self.assertEqual(
			len({row["canonical_key"] for row in process_rows}), len(process_rows)
		)
		self.assertTrue(all(len(row["delivery_todos"]) == 1 for row in process_rows))
		self.assertEqual(payload["ssot_policy"], "SOURCE_OPERATION_SSOT_TODO_DELIVERY_ONLY")

		user = self._engineer_user()
		frappe.set_user(user.name)
		isolated = get_my_actions(as_of="2026-08-18 12:00:00")
		self.assertFalse(
			any(row["service_project"] == self.project.name for row in isolated["actions"])
		)
		with self.assertRaises(frappe.PermissionError):
			get_launch_projects(as_of="2026-08-18 12:00:00")

	def test_launch_view_exposes_stage_steps_failed_gate_and_mg_blocker(self) -> None:
		first_stage = frappe.db.get_value(
			"Ferum Project Stage",
			{"project_process": self.generated["project_process"]},
			"name",
			order_by="sequence asc",
		)
		first_step = frappe.db.get_value(
			"Ferum Project Process Step",
			{"project_stage": first_stage, "status": "Ready"},
			"name",
			order_by="creation asc",
		)
		transition_process_step(first_step, "Blocked", reason="CA-14 blocker fixture")
		gate = evaluate_stage_gate(first_stage)
		self.assertEqual(gate["status"], "Failed")

		view = get_project_launch_view(
			self.project.name, as_of="2026-08-18 12:00:00"
		)
		self.assertEqual(len(view["stages"]), 7)
		self.assertEqual(view["stages"][0]["steps"][0]["status"], "Blocked")
		self.assertTrue(view["flags"]["blocked"])
		self.assertTrue(view["flags"]["missing_credentials"])
		self.assertIn(
			"FAILED_STAGE_GATE", {row["code"] for row in view["blocking_conditions"]}
		)
		self.assertIn("MG-CA-015", {row["code"] for row in view["blocking_conditions"]})
		self.assertTrue(view["failed_gates"][0]["failed_criteria"])

		queue = get_launch_projects(
			as_of="2026-08-18 12:00:00",
			company=self.project.company,
			project_manager="Administrator",
		)
		row = next(
			item
			for item in queue["projects"]
			if item["service_project"] == self.project.name
		)
		self.assertTrue(row["flags"]["blocked"])
		self.assertEqual(queue["projection_policy"], "READ_ONLY_NO_CACHE_NO_SECOND_SSOT")
		self.assertTrue(frappe.db.exists("Page", "ferum-my-actions"))
		self.assertTrue(frappe.db.exists("Page", "ferum-project-launches"))
		self.assertTrue(frappe.get_meta("Ferum Service Project").has_field("launch_view"))

	def _engineer_user(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"ca14-{uuid4().hex[:10]}@example.invalid",
				"first_name": "CA14 Engineer",
				"enabled": 1,
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		).insert(ignore_permissions=True)
		user.add_roles("Инженер")
		return user


if __name__ == "__main__":
	import unittest

	unittest.main()
