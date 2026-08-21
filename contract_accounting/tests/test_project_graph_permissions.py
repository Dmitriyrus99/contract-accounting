"""Runtime proof that scoped Desk roles cannot cross project boundaries."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime
from frappe.utils.file_manager import save_file

from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
    _make_address,
    _make_project,
)
from contract_accounting.infrastructure.project_graph_permissions import (
    DIRECT_PROJECT_DOCTYPES,
    INDIRECT_PROJECT_DOCTYPES,
    has_project_graph_permission,
)


class TestProjectGraphPermissions(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.engineer = self._make_user("Инженер")
        self.office = self._make_user("Офис-менеджер")
        self.engineer_project = _make_project()
        self.foreign_engineer_project = _make_project()
        self.office_project = _make_project()
        self.foreign_office_project = _make_project()
        self.engineer_chain = self._make_object_chain(
            self.engineer_project, responsible_engineer=self.engineer
        )
        self.foreign_engineer_chain = self._make_object_chain(self.foreign_engineer_project)
        self.office_document = self._make_document(self.office_project.name, owner_user=self.office)
        self.foreign_office_document = self._make_document(
            self.foreign_office_project.name, owner_user="Administrator"
        )

    def tearDown(self) -> None:
        frappe.set_user(self.previous_user)
        super().tearDown()

    def test_engineer_cannot_list_or_open_foreign_project_graph(self) -> None:
        own_request = self._make_request(self.engineer_project, self.engineer_chain)
        foreign_request = self._make_request(
            self.foreign_engineer_project, self.foreign_engineer_chain
        )
        frappe.set_user(self.engineer)

        for doctype, own, foreign in (
            (
                "Ferum Project Object",
                self.engineer_chain["project_object"],
                self.foreign_engineer_chain["project_object"],
            ),
            (
                "Ferum Service Object",
                self.engineer_chain["service_object"],
                self.foreign_engineer_chain["service_object"],
            ),
            (
                "Ferum Object System",
                self.engineer_chain["object_system"],
                self.foreign_engineer_chain["object_system"],
            ),
            ("Ferum Service Request", own_request.name, foreign_request.name),
        ):
            visible = set(frappe.get_list(doctype, pluck="name", limit_page_length=0))
            self.assertIn(own, visible, doctype)
            self.assertNotIn(foreign, visible, doctype)
            self.assertTrue(frappe.has_permission(doctype, "read", doc=own), doctype)
            self.assertFalse(frappe.has_permission(doctype, "read", doc=foreign), doctype)

    def test_office_manager_cannot_list_or_open_foreign_documents(self) -> None:
        frappe.set_user(self.office)
        visible = set(frappe.get_list("Ferum Project Document", pluck="name", limit_page_length=0))
        self.assertIn(self.office_document.name, visible)
        self.assertNotIn(self.foreign_office_document.name, visible)
        self.assertTrue(
            frappe.has_permission("Ferum Project Document", "read", doc=self.office_document.name)
        )
        self.assertFalse(
            frappe.has_permission(
                "Ferum Project Document", "read", doc=self.foreign_office_document.name
            )
        )

    def test_file_list_and_metadata_follow_the_parent_project_boundary(self) -> None:
        own_request = self._make_request(self.engineer_project, self.engineer_chain)
        foreign_request = self._make_request(
            self.foreign_engineer_project, self.foreign_engineer_chain
        )
        own_generic_file = save_file(
            f"acl-own-request-{uuid4().hex[:8]}.txt",
            b"synthetic own generic attachment",
            "Ferum Service Request",
            own_request.name,
            is_private=1,
        )
        foreign_generic_file = save_file(
            f"acl-foreign-request-{uuid4().hex[:8]}.txt",
            b"synthetic foreign generic attachment",
            "Ferum Service Request",
            foreign_request.name,
            is_private=1,
        )
        own_file = save_file(
            f"acl-own-{uuid4().hex[:8]}.txt",
            b"synthetic own project evidence",
            "Ferum Project Document",
            self.office_document.name,
            is_private=1,
        )
        foreign_file = save_file(
            f"acl-foreign-{uuid4().hex[:8]}.txt",
            b"synthetic foreign project evidence",
            "Ferum Project Document",
            self.foreign_office_document.name,
            is_private=1,
        )
        frappe.db.set_value(
            "Ferum Project Document", self.office_document.name, "file", own_file.name
        )
        frappe.db.set_value(
            "Ferum Project Document",
            self.foreign_office_document.name,
            "file",
            foreign_file.name,
        )
        frappe.set_user(self.office)

        visible = set(
            frappe.get_list(
                "File",
                filters={"name": ["in", [own_file.name, foreign_file.name]]},
                pluck="name",
                limit_page_length=0,
            )
        )
        self.assertIn(own_file.name, visible)
        self.assertNotIn(foreign_file.name, visible)
        self.assertFalse(frappe.has_permission("File", "read", doc=foreign_file.name))

        frappe.set_user(self.engineer)
        generic_visible = set(
            frappe.get_list(
                "File",
                filters={"name": ["in", [own_generic_file.name, foreign_generic_file.name]]},
                pluck="name",
                limit_page_length=0,
            )
        )
        self.assertIn(own_generic_file.name, generic_visible)
        self.assertNotIn(foreign_generic_file.name, generic_visible)

    def test_closed_assignments_revoke_whole_project_visibility(self) -> None:
        project_object = frappe.get_doc(
            "Ferum Project Object", self.engineer_chain["project_object"]
        )
        project_object.effective_to = date.today()
        project_object.save(ignore_permissions=True)
        frappe.set_user(self.engineer)
        self.assertFalse(
            frappe.has_permission("Ferum Service Project", "read", doc=self.engineer_project.name)
        )
        self.assertNotIn(
            self.engineer_chain["service_object"],
            frappe.get_list("Ferum Service Object", pluck="name", limit_page_length=0),
        )

        frappe.set_user("Administrator")
        frappe.db.set_value(
            "Ferum Project Document", self.office_document.name, "status", "Archived"
        )
        frappe.set_user(self.office)
        self.assertFalse(
            frappe.has_permission("Ferum Service Project", "read", doc=self.office_project.name)
        )
        self.assertFalse(
            frappe.has_permission("Ferum Project Document", "read", doc=self.office_document.name)
        )

    def test_every_registered_query_builds_under_the_role_that_can_read_it(self) -> None:
        """Execute every hook-generated SQL condition, not merely string-check it."""

        for role, user in (("Инженер", self.engineer), ("Офис-менеджер", self.office)):
            frappe.set_user(user)
            for doctype in sorted(DIRECT_PROJECT_DOCTYPES | INDIRECT_PROJECT_DOCTYPES):
                read_roles = {row.role for row in frappe.get_meta(doctype).permissions if row.read}
                if role not in read_roles:
                    continue
                frappe.get_list(doctype, fields=["name"], limit_page_length=1)

    def test_record_policy_fails_closed_for_every_direct_surface(self) -> None:
        frappe.set_user(self.engineer)
        for doctype in sorted(DIRECT_PROJECT_DOCTYPES):
            own = frappe._dict(
                doctype=doctype,
                name=f"OWN-{uuid4().hex[:8]}",
                service_project=self.engineer_project.name,
            )
            foreign = frappe._dict(
                doctype=doctype,
                name=f"FOREIGN-{uuid4().hex[:8]}",
                service_project=self.foreign_engineer_project.name,
            )
            orphan = frappe._dict(
                doctype=doctype,
                name=f"ORPHAN-{uuid4().hex[:8]}",
            )
            self.assertIsNone(has_project_graph_permission(own, "read", self.engineer))
            self.assertFalse(has_project_graph_permission(foreign, "read", self.engineer), doctype)
            self.assertFalse(has_project_graph_permission(orphan, "read", self.engineer), doctype)

    def _make_user(self, role: str) -> str:
        email = f"acl-{uuid4().hex[:12]}@example.invalid"
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": f"ACL {role}",
                "enabled": 1,
                "send_welcome_email": 0,
                "user_type": "System User",
            }
        ).insert(ignore_permissions=True)
        user.add_roles(role)
        return email

    def _make_object_chain(
        self, project, *, responsible_engineer: str | None = None
    ) -> dict[str, str]:
        service_object = frappe.get_doc(
            {
                "doctype": "Ferum Service Object",
                "object_name": f"ACL object {uuid4().hex[:10]}",
                "customer": project.customer,
                "address": _make_address(project.customer, "ACL runtime"),
            }
        ).insert(ignore_permissions=True)
        project_object = frappe.get_doc(
            {
                "doctype": "Ferum Project Object",
                "service_project": project.name,
                "service_object": service_object.name,
                "effective_from": project.contract_date or date.today(),
                "responsible_engineer": responsible_engineer,
            }
        ).insert(ignore_permissions=True)
        object_system = frappe.get_doc(
            {
                "doctype": "Ferum Object System",
                "service_object": service_object.name,
                "system_type": "Other",
                "system_name": f"ACL system {uuid4().hex[:10]}",
            }
        ).insert(ignore_permissions=True)
        return {
            "service_object": service_object.name,
            "project_object": project_object.name,
            "object_system": object_system.name,
        }

    def _make_request(self, project, chain: dict[str, str]):
        return frappe.get_doc(
            {
                "doctype": "Ferum Service Request",
                "service_project": project.name,
                "project_object": chain["project_object"],
                "object_system": chain["object_system"],
                "subject": f"ACL request {uuid4().hex[:10]}",
                "description": "Synthetic project-graph permission proof",
                "source_type": "Customer",
                "request_type": "Other",
                "requested_at": now_datetime(),
            }
        ).insert(ignore_permissions=True)

    def _make_document(self, project: str, *, owner_user: str):
        return frappe.get_doc(
            {
                "doctype": "Ferum Project Document",
                "source_doctype": "Ferum Service Project",
                "source_name": project,
                "document_type": "Other",
                "document_number": f"ACL-{uuid4().hex[:12]}",
                "document_date": date.today(),
                "version": "1",
                "owner_user": owner_user,
            }
        ).insert(ignore_permissions=True)
