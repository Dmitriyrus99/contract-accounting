"""Insert-time regressions for fields that grant project-wide visibility."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from contract_accounting.api.execution import generate_planned_visits
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
    _make_address,
    _make_project,
)


class TestAssignmentInsertBoundaries(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.engineer = self._make_user("Инженер")
        self.manager = self._make_user("Менеджер проектов")
        self.lawyer = self._make_user("Юрист")
        self.project = _make_project()
        self.chain = self._make_object_chain(self.project)

    def tearDown(self) -> None:
        frappe.set_user(self.previous_user)
        super().tearDown()

    def test_service_request_foreign_assignment_is_denied_but_manager_insert_succeeds(
        self,
    ) -> None:
        denied_subject = f"Denied request assignment {uuid4().hex[:10]}"
        frappe.set_user(self.lawyer)
        with self.assertRaises(frappe.PermissionError):
            self._new_request(denied_subject).insert(ignore_permissions=True)
        self.assertFalse(frappe.db.exists("Ferum Service Request", {"subject": denied_subject}))
        self.assertFalse(self._can_read_project(self.engineer))

        frappe.set_user(self.manager)
        allowed = self._new_request(f"Allowed request assignment {uuid4().hex[:10]}").insert(
            ignore_permissions=True
        )
        self.assertEqual(allowed.assigned_engineer, self.engineer)
        self.assertTrue(self._can_read_project(self.engineer))

    def test_maintenance_visit_foreign_assignment_is_denied_but_manager_insert_succeeds(
        self,
    ) -> None:
        template = self._maintenance_template()
        denied_key = f"SECURITY-DENIED-{uuid4().hex}"
        frappe.set_user(self.lawyer)
        with self.assertRaises(frappe.PermissionError):
            self._new_visit(template, denied_key).insert(ignore_permissions=True)
        self.assertFalse(
            frappe.db.exists("Ferum Maintenance Visit", {"generation_key": denied_key})
        )
        self.assertFalse(self._can_read_project(self.engineer))

        frappe.set_user(self.manager)
        allowed = self._new_visit(
            template,
            f"SECURITY-ALLOWED-{uuid4().hex}",
        ).insert(ignore_permissions=True)
        self.assertEqual(allowed.assigned_engineer, self.engineer)
        self.assertTrue(self._can_read_project(self.engineer))

    def _new_request(self, subject: str):
        return frappe.get_doc(
            {
                "doctype": "Ferum Service Request",
                "service_project": self.project.name,
                "project_object": self.chain.project_object.name,
                "object_system": self.chain.object_system.name,
                "subject": subject,
                "description": "Synthetic insert-time assignment boundary",
                "source_type": "Customer",
                "request_type": "Other",
                "requested_at": now_datetime(),
                "assigned_engineer": self.engineer,
            }
        )

    def _new_visit(self, template, generation_key: str):
        return frappe.get_doc(
            {
                "doctype": "Ferum Maintenance Visit",
                "service_project": template.service_project,
                "contract_obligation": template.contract_obligation,
                "maintenance_schedule": template.maintenance_schedule,
                "project_object": template.project_object,
                "service_object": template.service_object,
                "object_system": template.object_system,
                "period_key": template.period_key,
                "planned_date": template.planned_date,
                "window_start": template.window_start,
                "window_end": template.window_end,
                "generation_key": generation_key,
                "assigned_engineer": self.engineer,
            }
        )

    def _maintenance_template(self):
        frappe.set_user("Administrator")
        requirement = frappe.get_doc(
            {
                "doctype": "Ferum Contract Requirement",
                "service_project": self.project.name,
                "requirement_type": "Work",
                "requirement_source": "Contract",
                "source_document_reference": f"Security/{uuid4().hex[:10]}",
                "source_clause": "1.1",
                "description": "Synthetic maintenance insert boundary",
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
                "work_type": "Synthetic maintenance insert boundary",
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
        return frappe.get_doc("Ferum Maintenance Visit", generated["items"][0]["visit"])

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
        email = f"assignment-insert-{uuid4().hex[:12]}@example.invalid"
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": f"Assignment Insert {role}",
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
                "object_name": f"Assignment insert object {uuid4().hex[:10]}",
                "customer": project.customer,
                "address": _make_address(project.customer, "Assignment insert boundary"),
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
                "system_name": f"Assignment insert APS {uuid4().hex[:10]}",
                "equipment_count": 1,
            }
        ).insert(ignore_permissions=True)
        return frappe._dict(
            project_object=project_object,
            object_system=object_system,
        )
