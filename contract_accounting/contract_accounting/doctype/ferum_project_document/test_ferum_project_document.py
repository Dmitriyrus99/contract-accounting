"""Bench runtime acceptance tests for CA-05 project-document custody."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from contract_accounting.api.documents import (
	change_digital_copy_status,
	change_original_status,
	change_project_document_status,
	get_project_document_timeline,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
	_make_project,
)


class TestFerumProjectDocument(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		self._previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.project = _make_project()
		self.service_object = frappe.get_doc(
			{
				"doctype": "Ferum Service Object",
				"object_name": f"CA-05 Object {uuid4().hex[:10]}",
				"customer": self.project.customer,
				"address": "CA-05 runtime address",
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

	def tearDown(self) -> None:
		frappe.set_user(self._previous_user)
		super().tearDown()

	def test_copy_axes_transition_independently_with_immutable_events(self) -> None:
		document = self._make_document()
		file_doc = self._save_file(document.name, "contract.pdf")
		change_digital_copy_status(
			document.name,
			"Uploaded",
			"Digital copy registered",
			file_name=file_doc.name,
		)
		change_digital_copy_status(
			document.name,
			"Verified",
			"Hash and document identity checked",
			evidence_file=file_doc.name,
		)
		document.reload()
		self.assertEqual(document.digital_copy_status, "Verified")
		self.assertEqual(document.original_status, "Not Requested")
		self.assertEqual(document.content_hash, file_doc.content_hash)

		change_original_status(document.name, "Requested", "Original requested")
		change_original_status(
			document.name,
			"Received",
			"Original received by office",
			evidence_file=file_doc.name,
		)
		document.reload()
		self.assertEqual(document.digital_copy_status, "Verified")
		self.assertEqual(document.original_status, "Received")
		self.assertTrue(document.original_received_at)
		self.assertEqual(document.original_received_by, "Administrator")
		timeline = get_project_document_timeline(document.name)
		self.assertEqual(len(timeline), 4)
		self.assertEqual(
			[item["dimension"] for item in timeline],
			["Digital Copy", "Digital Copy", "Original", "Original"],
		)
		event = frappe.get_doc("Ferum Project Document Event", timeline[0]["name"])
		event.reason = "attempted rewrite"
		with self.assertRaises(frappe.PermissionError):
			event.save(ignore_permissions=True)

	def test_not_required_and_original_acceptance_fail_closed_without_evidence(self) -> None:
		document = self._make_document(document_number=f"NR-{uuid4().hex[:8]}")
		evidence = self._save_file(document.name, "normative-basis.txt")
		with self.assertRaises(frappe.ValidationError):
			change_digital_copy_status(document.name, "Not Required", "No digital copy")
		change_digital_copy_status(
			document.name,
			"Not Required",
			"Normative exception",
			evidence_file=evidence.name,
			basis="Customer regulation clause 7",
		)
		with self.assertRaises(frappe.ValidationError):
			change_original_status(document.name, "Not Required", "No paper original")
		change_original_status(
			document.name,
			"Not Required",
			"Normative exception",
			evidence_file=evidence.name,
			basis="Electronic-only exchange agreement",
		)
		document.reload()
		self.assertEqual(document.digital_copy_status, "Not Required")
		self.assertEqual(document.original_status, "Not Required")
		with self.assertRaises(frappe.ValidationError):
			change_project_document_status(document.name, "Active", "Attempt activation")

	def test_activation_identity_and_version_uniqueness_are_server_guarded(self) -> None:
		document = self._make_document(document_number=f"ACT-{uuid4().hex[:8]}")
		with self.assertRaises(frappe.ValidationError):
			change_project_document_status(document.name, "Active", "Premature activation")
		file_doc = self._save_file(document.name, "accepted.pdf")
		change_digital_copy_status(
			document.name,
			"Uploaded",
			"Uploaded",
			file_name=file_doc.name,
		)
		change_digital_copy_status(
			document.name,
			"Verified",
			"Verified",
			evidence_file=file_doc.name,
		)
		change_project_document_status(document.name, "Active", "Approved registry card")
		document.reload()
		self.assertEqual(document.status, "Active")
		original_number = document.document_number
		document.document_number = "SILENT-REWRITE"
		with self.assertRaises(frappe.ValidationError):
			document.save(ignore_permissions=True)
		with self.assertRaises(frappe.UniqueValidationError):
			self._make_document(
				document_number=original_number,
				document_date=document.document_date,
			)

	def test_accepted_binary_and_audit_evidence_cannot_be_deleted(self) -> None:
		document = self._make_document(document_number=f"LOCK-{uuid4().hex[:8]}")
		file_doc = self._save_file(document.name, "locked.pdf")
		change_digital_copy_status(
			document.name,
			"Uploaded",
			"Uploaded",
			file_name=file_doc.name,
		)
		change_digital_copy_status(
			document.name,
			"Verified",
			"Verified",
			evidence_file=file_doc.name,
		)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("File", file_doc.name).delete(ignore_permissions=True)
		document.reload()
		with self.assertRaises(frappe.PermissionError):
			document.delete(ignore_permissions=True)

	def test_source_related_and_billing_context_fail_closed(self) -> None:
		document = self._make_document(document_number=f"LINK-{uuid4().hex[:8]}")
		self.assertEqual(document.service_project, self.project.name)
		self.assertEqual(document.project_object, self.project_object.name)
		self.assertEqual(document.service_object, self.service_object.name)
		document.append(
			"related_entities",
			{
				"linked_doctype": "Ferum Service Project",
				"linked_name": self.project.name,
				"relation_type": "Basis",
			},
		)
		document.save(ignore_permissions=True)
		document.billing_reference_doctype = "Sales Order"
		document.billing_reference_name = "MISSING"
		with self.assertRaises(frappe.ValidationError):
			document.save(ignore_permissions=True)

		foreign_project = _make_project()
		with self.assertRaises(frappe.ValidationError):
			self._make_document(
				document_number=f"FOREIGN-{uuid4().hex[:8]}",
				service_project=foreign_project.name,
			)

	def _make_document(
		self,
		*,
		document_number: str | None = None,
		document_date: date | None = None,
		service_project: str | None = None,
	):
		return frappe.get_doc(
			{
				"doctype": "Ferum Project Document",
				"service_project": service_project,
				"source_doctype": "Ferum Project Object",
				"source_name": self.project_object.name,
				"document_type": "Contract",
				"document_number": document_number or f"DOC-{uuid4().hex[:10]}",
				"document_date": document_date or date.today(),
				"version": "1",
				"owner_user": "Administrator",
			}
		).insert(ignore_permissions=True)

	@staticmethod
	def _save_file(document_name: str, filename: str):
		return save_file(
			f"ca05-{uuid4().hex[:8]}-{filename}",
			b"CA-05 immutable evidence",
			"Ferum Project Document",
			document_name,
			is_private=1,
		)
