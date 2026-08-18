"""Bench runtime acceptance tests for the CA-09 derived timeline."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from contract_accounting.api.deadlines import get_deadline_timeline


class TestDeadlineTimeline(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		self._previous_user = frappe.session.user
		frappe.set_user("Administrator")

	def tearDown(self) -> None:
		frappe.set_user(self._previous_user)
		super().tearDown()

	def test_projection_is_source_linked_rebuildable_and_non_persistent(self) -> None:
		project = _make_project()
		stage = frappe.get_doc(
			{
				"doctype": "Ferum Contract Execution Stage",
				"service_project": project.name,
				"stage_number": 1,
				"execution_start_date": date.today() - timedelta(days=5),
				"execution_end_date": date.today() + timedelta(days=20),
				"acceptance_due_date": date.today() - timedelta(days=1),
				"billing_due_date": date.today() + timedelta(days=2),
				"payment_due_date": date.today() + timedelta(days=10),
				"currency": "RUB",
			}
		).insert(ignore_permissions=True)
		security = frappe.get_doc(
			{
				"doctype": "Ferum Contract Security",
				"service_project": project.name,
				"security_type": "Performance Security",
				"security_method": "Independent Guarantee",
				"currency": "RUB",
				"valid_from": date.today() - timedelta(days=10),
				"valid_until": date.today() + timedelta(days=5),
				"return_due_date": date.today() + timedelta(days=7),
				"reminder_date": date.today() - timedelta(days=1),
			}
		).insert(ignore_permissions=True)

		as_of = datetime.combine(date.today(), datetime.min.time()).replace(hour=12)
		first = get_deadline_timeline(project.name, as_of=as_of.isoformat())
		keys = [row["source_key"] for row in first["rows"]]
		self.assertEqual(len(keys), len(set(keys)))
		self.assertIn(
			f"Ferum Contract Execution Stage:{stage.name}:acceptance_due_date",
			keys,
		)
		self.assertIn(f"Ferum Contract Security:{security.name}:valid_until", keys)
		acceptance = next(
			row
			for row in first["rows"]
			if row["source_name"] == stage.name and row["source_field"] == "acceptance_due_date"
		)
		self.assertTrue(acceptance["is_overdue"])
		self.assertEqual(acceptance["display_status"], "Overdue")
		self.assertEqual(
			first["classification"]["warning_escalation"],
			"disabled_pending_MG-CA-013",
		)
		self.assertFalse(frappe.db.exists("DocType", "Ferum Deadline"))

		stage.acceptance_due_date = date.today() + timedelta(days=3)
		stage.save(ignore_permissions=True)
		second = get_deadline_timeline(project.name, as_of=as_of.isoformat())
		self.assertNotEqual(first["source_fingerprint"], second["source_fingerprint"])
		updated = next(
			row
			for row in second["rows"]
			if row["source_name"] == stage.name and row["source_field"] == "acceptance_due_date"
		)
		self.assertFalse(updated["is_overdue"])

	def test_without_explicit_as_of_classification_is_disabled(self) -> None:
		project = _make_project()
		result = get_deadline_timeline(project.name)
		self.assertEqual(result["classification"]["absolute_overdue"], "disabled")
		open_rows = [row for row in result["rows"] if row["severity"] != "Closed"]
		self.assertTrue(open_rows)
		self.assertTrue(all(row["is_overdue"] is None for row in open_rows))

	def test_project_read_permission_guards_projection(self) -> None:
		project = _make_project()
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				get_deadline_timeline(project.name)
		finally:
			frappe.set_user("Administrator")


def _make_project():
	suffix = uuid4().hex[:12]
	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": f"CA-09 Company {suffix}",
			"abbr": uuid4().hex[:5].upper(),
			"default_currency": "RUB",
			"country": "Russia",
		}
	).insert(ignore_permissions=True)
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": f"CA-09 Customer {suffix}",
			"customer_type": "Company",
			"customer_group": "Commercial",
			"territory": "Russia",
		}
	).insert(ignore_permissions=True)
	return frappe.get_doc(
		{
			"doctype": "Ferum Service Project",
			"project_name": f"CA-09 project {suffix}",
			"company": company.name,
			"customer": customer.name,
			"contract_number": f"CA09-{suffix}",
			"contract_date": date.today(),
			"contract_subject": "CA-09 timeline validation",
			"effective_from": date.today() - timedelta(days=2),
			"effective_to": date.today() + timedelta(days=30),
			"currency": "RUB",
		}
	).insert(ignore_permissions=True)
