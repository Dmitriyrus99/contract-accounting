"""Runtime regressions for assignment and private-File authorization boundaries."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime
from frappe.utils.file_manager import save_file

from contract_accounting.api.documents import (
    change_digital_copy_status,
    change_original_status,
)
from contract_accounting.api.execution import generate_planned_visits
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
    _make_address,
    _make_project,
)
from contract_accounting.infrastructure.file_access import get_authorized_file


class TestSecurityRegressions(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.engineer = self._make_user("Инженер")
        self.target_engineer = self._make_user("Инженер")
        self.office = self._make_user("Офис-менеджер")
        self.target_office = self._make_user("Офис-менеджер")
        self.manager = self._make_user("Менеджер проектов")
        self.lawyer = self._make_user("Юрист")
        self.project = _make_project()
        self.foreign_project = _make_project()
        self.chain = self._make_object_chain(self.project)

    def tearDown(self) -> None:
        frappe.set_user(self.previous_user)
        super().tearDown()

    def test_engineer_cannot_delegate_request_or_visit_project_access(self) -> None:
        request = self._make_request(self.engineer)
        visit = self._make_maintenance_visit(self.engineer)
        self.assertTrue(self._can_read_project(self.engineer))
        self.assertFalse(self._can_read_project(self.target_engineer))

        frappe.set_user(self.engineer)
        for doctype, name in (
            ("Ferum Service Request", request.name),
            ("Ferum Maintenance Visit", visit.name),
        ):
            document = frappe.get_doc(doctype, name)
            document.assigned_engineer = self.target_engineer
            with self.assertRaises(frappe.PermissionError):
                document.save(ignore_permissions=True)
            self.assertEqual(
                frappe.db.get_value(doctype, name, "assigned_engineer"),
                self.engineer,
            )

        self.assertFalse(self._can_read_project(self.target_engineer))

        frappe.set_user(self.manager)
        for doctype, name in (
            ("Ferum Service Request", request.name),
            ("Ferum Maintenance Visit", visit.name),
        ):
            document = frappe.get_doc(doctype, name)
            document.assigned_engineer = self.target_engineer
            document.save(ignore_permissions=True)
            self.assertEqual(document.assigned_engineer, self.target_engineer)

        self.assertTrue(self._can_read_project(self.target_engineer))

    def test_office_cannot_delegate_document_project_access(self) -> None:
        document = self._make_document(self.project.name, owner_user=self.office)
        self.assertTrue(self._can_read_project(self.office))
        self.assertFalse(self._can_read_project(self.target_office))

        frappe.set_user(self.office)
        attempted = frappe.get_doc("Ferum Project Document", document.name)
        attempted.owner_user = self.target_office
        with self.assertRaises(frappe.PermissionError):
            attempted.save(ignore_permissions=True)

        self.assertEqual(
            frappe.db.get_value("Ferum Project Document", document.name, "owner_user"),
            self.office,
        )
        self.assertFalse(self._can_read_project(self.target_office))

        frappe.set_user(self.manager)
        reassigned = frappe.get_doc("Ferum Project Document", document.name)
        reassigned.owner_user = self.target_office
        reassigned.save(ignore_permissions=True)

        self.assertEqual(reassigned.owner_user, self.target_office)
        self.assertTrue(self._can_read_project(self.target_office))
        self.assertFalse(self._can_read_project(self.office))

    def test_lawyer_cannot_delegate_document_project_access_on_insert(self) -> None:
        self.assertFalse(self._can_read_project(self.target_office))
        denied_number = f"SECURITY-DENIED-{uuid4().hex[:12]}"

        frappe.set_user(self.lawyer)
        attempted = frappe.get_doc(
            {
                "doctype": "Ferum Project Document",
                "source_doctype": "Ferum Service Project",
                "source_name": self.project.name,
                "document_type": "Other",
                "document_number": denied_number,
                "document_date": date.today(),
                "version": "1",
                "owner_user": self.target_office,
            }
        )
        with self.assertRaises(frappe.PermissionError):
            attempted.insert(ignore_permissions=True)

        self.assertFalse(
            frappe.db.exists(
                "Ferum Project Document",
                {"document_number": denied_number},
            )
        )
        self.assertFalse(self._can_read_project(self.target_office))

        frappe.set_user(self.manager)
        allowed = self._make_document(self.project.name, owner_user=self.target_office)

        self.assertEqual(allowed.owner_user, self.target_office)
        self.assertTrue(self._can_read_project(self.target_office))

    def test_typed_evidence_rejects_foreign_private_file_before_event_creation(
        self,
    ) -> None:
        own_document = self._make_document(self.project.name, owner_user=self.office)
        foreign_document = self._make_document(
            self.foreign_project.name,
            owner_user="Administrator",
        )
        own_file = self._attach_private_file(own_document, "own")
        foreign_file = self._attach_private_file(foreign_document, "foreign")

        frappe.set_user(self.office)
        self.assertEqual(get_authorized_file(own_file.name).name, own_file.name)
        with self.assertRaises(frappe.PermissionError):
            get_authorized_file(foreign_file.name)

        event_count = frappe.db.count(
            "Ferum Project Document Event",
            {"project_document": own_document.name},
        )
        foreign_reference_count = frappe.db.count(
            "Ferum Project Document Event",
            {"evidence_file": foreign_file.name},
        )
        with self.assertRaises(frappe.PermissionError):
            change_original_status(
                own_document.name,
                "Requested",
                "Synthetic foreign evidence must be rejected",
                evidence_file=foreign_file.name,
            )

        self.assertEqual(
            frappe.db.get_value("Ferum Project Document", own_document.name, "original_status"),
            "Not Requested",
        )
        self.assertEqual(
            frappe.db.count(
                "Ferum Project Document Event",
                {"project_document": own_document.name},
            ),
            event_count,
        )
        self.assertEqual(
            frappe.db.count(
                "Ferum Project Document Event",
                {"evidence_file": foreign_file.name},
            ),
            foreign_reference_count,
        )

        result = change_original_status(
            own_document.name,
            "Requested",
            "Synthetic own evidence is authorized",
            evidence_file=own_file.name,
        )
        self.assertEqual(result["original_status"], "Requested")
        self.assertEqual(
            frappe.db.count(
                "Ferum Project Document Event",
                {
                    "project_document": own_document.name,
                    "dimension": "Original",
                    "evidence_file": own_file.name,
                },
            ),
            1,
        )

    def _can_read_project(self, user: str) -> bool:
        return bool(
            frappe.has_permission(
                "Ferum Service Project",
                "read",
                doc=self.project.name,
                user=user,
            )
        )

    @staticmethod
    def _make_user(role: str) -> str:
        email = f"security-regression-{uuid4().hex[:12]}@example.invalid"
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": f"Security Regression {role}",
                "enabled": 1,
                "send_welcome_email": 0,
                "user_type": "System User",
            }
        ).insert(ignore_permissions=True)
        user.add_roles(role)
        return email

    @staticmethod
    def _make_object_chain(project):
        service_object = frappe.get_doc(
            {
                "doctype": "Ferum Service Object",
                "object_name": f"Security regression object {uuid4().hex[:10]}",
                "customer": project.customer,
                "address": _make_address(project.customer, "Security regression runtime"),
            }
        ).insert(ignore_permissions=True)
        project_object = frappe.get_doc(
            {
                "doctype": "Ferum Project Object",
                "service_project": project.name,
                "service_object": service_object.name,
                "effective_from": date.today(),
            }
        ).insert(ignore_permissions=True)
        object_system = frappe.get_doc(
            {
                "doctype": "Ferum Object System",
                "service_object": service_object.name,
                "system_type": "APS",
                "system_name": f"Security regression APS {uuid4().hex[:10]}",
                "equipment_count": 1,
            }
        ).insert(ignore_permissions=True)
        return frappe._dict(
            service_object=service_object,
            project_object=project_object,
            object_system=object_system,
        )

    def _make_request(self, assigned_engineer: str):
        return frappe.get_doc(
            {
                "doctype": "Ferum Service Request",
                "service_project": self.project.name,
                "project_object": self.chain.project_object.name,
                "object_system": self.chain.object_system.name,
                "subject": f"Security regression request {uuid4().hex[:10]}",
                "description": "Synthetic assignment-guard proof",
                "source_type": "Customer",
                "request_type": "Other",
                "requested_at": now_datetime(),
                "assigned_engineer": assigned_engineer,
            }
        ).insert(ignore_permissions=True)

    def _make_maintenance_visit(self, assigned_engineer: str):
        requirement = frappe.get_doc(
            {
                "doctype": "Ferum Contract Requirement",
                "service_project": self.project.name,
                "requirement_type": "Work",
                "requirement_source": "Contract",
                "source_document_reference": f"Security/{uuid4().hex[:10]}",
                "source_clause": "1.1",
                "description": "Synthetic maintenance assignment proof",
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
                "project_object": self.chain.project_object.name,
                "object_system": self.chain.object_system.name,
                "work_type": "Synthetic security maintenance",
                "obligation_type": "Maintenance",
                "recurrence": [
                    {
                        "frequency": "Monthly",
                        "interval": 1,
                        "period_anchor": "Contract Start",
                        "window_before_days": 1,
                        "window_after_days": 1,
                        "due_offset_days": 1,
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
        generated = generate_planned_visits(
            obligation.name,
            str(date.today()),
            str(date.today()),
        )
        visit = frappe.get_doc("Ferum Maintenance Visit", generated["items"][0]["visit"])
        visit.assigned_engineer = assigned_engineer
        visit.save(ignore_permissions=True)
        return visit

    @staticmethod
    def _make_document(project: str, *, owner_user: str):
        return frappe.get_doc(
            {
                "doctype": "Ferum Project Document",
                "source_doctype": "Ferum Service Project",
                "source_name": project,
                "document_type": "Other",
                "document_number": f"SECURITY-{uuid4().hex[:12]}",
                "document_date": date.today(),
                "version": "1",
                "owner_user": owner_user,
            }
        ).insert(ignore_permissions=True)

    @staticmethod
    def _attach_private_file(document, label: str):
        file_doc = save_file(
            f"security-regression-{label}-{uuid4().hex[:10]}.txt",
            f"synthetic {label} private evidence".encode(),
            document.doctype,
            document.name,
            is_private=1,
        )
        change_digital_copy_status(
            document.name,
            "Uploaded",
            f"Attach synthetic {label} private evidence",
            file_name=file_doc.name,
        )
        return file_doc
