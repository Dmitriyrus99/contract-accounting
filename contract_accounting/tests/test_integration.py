"""Bench runtime acceptance for the CA-15 integration trace and integrity scan."""

from __future__ import annotations

import json
from datetime import timedelta
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from contract_accounting.api.integration import (
	get_end_to_end_trace,
	get_project_integrity_report,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
	_make_project,
)


class TestIntegration(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		self.previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.project = _make_project()
		self.project.project_manager = "Administrator"
		self.project.save(ignore_permissions=True)
		self.service_object = frappe.get_doc(
			{
				"doctype": "Ferum Service Object",
				"object_name": f"CA-15 Object {uuid4().hex[:10]}",
				"customer": self.project.customer,
				"address": "CA-15 runtime address",
			}
		).insert(ignore_permissions=True)
		self.project_object = frappe.get_doc(
			{
				"doctype": "Ferum Project Object",
				"service_project": self.project.name,
				"service_object": self.service_object.name,
				"effective_from": frappe.utils.today(),
				"responsible_engineer": "Administrator",
			}
		).insert(ignore_permissions=True)
		self.system = frappe.get_doc(
			{
				"doctype": "Ferum Object System",
				"service_object": self.service_object.name,
				"system_type": "CCTV",
				"system_name": f"CA-15 System {uuid4().hex[:8]}",
			}
		).insert(ignore_permissions=True)
		self.request = frappe.get_doc(
			{
				"doctype": "Ferum Service Request",
				"service_project": self.project.name,
				"project_object": self.project_object.name,
				"object_system": self.system.name,
				"source_type": "Customer",
				"request_type": "Repair",
				"priority": "High",
				"requested_at": frappe.utils.now_datetime(),
				"resolution_due": frappe.utils.now_datetime() + timedelta(days=2),
				"assigned_engineer": "Administrator",
			}
		).insert(ignore_permissions=True)

	def tearDown(self) -> None:
		frappe.set_user(self.previous_user)
		super().tearDown()

	def test_trace_is_stable_source_linked_and_permission_filtered(self) -> None:
		first = get_end_to_end_trace(self.project.name)
		second = get_end_to_end_trace(self.project.name)
		self.assertEqual(first["source_fingerprint"], second["source_fingerprint"])
		self.assertEqual(
			[row["key"] for row in first["segments"]],
			["why", "where", "when", "who", "result", "evidence", "billing", "payment", "margin"],
		)
		result = next(row for row in first["segments"] if row["key"] == "result")
		self.assertIn(self.request.name, {row["source_name"] for row in result["items"]})
		where = next(row for row in first["segments"] if row["key"] == "where")
		self.assertIn(self.system.name, {row["source_name"] for row in where["items"]})
		self.assertEqual(first["policies"]["import_batch"], "INACTIVE_NOT_PRODUCTION_PROVEN_PENDING_MG-CA-023")

		manager = self._make_user("Менеджер проектов")
		frappe.set_user(manager.name)
		try:
			restricted = get_end_to_end_trace(self.project.name)
			self.assertEqual(next(row for row in restricted["segments"] if row["key"] == "payment")["access"], "restricted")
			self.assertNotIn("profit_without_vat", json.dumps(restricted, ensure_ascii=False, default=str))
			with self.assertRaises(frappe.PermissionError):
				get_project_integrity_report(self.project.name)
		finally:
			frappe.set_user("Administrator")

	def test_integrity_scan_is_read_only_and_reports_stable_orphan(self) -> None:
		before = {
			"projects": frappe.db.count("Ferum Service Project"),
			"requests": frappe.db.count("Ferum Service Request"),
			"systems": frappe.db.count("Ferum Object System"),
		}
		clean = get_project_integrity_report(self.project.name)
		self.assertEqual(clean["mode"], "READ_ONLY_DRY_RUN")
		self.assertEqual(clean["summary"]["issues"], 0)
		frappe.db.set_value("Ferum Service Request", self.request.name, "object_system", "MISSING-CA15-SYSTEM", update_modified=False)
		first = get_project_integrity_report(self.project.name)
		second = get_project_integrity_report(self.project.name)
		orphan = next(row for row in first["issues"] if row["code"] == "ORPHAN_LINK")
		self.assertEqual(orphan["source_name"], self.request.name)
		self.assertEqual(orphan["fieldname"], "object_system")
		self.assertEqual(orphan["issue_key"], next(row for row in second["issues"] if row["code"] == "ORPHAN_LINK")["issue_key"])
		self.assertEqual(
			before,
			{
				"projects": frappe.db.count("Ferum Service Project"),
				"requests": frappe.db.count("Ferum Service Request"),
				"systems": frappe.db.count("Ferum Object System"),
			},
		)
		for page in ("ferum-contract-360", "ferum-operations", "ferum-director-control"):
			self.assertTrue(frappe.db.exists("Page", page))

	@staticmethod
	def _make_user(role: str):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"ca15-{uuid4().hex[:12]}@example.invalid",
				"first_name": "CA15",
				"enabled": 1,
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		).insert(ignore_permissions=True)
		user.add_roles(role)
		return user


if __name__ == "__main__":
	import unittest

	unittest.main()
