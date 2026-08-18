"""Bench runtime acceptance tests for CA-10 Contract 360 projections."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from contract_accounting.api.contract_360 import (
	get_contract_360,
	get_director_control_center,
)
from contract_accounting.api.finance import recalculate_finance_summary
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
	_make_project,
)


class TestContract360(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		self._previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.project = _make_project()
		self.project.effective_from = date.today() - timedelta(days=30)
		self.project.effective_to = date.today() + timedelta(days=20)
		self.project.project_manager = "Administrator"
		self.project.contract_amount_with_vat = 100000
		self.project.save(ignore_permissions=True)
		self.service_object = frappe.get_doc(
			{
				"doctype": "Ferum Service Object",
				"object_name": f"CA-10 Object {uuid4().hex[:10]}",
				"customer": self.project.customer,
				"address": "CA-10 runtime address",
			}
		).insert(ignore_permissions=True)
		self.project_object = frappe.get_doc(
			{
				"doctype": "Ferum Project Object",
				"service_project": self.project.name,
				"service_object": self.service_object.name,
				"effective_from": date.today() - timedelta(days=30),
				"responsible_engineer": "Administrator",
			}
		).insert(ignore_permissions=True)
		self.request = self._make_request()
		summary = recalculate_finance_summary(self.project.name)
		frappe.db.set_value(
			"Ferum Project Finance Summary",
			summary["summary"],
			{
				"contract_amount_with_vat": 100000,
				"overdue_ar_with_vat": 25000,
				"profit_without_vat": -10000,
				"profitability_percent": -10,
			},
			update_modified=False,
		)
		self.summary = summary["summary"]

	def tearDown(self) -> None:
		frappe.set_user(self._previous_user)
		super().tearDown()

	def test_card_is_source_linked_stable_and_reads_stored_finance(self) -> None:
		before = {
			"projects": frappe.db.count("Ferum Service Project"),
			"objects": frappe.db.count("Ferum Project Object"),
			"requests": frappe.db.count("Ferum Service Request"),
			"summaries": frappe.db.count("Ferum Project Finance Summary"),
		}
		first = get_contract_360(self.project.name, as_of=str(date.today()))
		second = get_contract_360(self.project.name, as_of=str(date.today()))
		self.assertEqual(first["source_fingerprint"], second["source_fingerprint"])
		self.assertEqual(first["widgets"]["objects"]["count"], 1)
		self.assertEqual(first["widgets"]["systems"]["count"], 0)
		self.assertEqual(first["widgets"]["requests"]["open_count"], 1)
		self.assertEqual(first["finance"]["summary"], self.summary)
		self.assertEqual(first["finance"]["profit_without_vat"], -10000)
		rules = {item["rule"] for item in first["exceptions"]}
		self.assertTrue(
			{"Expiring Contract", "Object Without System Inventory", "Negative Margin"}
			.issubset(rules)
		)
		self.assertTrue(
			all(item["drilldown"]["name"] for item in first["exceptions"])
		)
		self.assertEqual(
			before,
			{
				"projects": frappe.db.count("Ferum Service Project"),
				"objects": frappe.db.count("Ferum Project Object"),
				"requests": frappe.db.count("Ferum Service Request"),
				"summaries": frappe.db.count("Ferum Project Finance Summary"),
			},
		)

	def test_source_change_rebuilds_card_without_cache_or_orphan(self) -> None:
		first = get_contract_360(self.project.name)
		second_request = self._make_request()
		second = get_contract_360(self.project.name)
		self.assertNotEqual(first["source_fingerprint"], second["source_fingerprint"])
		self.assertEqual(second["widgets"]["requests"]["open_count"], 2)
		self.assertIn(
			second_request.name,
			{item["source_name"] for item in second["widgets"]["requests"]["items"]},
		)
		self.assertFalse(frappe.db.exists("DocType", "Ferum Contract 360 Cache"))

	def test_non_finance_role_cannot_receive_money_or_margin_exceptions(self) -> None:
		user = self._make_user("Менеджер проектов")
		frappe.set_user(user.name)
		try:
			card = get_contract_360(self.project.name, as_of=str(date.today()))
			serialized = json.dumps(card, ensure_ascii=False, default=str)
			self.assertEqual(card["finance"]["access"], "restricted")
			self.assertNotIn("profit_without_vat", serialized)
			self.assertNotIn("contract_amount_with_vat", serialized)
			self.assertNotIn(
				"Negative Margin",
				{item["rule"] for item in card["exceptions"]},
			)
		finally:
			frappe.set_user("Administrator")

	def test_director_center_is_role_guarded_and_drills_to_projects(self) -> None:
		manager = self._make_user("Менеджер проектов")
		frappe.set_user(manager.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				get_director_control_center(as_of=str(date.today()))
		finally:
			frappe.set_user("Administrator")
		director = self._make_user("Генеральный директор")
		frappe.set_user(director.name)
		try:
			center = get_director_control_center(
				company=self.project.company,
				as_of=str(date.today()),
			)
			project_row = next(
				row for row in center["projects"] if row["service_project"] == self.project.name
			)
			self.assertEqual(project_row["drilldown"]["name"], self.project.name)
			self.assertEqual(project_row["finance"]["access"], "granted")
			self.assertGreater(center["kpi"]["exception_count"], 0)
			self.assertTrue(all(item["source_key"] for item in center["exceptions"]))
		finally:
			frappe.set_user("Administrator")

	def _make_request(self):
		return frappe.get_doc(
			{
				"doctype": "Ferum Service Request",
				"service_project": self.project.name,
				"project_object": self.project_object.name,
				"source_type": "Customer",
				"request_type": "Repair",
				"priority": "High",
				"requested_at": datetime.now(),
				"resolution_due": datetime.now() + timedelta(days=2),
			}
		).insert(ignore_permissions=True)

	@staticmethod
	def _make_user(role: str):
		email = f"ca10-{uuid4().hex[:12]}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "CA10",
				"enabled": 1,
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		).insert(ignore_permissions=True)
		user.add_roles(role)
		return user
