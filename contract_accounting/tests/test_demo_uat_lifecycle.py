"""Runtime lifecycle regressions for the synthetic demo/UAT dataset.

These tests require an ERPNext/Frappe test site with the Contract Accounting
app installed.  Every business master created here is synthetic and remains in
the Frappe test transaction: demo entrypoint commits are suppressed so
``FrappeTestCase`` can roll the complete fixture back.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping
from unittest.mock import patch

import frappe
from frappe.handler import download_file
from frappe.tests.utils import FrappeTestCase

from contract_accounting.contract_accounting.doctype.ferum_privacy_settings.ferum_privacy_settings import (
    PRIVACY_SETTINGS_WRITE_FLAG,
)
from contract_accounting.demo_uat import bootstrap as bootstrap_module
from contract_accounting.demo_uat import installer
from contract_accounting.demo_uat import reset as reset_module
from contract_accounting.demo_uat.bootstrap import _privacy_state, owned_record_rows
from contract_accounting.demo_uat.installer import CommitState, install
from contract_accounting.demo_uat.manifest import (
    INSTALL_CONFIRMATION_TOKEN,
    RESET_CONFIRMATION_TOKEN,
    VERIFY_CONFIRMATION_TOKEN,
    load_manifest,
)
from contract_accounting.demo_uat.ownership import (
    PINNED_USER_DELETE_DATA_EFFECTS,
    REGISTRY_FILE_NAME,
    find_registry_file_names,
    load_registry,
    manifest_record_presence,
)
from contract_accounting.demo_uat.reset import find_derived_residue, reset
from contract_accounting.demo_uat.runtime import DemoUATRuntimeError
from contract_accounting.demo_uat.verifier import verify


class TestDemoUATLifecycle(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.manifest = load_manifest()
        self._cleanup_preinstall_orphans()
        self.assertEqual(manifest_record_presence(self.manifest), [])
        self.assertEqual(find_registry_file_names(), [])

    def tearDown(self) -> None:
        try:
            frappe.set_user("Administrator")
            if find_registry_file_names():
                with self._suppress_entrypoint_commits():
                    reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
        finally:
            frappe.set_user(self.previous_user)
            super().tearDown()

    def test_pinned_user_delete_effect_inventory_is_explicit(self) -> None:
        self.assertEqual(
            set(PINNED_USER_DELETE_DATA_EFFECTS),
            {
                "ToDo.allocated_to/delete",
                "ToDo.assigned_by/null",
                "Event.private-owner/delete",
                "DocShare.user/delete",
                "Communication.chat-notification/delete",
                "Contact.user/null",
                "Notification Settings/delete",
                "User Permission.user/delete",
                "OAuth Authorization Code.user/delete",
                "Token Cache.user/delete",
                "Energy Point Log.user/delete",
                "Workflow Action.user/null",
                "List Filter.for_user/delete",
                "Note Seen By.user/remove-and-save-parent",
                "User Invitation.email/unlink-and-save",
                "File.attached_to_User/delete-doc-attachment",
            },
        )

    def test_install_twice_is_idempotent_and_verify_is_read_only(self) -> None:
        before_files = self._private_file_paths()

        with self._suppress_entrypoint_commits():
            first = install(INSTALL_CONFIRMATION_TOKEN)
            exact_after_first = self._owned_snapshot()
            second = install(INSTALL_CONFIRMATION_TOKEN)
            exact_after_second = self._owned_snapshot()
            with patch.object(
                bootstrap_module,
                "_ensure_billing_cycle_reference_bindings",
                side_effect=AssertionError("verifier attempted reference write path"),
            ):
                verified = verify(VERIFY_CONFIRMATION_TOKEN)
            exact_after_verify = self._owned_snapshot()

        self.assertEqual(first["status"], "INSTALLED_STRUCTURAL_OK_MANUAL_UAT_REQUIRED")
        self.assertEqual(
            second["status"],
            "ALREADY_INSTALLED_STRUCTURAL_OK_MANUAL_UAT_REQUIRED",
        )
        self.assertEqual(second["created_count"], 0)
        self.assertEqual(verified["status"], "STRUCTURAL_OK_MANUAL_UAT_REQUIRED")
        self.assertNotIn("PASS", verified["status"])
        self.assertEqual(exact_after_second, exact_after_first)
        self.assertEqual(exact_after_verify, exact_after_first)
        self.assertGreaterEqual(self._private_file_paths(), before_files)

    def test_reset_dry_run_returns_exact_plan_and_changes_nothing(self) -> None:
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            before = self._owned_snapshot()
            result = reset(RESET_CONFIRMATION_TOKEN)
            repeated = reset(RESET_CONFIRMATION_TOKEN)
            after = self._owned_snapshot()

        self.assertEqual(result["status"], "RESET_DRY_RUN_ONLY")
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["delete_count"], 0)
        self.assertEqual(result["blockers"], [])
        self.assertEqual(before, after)

        planned = {(row["doctype"], row["name"]) for row in result["plan"]}
        self.assertEqual(result["plan"], repeated["plan"])
        self.assertEqual(
            len(planned), len(result["plan"]), "reset plan must not contain duplicates"
        )
        self.assertLessEqual(self._expected_owned_keys(before["registry_name"]), planned)
        self.assertEqual(result["plan"][-1]["doctype"], "File")
        self.assertEqual(result["plan"][-1]["name"], before["registry_name"])

    def test_reset_twice_is_idempotent_and_leaves_zero_residue(self) -> None:
        before_files = self._private_file_paths()
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            first = reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
            self._assert_zero_owned_residue(before_files)

            # A retry after an ambiguous client/network outcome must be safe.
            second = reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
            self._assert_zero_owned_residue(before_files)

        self.assertEqual(first["status"], "RESET_COMPLETE_NOT_A_UAT_RESULT")
        self.assertFalse(first["dry_run"])
        self.assertEqual(second["delete_count"], 0)
        self.assertFalse(second["dry_run"])

    def test_reset_restores_exact_audit_history_baseline(self) -> None:
        before_files = self._private_file_paths()
        before_audit = self._reset_audit_snapshot()
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            result = reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
        self.assertEqual(result["status"], "RESET_COMPLETE_NOT_A_UAT_RESULT")
        self.assertEqual(self._reset_audit_snapshot(), before_audit)
        self._assert_zero_owned_residue(before_files)

    def test_reset_preserves_external_exact_audit_history(self) -> None:
        before_audit = self._reset_audit_snapshot()
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            external = frappe.get_doc(
                {
                    "doctype": "Comment",
                    "comment_type": "Deleted",
                    "reference_doctype": "Company",
                    "reference_name": "CA-DEMO-V1-COMPANY",
                    "subject": "Company CA-DEMO-V1-COMPANY",
                    "owner": "Guest",
                }
            )
            external.db_insert()
            blocked = reset(RESET_CONFIRMATION_TOKEN)
            self.assertEqual(blocked["status"], "RESET_BLOCKED_BY_INBOUND_NON_DEMO_LINKS")
            self.assertTrue(frappe.db.exists("Comment", external.name))
            frappe.db.delete("Comment", {"name": external.name})
            result = reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
        self.assertEqual(result["status"], "RESET_COMPLETE_NOT_A_UAT_RESULT")
        self.assertEqual(self._reset_audit_snapshot(), before_audit)

    def test_no_registry_detector_refuses_exact_reset_audit_residue(self) -> None:
        artifacts = (
            {
                "doctype": "Comment",
                "comment_type": "Deleted",
                "reference_doctype": "Company",
                "subject": "Company CA-DEMO-V1-COMPANY",
            },
            {
                "doctype": "Deleted Document",
                "deleted_doctype": "Notification Settings",
                "deleted_name": "ca-demo-v1-own-engineer@example.invalid",
                "data": "{}",
            },
            {
                "doctype": "Version",
                "ref_doctype": "Company",
                "docname": "CA-DEMO-V1-COMPANY",
                "data": "{}",
            },
        )
        for values in artifacts:
            with self.subTest(doctype=values["doctype"]):
                document = frappe.get_doc(dict(values))
                document.db_insert()
                with self.assertRaisesRegex(
                    DemoUATRuntimeError,
                    "owned-looking records exist without registry",
                ):
                    reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
                frappe.db.delete(values["doctype"], {"name": document.name})

    def test_install_fault_rolls_back_registry_database_and_file(self) -> None:
        before_files = self._private_file_paths()

        with (
            self._suppress_entrypoint_commits(),
            patch.object(
                installer,
                "verify_registered_dataset",
                side_effect=RuntimeError("synthetic post-registry fault"),
            ),
            self.assertRaisesRegex(RuntimeError, "synthetic post-registry fault"),
        ):
            install(INSTALL_CONFIRMATION_TOKEN)

        self.assertEqual(manifest_record_presence(self.manifest), [])
        self.assertEqual(find_registry_file_names(), [])
        self.assertEqual(
            self._private_file_paths(),
            before_files,
            "savepoint rollback must remove physical registry/fixture files too",
        )

    def test_installer_commit_failure_leaves_no_orphan_fixture_bytes(self) -> None:
        before_files = self._private_file_paths()
        before_recovery = self._recovery_directories()
        with (
            patch.object(
                frappe.db,
                "commit",
                side_effect=RuntimeError("synthetic installer commit failure"),
            ),
            self.assertRaisesRegex(RuntimeError, "installer commit failure"),
        ):
            install(INSTALL_CONFIRMATION_TOKEN)

        self.assertEqual(manifest_record_presence(self.manifest), [])
        self.assertEqual(find_registry_file_names(), [])
        self.assertEqual(self._private_file_paths(), before_files)
        self.assertEqual(self._recovery_directories(), before_recovery)

    def test_installer_removes_exact_disk_only_fixture_orphans_before_bootstrap(self) -> None:
        private_files = Path(frappe.get_site_path("private", "files")).resolve()
        private_files.mkdir(parents=True, exist_ok=True)
        for fixture in self._binary_fixtures():
            path = private_files / str(fixture["file_name"])
            path.write_bytes(str(fixture["content_literal"]).encode("utf-8"))
        registry_path = private_files / REGISTRY_FILE_NAME
        registry_path.write_text(
            json.dumps(
                {
                    "schema": "contract-accounting/demo-uat-ownership/v1",
                    "dataset_id": self.manifest["dataset_id"],
                    "manifest_sha256": self.manifest["integrity"]["canonical_sha256"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)

        for fixture in self._binary_fixtures():
            document = frappe.get_doc("File", str(fixture["record_name"]))
            self.assertEqual(document.file_name, fixture["file_name"])
            self.assertEqual(
                hashlib.sha256(Path(document.get_full_path()).read_bytes()).hexdigest(),
                fixture["content_sha256"],
            )
        self.assertEqual(len(find_registry_file_names()), 1)

    def test_installer_resolves_commit_then_transport_exception_as_committed(self) -> None:
        original_commit = frappe.db.commit

        def commit_then_raise() -> None:
            original_commit()
            raise RuntimeError("synthetic installer post-commit transport failure")

        with patch.object(frappe.db, "commit", side_effect=commit_then_raise):
            result = install(INSTALL_CONFIRMATION_TOKEN)
        self.assertEqual(result["status"], "INSTALLED_STRUCTURAL_OK_MANUAL_UAT_REQUIRED")
        self.assertEqual(
            len(manifest_record_presence(self.manifest)), len(self.manifest["entities"])
        )
        self.assertEqual(len(find_registry_file_names()), 1)
        reset(RESET_CONFIRMATION_TOKEN, dry_run=False)

    def test_private_registry_is_invisible_to_engineer_on_all_read_surfaces(self) -> None:
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
        registry_name = self._only_registry_name()
        registry_doc = frappe.get_doc("File", registry_name)
        self.assertEqual(registry_doc.is_private, 1)
        self.assertFalse(registry_doc.attached_to_doctype)
        self.assertFalse(registry_doc.attached_to_name)

        frappe.set_user(self._bindings()["own_engineer_user"])
        visible = frappe.get_list(
            "File",
            filters={"name": registry_name},
            pluck="name",
            limit_page_length=0,
        )
        self.assertEqual(visible, [])
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc("File", registry_name).check_permission("read")
        with self.assertRaises(frappe.PermissionError):
            download_file(registry_doc.file_url)

    def test_reset_accepts_valid_uat_workflow_mutation(self) -> None:
        before_files = self._private_file_paths()
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)

            own_request = self._entity("ca.demo.v1.own.service_request")
            frappe.set_user(self._bindings()["own_engineer_user"])
            request = frappe.get_doc(own_request["doctype"], own_request["record_name"])
            request.status = "Assigned"
            request.save()

            frappe.set_user("Administrator")
            result = reset(RESET_CONFIRMATION_TOKEN, dry_run=False)

        self.assertEqual(result["status"], "RESET_COMPLETE_NOT_A_UAT_RESULT")
        self._assert_zero_owned_residue(before_files)

    def test_registry_and_database_contain_exact_owned_record_and_file_sets(self) -> None:
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)

        snapshot = self._owned_snapshot()
        registry, registry_name = load_registry(
            self.manifest,
            site=frappe.local.site,
            required=True,
        )
        assert registry is not None and registry_name is not None

        expected_registry_records = [
            {
                "external_id": entity["external_id"],
                "project_key": entity["project_key"],
                "doctype": entity["doctype"],
                "name": entity["record_name"],
            }
            for entity in self.manifest["entities"]
        ]
        self.assertEqual(registry["records"], expected_registry_records)
        self.assertEqual(
            snapshot["domain"],
            {(row["doctype"], row["name"]) for row in expected_registry_records},
        )
        self.assertEqual(
            snapshot["files"],
            {*(fixture["record_name"] for fixture in self._binary_fixtures()), registry_name},
        )
        self._assert_binary_fixture_files()

    def test_reset_runs_standard_company_user_cleanup_and_leaves_no_derived_residue(self) -> None:
        before_files = self._private_file_paths()
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            registry, _ = load_registry(self.manifest, site=frappe.local.site, required=True)
            assert registry is not None
            user_effect_rows = self._create_standard_user_derivatives(registry["bindings"])
            derived_before = find_derived_residue(
                registry_records=registry["records"],
                bootstrap_records=registry["bootstrap_records"],
                bindings=registry["bindings"],
            )
            self.assertTrue(
                {
                    "Account",
                    "Warehouse",
                    "Cost Center",
                    "Department",
                    "User Permission",
                    "ToDo",
                    "DocShare",
                    "Token Cache",
                    "Sessions",
                }.issubset({row["doctype"] for row in derived_before})
            )
            result = reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
            derived_after = find_derived_residue(
                registry_records=registry["records"],
                bootstrap_records=registry["bootstrap_records"],
                bindings=registry["bindings"],
            )

        self.assertEqual(result["status"], "RESET_COMPLETE_NOT_A_UAT_RESULT")
        self.assertEqual(derived_after, [])
        for doctype, name in user_effect_rows:
            self.assertFalse(frappe.db.exists(doctype, name), f"{doctype}/{name}")
        self._assert_zero_owned_residue(before_files)

    def test_external_dynamic_link_to_bootstrap_record_blocks_reset(self) -> None:
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            bindings = self._bindings()
            todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": "external non-demo inbound regression",
                    "allocated_to": "Administrator",
                    "reference_type": "Customer",
                    "reference_name": bindings["customer"],
                }
            ).insert(ignore_permissions=True)
            result = reset(RESET_CONFIRMATION_TOKEN)

        self.assertEqual(result["status"], "RESET_BLOCKED_BY_INBOUND_NON_DEMO_LINKS")
        self.assertTrue(
            any(
                row["source_doctype"] == "ToDo" and todo.name in row["source_name"]
                for row in result["blockers"]
            )
        )
        for blocker in result["blockers"]:
            source_doctype = blocker["source_doctype"]
            source_name = blocker["source_name"]
            if source_doctype == "Comment":
                frappe.delete_doc(
                    source_doctype,
                    source_name,
                    ignore_permissions=True,
                    force=True,
                    delete_permanently=True,
                )
        todo.delete(ignore_permissions=True)

    def test_registry_file_is_a_normal_inbound_target_for_guest_sources(self) -> None:
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            registry_name = self._only_registry_name()
            comment_before = set(frappe.get_all("Comment", pluck="name") or [])
            guest_comment = frappe.get_doc(
                {
                    "doctype": "Comment",
                    "comment_type": "Comment",
                    "reference_doctype": "File",
                    "reference_name": registry_name,
                    "content": "external guest comment",
                    "owner": "Guest",
                }
            )
            guest_comment.db_insert()
            guest_version = frappe.get_doc(
                {
                    "doctype": "Version",
                    "ref_doctype": "File",
                    "docname": registry_name,
                    "data": "{}",
                    "owner": "Guest",
                }
            )
            guest_version.db_insert()
            frappe.db.set_value(
                "Version", guest_version.name, "owner", "Guest", update_modified=False
            )
            guest_todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": "external registry reference",
                    "allocated_to": "Administrator",
                    "reference_type": "File",
                    "reference_name": registry_name,
                }
            ).insert(ignore_permissions=True)

            result = reset(RESET_CONFIRMATION_TOKEN)

        blockers = {
            (row["source_doctype"], row["source_name"], row["fieldname"])
            for row in result["blockers"]
        }
        self.assertEqual(result["status"], "RESET_BLOCKED_BY_INBOUND_NON_DEMO_LINKS")
        self.assertIn(("Comment", guest_comment.name, "reference_name"), blockers)
        self.assertIn(("Version", guest_version.name, "docname"), blockers)
        self.assertIn(("ToDo", guest_todo.name, "reference_name"), blockers)
        frappe.db.delete("Comment", {"name": guest_comment.name})
        frappe.db.delete("Version", {"name": guest_version.name})
        frappe.db.delete("ToDo", {"name": guest_todo.name})
        new_comments = set(frappe.get_all("Comment", pluck="name") or []) - comment_before
        if new_comments:
            frappe.db.delete("Comment", {"name": ["in", sorted(new_comments)]})

    def test_company_derived_row_is_inbound_target_for_external_file_todo_and_link(self) -> None:
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            account = frappe.get_all(
                "Account",
                filters={"company": self._bindings()["company"]},
                pluck="name",
                limit=1,
            )[0]
            audit_before = self._reset_audit_snapshot()
            comment_before = set(frappe.get_all("Comment", pluck="name") or [])
            external_file = frappe.get_doc(
                {
                    "doctype": "File",
                    "file_name": "external-company-derived-link.txt",
                    "is_private": 1,
                    "attached_to_doctype": "Account",
                    "attached_to_name": account,
                    "content": b"external inbound file\n",
                }
            ).insert(ignore_permissions=True)
            frappe.db.set_value("File", external_file.name, "owner", "Guest", update_modified=False)
            external_path = Path(external_file.get_full_path()).resolve()
            external_todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": "external company-derived target",
                    "allocated_to": "Administrator",
                    "reference_type": "Account",
                    "reference_name": account,
                }
            ).insert(ignore_permissions=True)
            external_bank = frappe.get_doc(
                {
                    "doctype": "Bank",
                    "bank_name": "External CA demo regression bank",
                    "owner": "Guest",
                }
            )
            external_bank.db_insert()
            external_link = frappe.get_doc(
                {
                    "doctype": "Bank Account",
                    "account_name": "External CA demo regression bank account",
                    "bank": external_bank.name,
                    "account": account,
                    "owner": "Guest",
                }
            )
            external_link.db_insert()
            frappe.db.set_value(
                "Bank Account", external_link.name, "owner", "Guest", update_modified=False
            )

            result = reset(RESET_CONFIRMATION_TOKEN)

        blockers = {
            (row["source_doctype"], row["source_name"], row["fieldname"])
            for row in result["blockers"]
        }
        self.assertEqual(result["status"], "RESET_BLOCKED_BY_INBOUND_NON_DEMO_LINKS")
        self.assertIn(("File", external_file.name, "attached_to_name"), blockers)
        self.assertIn(("ToDo", external_todo.name, "reference_name"), blockers)
        self.assertIn(("Bank Account", external_link.name, "account"), blockers)
        frappe.db.delete("File", {"name": external_file.name})
        if external_path.exists():
            external_path.unlink()
        frappe.db.delete("ToDo", {"name": external_todo.name})
        frappe.db.delete("Bank Account", {"name": external_link.name})
        frappe.db.delete("Bank", {"name": external_bank.name})
        new_comments = set(frappe.get_all("Comment", pluck="name") or []) - comment_before
        if new_comments:
            frappe.db.delete("Comment", {"name": ["in", sorted(new_comments)]})
        for doctype, names in audit_before.items():
            current = set(frappe.get_all(doctype, pluck="name") or [])
            extras = current - names
            if extras:
                frappe.db.delete(doctype, {"name": ["in", sorted(extras)]})

    def test_reset_cleans_browser_activity_for_registry_owned_synthetic_user(self) -> None:
        before_files = self._private_file_paths()
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            registry, _ = load_registry(self.manifest, site=frappe.local.site, required=True)
            assert registry is not None
            activity = frappe.get_doc(
                {
                    "doctype": "Activity Log",
                    "subject": "Synthetic browser login during CA demo lifecycle",
                    "operation": "Login",
                    "status": "Success",
                    "user": registry["bindings"]["own_engineer_user"],
                }
            ).insert(ignore_permissions=True)

            dry_run = reset(RESET_CONFIRMATION_TOKEN)
            self.assertEqual(dry_run["status"], "RESET_DRY_RUN_ONLY")
            self.assertIn(
                ("Activity Log", activity.name),
                {(row["doctype"], row["name"]) for row in dry_run["plan"]},
            )
            result = reset(RESET_CONFIRMATION_TOKEN, dry_run=False)

        self.assertEqual(result["status"], "RESET_COMPLETE_NOT_A_UAT_RESULT")
        self.assertFalse(frappe.db.exists("Activity Log", activity.name))
        self._assert_zero_owned_residue(before_files)

    def test_historical_activity_for_synthetic_user_remains_external_blocker(self) -> None:
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            registry, _ = load_registry(self.manifest, site=frappe.local.site, required=True)
            assert registry is not None
            activity = frappe.get_doc(
                {
                    "doctype": "Activity Log",
                    "subject": "Historical row must not be adopted by demo ownership",
                    "operation": "Login",
                    "status": "Success",
                    "user": registry["bindings"]["foreign_engineer_user"],
                }
            ).insert(ignore_permissions=True)
            historical_creation = frappe.utils.add_to_date(
                registry["created_at"], seconds=-1, as_datetime=True
            )
            frappe.db.set_value(
                "Activity Log",
                activity.name,
                "creation",
                historical_creation,
                update_modified=False,
            )

            result = reset(RESET_CONFIRMATION_TOKEN)

        self.assertEqual(result["status"], "RESET_BLOCKED_BY_INBOUND_NON_DEMO_LINKS")
        self.assertTrue(
            any(
                row["source_doctype"] == "Activity Log"
                and row["source_name"] == activity.name
                and row["fieldname"] == "user"
                for row in result["blockers"]
            )
        )
        frappe.delete_doc(
            "Activity Log",
            activity.name,
            ignore_permissions=True,
            force=True,
            delete_permanently=True,
        )

    def test_recent_impersonate_and_external_reference_activity_are_blockers(self) -> None:
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            user = self._bindings()["own_engineer_user"]
            impersonate = frappe.get_doc(
                {
                    "doctype": "Activity Log",
                    "subject": "Synthetic impersonation must stay external",
                    "operation": "Impersonate",
                    "status": "Success",
                    "user": user,
                }
            ).insert(ignore_permissions=True)
            external_reference = frappe.get_doc(
                {
                    "doctype": "Activity Log",
                    "subject": "Synthetic login with external reference",
                    "operation": "Login",
                    "status": "Success",
                    "user": user,
                    "reference_doctype": "User",
                    "reference_name": "Administrator",
                }
            ).insert(ignore_permissions=True)
            result = reset(RESET_CONFIRMATION_TOKEN)

        blockers = {
            (row["source_doctype"], row["source_name"], row["fieldname"])
            for row in result["blockers"]
        }
        self.assertEqual(result["status"], "RESET_BLOCKED_BY_INBOUND_NON_DEMO_LINKS")
        self.assertIn(("Activity Log", impersonate.name, "user"), blockers)
        self.assertIn(("Activity Log", external_reference.name, "user"), blockers)
        frappe.db.delete(
            "Activity Log", {"name": ["in", [impersonate.name, external_reference.name]]}
        )

    def test_external_user_on_trash_effects_block_reset_without_mutation(self) -> None:
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            registry, _ = load_registry(self.manifest, site=frappe.local.site, required=True)
            assert registry is not None
            user = registry["bindings"]["own_engineer_user"]
            user_creation = frappe.db.get_value("User", user, "creation")

            sources: list[tuple[str, str, str]] = []
            todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": "external target must block",
                    "allocated_to": user,
                    "reference_type": "User",
                    "reference_name": "Administrator",
                }
            ).insert(ignore_permissions=True)
            sources.append(("ToDo", todo.name, "allocated_to"))

            contact = frappe.get_doc(
                {
                    "doctype": "Contact",
                    "first_name": "External Contact",
                    "email_id": "external-contact@example.invalid",
                    "user": user,
                }
            ).insert(ignore_permissions=True)
            sources.append(("Contact", contact.name, "user"))

            event = frappe.get_doc(
                {
                    "doctype": "Event",
                    "subject": "External private event",
                    "event_type": "Private",
                    "starts_on": frappe.utils.now_datetime(),
                    "reference_doctype": "User",
                    "reference_docname": "Administrator",
                }
            ).insert(ignore_permissions=True)
            frappe.db.set_value("Event", event.name, "owner", user, update_modified=False)
            sources.append(("Event", event.name, "owner"))

            list_filter = frappe.get_doc(
                {
                    "doctype": "List Filter",
                    "filter_name": "External historical filter",
                    "reference_doctype": "User",
                    "for_user": user,
                    "filters": "[]",
                }
            ).insert(ignore_permissions=True)
            frappe.db.set_value(
                "List Filter",
                list_filter.name,
                "creation",
                frappe.utils.add_to_date(user_creation, seconds=-1, as_datetime=True),
                update_modified=False,
            )
            sources.append(("List Filter", list_filter.name, "for_user"))

            file_before_comments = set(frappe.get_all("Comment", pluck="name"))
            attached_file = frappe.get_doc(
                {
                    "doctype": "File",
                    "file_name": "external-user-attachment.txt",
                    "is_private": 1,
                    "attached_to_doctype": "User",
                    "attached_to_name": user,
                    "content": b"external attachment must not be adopted\n",
                }
            ).insert(ignore_permissions=True)
            frappe.db.set_value("File", attached_file.name, "owner", "Guest", update_modified=False)
            sources.append(("File", attached_file.name, "attached_to_name"))

            result = reset(RESET_CONFIRMATION_TOKEN)

        blockers = {
            (row["source_doctype"], row["source_name"], row["fieldname"])
            for row in result["blockers"]
        }
        self.assertEqual(result["status"], "RESET_BLOCKED_BY_INBOUND_NON_DEMO_LINKS")
        for source in sources:
            self.assertIn(source, blockers)
        self.assertTrue(frappe.db.exists("ToDo", todo.name))
        self.assertEqual(frappe.db.get_value("Contact", contact.name, "user"), user)
        self.assertTrue(frappe.db.exists("Event", event.name))
        self.assertTrue(frappe.db.exists("List Filter", list_filter.name))
        self.assertTrue(frappe.db.exists("File", attached_file.name))

        for doctype, name, _fieldname in sources[:-1]:
            frappe.db.delete(doctype, {"name": name})
        frappe.delete_doc(
            "File",
            attached_file.name,
            ignore_permissions=True,
            force=True,
            delete_permanently=True,
        )
        new_comments = set(frappe.get_all("Comment", pluck="name")) - file_before_comments
        if new_comments:
            frappe.db.delete("Comment", {"name": ["in", sorted(new_comments)]})

    def test_reset_fault_after_physical_file_delete_restores_exact_rows_and_blobs(self) -> None:
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            before = self._owned_file_state()
            original_delete = frappe.delete_doc
            file_calls = 0

            def delete_then_fault(doctype: str, name: str, **kwargs: Any) -> Any:
                nonlocal file_calls
                result = original_delete(doctype, name, **kwargs)
                if doctype == "File":
                    file_calls += 1
                    if file_calls == 1:
                        raise RuntimeError("synthetic fault after physical File delete")
                return result

            with (
                patch.object(frappe, "delete_doc", side_effect=delete_then_fault),
                self.assertRaisesRegex(RuntimeError, "after physical File delete"),
            ):
                reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
            after = self._owned_file_state()

        self.assertEqual(file_calls, 1)
        self.assertEqual(after, before)
        self.assertEqual(
            len(manifest_record_presence(self.manifest)), len(self.manifest["entities"])
        )
        cleaned = reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
        self.assertEqual(cleaned["status"], "RESET_COMPLETE_NOT_A_UAT_RESULT")
        retried = reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
        self.assertEqual(retried["delete_count"], 0)

    def test_reset_commit_failure_restores_exact_database_paths_and_hashes(self) -> None:
        before_recovery = self._recovery_directories()
        install(INSTALL_CONFIRMATION_TOKEN)
        before_files = self._owned_file_state()
        before_records = manifest_record_presence(self.manifest)
        before_privacy = _privacy_state(frappe.get_single("Ferum Privacy Settings"))
        try:
            with (
                patch.object(
                    frappe.db,
                    "commit",
                    side_effect=RuntimeError("synthetic reset commit failure"),
                ),
                self.assertRaisesRegex(RuntimeError, "reset commit failure"),
            ):
                reset(RESET_CONFIRMATION_TOKEN, dry_run=False)

            self.assertEqual(manifest_record_presence(self.manifest), before_records)
            self.assertEqual(self._owned_file_state(), before_files)
            self.assertEqual(
                _privacy_state(frappe.get_single("Ferum Privacy Settings")), before_privacy
            )
            self.assertEqual(self._recovery_directories(), before_recovery)
        finally:
            if find_registry_file_names():
                reset(RESET_CONFIRMATION_TOKEN, dry_run=False)

    def test_reset_resolves_commit_then_transport_exception_as_committed(self) -> None:
        before_files = self._private_file_paths()
        install(INSTALL_CONFIRMATION_TOKEN)
        expected_delete_count = len(reset(RESET_CONFIRMATION_TOKEN)["plan"])
        original_commit = frappe.db.commit

        def commit_then_raise() -> None:
            original_commit()
            raise RuntimeError("synthetic reset post-commit transport failure")

        with patch.object(frappe.db, "commit", side_effect=commit_then_raise):
            result = reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
        self.assertEqual(result["delete_count"], expected_delete_count)
        self.assertEqual(manifest_record_presence(self.manifest), [])
        self.assertEqual(find_registry_file_names(), [])
        self.assertEqual(self._private_file_paths(), before_files)

    def test_reset_commit_guard_blocks_after_commit_version(self) -> None:
        install(INSTALL_CONFIRMATION_TOKEN)
        expected_delete_count = len(reset(RESET_CONFIRMATION_TOKEN)["plan"])
        target = self._entity("ca.demo.v1.own.service_project")
        attempted: list[str] = []

        def create_late_version() -> None:
            attempted.append("called")
            frappe.get_doc(
                {
                    "doctype": "Version",
                    "ref_doctype": target["doctype"],
                    "docname": target["record_name"],
                    "data": "{}",
                }
            ).insert(ignore_permissions=True)

        frappe.db.after_commit.add(create_late_version)
        result = reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
        self.assertEqual(attempted, ["called"])
        self.assertEqual(result["delete_count"], expected_delete_count)
        self.assertFalse(
            frappe.db.exists(
                "Version",
                {"ref_doctype": target["doctype"], "docname": target["record_name"]},
            )
        )

    def test_no_registry_activity_log_for_deterministic_user_blocks_zero_reset(self) -> None:
        activity = frappe.get_doc(
            {
                "doctype": "Activity Log",
                "user": "ca-demo-v1-own-engineer@example.invalid",
                "operation": "Login",
                "status": "Success",
            }
        )
        activity.db_insert()
        try:
            with self.assertRaisesRegex(
                DemoUATRuntimeError,
                "owned-looking records exist without registry",
            ):
                reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
        finally:
            frappe.db.delete("Activity Log", {"name": activity.name})

    def test_no_registry_activity_log_blocks_install_before_bootstrap(self) -> None:
        activity = frappe.get_doc(
            {
                "doctype": "Activity Log",
                "user": "ca-demo-v1-own-engineer@example.invalid",
                "operation": "Login",
                "status": "Success",
            }
        )
        activity.db_insert()
        before_files = self._private_file_paths()
        try:
            with self.assertRaisesRegex(
                DemoUATRuntimeError,
                "deterministic demo names exist without an ownership registry",
            ):
                install(INSTALL_CONFIRMATION_TOKEN)
            self.assertEqual(manifest_record_presence(self.manifest), [])
            self.assertEqual(find_registry_file_names(), [])
            self.assertEqual(self._private_file_paths(), before_files)
        finally:
            frappe.db.delete("Activity Log", {"name": activity.name})

    def test_ambiguous_commit_probe_failure_is_unknown_not_not_committed(self) -> None:
        with patch.object(installer, "load_registry", side_effect=ConnectionError("probe down")):
            self.assertIs(
                installer._install_commit_state(frappe, self.manifest, site=frappe.local.site),
                CommitState.UNKNOWN,
            )

    def test_reset_after_commit_external_audit_mutation_is_rolled_back(self) -> None:
        external = frappe.get_doc(
            {
                "doctype": "Version",
                "ref_doctype": "User",
                "docname": "Administrator",
                "data": '{"baseline": true}',
            }
        )
        external.db_insert()
        frappe.db.commit()
        install(INSTALL_CONFIRMATION_TOKEN)
        attempted: list[str] = []

        def mutate_external_audit() -> None:
            attempted.append("called")
            frappe.db.set_value(
                "Version", external.name, "data", '{"mutated": true}', update_modified=False
            )

        frappe.db.after_commit.add(mutate_external_audit)
        try:
            result = reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
            self.assertEqual(result["status"], "RESET_COMPLETE_NOT_A_UAT_RESULT")
            self.assertEqual(attempted, ["called"])
            self.assertEqual(
                frappe.db.get_value("Version", external.name, "data"), '{"baseline": true}'
            )
        finally:
            frappe.db.delete("Version", {"name": external.name})
            frappe.db.commit()

    def test_reset_watchdog_runs_after_callbacks_enqueued_during_commit(self) -> None:
        install(INSTALL_CONFIRMATION_TOKEN)
        created: list[str] = []

        def enqueue_late_mutation() -> None:
            def create_late_comment() -> None:
                document = frappe.get_doc(
                    {
                        "doctype": "Comment",
                        "comment_type": "Comment",
                        "reference_doctype": "User",
                        "reference_name": "Administrator",
                        "content": "synthetic late reset callback",
                    }
                )
                document.db_insert()
                created.append(document.name)

            frappe.db.after_commit.add(create_late_comment)

        frappe.db.after_commit.add(enqueue_late_mutation)
        result = reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
        self.assertEqual(result["status"], "RESET_COMPLETE_NOT_A_UAT_RESULT")
        self.assertEqual(len(created), 1)
        self.assertFalse(frappe.db.exists("Comment", created[0]))
        reinstalled = install(INSTALL_CONFIRMATION_TOKEN)
        self.assertEqual(reinstalled["status"], "INSTALLED_STRUCTURAL_OK_MANUAL_UAT_REQUIRED")
        reset(RESET_CONFIRMATION_TOKEN, dry_run=False)

    def test_reset_unavailable_durable_probe_is_unknown(self) -> None:
        with patch.object(
            reset_module, "manifest_record_presence", side_effect=ConnectionError("probe down")
        ):
            self.assertIs(
                reset_module._reset_commit_state(
                    frappe,
                    manifest=self.manifest,
                    registry={"records": [], "bootstrap_records": [], "bindings": {}},
                    expected_audit_snapshot={
                        doctype: set() for doctype in ("Comment", "Deleted Document", "Version")
                    },
                    file_snapshots={"rows": []},
                    expected_audit_fingerprints={},
                ),
                CommitState.UNKNOWN,
            )

    def test_committed_guest_version_blocks_before_reset_commit(self) -> None:
        install(INSTALL_CONFIRMATION_TOKEN)
        target = self._entity("ca.demo.v1.own.service_project")
        external = frappe.get_doc(
            {
                "doctype": "Version",
                "ref_doctype": target["doctype"],
                "docname": target["record_name"],
                "data": "{}",
                "owner": "Guest",
            }
        )
        external.db_insert()
        frappe.db.set_value("Version", external.name, "owner", "Guest", update_modified=False)
        frappe.db.commit()
        try:
            with (
                patch.object(
                    frappe.db,
                    "commit",
                    side_effect=AssertionError("blocked reset reached commit"),
                ),
                self.assertRaisesRegex(DemoUATRuntimeError, "inbound non-demo links"),
            ):
                reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
            self.assertTrue(frappe.db.exists("Version", external.name))
            self.assertEqual(
                len(manifest_record_presence(self.manifest)), len(self.manifest["entities"])
            )
        finally:
            frappe.db.delete("Version", {"name": external.name})
            frappe.db.commit()
            if find_registry_file_names():
                reset(RESET_CONFIRMATION_TOKEN, dry_run=False)

    def test_disabled_privacy_policy_roundtrips_exactly(self) -> None:
        disabled = self._set_privacy_state(
            {
                "enabled": 0,
                "activation_mode": "Disabled",
                "activated_at": None,
                "activated_by": None,
                "approval_reference": None,
                "last_reason": "Synthetic disabled baseline",
                "configuration_revision": 17,
            }
        )
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            self.assertEqual(
                _privacy_state(frappe.get_single("Ferum Privacy Settings"))["activation_mode"],
                "Synthetic Test",
            )
            reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
        self.assertEqual(_privacy_state(frappe.get_single("Ferum Privacy Settings")), disabled)

    def test_preexisting_synthetic_privacy_policy_is_preserved(self) -> None:
        existing = self._set_privacy_state(
            {
                "enabled": 1,
                "activation_mode": "Synthetic Test",
                "activated_at": "2026-08-19 12:00:00",
                "activated_by": "Administrator",
                "approval_reference": "TEST-PREEXISTING-SYNTHETIC",
                "last_reason": "Preexisting synthetic policy for regression",
                "configuration_revision": 23,
            }
        )
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
        self.assertEqual(_privacy_state(frappe.get_single("Ferum Privacy Settings")), existing)

    def test_external_privacy_drift_blocks_reset_before_delete(self) -> None:
        self._set_privacy_state(
            {
                "enabled": 0,
                "activation_mode": "Disabled",
                "activated_at": None,
                "activated_by": None,
                "approval_reference": None,
                "last_reason": "Synthetic disabled baseline",
                "configuration_revision": 31,
            }
        )
        with self._suppress_entrypoint_commits():
            install(INSTALL_CONFIRMATION_TOKEN)
            registry, _ = load_registry(self.manifest, site=frappe.local.site, required=True)
            assert registry is not None
            drifted = dict(registry["privacy_policy"]["demo_state"])
            drifted["last_reason"] = "External change after demo activation"
            self._set_privacy_state(drifted)
            with self.assertRaisesRegex(DemoUATRuntimeError, "external drift"):
                verify(VERIFY_CONFIRMATION_TOKEN)
            with self.assertRaisesRegex(DemoUATRuntimeError, "external drift"):
                reset(RESET_CONFIRMATION_TOKEN, dry_run=False)
            self.assertEqual(
                len(manifest_record_presence(self.manifest)), len(self.manifest["entities"])
            )
            self._set_privacy_state(registry["privacy_policy"]["demo_state"])

    @contextmanager
    def _suppress_entrypoint_commits(self) -> Iterator[None]:
        """Keep production commit calls observable without escaping test rollback."""

        with patch.object(frappe.db, "commit"):
            yield

    def _cleanup_preinstall_orphans(self) -> None:
        stale_file_names = [str(row["record_name"]) for row in self._binary_fixtures()]
        if stale_file_names:
            for file_name in sorted(
                set(
                    str(row)
                    for row in frappe.get_all(
                        "File", filters={"name": ["in", stale_file_names]}, pluck="name"
                    )
                )
            ):
                try:
                    document = frappe.get_doc("File", file_name)
                    path = Path(document.get_full_path()).resolve()
                    if path.is_file():
                        path.unlink()
                except Exception:
                    pass
                frappe.db.sql(
                    "DELETE FROM `tabFile` WHERE `name`=%s", (file_name,), auto_commit=True
                )

        stale_comments = frappe.get_all(
            "Comment",
            filters={
                "reference_name": "CA-DEMO-V1-COMPANY",
            },
            pluck="name",
        )
        stale_comments.extend(
            frappe.get_all(
                "Comment",
                filters={"subject": ["like", "%CA-DEMO-V1-COMPANY%"]},
                pluck="name",
            )
        )
        stale_comment_names = sorted({str(name) for name in stale_comments})
        for name in stale_comment_names:
            frappe.db.sql("DELETE FROM `tabComment` WHERE `name`=%s", (name,), auto_commit=True)

        frappe.db.commit()

    def _bindings(self) -> Mapping[str, str]:
        registry, _ = load_registry(self.manifest, site=frappe.local.site, required=True)
        assert registry is not None
        return registry["bindings"]

    def _entity(self, external_id: str) -> Mapping[str, Any]:
        return next(
            entity for entity in self.manifest["entities"] if entity["external_id"] == external_id
        )

    def _binary_fixtures(self) -> list[Mapping[str, Any]]:
        graph = self.manifest.get("business_graph") or {}
        return list(graph.get("binary_fixtures") or [])

    def _only_registry_name(self) -> str:
        names = find_registry_file_names()
        self.assertEqual(len(names), 1)
        return names[0]

    def _owned_snapshot(self) -> dict[str, Any]:
        registry_name = self._only_registry_name()
        expected_doctypes = {str(entity["doctype"]) for entity in self.manifest["entities"]}
        domain: set[tuple[str, str]] = set()
        for doctype in expected_doctypes:
            names = frappe.get_all(
                doctype,
                filters={"name": ["like", "CA-DEMO-V1-%"]},
                pluck="name",
            )
            domain.update((doctype, str(name)) for name in names)

        fixture_names = {str(row["record_name"]) for row in self._binary_fixtures()}
        files = {
            str(name)
            for name in frappe.get_all(
                "File",
                filters={"name": ["in", sorted(fixture_names | {registry_name})]},
                pluck="name",
            )
        }
        prefixed_files = {
            str(name)
            for name in frappe.get_all(
                "File",
                filters={"name": ["like", "CA-DEMO-V1-%"]},
                pluck="name",
            )
        }
        registry_files = {
            str(name)
            for name in frappe.get_all(
                "File",
                filters={"file_name": ["like", f"{REGISTRY_FILE_NAME}%"]},
                pluck="name",
            )
        }
        files.update(prefixed_files)
        files.update(registry_files)
        return {"domain": domain, "files": files, "registry_name": registry_name}

    def _expected_owned_keys(self, registry_name: str) -> set[tuple[str, str]]:
        keys = {
            (str(entity["doctype"]), str(entity["record_name"]))
            for entity in self.manifest["entities"]
        }
        keys.update(("File", str(row["record_name"])) for row in self._binary_fixtures())
        keys.update((str(row["doctype"]), str(row["name"])) for row in owned_record_rows())
        keys.add(("File", registry_name))
        return keys

    def _assert_binary_fixture_files(self) -> None:
        entities = {str(entity["external_id"]): entity for entity in self.manifest["entities"]}
        for fixture in self._binary_fixtures():
            document = frappe.get_doc("File", fixture["record_name"])
            target = entities[str(fixture["attached_to_external_id"])]
            self.assertEqual(document.file_name, fixture["file_name"])
            self.assertEqual(document.is_private, fixture["is_private"])
            self.assertEqual(document.attached_to_doctype, target["doctype"])
            self.assertEqual(document.attached_to_name, target["record_name"])
            content = document.get_content()
            if isinstance(content, str):
                content = content.encode("utf-8")
            self.assertEqual(hashlib.sha256(content).hexdigest(), fixture["content_sha256"])

    def _owned_file_state(self) -> dict[str, dict[str, Any]]:
        names = {str(row["record_name"]) for row in self._binary_fixtures()}
        names.update(find_registry_file_names())
        state: dict[str, dict[str, Any]] = {}
        for name in sorted(names):
            document = frappe.get_doc("File", name)
            path = Path(document.get_full_path()).resolve()
            content = path.read_bytes()
            state[name] = {
                "file_url": str(document.file_url),
                "content_hash": str(document.content_hash),
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": content,
                "path": str(path),
            }
        return state

    def _create_standard_user_derivatives(
        self, bindings: Mapping[str, str]
    ) -> list[tuple[str, str]]:
        user = bindings["own_engineer_user"]
        project = self._entity("ca.demo.v1.own.service_project")
        created: list[tuple[str, str]] = []
        user_permission = frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": user,
                "allow": "Company",
                "for_value": bindings["company"],
                "apply_to_all_doctypes": 1,
            }
        ).insert(ignore_permissions=True)
        created.append(("User Permission", user_permission.name))
        todo = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "synthetic owned-user cleanup regression",
                "allocated_to": user,
            }
        ).insert(ignore_permissions=True)
        created.append(("ToDo", todo.name))
        share = frappe.get_doc(
            {
                "doctype": "DocShare",
                "share_doctype": project["doctype"],
                "share_name": project["record_name"],
                "user": user,
                "read": 1,
            }
        ).insert(ignore_permissions=True)
        created.append(("DocShare", share.name))
        token = frappe.get_doc({"doctype": "Token Cache", "user": user}).insert(
            ignore_permissions=True
        )
        created.append(("Token Cache", token.name))
        event = frappe.get_doc(
            {
                "doctype": "Event",
                "subject": "Synthetic owned private event",
                "event_type": "Private",
                "starts_on": frappe.utils.now_datetime(),
                "reference_doctype": project["doctype"],
                "reference_docname": project["record_name"],
            }
        ).insert(ignore_permissions=True)
        frappe.db.set_value("Event", event.name, "owner", user, update_modified=False)
        created.append(("Event", event.name))
        list_filter = frappe.get_doc(
            {
                "doctype": "List Filter",
                "filter_name": "Synthetic owned filter",
                "reference_doctype": project["doctype"],
                "for_user": user,
                "filters": "[]",
            }
        ).insert(ignore_permissions=True)
        created.append(("List Filter", list_filter.name))
        attachment = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": "ca-demo-v1-owned-user-attachment.txt",
                "is_private": 1,
                "attached_to_doctype": "User",
                "attached_to_name": user,
                "content": b"synthetic owned user attachment\n",
            }
        ).insert(ignore_permissions=True)
        created.append(("File", attachment.name))
        frappe.db.sql(
            """
            insert into `tabSessions`
                (`user`, `sid`, `sessiondata`, `ipaddress`, `lastupdate`, `status`)
            values (%s, %s, %s, %s, NOW(6), %s)
            """,
            (user, "ca-demo-v1-synthetic-session", "{}", "127.0.0.1", "Active"),
        )
        return created

    @staticmethod
    def _set_privacy_state(changes: Mapping[str, Any]) -> dict[str, Any]:
        previous = frappe.flags.get(PRIVACY_SETTINGS_WRITE_FLAG)
        frappe.flags[PRIVACY_SETTINGS_WRITE_FLAG] = True
        try:
            settings = frappe.get_single("Ferum Privacy Settings")
            for fieldname, value in changes.items():
                settings.set(fieldname, value)
            settings.save(ignore_permissions=True)
        finally:
            frappe.flags[PRIVACY_SETTINGS_WRITE_FLAG] = previous
        return _privacy_state(frappe.get_single("Ferum Privacy Settings"))

    def _assert_zero_owned_residue(self, before_files: set[Path]) -> None:
        self.assertEqual(manifest_record_presence(self.manifest), [])
        self.assertEqual(find_registry_file_names(), [])
        fixture_names = [str(row["record_name"]) for row in self._binary_fixtures()]
        if fixture_names:
            self.assertEqual(
                frappe.get_all("File", filters={"name": ["in", fixture_names]}, pluck="name"),
                [],
            )
        self.assertEqual(self._private_file_paths(), before_files)

    @staticmethod
    def _reset_audit_snapshot() -> dict[str, set[str]]:
        return {
            doctype: set(frappe.get_all(doctype, pluck="name") or [])
            for doctype in ("Comment", "Deleted Document", "Version")
        }

    @staticmethod
    def _private_file_paths() -> set[Path]:
        directory = Path(frappe.get_site_path("private", "files"))
        if not directory.exists():
            return set()
        return {path.resolve() for path in directory.iterdir() if path.is_file()}

    @staticmethod
    def _recovery_directories() -> set[Path]:
        directory = Path(
            frappe.get_site_path("private", "files", ".ca-demo-uat-recovery")
        ).resolve()
        if not directory.is_dir():
            return set()
        return {path.resolve() for path in directory.iterdir() if path.is_dir()}
