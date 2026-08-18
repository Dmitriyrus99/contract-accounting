"""Bench runtime acceptance tests for the CA-01 lifecycle contract root.

These tests require an ERPNext v15 site with the ``contract_accounting`` app
installed. They are intentionally not imported by the standalone unit suite.
"""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import patch
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from contract_accounting.api.lifecycle import change_status, resume, suspend
from contract_accounting.infrastructure.frappe_lifecycle import (
	LIFECYCLE_AUDIT_DOCTYPE,
	SERVICE_PROJECT_DOCTYPE,
	FrappeLifecycleUnitOfWork,
)


class TestFerumServiceProjectLifecycle(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		self._previous_user = frappe.session.user
		frappe.set_user("Administrator")

	def tearDown(self) -> None:
		frappe.set_user(self._previous_user)
		super().tearDown()

	def test_new_project_starts_in_exact_default_pair(self) -> None:
		doc = _make_project()
		self.assertEqual(doc.legal_status, "Draft")
		self.assertEqual(doc.execution_status, "Not Started")

	def test_new_project_rejects_non_default_lifecycle(self) -> None:
		doc = _project_document()
		doc.legal_status = "Approved"
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True, ignore_links=True)

	def test_direct_lifecycle_edit_is_rejected(self) -> None:
		doc = _make_project()
		doc.legal_status = "On Approval"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)
		doc.reload()
		self.assertEqual(doc.legal_status, "Draft")

	def test_server_transition_writes_immutable_audit(self) -> None:
		doc = _make_project()
		result = change_status(doc.name, target_legal_status="On Approval")
		self.assertEqual(result["legal_status"], "On Approval")
		self.assertEqual(result["audit_event_count"], 1)
		events = frappe.get_all(
			LIFECYCLE_AUDIT_DOCTYPE,
			filters={"correlation_id": result["correlation_id"]},
			pluck="name",
		)
		self.assertEqual(len(events), 1)
		event = frappe.get_doc(LIFECYCLE_AUDIT_DOCTYPE, events[0])
		event.reason = "attempted mutation"
		with self.assertRaises(frappe.PermissionError):
			event.save(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc(
				LIFECYCLE_AUDIT_DOCTYPE,
				event.name,
				ignore_permissions=True,
			)

	def test_atomic_cancel_writes_two_correlated_events(self) -> None:
		doc = _make_project()
		result = change_status(
			doc.name,
			target_legal_status="Cancelled",
			target_execution_status="Stopped",
			reason="Tender withdrawn",
			comment="Agreement was not concluded",
			effective_date=date.today(),
			evidence=json.dumps(["Project Document/CANCEL-TEST"]),
		)
		self.assertEqual(result["audit_event_count"], 2)
		self.assertEqual(
			frappe.db.count(
				LIFECYCLE_AUDIT_DOCTYPE,
				{"correlation_id": result["correlation_id"]},
			),
			2,
		)
		doc.reload()
		self.assertEqual((doc.legal_status, doc.execution_status), ("Cancelled", "Stopped"))

	def test_audit_insert_failure_rolls_state_back_to_savepoint(self) -> None:
		doc = _make_project()
		with patch.object(
			FrappeLifecycleUnitOfWork,
			"append_audit_events",
			side_effect=RuntimeError("simulated audit failure"),
		), self.assertRaisesRegex(RuntimeError, "simulated audit failure"):
			change_status(doc.name, target_legal_status="On Approval")
		doc.reload()
		self.assertEqual((doc.legal_status, doc.execution_status), ("Draft", "Not Started"))
		self.assertEqual(
			frappe.db.count(
				LIFECYCLE_AUDIT_DOCTYPE,
				{"service_project": doc.name},
			),
			0,
		)

	def test_launching_and_active_suspend_resume_round_trip(self) -> None:
		doc = _make_project()
		for legal_status in ("On Approval", "Approved", "Signing", "Signed"):
			change_status(doc.name, target_legal_status=legal_status)
		change_status(doc.name, target_execution_status="Launching")
		result = suspend(
			doc.name,
			reason="Waiting for access",
			effective_date=date.today(),
		)
		self.assertEqual(result["suspended_from_status"], "Launching")
		self.assertEqual(resume(doc.name)["execution_status"], "Launching")

		change_status(doc.name, target_legal_status="In Force")
		change_status(doc.name, target_execution_status="Active")
		result = suspend(
			doc.name,
			reason="Safety hold",
			effective_date=date.today(),
		)
		self.assertEqual(result["suspended_from_status"], "Active")
		self.assertEqual(resume(doc.name)["execution_status"], "Active")
		doc.reload()
		self.assertEqual(doc.legal_status, "In Force")

	def test_composite_contract_identity_is_unique(self) -> None:
		first = _make_project()
		duplicate = _project_document(
			company=first.company,
			contract_number=first.contract_number,
			contract_date=first.contract_date,
		)
		with self.assertRaises(frappe.UniqueValidationError):
			duplicate.insert(ignore_permissions=True, ignore_links=True)


def _make_project():
	doc = _project_document()
	doc.company = _make_company(doc.company)
	doc.customer = _make_customer(doc.customer)
	doc.insert(ignore_permissions=True)
	return doc


def _make_company(company_name: str) -> str:
	doc = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": company_name,
			"abbr": uuid4().hex[:5].upper(),
			"default_currency": "RUB",
			"country": "Russia",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_customer(customer_name: str) -> str:
	doc = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": customer_name,
			"customer_type": "Company",
			"customer_group": "All Customer Groups",
			"territory": "All Territories",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _project_document(**overrides: object):
	suffix = uuid4().hex[:12]
	values: dict[str, object] = {
		"doctype": SERVICE_PROJECT_DOCTYPE,
		"project_name": f"CA-01 runtime test {suffix}",
		"company": f"CA Test Company {suffix}",
		"customer": f"CA Test Customer {suffix}",
		"contract_number": f"CA-TEST-{suffix}",
		"contract_date": date.today(),
		"contract_subject": "CA-01 runtime lifecycle validation",
		"currency": "RUB",
	}
	values.update(overrides)
	return frappe.get_doc(values)
