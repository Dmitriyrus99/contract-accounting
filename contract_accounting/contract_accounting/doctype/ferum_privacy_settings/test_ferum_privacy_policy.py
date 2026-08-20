"""Synthetic Bench acceptance for FR-06 privacy, readiness and controls."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime
from frappe.utils.file_manager import save_file
from PIL import Image
from pypdf import PdfWriter

from contract_accounting.api.contractors import (
    change_contractor_assignment_status,
    create_contractor_assignment,
    evaluate_contractor_readiness,
)
from contract_accounting.api.privacy import (
    activate_privacy_policy,
    create_contractor_worker,
    create_personnel_credential,
    deactivate_privacy_policy,
    download_credential_attachment,
    expire_personnel_credentials,
    get_contractor_worker,
    get_personnel_credential,
    get_supplier_qualification_summary,
    record_credential_scan_result,
    record_privacy_event,
    revoke_or_reject_credential,
    transition_contractor_worker,
    verify_credential_applicability,
    verify_credential_source,
)
from contract_accounting.api.privacy_controls import (
    approve_break_glass,
    approve_legal_hold,
    approve_legal_hold_release,
    has_active_break_glass,
    request_break_glass,
    request_legal_hold,
    request_legal_hold_release,
)
from contract_accounting.api.privacy_event_retention import anonymize_expired_privacy_events
from contract_accounting.api.privacy_retention import get_privacy_retention_plan
from contract_accounting.contract_accounting.doctype.ferum_privacy_break_glass.ferum_privacy_break_glass import (
    BREAK_GLASS_WRITE_FLAG,
)
from contract_accounting.contract_accounting.doctype.ferum_privacy_legal_hold.ferum_privacy_legal_hold import (
    LEGAL_HOLD_WRITE_FLAG,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
    _make_address,
    _make_project,
)
from contract_accounting.domain.privacy import SYNTHETIC_ACTIVATION_CONFIRMATION
from contract_accounting.patches.v0_20_0.migrate_credential_number_to_password import (
    execute as migrate_credential_numbers,
)


class TestFerumPrivacyPolicy(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.previous_user = frappe.session.user
        self.previous_developer_mode = frappe.conf.get("developer_mode")
        frappe.conf.developer_mode = 1
        frappe.set_user("Administrator")
        if frappe.db.get_single_value("Ferum Privacy Settings", "enabled"):
            deactivate_privacy_policy("Reset synthetic privacy test state")
        token = uuid4().hex[:10]
        self.product_owner = self._make_user(token, "po", "Генеральный директор")
        self.data_owner = self._make_user(token, "data", "Менеджер персональных данных")
        self.verifier = self._make_user(token, "verify", "Проверяющий допуски")
        self.dpo = self._make_user(token, "dpo", "Ответственный за ПДн")
        self.dual_approver = self._make_user(token, "dual", "Ответственный за ПДн")
        frappe.get_doc("User", self.dual_approver).add_roles(
            "Ответственный за ИБ", "Генеральный директор"
        )
        self.security = self._make_user(token, "security", "Ответственный за ИБ")
        self.support = self._make_user(token, "support", "System Manager")
        self.tender = self._make_user(token, "tender", "Тендерный специалист")
        self.project_manager = self._make_user(token, "pm", "Руководитель проектов")
        self.engineer = self._make_user(token, "engineer", "Инженер")
        self.accountant = self._make_user(token, "accountant", "Бухгалтер")
        self.contractor = self._make_user(token, "contractor", "Подрядчик")
        self.supplier = self._make_supplier(token)
        frappe.set_user(self.product_owner)
        activate_privacy_policy(
            "Synthetic Test",
            SYNTHETIC_ACTIVATION_CONFIRMATION,
            f"TEST-FR06-{token}",
            "Synthetic FR-06 runtime acceptance only",
        )

    def tearDown(self) -> None:
        try:
            frappe.set_user(self.product_owner)
            if frappe.db.get_single_value("Ferum Privacy Settings", "enabled"):
                deactivate_privacy_policy("Disable policy after synthetic runtime test")
        finally:
            frappe.conf.developer_mode = self.previous_developer_mode
            frappe.set_user(self.previous_user)
            super().tearDown()

    def test_worker_credential_dual_verification_and_masking(self) -> None:
        worker = self._active_worker()
        self._scope_worker_to_project(worker, self.verifier)
        frappe.set_user(self.data_owner)
        credential = create_personnel_credential(
            "Ferum Contractor Worker",
            worker,
            "Electrical Safety",
            "ES-12345678",
            "TEST-SUPPLIER-BASIS",
            issued_on=str(date.today()),
            no_expiry=1,
            issuer="Synthetic Training Centre",
        )["credential"]
        source = verify_credential_source(credential, "Synthetic source verified by data owner")
        self.assertEqual(source["verification_status"], "Draft")
        frappe.set_user(self.verifier)
        verified = verify_credential_applicability(
            credential, "Synthetic applicability verified for scoped work"
        )
        self.assertEqual(verified["verification_status"], "Verified")
        self.assertEqual(verified["credential_number"], "••••5678")
        frappe.set_user(self.tender)
        summary = get_supplier_qualification_summary(
            self.supplier, "Synthetic tender qualification check"
        )
        self.assertEqual(summary["qualifications"][0]["valid_count"], 1)
        self.assertNotIn("holder", summary["qualifications"][0])
        self.assertNotIn("credential_number", summary["qualifications"][0])
        self.assertGreaterEqual(
            frappe.db.count(
                "Ferum Privacy Event",
                {"target_doctype": "Ferum Personnel Credential", "target_name": credential},
            ),
            3,
        )

        direct = frappe.get_doc("Ferum Personnel Credential", credential)
        direct.issuer = "Forbidden direct edit"
        with self.assertRaises(frappe.PermissionError):
            direct.save(ignore_permissions=True)

        frappe.set_user(self.data_owner)
        expired = create_personnel_credential(
            "Ferum Contractor Worker",
            worker,
            "Occupational Safety",
            "OSH-EXPIRED-01",
            "TEST-SUPPLIER-BASIS",
            issued_on=str(date.today() - timedelta(days=365)),
            expires_on=str(date.today() - timedelta(days=1)),
        )["credential"]
        verify_credential_source(expired, "Synthetic expired source evidence checked")
        frappe.set_user(self.verifier)
        verify_credential_applicability(expired, "Synthetic expired applicability checked")
        self.assertEqual(expire_personnel_credentials(), 1)
        self.assertEqual(
            frappe.db.get_value("Ferum Personnel Credential", expired, "verification_status"),
            "Expired",
        )

    def test_three_year_privacy_event_anonymization_clears_pii_and_standard_artifacts(
        self,
    ) -> None:
        event_name = record_privacy_event(
            "Synthetic Expired Audit",
            "Ferum Privacy Settings",
            "Ferum Privacy Settings",
            "Synthetic PII event eligible for three-year minimization",
            {"subject": "synthetic PII"},
        )
        expired_at = now_datetime() - timedelta(days=365 * 4)
        frappe.db.set_value(
            "Ferum Privacy Event", event_name, "occurred_at", expired_at, update_modified=False
        )
        frappe.get_doc(
            {
                "doctype": "Version",
                "ref_doctype": "Ferum Privacy Event",
                "docname": event_name,
                "data": json.dumps({"pii": "synthetic secret"}),
            }
        ).insert(ignore_permissions=True)
        frappe.get_doc(
            {
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": "Ferum Privacy Event",
                "reference_name": event_name,
                "content": "synthetic PII comment",
            }
        ).insert(ignore_permissions=True)
        frappe.get_doc(
            {
                "doctype": "Activity Log",
                "subject": "synthetic PII activity",
                "reference_doctype": "Ferum Privacy Event",
                "reference_name": event_name,
            }
        ).insert(ignore_permissions=True)

        with patch(
            "contract_accounting.api.privacy_event_retention.frappe.get_all",
            return_value=[event_name],
        ):
            self.assertEqual(anonymize_expired_privacy_events(), 1)
        minimized = frappe.db.get_value(
            "Ferum Privacy Event",
            event_name,
            (
                "target_name",
                "actor",
                "reason",
                "ticket",
                "payload_json",
                "event_type",
                "occurred_at",
                "correlation_key",
                "anonymized_at",
                "anonymization_hash",
            ),
            as_dict=True,
        )
        for fieldname in ("target_name", "actor", "reason", "ticket", "payload_json"):
            self.assertFalse(minimized.get(fieldname))
        self.assertTrue(minimized.event_type)
        self.assertTrue(minimized.occurred_at)
        self.assertTrue(minimized.correlation_key)
        self.assertTrue(minimized.anonymized_at)
        self.assertEqual(len(minimized.anonymization_hash), 64)
        self.assertFalse(
            frappe.db.exists(
                "Version", {"ref_doctype": "Ferum Privacy Event", "docname": event_name}
            )
        )
        for doctype in ("Comment", "Activity Log"):
            self.assertFalse(
                frappe.db.exists(
                    doctype,
                    {
                        "reference_doctype": "Ferum Privacy Event",
                        "reference_name": event_name,
                    },
                )
            )

        held_event = record_privacy_event(
            "Synthetic Retention Hold",
            "Ferum Privacy Settings",
            "Ferum Privacy Settings",
            "Synthetic event awaiting legal review",
            {"subject": "synthetic PII"},
        )
        frappe.db.set_value(
            "Ferum Privacy Event", held_event, "occurred_at", expired_at, update_modified=False
        )
        self.assertTrue(frappe.db.exists("Ferum Privacy Event", held_event))
        frappe.set_user(self.dpo)
        request_legal_hold(
            "Ferum Privacy Event",
            held_event,
            "Pending hold blocks audit minimization",
            str(date.today() + timedelta(days=30)),
        )
        with patch(
            "contract_accounting.api.privacy_event_retention.frappe.get_all",
            return_value=[held_event],
        ):
            self.assertEqual(anonymize_expired_privacy_events(), 0)
        self.assertFalse(frappe.db.get_value("Ferum Privacy Event", held_event, "anonymized_at"))

    def test_break_glass_and_joint_legal_hold_are_exact_target(self) -> None:
        worker = self._active_worker()
        frappe.set_user(self.support)
        frappe.local.response = frappe._dict()
        denied = get_contractor_worker(worker, "Support typed Worker read without active grant")
        self.assertEqual(denied, {"ok": False, "error": "permission_denied"})
        self.assertEqual(frappe.local.response.http_status_code, 403)
        request = request_break_glass(
            "TEST-INC-001",
            "Investigate exact synthetic worker record",
            "Ferum Contractor Worker",
            worker,
            "Read",
            60,
        )["break_glass"]
        frappe.set_user(self.security)
        self.assertEqual(
            approve_break_glass(request, "Security", "Security approves exact read only")["status"],
            "Partially Approved",
        )
        frappe.set_user(self.dpo)
        self.assertEqual(
            approve_break_glass(request, "DPO", "DPO approves exact synthetic read only")["status"],
            "Active",
        )
        self.assertTrue(
            has_active_break_glass(self.support, "Ferum Contractor Worker", worker, "Read")
        )
        self.assertFalse(
            has_active_break_glass(self.support, "Ferum Personnel Credential", worker, "Read")
        )
        frappe.set_user(self.support)
        self.assertFalse(frappe.has_permission("Ferum Contractor Worker", "read", doc=worker))
        self.assertEqual(
            frappe.get_list("Ferum Contractor Worker", filters={"name": worker}, pluck="name"),
            [],
        )
        typed_worker = get_contractor_worker(
            worker, "Support uses exact active typed Worker Read grant"
        )
        self.assertEqual(set(typed_worker), {"worker", "worker_external_id", "status"})
        self.assertTrue(
            frappe.db.exists(
                "Ferum Privacy Event",
                {"target_name": worker, "event_type": "Worker Typed Read"},
            )
        )

        frappe.set_user(self.data_owner)
        hold = request_legal_hold(
            "Ferum Contractor Worker",
            worker,
            "Synthetic investigation requires retention pause",
            str(date.today() + timedelta(days=30)),
        )["legal_hold"]
        frappe.set_user(self.dpo)
        self.assertEqual(
            approve_legal_hold(hold, "Legal", "Legal approves exact synthetic hold")["status"],
            "Pending",
        )
        frappe.set_user(self.product_owner)
        self.assertEqual(
            approve_legal_hold(
                hold, "Product Owner", "Product Owner approves exact synthetic hold"
            )["status"],
            "Active",
        )
        frappe.set_user(self.dpo)
        plan = get_privacy_retention_plan(str(date.today() + timedelta(days=365 * 4)))
        held_actions = [row for row in plan["actions"] if row["target_name"] == worker]
        self.assertTrue(held_actions)
        self.assertTrue(all(row["blocked_by_legal_hold"] for row in held_actions))

    def test_control_approvals_require_explicit_roles_and_distinct_actors(self) -> None:
        worker = self._active_worker()
        frappe.set_user(self.support)
        request = request_break_glass(
            "TEST-INC-SOD-001",
            "Validate strict synthetic break-glass separation",
            "Ferum Contractor Worker",
            worker,
            "Read",
            60,
        )["break_glass"]

        frappe.set_user("Administrator")
        with self.assertRaises(frappe.PermissionError):
            approve_break_glass(request, "DPO", "Administrator is not a DPO approver")

        frappe.set_user(self.dual_approver)
        self.assertEqual(
            approve_break_glass(request, "DPO", "Dual-role user records DPO approval")["status"],
            "Partially Approved",
        )
        with self.assertRaises(frappe.PermissionError):
            approve_break_glass(
                request,
                "Security",
                "Same user must not provide the second approval",
            )
        invalid_request = frappe.get_doc("Ferum Privacy Break Glass", request)
        invalid_request.security_approved_by = self.dual_approver
        invalid_request.security_approved_at = now_datetime()
        invalid_request.status = "Active"
        invalid_request.activated_at = now_datetime()
        invalid_request.expires_at = now_datetime() + timedelta(minutes=60)
        previous_writer = frappe.flags.get(BREAK_GLASS_WRITE_FLAG)
        try:
            frappe.flags[BREAK_GLASS_WRITE_FLAG] = True
            with self.assertRaisesRegex(frappe.ValidationError, "разными"):
                invalid_request.save(ignore_permissions=True)
        finally:
            frappe.flags[BREAK_GLASS_WRITE_FLAG] = previous_writer
        frappe.set_user(self.security)
        self.assertEqual(
            approve_break_glass(request, "Security", "Independent security approval")["status"],
            "Active",
        )

        frappe.set_user(self.data_owner)
        hold = request_legal_hold(
            "Ferum Contractor Worker",
            worker,
            "Validate strict synthetic legal hold separation",
            str(date.today() + timedelta(days=30)),
        )["legal_hold"]
        frappe.set_user("Administrator")
        with self.assertRaises(frappe.PermissionError):
            request_legal_hold(
                "Ferum Contractor Worker",
                worker,
                "Administrator cannot substitute for a legal hold requester",
                str(date.today() + timedelta(days=30)),
            )
        with self.assertRaises(frappe.PermissionError):
            approve_legal_hold(hold, "Legal", "Administrator is not a Legal approver")
        frappe.set_user(self.dpo)
        approve_legal_hold(hold, "Legal", "Independent legal activation approval")
        invalid_hold = frappe.get_doc("Ferum Privacy Legal Hold", hold)
        invalid_hold.product_owner_approved_by = self.dpo
        invalid_hold.product_owner_approved_at = now_datetime()
        invalid_hold.status = "Active"
        previous_writer = frappe.flags.get(LEGAL_HOLD_WRITE_FLAG)
        try:
            frappe.flags[LEGAL_HOLD_WRITE_FLAG] = True
            with self.assertRaisesRegex(frappe.ValidationError, "разными"):
                invalid_hold.save(ignore_permissions=True)
        finally:
            frappe.flags[LEGAL_HOLD_WRITE_FLAG] = previous_writer
        frappe.set_user(self.product_owner)
        self.assertEqual(
            approve_legal_hold(
                hold,
                "Product Owner",
                "Independent product owner activation approval",
            )["status"],
            "Active",
        )

        frappe.set_user(self.dpo)
        request_legal_hold_release(hold, "Independent release review requested")
        frappe.set_user("Administrator")
        with self.assertRaises(frappe.PermissionError):
            request_legal_hold_release(
                hold, "Administrator cannot substitute for a release requester"
            )
        with self.assertRaises(frappe.PermissionError):
            approve_legal_hold_release(
                hold, "Legal", "Administrator is not a Legal release approver"
            )
        frappe.set_user(self.dual_approver)
        self.assertEqual(
            approve_legal_hold_release(hold, "Legal", "Independent legal release approval")[
                "status"
            ],
            "Release Pending",
        )
        with self.assertRaises(frappe.PermissionError):
            approve_legal_hold_release(
                hold,
                "Product Owner",
                "Same user must not provide both release approvals",
            )
        frappe.set_user(self.product_owner)
        self.assertEqual(
            approve_legal_hold_release(
                hold,
                "Product Owner",
                "Independent product owner release approval",
            )["status"],
            "Released",
        )

    def test_cross_role_scope_masking_report_and_export_boundaries(self) -> None:
        worker = self._active_worker()
        foreign_worker = self._active_worker()
        frappe.set_user(self.data_owner)
        credential = create_personnel_credential(
            "Ferum Contractor Worker",
            worker,
            "Electrical Safety",
            "SCOPE-12345678",
            "TEST-SUPPLIER-BASIS",
            no_expiry=1,
        )["credential"]
        foreign_credential = create_personnel_credential(
            "Ferum Contractor Worker",
            foreign_worker,
            "Occupational Safety",
            "FOREIGN-87654321",
            "TEST-SUPPLIER-BASIS",
            no_expiry=1,
        )["credential"]
        verify_credential_source(credential, "Scoped source evidence checked")
        verify_credential_source(foreign_credential, "Foreign source evidence checked")
        self._scope_worker_to_project(worker)

        frappe.set_user(self.project_manager)
        verified = verify_credential_applicability(
            credential, "Scoped project applicability checked"
        )
        self.assertEqual(verified["verification_status"], "Verified")
        projection = get_personnel_credential(
            credential, "Scoped verifier requests masked credential projection"
        )
        self.assertEqual(projection["credential_number"], "••••5678")
        self.assertEqual(
            frappe.get_list(
                "Ferum Personnel Credential",
                filters={"name": ["in", [credential, foreign_credential]]},
                pluck="name",
            ),
            [credential],
        )
        self.assertTrue(
            frappe.has_permission(
                "Ferum Personnel Credential", "report", doc=credential, user=self.project_manager
            )
        )
        self.assertFalse(
            frappe.has_permission(
                "Ferum Personnel Credential", "export", doc=credential, user=self.project_manager
            )
        )
        frappe.local.response = frappe._dict()
        denied_foreign = get_personnel_credential(
            foreign_credential, "Unscoped verifier requests foreign credential"
        )
        self.assertEqual(denied_foreign, {"ok": False, "error": "permission_denied"})
        self.assertEqual(frappe.local.response.http_status_code, 403)

        frappe.set_user(self.verifier)
        verifier_doc = frappe.get_doc("Ferum Personnel Credential", credential)
        self.assertEqual(verifier_doc.credential_number_masked, "••••5678")
        with self.assertRaises(frappe.PermissionError):
            verify_credential_applicability(
                foreign_credential, "Unscoped applicability must be rejected"
            )

        frappe.set_user(self.engineer)
        engineer_projection = get_personnel_credential(
            credential, "Scoped engineer requests minimal credential projection"
        )
        self.assertNotIn("credential_number", engineer_projection)
        self.assertEqual(
            frappe.get_list(
                "Ferum Contractor Worker",
                filters={"name": ["in", [worker, foreign_worker]]},
                pluck="name",
            ),
            [worker],
        )
        self.assertTrue(
            frappe.has_permission(
                "Ferum Contractor Worker", "report", doc=worker, user=self.engineer
            )
        )
        self.assertFalse(
            frappe.has_permission(
                "Ferum Personnel Credential", "export", doc=credential, user=self.engineer
            )
        )

        office_user = frappe.get_doc("User", self.accountant)
        office_user.set("roles", [])
        office_user.append("roles", {"role": "Офис-менеджер"})
        office_user.save(ignore_permissions=True)
        for user in (self.data_owner, self.dpo, self.product_owner, self.accountant):
            frappe.set_user(user)
            standard_doc = frappe.get_doc("Ferum Personnel Credential", credential).as_dict()
            self.assertNotIn("SCOPE-12345678", json.dumps(standard_doc, default=str))
            standard_list = frappe.get_list(
                "Ferum Personnel Credential",
                filters={"name": credential},
                fields=["name", "credential_number"],
            )
            self.assertNotIn("SCOPE-12345678", json.dumps(standard_list, default=str))
            full = get_personnel_credential(
                credential, "Approved single-record full read for synthetic UAT"
            )
            self.assertEqual(full["credential_number"], "SCOPE-12345678")
            self.assertFalse(
                frappe.has_permission(
                    "Ferum Personnel Credential", "export", doc=credential, user=user
                )
            )
        frappe.set_user(self.accountant)
        self.assertEqual(
            set(
                frappe.get_list(
                    "Ferum Personnel Credential",
                    filters={"name": ["in", [credential, foreign_credential]]},
                    pluck="name",
                )
            ),
            {credential, foreign_credential},
        )
        frappe.set_user("Administrator")
        accountant_user = frappe.get_doc("User", self.accountant)
        accountant_user.set("roles", [])
        accountant_user.append("roles", {"role": "Бухгалтер"})
        accountant_user.save(ignore_permissions=True)

        for user in (
            self.security,
            self.accountant,
            self.contractor,
            self.support,
            self.tender,
        ):
            self.assertFalse(
                frappe.has_permission(
                    "Ferum Personnel Credential", "read", doc=credential, user=user
                )
            )
            self.assertFalse(
                frappe.has_permission("Ferum Contractor Worker", "read", doc=worker, user=user)
            )

    def test_private_file_scanner_download_and_exact_break_glass(self) -> None:
        worker = self._active_worker()
        self._scope_worker_to_project(worker)
        content = self._image_bytes("PNG", (255, 0, 0))
        frappe.set_user(self.data_owner)
        file_doc = save_file(
            "fr06-synthetic.png", content, "Ferum Contractor Worker", worker, is_private=1
        )
        credential = create_personnel_credential(
            "Ferum Contractor Worker",
            worker,
            "Electrical Safety",
            "FILE-12345678",
            "TEST-SUPPLIER-BASIS",
            no_expiry=1,
            document=file_doc.name,
        )["credential"]
        with self.assertRaisesRegex(frappe.ValidationError, "Clean malware"):
            verify_credential_source(credential, "Pending file must block source verification")
        self.assertFalse(
            frappe.has_permission("File", "read", doc=file_doc.name, user=self.data_owner)
        )

        frappe.set_user(self.security)
        scan = record_credential_scan_result(
            credential,
            "Clean",
            "TEST-SCANNER-CLEAN-001",
            "Synthetic scanner reports clean attachment",
        )
        self.assertEqual(set(scan), {"credential", "malware_status", "verification_status"})
        self.assertEqual(scan["malware_status"], "Clean")
        scanned_hash = frappe.db.get_value(
            "Ferum Personnel Credential", credential, "scanned_file_hash"
        )
        self.assertEqual(scanned_hash, hashlib.sha256(content).hexdigest())
        self.assertNotEqual(
            scanned_hash, frappe.db.get_value("File", file_doc.name, "content_hash")
        )
        frappe.local.response = frappe._dict()
        denied = download_credential_attachment(
            credential, "Security has metadata access but no business file access"
        )
        self.assertEqual(denied, {"ok": False, "error": "permission_denied"})
        self.assertEqual(frappe.local.response.http_status_code, 403)
        self.assertTrue(
            frappe.db.exists(
                "Ferum Privacy Event",
                {
                    "target_name": credential,
                    "event_type": "Credential Attachment Download Denied",
                },
            )
        )

        frappe.set_user(self.data_owner)
        verify_credential_source(credential, "Clean attachment source evidence checked")
        frappe.local.response = frappe._dict()
        download_credential_attachment(
            credential, "Data owner downloads exact clean attachment for verification"
        )
        self.assertEqual(frappe.local.response.filecontent, content)
        original_hash = frappe.db.get_value("File", file_doc.name, "content_hash")
        frappe.set_user("Administrator")
        frappe.db.set_value("File", file_doc.name, "content_hash", "synthetic-drift")
        frappe.set_user(self.data_owner)
        frappe.local.response = frappe._dict()
        download_credential_attachment(
            credential, "Metadata hash drift does not replace real byte verification"
        )
        self.assertEqual(frappe.local.response.filecontent, content)
        frappe.set_user("Administrator")
        frappe.db.set_value("File", file_doc.name, "content_hash", original_hash)
        file_path = Path(file_doc.get_full_path())
        original_bytes = file_path.read_bytes()
        try:
            file_path.write_bytes(b"synthetic tampered bytes")
            frappe.set_user(self.data_owner)
            with self.assertRaisesRegex(frappe.PermissionError, "изменён после malware scan"):
                download_credential_attachment(
                    credential, "Changed real bytes must invalidate the scanner decision"
                )
        finally:
            file_path.write_bytes(original_bytes)

        frappe.set_user(self.project_manager)
        verify_credential_applicability(
            credential, "Project-scoped applicability and attachment checked"
        )
        frappe.local.response = frappe._dict()
        download_credential_attachment(
            credential, "Project verifier downloads exact clean attachment"
        )
        self.assertEqual(frappe.local.response.filecontent, content)

        frappe.set_user(self.engineer)
        frappe.local.response = frappe._dict()
        denied = download_credential_attachment(
            credential, "Engineer must not receive credential attachment"
        )
        self.assertEqual(denied, {"ok": False, "error": "permission_denied"})
        self.assertEqual(frappe.local.response.http_status_code, 403)

        frappe.set_user(self.support)
        frappe.local.response = frappe._dict()
        denied_read = get_personnel_credential(
            credential,
            "Support typed read without an approved exact-target grant",
        )
        self.assertEqual(denied_read, {"ok": False, "error": "permission_denied"})
        self.assertEqual(frappe.local.response.http_status_code, 403)
        read_request = request_break_glass(
            "TEST-INC-READ-001",
            "Investigate exact synthetic credential metadata",
            "Ferum Personnel Credential",
            credential,
            "Read",
            60,
        )["break_glass"]
        frappe.set_user(self.security)
        approve_break_glass(read_request, "Security", "Security approves exact typed read")
        frappe.set_user(self.dpo)
        approve_break_glass(read_request, "DPO", "DPO approves exact typed read")
        frappe.set_user(self.support)
        self.assertFalse(
            frappe.has_permission("Ferum Personnel Credential", "read", doc=credential)
        )
        self.assertEqual(
            frappe.get_list(
                "Ferum Personnel Credential", filters={"name": credential}, pluck="name"
            ),
            [],
        )
        allowed_read = get_personnel_credential(
            credential,
            "Support uses approved exact-target typed metadata read",
        )
        self.assertNotEqual(allowed_read, {"ok": False, "error": "permission_denied"})
        self.assertNotIn("credential_number", allowed_read)
        self.assertTrue(
            frappe.db.exists(
                "Ferum Privacy Event",
                {"target_name": credential, "event_type": "Credential Break Glass Read"},
            )
        )

        request = request_break_glass(
            "TEST-INC-FILE-001",
            "Investigate exact synthetic credential file",
            "File",
            file_doc.name,
            "Download",
            60,
        )["break_glass"]
        frappe.set_user(self.security)
        approve_break_glass(request, "Security", "Security approves exact file download")
        frappe.set_user(self.dpo)
        approve_break_glass(request, "DPO", "DPO approves exact file download")
        frappe.set_user(self.support)
        self.assertFalse(frappe.has_permission("File", "read", doc=file_doc.name))
        self.assertFalse(frappe.has_permission("File", "write", doc=file_doc.name))
        self.assertFalse(frappe.has_permission("File", "delete", doc=file_doc.name))
        frappe.local.response = frappe._dict()
        download_credential_attachment(credential, "Support uses approved exact-target break-glass")
        self.assertEqual(frappe.local.response.filecontent, content)

        frappe.set_user("Administrator")
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc("File", file_doc.name).delete(ignore_permissions=True)
        self.assertEqual(frappe.get_doc("File", file_doc.name).get_content(), content)

        frappe.set_user(self.data_owner)
        rejected_file = save_file(
            "fr06-rejected.png",
            self._image_bytes("PNG", (0, 0, 255)),
            "Ferum Contractor Worker",
            worker,
            is_private=1,
        )
        rejected = create_personnel_credential(
            "Ferum Contractor Worker",
            worker,
            "Work at Height",
            "FILE-REJECTED-01",
            "TEST-SUPPLIER-BASIS",
            no_expiry=1,
            document=rejected_file.name,
        )["credential"]
        frappe.set_user(self.security)
        rejected_scan = record_credential_scan_result(
            rejected,
            "Rejected",
            "TEST-SCANNER-REJECT-001",
            "Synthetic scanner rejects attachment payload",
        )
        self.assertEqual(rejected_scan["malware_status"], "Rejected")
        with self.assertRaisesRegex(frappe.ValidationError, "нельзя повторно"):
            record_credential_scan_result(
                rejected,
                "Clean",
                "TEST-SCANNER-RESCAN-001",
                "Rejected payload must use an explicit replacement credential",
            )
        frappe.set_user(self.data_owner)
        with self.assertRaisesRegex(frappe.ValidationError, "Clean scan"):
            download_credential_attachment(rejected, "Rejected attachment cannot be downloaded")

        for file_name, allowed_content, credential_type in (
            (
                "fr06-allowed.jpg",
                self._image_bytes("JPEG", (255, 0, 255)),
                "Occupational Safety",
            ),
            ("fr06-allowed.pdf", self._pdf_bytes(), "Other Mandatory"),
        ):
            allowed_file = save_file(
                file_name,
                allowed_content,
                "Ferum Contractor Worker",
                worker,
                is_private=1,
            )
            allowed = create_personnel_credential(
                "Ferum Contractor Worker",
                worker,
                credential_type,
                f"ALLOWED-{credential_type.upper().replace(' ', '-')}",
                "TEST-SUPPLIER-BASIS",
                no_expiry=1,
                document=allowed_file.name,
            )
            self.assertEqual(allowed["malware_status"], "Pending")

        public_file = save_file(
            "fr06-public.png",
            self._image_bytes("PNG", (0, 255, 0)),
            "Ferum Contractor Worker",
            worker,
            is_private=0,
        )
        with self.assertRaisesRegex(frappe.ValidationError, "private"):
            create_personnel_credential(
                "Ferum Contractor Worker",
                worker,
                "Professional Qualification",
                "PUBLIC-FILE-01",
                "TEST-SUPPLIER-BASIS",
                no_expiry=1,
                document=public_file.name,
            )
        forbidden_file = save_file(
            "fr06-forbidden.docx",
            b"synthetic office payload",
            "Ferum Contractor Worker",
            worker,
            is_private=1,
        )
        with self.assertRaisesRegex(frappe.ValidationError, "allowlist"):
            create_personnel_credential(
                "Ferum Contractor Worker",
                worker,
                "Professional Qualification",
                "FORBIDDEN-FILE-01",
                "TEST-SUPPLIER-BASIS",
                no_expiry=1,
                document=forbidden_file.name,
            )
        oversized_file = save_file(
            "fr06-oversized.png",
            self._image_bytes("PNG", (255, 255, 0)),
            "Ferum Contractor Worker",
            worker,
            is_private=1,
        )
        frappe.db.set_value(
            "File", oversized_file.name, "file_size", 10 * 1024 * 1024 + 1, update_modified=False
        )
        with self.assertRaisesRegex(frappe.ValidationError, "10 MB"):
            create_personnel_credential(
                "Ferum Contractor Worker",
                worker,
                "Professional Qualification",
                "OVERSIZED-FILE-01",
                "TEST-SUPPLIER-BASIS",
                no_expiry=1,
                document=oversized_file.name,
            )

    def test_scanner_hashes_real_bytes_and_download_rejects_byte_tamper(self) -> None:
        worker = self._active_worker()
        content = self._image_bytes("PNG", (12, 34, 56))
        frappe.set_user(self.data_owner)
        file_doc = save_file(
            "fr06-byte-hash.png", content, "Ferum Contractor Worker", worker, is_private=1
        )
        credential = create_personnel_credential(
            "Ferum Contractor Worker",
            worker,
            "Electrical Safety",
            "BYTE-HASH-12345678",
            "TEST-SUPPLIER-BASIS",
            no_expiry=1,
            document=file_doc.name,
        )["credential"]
        frappe.set_user(self.security)
        record_credential_scan_result(
            credential,
            "Clean",
            "TEST-SCANNER-SHA256-001",
            "Scanner hashes the exact synthetic attachment bytes",
        )
        scanned_hash = frappe.db.get_value(
            "Ferum Personnel Credential", credential, "scanned_file_hash"
        )
        self.assertEqual(scanned_hash, hashlib.sha256(content).hexdigest())
        self.assertNotEqual(
            scanned_hash, frappe.db.get_value("File", file_doc.name, "content_hash")
        )

        frappe.set_user(self.data_owner)
        frappe.local.response = frappe._dict()
        download_credential_attachment(credential, "Download verifies exact clean bytes")
        self.assertEqual(frappe.local.response.filecontent, content)
        file_path = Path(file_doc.get_full_path())
        original_bytes = file_path.read_bytes()
        try:
            file_path.write_bytes(b"synthetic byte-level tamper")
            with self.assertRaisesRegex(frappe.PermissionError, "изменён после malware scan"):
                download_credential_attachment(
                    credential, "Byte-level tamper must invalidate the scan result"
                )
        finally:
            file_path.write_bytes(original_bytes)

    def test_legacy_plaintext_credential_number_patch_is_idempotent(self) -> None:
        from frappe.utils.password import remove_encrypted_password

        worker = self._active_worker()
        frappe.set_user(self.data_owner)
        native_number = "TEST-NATIVE-87654321"
        native_credential = create_personnel_credential(
            "Ferum Contractor Worker",
            worker,
            "Occupational Safety",
            native_number,
            "TEST-SUPPLIER-BASIS",
            no_expiry=1,
        )["credential"]
        legacy_number = "TEST-LEGACY-12345678"
        credential = create_personnel_credential(
            "Ferum Contractor Worker",
            worker,
            "Electrical Safety",
            legacy_number,
            "TEST-SUPPLIER-BASIS",
            no_expiry=1,
        )["credential"]
        remove_encrypted_password("Ferum Personnel Credential", credential, "credential_number")
        frappe.db.sql(
            """update `tabFerum Personnel Credential`
               set credential_number = %s
               where name = %s""",
            (legacy_number, credential),
        )

        first = migrate_credential_numbers()
        self.assertEqual(first["migrated"], 1)
        self.assertGreaterEqual(first["verified_existing"], 1)
        self.assertEqual(
            frappe.db.sql(
                """select count(*) from `tabFerum Personnel Credential`
                   where name = %s and credential_number is not null""",
                (credential,),
            )[0][0],
            0,
        )
        migrated = frappe.get_doc("Ferum Personnel Credential", credential)
        self.assertEqual(
            hashlib.sha256(migrated.get_password("credential_number").encode()).digest(),
            hashlib.sha256(legacy_number.encode()).digest(),
        )
        self.assertEqual(migrated.credential_number_masked, "••••5678")
        native = frappe.get_doc("Ferum Personnel Credential", native_credential)
        self.assertEqual(
            hashlib.sha256(native.get_password("credential_number").encode()).digest(),
            hashlib.sha256(native_number.encode()).digest(),
        )
        self.assertEqual(native.credential_number_masked, "••••4321")

        second = migrate_credential_numbers()
        self.assertEqual(second["migrated"], 0)
        self.assertGreaterEqual(second["verified_existing"], 1)

    @staticmethod
    def _image_bytes(image_format: str, color: tuple[int, int, int]) -> bytes:
        payload = BytesIO()
        Image.new("RGB", (1, 1), color).save(payload, format=image_format)
        return payload.getvalue()

    @staticmethod
    def _pdf_bytes() -> bytes:
        payload = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.write(payload)
        return payload.getvalue()

    def test_assignment_readiness_invalidates_after_revoke(self) -> None:
        worker = self._active_worker()
        self._scope_worker_to_project(worker, self.verifier)
        frappe.set_user(self.data_owner)
        credential = create_personnel_credential(
            "Ferum Contractor Worker",
            worker,
            "Electrical Safety",
            "ES-READY-0001",
            "TEST-SUPPLIER-BASIS",
            issued_on=str(date.today()),
            expires_on=str(date.today() + timedelta(days=90)),
        )["credential"]
        verify_credential_source(credential, "Synthetic source evidence checked")
        frappe.set_user(self.verifier)
        verify_credential_applicability(credential, "Synthetic work applicability checked")

        frappe.set_user("Administrator")
        project = _make_project()
        service_object = frappe.get_doc(
            {
                "doctype": "Ferum Service Object",
                "object_name": f"FR-06 Object {uuid4().hex[:8]}",
                "customer": project.customer,
                "address": _make_address(project.customer, "FR-06 synthetic address"),
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
        assignment = create_contractor_assignment(
            project.name,
            "Contractor",
            project_object.name,
            "Electrical maintenance",
            "Synthetic scoped work",
            str(date.today()),
            effective_to=str(date.today() + timedelta(days=30)),
            supplier=self.supplier,
            contractor_worker=worker,
            required_credential_types='["Electrical Safety"]',
        )["contractor_assignment"]
        change_contractor_assignment_status(assignment, "Approved", "Synthetic assignment approval")
        ready = evaluate_contractor_readiness(
            assignment, 1, "Project manager confirms current synthetic evidence"
        )
        self.assertEqual(ready["credentials_readiness"], "Ready")
        self.assertTrue(ready["confirmed"])

        frappe.set_user(self.data_owner)
        revoke_or_reject_credential(
            credential, "Revoked", "Synthetic credential withdrawn by issuer"
        )
        frappe.set_user("Administrator")
        stale = evaluate_contractor_readiness(assignment)
        self.assertEqual(stale["credentials_readiness"], "Expired")
        self.assertFalse(stale["confirmed"])

    def _active_worker(self) -> str:
        frappe.set_user(self.data_owner)
        worker = create_contractor_worker(
            self.supplier,
            "TEST Synthetic Worker",
            "TEST-SUPPLIER-BASIS",
            self.data_owner,
            position="Synthetic Engineer",
        )["worker"]
        transition_contractor_worker(worker, "Active", "Synthetic source and basis rechecked")
        return worker

    def _scope_worker_to_project(
        self, worker: str, project_manager: str | None = None
    ) -> tuple[str, str]:
        frappe.set_user("Administrator")
        project = _make_project()
        project.project_manager = project_manager or self.project_manager
        project.requires_contractor = 1
        project.save(ignore_permissions=True)
        service_object = frappe.get_doc(
            {
                "doctype": "Ferum Service Object",
                "object_name": f"FR-06 Scope Object {uuid4().hex[:8]}",
                "customer": project.customer,
                "address": _make_address(project.customer, "FR-06 scoped address"),
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
        contractor_assignment = create_contractor_assignment(
            project.name,
            "Contractor",
            project_object.name,
            "Scoped contractor work",
            "Synthetic project-scoped credential access",
            str(date.today()),
            effective_to=str(date.today() + timedelta(days=30)),
            supplier=self.supplier,
            contractor_worker=worker,
        )["contractor_assignment"]
        change_contractor_assignment_status(
            contractor_assignment, "Approved", "Synthetic scoped contractor assignment"
        )
        employee = self._make_employee(self.engineer, project.company)
        internal_assignment = create_contractor_assignment(
            project.name,
            "Internal",
            project_object.name,
            "Internal engineering",
            "Synthetic engineer shares exact project object",
            str(date.today()),
            effective_to=str(date.today() + timedelta(days=30)),
            employee=employee,
        )["contractor_assignment"]
        change_contractor_assignment_status(
            internal_assignment, "Approved", "Synthetic internal engineer assignment"
        )
        return project.name, project_object.name

    @staticmethod
    def _make_employee(user: str, company: str) -> str:
        return (
            frappe.get_doc(
                {
                    "doctype": "Employee",
                    "first_name": "FR06 Synthetic Engineer",
                    "company": company,
                    "status": "Active",
                    "gender": frappe.db.get_value("Gender", {}, "name"),
                    "date_of_birth": "1990-01-01",
                    "date_of_joining": str(date.today()),
                    "user_id": user,
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    @staticmethod
    def _make_user(token: str, label: str, role: str) -> str:
        email = f"fr06-{label}-{token}@example.test"
        previous_import_flag = frappe.flags.in_import
        try:
            frappe.flags.in_import = True
            return (
                frappe.get_doc(
                    {
                        "doctype": "User",
                        "email": email,
                        "first_name": f"FR06 {label}",
                        "send_welcome_email": 0,
                        "roles": [{"role": role}],
                    }
                )
                .insert(ignore_permissions=True)
                .name
            )
        finally:
            frappe.flags.in_import = previous_import_flag

    @staticmethod
    def _make_supplier(token: str) -> str:
        return (
            frappe.get_doc(
                {
                    "doctype": "Supplier",
                    "supplier_name": f"FR06 Supplier {token}",
                    "supplier_group": frappe.db.get_value(
                        "Supplier Group", {"is_group": 0}, "name"
                    ),
                }
            )
            .insert(ignore_permissions=True)
            .name
        )
