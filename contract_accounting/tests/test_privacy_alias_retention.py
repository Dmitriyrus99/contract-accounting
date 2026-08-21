"""Runtime regressions for credential File aliases and retention races."""

from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from typing import Any, Iterator
from unittest.mock import patch
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file
from frappe.utils.password import set_encrypted_password
from frappe.utils.response import download_private_file
from werkzeug.exceptions import Forbidden

from contract_accounting.api import privacy, privacy_controls, privacy_retention
from contract_accounting.api.contractors import (
    change_contractor_assignment_status,
    create_contractor_assignment,
)
from contract_accounting.api.privacy import (
    PRIVACY_WRITE_FLAG,
    activate_privacy_policy,
    create_contractor_worker,
    create_personnel_credential,
    deactivate_privacy_policy,
    transition_contractor_worker,
)
from contract_accounting.api.privacy_controls import (
    approve_legal_hold,
    request_legal_hold,
)
from contract_accounting.api.privacy_retention import (
    execute_privacy_retention,
    get_privacy_retention_plan,
)
from contract_accounting.contract_accounting.doctype.ferum_personnel_credential import (
    ferum_personnel_credential as credential_controller,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
    _make_address,
    _make_project,
)
from contract_accounting.domain.privacy import (
    POLICY_HASH,
    POLICY_REFERENCE,
    SYNTHETIC_ACTIVATION_CONFIRMATION,
    SYNTHETIC_RETENTION_CONFIRMATION,
)
from contract_accounting.infrastructure import privacy_file_guard
from contract_accounting.infrastructure.privacy_target_lock import lock_assignment_privacy_target


class TestPrivacyAliasRetention(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.previous_user = frappe.session.user
        self.previous_developer_mode = frappe.conf.get("developer_mode")
        frappe.conf.developer_mode = 1
        frappe.set_user("Administrator")
        if frappe.db.get_single_value("Ferum Privacy Settings", "enabled"):
            deactivate_privacy_policy("Reset alias retention test state")
        token = uuid4().hex[:10]
        self.product_owner = self._make_user(token, "po", "Генеральный директор")
        self.data_owner = self._make_user(
            token,
            "data",
            "Менеджер персональных данных",
        )
        self.dpo = self._make_user(token, "dpo", "Ответственный за ПДн")
        self.legal = self._make_user(token, "legal", "Юрист")
        self.supplier = self._make_supplier(token)
        frappe.set_user(self.product_owner)
        activate_privacy_policy(
            "Synthetic Test",
            SYNTHETIC_ACTIVATION_CONFIRMATION,
            f"TEST-ALIAS-{token}",
            "Synthetic credential alias and retention acceptance",
        )

    def tearDown(self) -> None:
        try:
            frappe.set_user(self.product_owner)
            if frappe.db.get_single_value("Ferum Privacy Settings", "enabled"):
                deactivate_privacy_policy("Disable alias retention test policy")
        finally:
            frappe.conf.developer_mode = self.previous_developer_mode
            frappe.set_user(self.previous_user)
            super().tearDown()

    def test_hash_aliases_are_native_hidden_and_public_duplicate_is_rejected(self) -> None:
        worker = self._active_worker()
        content = f"synthetic-private-{uuid4().hex}".encode()
        canonical, alias = self._private_aliases(worker, content)
        credential = self._credential(worker, canonical.name)
        self.assertTrue(credential)
        self.assertNotEqual(canonical.name, alias.name)
        self.assertEqual(canonical.content_hash, alias.content_hash)

        frappe.set_user(self.data_owner)
        for file_name in (canonical.name, alias.name):
            self.assertFalse(frappe.has_permission("File", "read", doc=file_name))
            self.assertFalse(frappe.has_permission("File", "write", doc=file_name))
            self.assertFalse(frappe.has_permission("File", "delete", doc=file_name))
            self.assertFalse(frappe.get_doc("File", file_name).is_downloadable())
        frappe.set_user("Administrator")
        with self.assertRaises(frappe.PermissionError):
            frappe.delete_doc("File", alias.name, ignore_permissions=True, force=True)
        with self.assertRaisesRegex(frappe.PermissionError, "Public File alias"):
            save_file(
                "credential-public-bypass.txt",
                content,
                "Ferum Contractor Worker",
                worker,
                is_private=0,
            )
        self.assertFalse(
            frappe.db.exists(
                "File",
                {"content_hash": canonical.content_hash, "is_private": 0},
            )
        )

    def test_private_http_download_denies_owner_for_every_credential_state_and_alias(
        self,
    ) -> None:
        worker = self._active_worker()
        canonical, alias = self._private_aliases(worker, uuid4().bytes)
        credential = self._credential(worker, canonical.name)
        frappe.set_user(self.data_owner)
        self.assertEqual(canonical.owner, self.data_owner)
        previous_form_dict = frappe.local.form_dict
        try:
            frappe.local.form_dict = frappe._dict()
            for malware_status, verification_status in (
                ("Pending", "Draft"),
                ("Rejected", "Rejected"),
                ("Clean", "Revoked"),
            ):
                frappe.db.set_value(
                    "Ferum Personnel Credential",
                    credential,
                    {
                        "malware_status": malware_status,
                        "verification_status": verification_status,
                    },
                    update_modified=False,
                )
                for file_name in (canonical.name, alias.name):
                    file_doc = frappe.get_doc("File", file_name)
                    self.assertFalse(file_doc.is_downloadable())
                    with self.assertRaises(Forbidden) as denied:
                        download_private_file(str(file_doc.file_url))
                    self.assertEqual(denied.exception.code, 403)
        finally:
            frappe.local.form_dict = previous_form_dict

    def test_legal_hold_on_any_alias_blocks_file_retention(self) -> None:
        worker = self._active_worker()
        canonical, alias = self._private_aliases(worker, uuid4().bytes)
        credential = self._credential(worker, canonical.name)
        frappe.set_user(self.dpo)
        hold = request_legal_hold(
            "File",
            alias.name,
            "Synthetic alias requires complete retention pause",
            str(date.today() + timedelta(days=30)),
        )["legal_hold"]
        frappe.set_user(self.legal)
        approve_legal_hold(hold, "Legal", "Legal approves alias retention pause")
        frappe.set_user(self.product_owner)
        approve_legal_hold(
            hold,
            "Product Owner",
            "Product Owner approves alias retention pause",
        )

        frappe.set_user(self.dpo)
        plan = get_privacy_retention_plan(str(date.today() + timedelta(days=365 * 4)))
        deletion = next(
            action
            for action in plan["actions"]
            if action["target_name"] == credential and action["action"] == "Delete Credential File"
        )
        self.assertEqual(
            set(deletion["file_aliases"]),
            {canonical.name, alias.name},
        )
        self.assertTrue(deletion["blocked_by_legal_hold"])

    def test_shared_blob_second_credential_and_standard_attach_block_retention(self) -> None:
        worker = self._active_worker()
        canonical, _alias = self._private_aliases(worker, uuid4().bytes)
        first = self._credential(worker, canonical.name)
        second_canonical, _second_alias = self._private_aliases(worker, uuid4().bytes)
        second = self._credential(worker, second_canonical.name)
        frappe.db.set_value("Ferum Personnel Credential", second, "document", canonical.name)
        as_of = date.today() + timedelta(days=365 * 4)
        stale = privacy_retention._action(
            "Delete Credential File",
            "Ferum Personnel Credential",
            first,
            date.today(),
            file_name=canonical.name,
        )
        self.assertIsNone(privacy_retention._lock_and_revalidate_action(stale, as_of))
        self.assertTrue(frappe.db.exists("Ferum Personnel Credential", second))
        self.assertTrue(Path(canonical.get_full_path()).is_file())

        frappe.set_user(self.dpo)
        hold = request_legal_hold(
            "Ferum Personnel Credential",
            second,
            "Shared credential B requires retention hold",
            str(date.today() + timedelta(days=30)),
        )["legal_hold"]
        frappe.set_user(self.legal)
        approve_legal_hold(hold, "Legal", "Legal approves shared blob hold B")
        frappe.set_user(self.product_owner)
        approve_legal_hold(
            hold,
            "Product Owner",
            "Product Owner approves shared blob hold B",
        )
        planned = privacy_retention._action(
            "Delete Credential File",
            "Ferum Personnel Credential",
            first,
            date.today(),
            file_name=canonical.name,
        )
        self.assertTrue(planned["blocked_by_legal_hold"])

        frappe.db.set_value("Ferum Personnel Credential", second, "document", None)
        frappe.db.set_value("User", self.data_owner, "user_image", canonical.file_url)
        self.assertIsNone(privacy_retention._lock_and_revalidate_action(stale, as_of))
        self.assertTrue(Path(canonical.get_full_path()).is_file())

    def test_credential_file_never_materializes_public_thumbnail(self) -> None:
        worker = self._active_worker()
        canonical, _alias = self._private_aliases(worker, uuid4().bytes)
        self._credential(worker, canonical.name)
        with self.assertRaisesRegex(frappe.PermissionError, "Thumbnail"):
            frappe.get_doc("File", canonical.name).make_thumbnail()
        self.assertFalse(frappe.db.get_value("File", canonical.name, "thumbnail_url"))

    def test_retention_deletes_entire_alias_set_and_every_physical_path(self) -> None:
        worker = self._active_worker()
        canonical, alias = self._private_aliases(worker, uuid4().bytes)
        credential = self._credential(worker, canonical.name)
        paths = {
            frappe.get_doc("File", file_name).get_full_path()
            for file_name in (canonical.name, alias.name)
        }
        path_payloads = {path: Path(path).read_bytes() for path in paths}
        content_hash = canonical.content_hash
        self.assertTrue(all(os.path.exists(path) for path in paths))

        frappe.set_user(self.dpo)
        as_of = date.today() + timedelta(days=365 * 4)
        target_actions = [
            action
            for action in privacy_retention._build_plan(as_of)
            if action["target_doctype"] == "Ferum Personnel Credential"
            and action["target_name"] == credential
        ]
        self.assertEqual(
            {action["action"] for action in target_actions},
            {"Delete Credential File", "Minimize Credential Metadata"},
        )
        try:
            # execute_privacy_retention intentionally operates on the complete site.
            # A destructive regression must never erase committed UAT/demo Files
            # merely because they are also due on this synthetic future date.
            scheduled: list[tuple[tuple[dict[str, Any], ...], str]] = []
            with (
                patch.object(privacy_retention, "_build_plan", return_value=target_actions),
                patch.object(
                    privacy_retention,
                    "_schedule_physical_deletions",
                    side_effect=lambda entries, credential_name: scheduled.append(
                        (entries, credential_name)
                    ),
                ),
            ):
                result = execute_privacy_retention(
                    str(as_of),
                    SYNTHETIC_RETENTION_CONFIRMATION,
                    "Synthetic full alias retention execution",
                )
            self.assertEqual(result["planned"], 2)
            self.assertEqual(result["executed"], 2)
            self.assertFalse(frappe.db.exists("File", canonical.name))
            self.assertFalse(frappe.db.exists("File", alias.name))
            self.assertFalse(frappe.db.exists("File", {"content_hash": content_hash}))
            self.assertEqual(len(scheduled), 1)
            self.assertTrue(all(os.path.exists(path) for path in paths))
            pending_job = privacy_retention._publish_pending_physical_deletion(*scheduled[0])
            privacy_retention._stage_pending_physical_deletion(pending_job)
            privacy_retention._commit_pending_physical_deletion(pending_job)
            self.assertTrue(all(not os.path.exists(path) for path in paths))
            retained = frappe.get_doc("Ferum Personnel Credential", credential)
            self.assertFalse(retained.document)
            self.assertEqual(retained.retention_status, "Metadata Only")
            self.assertIsNone(retained.get_password("credential_number", raise_exception=False))
            self.assertFalse(retained.credential_number_masked)
        finally:
            # Frappe rolls database rows back after the test but physical deletion
            # is irreversible. Restore bytes before that rollback so its registered
            # new-File callbacks can remove this test's files without stale rows.
            for path, payload in path_payloads.items():
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                Path(path).write_bytes(payload)

    def test_stale_action_rechecks_new_open_ended_active_assignment(self) -> None:
        worker = self._active_worker()
        as_of = date.today() + timedelta(days=365 * 4)
        stale = privacy_retention._action(
            "Anonymize Worker",
            "Ferum Contractor Worker",
            worker,
            date.today(),
        )
        self._open_ended_assignment(worker)

        current = privacy_retention._lock_and_revalidate_action(stale, as_of)
        self.assertIsNone(current)
        self.assertEqual(
            frappe.db.get_value("Ferum Contractor Worker", worker, "retention_status"),
            "Active",
        )

    def test_postcommit_quarantine_retries_after_first_alias_move_fault(self) -> None:
        with TemporaryDirectory() as directory:
            paths = [Path(directory) / "first.bin", Path(directory) / "second.bin"]
            for index, path in enumerate(paths):
                path.write_bytes(f"alias-{index}".encode())
            entries = tuple(
                {"path": str(path), "file_urls": [], "content_hashes": []} for path in paths
            )
            with patch.object(
                privacy_retention.frappe,
                "get_site_path",
                return_value=directory,
            ):
                pending_job = privacy_retention._publish_pending_physical_deletion(
                    entries,
                    "TEST-QUARANTINE-FAULT",
                )
            real_replace = os.replace
            calls = 0

            def fail_after_first_alias(source: object, target: object) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("synthetic second-alias quarantine fault")
                real_replace(source, target)

            with (
                patch.object(
                    privacy_retention.frappe,
                    "get_site_path",
                    return_value=directory,
                ),
                patch.object(
                    privacy_retention.os,
                    "replace",
                    side_effect=fail_after_first_alias,
                ),
            ):
                with self.assertRaisesRegex(OSError, "second-alias"):
                    privacy_retention._stage_pending_physical_deletion(pending_job)
            self.assertTrue(paths[0].exists())
            self.assertTrue(paths[1].exists())
            self.assertFalse(list(Path(directory).glob("*.pending")))
            self.assertFalse(list(Path(directory).glob("*.committed")))

    def test_pending_manifest_publish_failure_never_moves_source_bytes(self) -> None:
        with TemporaryDirectory() as directory:
            original = Path(directory) / "source.bin"
            original.write_bytes(b"manifest-publication-fault")
            entries = ({"path": str(original), "file_urls": [], "content_hashes": []},)
            with (
                patch.object(
                    privacy_retention.frappe,
                    "get_site_path",
                    return_value=directory,
                ),
                patch.object(
                    privacy_retention.os,
                    "replace",
                    side_effect=OSError("synthetic manifest publication fault"),
                ),
            ):
                with self.assertRaisesRegex(OSError, "manifest publication fault"):
                    privacy_retention._publish_pending_physical_deletion(
                        entries,
                        "TEST-MANIFEST-FAULT",
                    )
            self.assertEqual(original.read_bytes(), b"manifest-publication-fault")
            self.assertFalse(list(Path(directory).glob("*.pending")))

    def test_corrupt_quarantine_manifest_rejects_blob_path_traversal(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "source.bin"
            original.write_bytes(b"traversal-regression")
            job = root / "malicious.pending"
            job.mkdir()
            (job / "manifest.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "credential": "TEST-TRAVERSAL",
                        "created_at": 0,
                        "entries": [
                            {
                                "path": str(original),
                                "blob": "../escape.bin",
                                "file_urls": [],
                                "content_hashes": [],
                                "size": original.stat().st_size,
                                "sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(
                privacy_retention.frappe,
                "get_site_path",
                return_value=directory,
            ):
                with self.assertRaises(frappe.ValidationError):
                    privacy_retention._read_quarantine_manifest(job)
            self.assertEqual(original.read_bytes(), b"traversal-regression")

    def _active_worker(self) -> str:
        frappe.set_user(self.data_owner)
        worker = create_contractor_worker(
            self.supplier,
            "TEST Alias Worker",
            "TEST-SUPPLIER-BASIS",
            self.data_owner,
        )["worker"]
        transition_contractor_worker(worker, "Active", "Synthetic alias worker activated")
        return worker

    def _private_aliases(self, worker: str, content: bytes) -> tuple[object, object]:
        frappe.set_user(self.data_owner)
        canonical = save_file(
            f"credential-{uuid4().hex}.png",
            content,
            "Ferum Contractor Worker",
            worker,
            is_private=1,
        )
        alias = save_file(
            f"credential-alias-{uuid4().hex}.png",
            content,
            "Ferum Contractor Worker",
            worker,
            is_private=1,
        )
        for path in {
            Path(canonical.get_full_path()).resolve(),
            Path(alias.get_full_path()).resolve(),
        }:
            self.addCleanup(path.unlink, missing_ok=True)
        return canonical, alias

    def _credential(self, worker: str, document: str) -> str:
        frappe.set_user(self.data_owner)
        return create_personnel_credential(
            "Ferum Contractor Worker",
            worker,
            "Electrical Safety",
            f"ALIAS-{uuid4().hex[:12]}",
            "TEST-SUPPLIER-BASIS",
            no_expiry=1,
            document=document,
        )["credential"]

    def _open_ended_assignment(self, worker: str) -> str:
        frappe.set_user("Administrator")
        project = _make_project()
        service_object = frappe.get_doc(
            {
                "doctype": "Ferum Service Object",
                "object_name": f"Alias retention object {uuid4().hex[:8]}",
                "customer": project.customer,
                "address": _make_address(project.customer, "Alias retention address"),
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
            "Alias retention work",
            "Synthetic open-ended assignment race",
            str(date.today()),
            supplier=self.supplier,
            contractor_worker=worker,
        )["contractor_assignment"]
        change_contractor_assignment_status(
            assignment,
            "Approved",
            "Synthetic active assignment wins retention race",
        )
        return assignment

    @staticmethod
    def _make_user(token: str, label: str, role: str) -> str:
        email = f"alias-{label}-{token}@example.test"
        previous_import_flag = frappe.flags.in_import
        try:
            frappe.flags.in_import = True
            return (
                frappe.get_doc(
                    {
                        "doctype": "User",
                        "email": email,
                        "first_name": f"Alias {label}",
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
                    "supplier_name": f"Alias Supplier {token}",
                    "supplier_group": frappe.db.get_value(
                        "Supplier Group",
                        {"is_group": 0},
                        "name",
                    ),
                }
            )
            .insert(ignore_permissions=True)
            .name
        )


class TestPrivacyRetentionTwoConnectionRace(FrappeTestCase):
    """Prove stale plans fail closed against committed concurrent blockers."""

    WAIT_SECONDS = 20

    def test_new_active_hold_between_plan_and_execute_causes_zero_mutation(self) -> None:
        self._run_two_connection_race("hold")

    def test_new_active_assignment_between_plan_and_execute_causes_zero_mutation(self) -> None:
        self._run_two_connection_race("assignment")

    def test_pending_hold_activation_linearizes_before_retention_recheck(self) -> None:
        site = str(frappe.local.site)
        token = uuid4().hex[:12]
        worker = f"CW-PENDING-HOLD-{token}"
        actors = {
            "requester": f"pending-dpo-{token}@example.test",
            "legal": f"pending-legal-{token}@example.test",
            "product_owner": f"pending-po-{token}@example.test",
        }
        self._insert_committed_worker(worker, token)
        for user, role in (
            (actors["requester"], "Ответственный за ПДн"),
            (actors["legal"], "Юрист"),
            (actors["product_owner"], "Генеральный директор"),
        ):
            self._insert_committed_actor(user, role)
        synthetic_settings = frappe._dict(activation_mode="Synthetic Test")
        with patch.object(
            privacy_controls,
            "active_privacy_settings",
            return_value=synthetic_settings,
        ):
            frappe.set_user(actors["requester"])
            hold = request_legal_hold(
                "Ferum Contractor Worker",
                worker,
                "Pending hold must serialize final activation with retention",
                str(date.today() + timedelta(days=30)),
            )["legal_hold"]
            frappe.set_user(actors["legal"])
            approve_legal_hold(hold, "Legal", "Legal pre-approves pending race hold")
            frappe.db.commit()
        self.addCleanup(
            self._cleanup_committed_race,
            worker,
            hold,
            tuple(actors.values()),
        )

        stale_action = privacy_retention._action(
            "Anonymize Worker",
            "Ferum Contractor Worker",
            worker,
            date.today(),
        )
        approval_has_target = Event()
        retention_started = Event()
        connection_ids: dict[str, int] = {}
        real_context_lock = privacy_controls._lock_protected_target_context

        def observed_context_lock(target_doctype: str, target_name: str) -> bool:
            locked = real_context_lock(target_doctype, target_name)
            approval_has_target.set()
            if not retention_started.wait(self.WAIT_SECONDS):
                raise AssertionError("retention did not start within bounded wait")
            return locked

        def stale_plan(_as_of: date) -> list[dict[str, Any]]:
            if not approval_has_target.wait(self.WAIT_SECONDS):
                raise AssertionError("pending hold approval did not lock target")
            retention_started.set()
            return [dict(stale_action)]

        def activate_pending_hold() -> None:
            with self._thread_site(site) as database:
                connection_ids["approval"] = self._connection_id(database)
                frappe.set_user(actors["product_owner"])
                with patch.object(
                    privacy_controls,
                    "_lock_protected_target_context",
                    side_effect=observed_context_lock,
                ):
                    result = approve_legal_hold(
                        hold,
                        "Product Owner",
                        "Product Owner activates pending race hold",
                    )
                if result["status"] != "Active":
                    raise AssertionError("pending legal hold did not become Active")
                database.commit()

        def execute_retention() -> dict[str, Any]:
            with self._thread_site(site) as database:
                connection_ids["retention"] = self._connection_id(database)
                return privacy_retention.execute_privacy_retention(
                    str(date.today() + timedelta(days=365 * 4)),
                    SYNTHETIC_RETENTION_CONFIRMATION,
                    "Pending hold activation race retention attempt",
                )

        with (
            patch.object(privacy_retention, "_build_plan", side_effect=stale_plan),
            patch.object(
                privacy_retention,
                "active_privacy_settings",
                return_value=synthetic_settings,
            ),
            patch.object(
                privacy_controls,
                "active_privacy_settings",
                return_value=synthetic_settings,
            ),
            ThreadPoolExecutor(max_workers=2, thread_name_prefix="pending-hold") as pool,
        ):
            approval_future = pool.submit(activate_pending_hold)
            retention_future = pool.submit(execute_retention)
            approval_future.result(timeout=self.WAIT_SECONDS)
            result = retention_future.result(timeout=self.WAIT_SECONDS)

        frappe.db.rollback()
        self.assertNotEqual(connection_ids["approval"], connection_ids["retention"])
        self.assertEqual(result["planned"], 1)
        self.assertEqual(result["executed"], 0)
        self.assertEqual(result["skipped_after_recheck"], 1)
        self.assertEqual(
            frappe.db.get_value("Ferum Contractor Worker", worker, "retention_status"),
            "Active",
        )
        self.assertEqual(
            frappe.db.get_value("Ferum Privacy Legal Hold", hold, "status"),
            "Active",
        )
        self.assertEqual(self._retention_audit_count(worker), 0)

    def _run_two_connection_race(self, blocker: str) -> None:
        site = str(frappe.local.site)
        token = uuid4().hex[:12]
        worker = f"CW-RACE-{token}"
        blocker_name = f"RACE-{blocker.upper()}-{token}"
        actors = {
            "requester": f"race-dpo-{token}@example.test",
            "legal": f"race-legal-{token}@example.test",
            "product_owner": f"race-po-{token}@example.test",
        }
        self._insert_committed_worker(worker, token)
        self.addCleanup(
            self._cleanup_committed_race,
            worker,
            blocker_name,
            tuple(actors.values()),
        )
        self._insert_committed_actor(actors["requester"], "Ответственный за ПДн")
        self._insert_committed_actor(actors["legal"], "Юрист")
        self._insert_committed_actor(actors["product_owner"], "Генеральный директор")
        before = self._worker_snapshot(worker)
        audit_before = self._retention_audit_count(worker)
        stale_action = {
            "action": "Anonymize Worker",
            "target_doctype": "Ferum Contractor Worker",
            "target_name": worker,
            "file": None,
            "file_aliases": [],
            "base_date": str(date.today()),
            "blocked_by_legal_hold": False,
        }
        plan_ready = Event()
        blocker_committed = Event()
        connection_ids: dict[str, int] = {}

        def stale_plan(_as_of: date) -> list[dict[str, Any]]:
            plan_ready.set()
            if not blocker_committed.wait(self.WAIT_SECONDS):
                raise AssertionError("concurrent blocker did not commit within bounded wait")
            return [dict(stale_action)]

        def execute_stale_plan() -> dict[str, Any]:
            with self._thread_site(site) as database:
                connection_ids["retention"] = self._connection_id(database)
                return privacy_retention.execute_privacy_retention(
                    str(date.today() + timedelta(days=365 * 4)),
                    SYNTHETIC_RETENTION_CONFIRMATION,
                    "Two-connection stale retention plan regression",
                )

        def commit_blocker() -> None:
            if not plan_ready.wait(self.WAIT_SECONDS):
                raise AssertionError("retention plan was not built within bounded wait")
            with self._thread_site(site) as database:
                connection_ids["blocker"] = self._connection_id(database)
                if blocker == "hold":
                    self._create_active_hold(worker, actors)
                else:
                    self._insert_active_assignment(worker, blocker_name)
                database.commit()
            blocker_committed.set()

        synthetic_settings = frappe._dict(activation_mode="Synthetic Test")
        with (
            patch.object(privacy_retention, "_build_plan", side_effect=stale_plan),
            patch.object(
                privacy_retention,
                "active_privacy_settings",
                return_value=synthetic_settings,
            ),
            patch.object(
                privacy_controls,
                "active_privacy_settings",
                return_value=synthetic_settings,
            ),
            ThreadPoolExecutor(max_workers=2, thread_name_prefix=f"privacy-{blocker}") as pool,
        ):
            retention_future = pool.submit(execute_stale_plan)
            blocker_future = pool.submit(commit_blocker)
            blocker_future.result(timeout=self.WAIT_SECONDS)
            result = retention_future.result(timeout=self.WAIT_SECONDS)

        frappe.db.rollback()
        self.assertNotEqual(connection_ids["retention"], connection_ids["blocker"])
        self.assertEqual(result["planned"], 1)
        self.assertEqual(result["executed"], 0)
        self.assertEqual(result["skipped_after_recheck"], 1)
        self.assertEqual(self._worker_snapshot(worker), before)
        self.assertEqual(self._retention_audit_count(worker), audit_before)
        if blocker == "hold":
            self.assertTrue(
                frappe.db.exists(
                    "Ferum Privacy Legal Hold",
                    {
                        "target_doctype": "Ferum Contractor Worker",
                        "target_name": worker,
                        "status": "Active",
                    },
                )
            )
        else:
            self.assertEqual(
                frappe.db.get_value("Ferum Contractor Assignment", blocker_name, "status"),
                "Approved",
            )

    @staticmethod
    @contextmanager
    def _thread_site(site: str) -> Iterator[Any]:
        frappe.init(site=site)
        frappe.connect()
        try:
            frappe.set_user("Administrator")
            yield frappe.db
        finally:
            frappe.db.rollback()
            frappe.destroy()

    @staticmethod
    def _connection_id(database: Any) -> int:
        return int(database.sql("select connection_id()")[0][0])

    @staticmethod
    def _insert_committed_worker(worker: str, token: str) -> None:
        now = frappe.utils.now_datetime()
        frappe.db.sql(
            """
            insert into `tabFerum Contractor Worker`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 supplier, worker_external_id, display_name, status,
                 privacy_basis_reference, privacy_policy_reference,
                 privacy_policy_hash, retention_status)
            values
                (%s, %s, %s, 'Administrator', 'Administrator', 0, 0,
                 %s, %s, %s, 'Active', %s, %s, %s, 'Active')
            """,
            (
                worker,
                now,
                now,
                f"RACE-SUPPLIER-{token}",
                f"RACE-EXT-{token}",
                f"Race Worker {token}",
                f"TEST-RACE-{token}",
                POLICY_REFERENCE,
                POLICY_HASH,
            ),
        )
        frappe.db.commit()

    @staticmethod
    def _insert_committed_actor(user: str, role: str) -> None:
        now = frappe.utils.now_datetime()
        frappe.db.sql(
            """
            insert into `tabUser`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 email, first_name, enabled, user_type)
            values
                (%s, %s, %s, 'Administrator', 'Administrator', 0, 0,
                 %s, 'Race Actor', 1, 'System User')
            """,
            (user, now, now, user),
        )
        frappe.db.sql(
            """
            insert into `tabHas Role`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 parent, parenttype, parentfield, role)
            values
                (%s, %s, %s, 'Administrator', 'Administrator', 0, 1,
                 %s, 'User', 'roles', %s)
            """,
            (frappe.generate_hash(length=10), now, now, user, role),
        )
        frappe.db.commit()

    @staticmethod
    def _create_active_hold(worker: str, actors: dict[str, str]) -> None:
        frappe.set_user(actors["requester"])
        hold = request_legal_hold(
            "Ferum Contractor Worker",
            worker,
            "Two-connection legal hold wins stale retention plan",
            str(date.today() + timedelta(days=30)),
        )["legal_hold"]
        frappe.set_user(actors["legal"])
        approve_legal_hold(hold, "Legal", "Distinct Legal actor approves race hold")
        frappe.set_user(actors["product_owner"])
        result = approve_legal_hold(
            hold,
            "Product Owner",
            "Distinct Product Owner approves race hold",
        )
        if result["status"] != "Active":
            raise AssertionError("concurrent legal hold did not reach Active")

    @staticmethod
    def _insert_active_assignment(worker: str, assignment_name: str) -> None:
        proposed = frappe._dict(
            status="Approved",
            execution_mode="Contractor",
            contractor_worker=worker,
        )
        lock_assignment_privacy_target(proposed)
        now = frappe.utils.now_datetime()
        frappe.db.sql(
            """
            insert into `tabFerum Contractor Assignment`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 contractor_worker, status, effective_from)
            values
                (%s, %s, %s, 'Administrator', 'Administrator', 0, 0,
                 %s, 'Approved', %s)
            """,
            (assignment_name, now, now, worker, date.today()),
        )

    @staticmethod
    def _worker_snapshot(worker: str) -> dict[str, Any]:
        row = frappe.db.get_value(
            "Ferum Contractor Worker",
            worker,
            (
                "display_name",
                "supplier",
                "status",
                "privacy_basis_reference",
                "retention_status",
            ),
            as_dict=True,
        )
        return dict(row or {})

    @staticmethod
    def _retention_audit_count(worker: str) -> int:
        return int(
            frappe.db.count(
                "Ferum Privacy Event",
                {
                    "target_doctype": "Ferum Contractor Worker",
                    "target_name": worker,
                    "event_type": ["in", ["Clear Worker Contact", "Anonymize Worker"]],
                },
            )
        )

    @staticmethod
    def _cleanup_committed_race(
        worker: str,
        blocker_name: str,
        actors: tuple[str, ...],
    ) -> None:
        frappe.db.rollback()
        frappe.db.sql(
            "delete from `tabFerum Privacy Event` where target_doctype = %s and target_name = %s",
            ("Ferum Contractor Worker", worker),
        )
        frappe.db.sql(
            """
            delete from `tabFerum Privacy Event`
             where target_doctype = 'Ferum Privacy Legal Hold'
               and target_name in (
                   select name from `tabFerum Privacy Legal Hold`
                    where target_doctype = 'Ferum Contractor Worker' and target_name = %s
               )
            """,
            (worker,),
        )
        frappe.db.sql(
            """
            delete from `tabFerum Privacy Legal Hold`
             where target_doctype = 'Ferum Contractor Worker' and target_name = %s
            """,
            (worker,),
        )
        frappe.db.sql("delete from `tabFerum Contractor Assignment` where name = %s", blocker_name)
        frappe.db.sql("delete from `tabFerum Contractor Worker` where name = %s", worker)
        for user in actors:
            frappe.db.sql("delete from `tabHas Role` where parent = %s", user)
            frappe.db.sql("delete from `tabUser` where name = %s", user)
        frappe.db.commit()


class TestPrivacyDownloadTwoConnectionRace(FrappeTestCase):
    """A committed concurrent terminal state must make typed download fail closed."""

    WAIT_SECONDS = 20

    def test_committed_revoke_wins_against_waiting_download(self) -> None:
        self._run_download_race("revoke")

    def test_committed_retention_wins_against_waiting_download(self) -> None:
        self._run_download_race("retention")

    def test_committed_expiry_wins_against_waiting_download(self) -> None:
        self._run_download_race("expiry")

    def test_retention_event_fault_rolls_back_database_and_physical_bytes(self) -> None:
        fixture = self._committed_retention_fault_fixture("event")
        synthetic_settings = frappe._dict(activation_mode="Synthetic Test")
        with (
            patch.object(
                credential_controller,
                "active_privacy_settings",
                return_value=synthetic_settings,
            ),
            patch.object(
                privacy_retention,
                "record_privacy_event",
                side_effect=RuntimeError("synthetic audit event fault"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "audit event fault"):
                privacy_retention._execute_action(
                    fixture["delete_action"],
                    "Retention audit failure must rollback physical quarantine",
                )
        frappe.db.rollback()
        self._assert_retention_fault_rolled_back(fixture)

    def test_before_commit_callback_fault_never_moves_physical_bytes(self) -> None:
        fixture = self._committed_retention_fault_fixture("before-commit")
        synthetic_settings = frappe._dict(activation_mode="Synthetic Test")
        with patch.object(
            credential_controller,
            "active_privacy_settings",
            return_value=synthetic_settings,
        ):
            physical_job = privacy_retention._execute_action(
                fixture["delete_action"],
                "Before-commit failure must leave physical bytes untouched",
            )
        self.assertIsNotNone(physical_job)
        real_stage = privacy_retention._stage_pending_physical_deletion

        def stage_then_fail(job: Path) -> None:
            real_stage(job)
            raise RuntimeError("synthetic before-commit callback fault")

        privacy_retention._register_physical_deletion_commit_callbacks((physical_job,))
        with patch.object(
            privacy_retention,
            "_stage_pending_physical_deletion",
            side_effect=stage_then_fail,
        ):
            with self.assertRaisesRegex(RuntimeError, "before-commit callback fault"):
                frappe.db.commit()
        self.assertEqual(fixture["physical_path"].read_bytes(), fixture["content"])
        frappe.db.rollback()
        self._assert_retention_fault_rolled_back(fixture)

    def test_sql_commit_exception_restores_database_path_and_hash_on_rollback(self) -> None:
        fixture = self._committed_retention_fault_fixture("sql-commit")
        synthetic_settings = frappe._dict(activation_mode="Synthetic Test")
        with patch.object(
            credential_controller,
            "active_privacy_settings",
            return_value=synthetic_settings,
        ):
            physical_job = privacy_retention._execute_action(
                fixture["delete_action"],
                "SQL COMMIT failure must restore exact credential blob",
            )
        self.assertIsNotNone(physical_job)
        privacy_retention._register_physical_deletion_commit_callbacks((physical_job,))
        real_sql = frappe.db.sql

        def fail_sql_commit(query: str, *args: Any, **kwargs: Any) -> Any:
            if str(query).strip().lower() == "commit":
                raise RuntimeError("synthetic SQL COMMIT exception")
            return real_sql(query, *args, **kwargs)

        with patch.object(frappe.db, "sql", side_effect=fail_sql_commit):
            with self.assertRaisesRegex(RuntimeError, "SQL COMMIT exception"):
                frappe.db.commit()
        frappe.db.rollback()
        self._assert_retention_fault_rolled_back(fixture)

    def test_retention_next_action_fault_rolls_back_prior_file_action(self) -> None:
        fixture = self._committed_retention_fault_fixture("next-action")
        real_execute = privacy_retention._execute_action
        calls = 0

        def fail_second_action(action: dict[str, Any], reason: str) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("synthetic next retention action fault")
            real_execute(action, reason)

        synthetic_settings = frappe._dict(activation_mode="Synthetic Test")
        with (
            patch.object(
                privacy_retention,
                "_build_plan",
                return_value=[fixture["delete_action"], fixture["metadata_action"]],
            ),
            patch.object(
                privacy_retention,
                "active_privacy_settings",
                return_value=synthetic_settings,
            ),
            patch.object(
                credential_controller,
                "active_privacy_settings",
                return_value=synthetic_settings,
            ),
            patch.object(
                privacy_retention,
                "_execute_action",
                side_effect=fail_second_action,
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "next retention action fault"):
                privacy_retention.execute_privacy_retention(
                    str(date.today() + timedelta(days=365 * 4)),
                    SYNTHETIC_RETENTION_CONFIRMATION,
                    "Later retention action failure must rollback earlier file action",
                )
        frappe.db.rollback()
        self.assertEqual(calls, 2)
        self._assert_retention_fault_rolled_back(fixture)

    def test_postcommit_unlink_fault_leaves_retryable_committed_ledger(self) -> None:
        with TemporaryDirectory() as directory:
            paths = [Path(directory) / "first.bin", Path(directory) / "second.bin"]
            for index, path in enumerate(paths):
                path.write_bytes(f"unlink-{index}".encode())
            entries = tuple(
                {"path": str(path), "file_urls": [], "content_hashes": []} for path in paths
            )
            real_unlink = Path.unlink
            failed = False

            with patch.object(
                privacy_retention.frappe,
                "get_site_path",
                return_value=directory,
            ):
                pending_job = privacy_retention._publish_pending_physical_deletion(
                    entries,
                    "TEST-POSTCOMMIT-UNLINK",
                )
                privacy_retention._stage_pending_physical_deletion(pending_job)
                committed_job = pending_job.with_suffix(".committed")
                os.replace(pending_job, committed_job)

            def fail_first_blob_unlink(
                path: Path,
                missing_ok: bool = False,
            ) -> None:
                nonlocal failed
                if path.suffix == ".blob" and not failed:
                    failed = True
                    raise OSError("synthetic post-commit unlink fault")
                real_unlink(path, missing_ok=missing_ok)

            with (
                patch.object(
                    privacy_retention.frappe,
                    "get_site_path",
                    return_value=directory,
                ),
                patch.object(Path, "unlink", new=fail_first_blob_unlink),
            ):
                with self.assertRaisesRegex(OSError, "post-commit unlink fault"):
                    privacy_retention._finish_committed_physical_deletion(committed_job)
            self.assertTrue(failed)
            self.assertTrue(all(not path.exists() for path in paths))
            self.assertEqual(len(list(Path(directory).glob("*.committed"))), 1)
            with patch.object(
                privacy_retention.frappe,
                "get_site_path",
                return_value=directory,
            ):
                self.assertEqual(privacy_retention.retry_committed_physical_deletions(), 1)
            self.assertFalse(list(Path(directory).glob("*.committed")))

    def test_corrupt_jobs_are_isolated_and_valid_job_continues_without_blocking_execute(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            valid_source = root / "valid.bin"
            valid_source.write_bytes(b"valid-ledger-job")
            valid_entries = ({"path": str(valid_source), "file_urls": [], "content_hashes": []},)
            for name in ("000-corrupt.pending", "001-corrupt.committed"):
                job = root / name
                job.mkdir()
                (job / "manifest.json").write_text("{corrupt", encoding="utf-8")
            synthetic_settings = frappe._dict(activation_mode="Synthetic Test")
            frappe.set_user("Administrator")
            with patch.object(
                privacy_retention.frappe,
                "get_site_path",
                return_value=directory,
            ):
                valid_pending = privacy_retention._publish_pending_physical_deletion(
                    valid_entries,
                    "TEST-VALID-LEDGER",
                )
                privacy_retention._stage_pending_physical_deletion(valid_pending)
                valid_committed = valid_pending.with_suffix(".committed")
                os.replace(valid_pending, valid_committed)
                with (
                    patch.object(
                        privacy_retention,
                        "active_privacy_settings",
                        return_value=synthetic_settings,
                    ),
                    patch.object(privacy_retention, "_build_plan", return_value=[]),
                    patch.object(privacy_retention.frappe, "log_error") as logged,
                ):
                    result = privacy_retention.execute_privacy_retention(
                        str(date.today()),
                        SYNTHETIC_RETENTION_CONFIRMATION,
                        "Corrupt jobs must not globally block valid retention queue",
                    )
            self.assertEqual(result["executed"], 0)
            self.assertFalse(valid_source.exists())
            self.assertFalse(valid_committed.exists())
            error_jobs = sorted(root.glob("*.error"))
            self.assertEqual(len(error_jobs), 2)
            self.assertTrue(all((job / "error.json").is_file() for job in error_jobs))
            self.assertEqual(logged.call_count, 2)

    def test_pending_recovery_serializes_with_concurrent_private_alias(self) -> None:
        fixture = self._committed_retention_fault_fixture("recovery-alias")
        site = str(frappe.local.site)
        credential = str(fixture["credential"])
        file_doc = frappe.get_doc("File", fixture["file"])
        entries = privacy_retention._physical_deletion_entries([file_doc])
        pending_job = privacy_retention._publish_pending_physical_deletion(entries, credential)
        privacy_retention._stage_pending_physical_deletion(pending_job)
        self.addCleanup(self._cleanup_pending_recovery_job, pending_job)
        self.assertFalse(fixture["physical_path"].exists())

        recovery_locked = Event()
        alias_lock_entered = Event()
        alias_lock_returned = Event()
        connection_ids: dict[str, int] = {}
        real_recovery_lock = privacy_retention.lock_privacy_target
        real_alias_lock = privacy_file_guard.lock_privacy_target

        def observed_recovery_lock(target_doctype: str, target_name: str) -> bool:
            locked = real_recovery_lock(target_doctype, target_name)
            if target_doctype == "Ferum Personnel Credential" and target_name == credential:
                recovery_locked.set()
                if not alias_lock_entered.wait(self.WAIT_SECONDS):
                    raise AssertionError("private alias did not enter recovery Credential lock")
                if alias_lock_returned.is_set():
                    raise AssertionError("private alias bypassed recovery Credential lock")
            return locked

        def observed_alias_lock(target_doctype: str, target_name: str) -> bool:
            is_target = target_doctype == "Ferum Personnel Credential" and target_name == credential
            if is_target:
                alias_lock_entered.set()
            locked = real_alias_lock(target_doctype, target_name)
            if is_target:
                alias_lock_returned.set()
            return locked

        def recover_pending() -> None:
            with TestPrivacyRetentionTwoConnectionRace._thread_site(site) as database:
                connection_ids["recovery"] = TestPrivacyRetentionTwoConnectionRace._connection_id(
                    database
                )
                with patch.object(
                    privacy_retention,
                    "lock_privacy_target",
                    side_effect=observed_recovery_lock,
                ):
                    if not privacy_retention._recover_pending_physical_deletion(
                        pending_job,
                        force=True,
                    ):
                        raise AssertionError("pending recovery did not run")
                database.commit()

        def create_alias() -> tuple[str, Path]:
            if not recovery_locked.wait(self.WAIT_SECONDS):
                raise AssertionError("recovery did not acquire Credential lock")
            with TestPrivacyRetentionTwoConnectionRace._thread_site(site) as database:
                connection_ids["alias"] = TestPrivacyRetentionTwoConnectionRace._connection_id(
                    database
                )
                alias = save_file(
                    f"recovery-alias-{uuid4().hex}.png",
                    fixture["content"],
                    "Ferum Contractor Worker",
                    fixture["worker"],
                    is_private=1,
                )
                alias_path = Path(alias.get_full_path()).resolve()
                database.commit()
                return str(alias.name), alias_path

        synthetic_settings = frappe._dict(activation_mode="Synthetic Test")
        with (
            patch.object(
                credential_controller,
                "active_privacy_settings",
                return_value=synthetic_settings,
            ),
            patch.object(
                privacy_file_guard,
                "lock_privacy_target",
                side_effect=observed_alias_lock,
            ),
            ThreadPoolExecutor(max_workers=2, thread_name_prefix="pending-recovery") as pool,
        ):
            recovery_future = pool.submit(recover_pending)
            alias_future = pool.submit(create_alias)
            recovery_future.result(timeout=self.WAIT_SECONDS)
            alias_name, alias_path = alias_future.result(timeout=self.WAIT_SECONDS)

        self.addCleanup(alias_path.unlink, missing_ok=True)
        frappe.db.rollback()
        self.assertNotEqual(connection_ids["recovery"], connection_ids["alias"])
        self.assertTrue(alias_lock_entered.is_set())
        self.assertTrue(alias_lock_returned.is_set())
        self.assertEqual(fixture["physical_path"].read_bytes(), fixture["content"])
        self.assertEqual(alias_path.read_bytes(), fixture["content"])
        self.assertTrue(frappe.db.exists("File", alias_name))
        self.assertFalse(pending_job.exists())

    def _run_download_race(self, mutation: str) -> None:
        site = str(frappe.local.site)
        token = uuid4().hex[:12]
        worker = f"CW-DOWNLOAD-RACE-{token}"
        credential = f"FPCR-DOWNLOAD-RACE-{token}"
        content = f"synthetic-download-race-{token}".encode()
        # Every race starts from an actually downloadable credential. The
        # concurrent Expired status transition, not an already elapsed date,
        # must be what makes the waiting download fail closed.
        expires_on = None
        file_doc = self._insert_committed_download_fixture(
            worker,
            credential,
            token,
            content,
            expires_on,
        )
        physical_path = Path(file_doc.get_full_path()).resolve()
        self.addCleanup(
            self._cleanup_committed_download_fixture,
            worker,
            credential,
            str(file_doc.content_hash),
            physical_path,
        )
        mutation_locked = Event()
        download_started = Event()
        connection_ids: dict[str, int] = {}
        synthetic_settings = frappe._dict(activation_mode="Synthetic Test")

        def commit_terminal_state() -> None:
            with TestPrivacyRetentionTwoConnectionRace._thread_site(site) as database:
                connection_ids["mutation"] = TestPrivacyRetentionTwoConnectionRace._connection_id(
                    database
                )
                if not privacy.lock_privacy_target(privacy.CREDENTIAL_DOCTYPE, credential):
                    raise AssertionError("download-race Credential lock target is missing")
                mutation_locked.set()
                if not download_started.wait(self.WAIT_SECONDS):
                    raise AssertionError("download did not start within bounded wait")
                if mutation == "revoke":
                    privacy.revoke_or_reject_credential(
                        credential,
                        "Revoked",
                        "Concurrent revoke must win before typed download",
                    )
                elif mutation == "retention":
                    physical_job = privacy_retention._execute_action(
                        {
                            "action": "Delete Credential File",
                            "target_doctype": "Ferum Personnel Credential",
                            "target_name": credential,
                            "file": file_doc.name,
                            "file_aliases": [file_doc.name],
                            "base_date": str(date.today()),
                            "blocked_by_legal_hold": False,
                        },
                        "Concurrent retention must win before typed download",
                    )
                    if not physical_job:
                        raise AssertionError("retention did not schedule physical deletion")
                    privacy_retention._register_physical_deletion_commit_callbacks((physical_job,))
                else:
                    doc = frappe.get_doc("Ferum Personnel Credential", credential)
                    with (
                        privacy._flag(PRIVACY_WRITE_FLAG),
                        privacy._flag(
                            privacy.PRIVACY_TRANSITION_FLAG,
                            "Expired",
                        ),
                    ):
                        doc.verification_status = "Expired"
                        doc.transition_reason = "Concurrent credential expiry wins download race"
                        doc.save(ignore_permissions=True)
                    privacy._event(
                        "Credential Automatically Expired",
                        doc,
                        doc.transition_reason,
                        {"expires_on": str(doc.expires_on)},
                    )
                database.commit()

        def attempt_download() -> str:
            if not mutation_locked.wait(self.WAIT_SECONDS):
                raise AssertionError("terminal mutation did not acquire Credential lock")
            with TestPrivacyRetentionTwoConnectionRace._thread_site(site) as database:
                connection_ids["download"] = TestPrivacyRetentionTwoConnectionRace._connection_id(
                    database
                )
                download_started.set()
                frappe.local.response = frappe._dict()
                try:
                    privacy.download_credential_attachment(
                        credential,
                        "Waiting typed download must recheck committed terminal state",
                    )
                except (frappe.PermissionError, frappe.ValidationError, frappe.DoesNotExistError):
                    if frappe.local.response.get("filecontent"):
                        raise AssertionError("denied download exposed response bytes")
                    return "denied"
                raise AssertionError("terminal-state race unexpectedly returned attachment bytes")

        with (
            patch.object(privacy, "_active_settings", return_value=synthetic_settings),
            patch.object(
                credential_controller,
                "active_privacy_settings",
                return_value=synthetic_settings,
            ),
            patch.object(
                privacy.frappe,
                "get_roles",
                return_value=["Менеджер персональных данных"],
            ),
            ThreadPoolExecutor(max_workers=2, thread_name_prefix=f"download-{mutation}") as pool,
        ):
            mutation_future = pool.submit(commit_terminal_state)
            download_future = pool.submit(attempt_download)
            self.assertEqual(download_future.result(timeout=self.WAIT_SECONDS), "denied")
            mutation_future.result(timeout=self.WAIT_SECONDS)

        frappe.db.rollback()
        self.assertNotEqual(connection_ids["mutation"], connection_ids["download"])
        self.assertEqual(
            frappe.db.count(
                "Ferum Privacy Event",
                {
                    "target_doctype": "Ferum Personnel Credential",
                    "target_name": credential,
                    "event_type": "Credential Attachment Downloaded",
                },
            ),
            0,
        )

    def _committed_retention_fault_fixture(self, label: str) -> dict[str, Any]:
        token = uuid4().hex[:12]
        worker = f"CW-RETENTION-FAULT-{token}"
        credential = f"FPCR-RETENTION-FAULT-{token}"
        content = f"synthetic-retention-{label}-{token}".encode()
        file_doc = self._insert_committed_download_fixture(
            worker,
            credential,
            token,
            content,
            None,
        )
        physical_path = Path(file_doc.get_full_path()).resolve()
        self.addCleanup(
            self._cleanup_committed_download_fixture,
            worker,
            credential,
            str(file_doc.content_hash),
            physical_path,
        )
        common = {
            "target_doctype": "Ferum Personnel Credential",
            "target_name": credential,
            "base_date": str(date.today()),
            "blocked_by_legal_hold": False,
        }
        return {
            "worker": worker,
            "credential": credential,
            "file": str(file_doc.name),
            "file_url": str(file_doc.file_url),
            "content_hash": str(file_doc.content_hash),
            "content": content,
            "physical_path": physical_path,
            "quarantine_baseline": frozenset(
                path
                for pattern in ("*.pending", "*.committed")
                for path in physical_path.parent.glob(f".privacy-retention-quarantine/{pattern}")
            ),
            "delete_action": {
                **common,
                "action": "Delete Credential File",
                "file": str(file_doc.name),
                "file_aliases": [str(file_doc.name)],
            },
            "metadata_action": {
                **common,
                "action": "Minimize Credential Metadata",
                "file": None,
                "file_aliases": [],
            },
        }

    @staticmethod
    def _cleanup_pending_recovery_job(job: Path) -> None:
        if job.exists():
            privacy_retention._recover_pending_physical_deletion(job, force=True)
        committed = job.with_suffix(".committed")
        if committed.exists():
            privacy_retention._finish_committed_physical_deletion(committed)

    def _assert_retention_fault_rolled_back(self, fixture: dict[str, Any]) -> None:
        credential = str(fixture["credential"])
        file_name = str(fixture["file"])
        physical_path = fixture["physical_path"]
        self.assertEqual(
            frappe.db.get_value("Ferum Personnel Credential", credential, "document"),
            file_name,
        )
        self.assertEqual(
            frappe.db.get_value("Ferum Personnel Credential", credential, "retention_status"),
            "Active",
        )
        self.assertTrue(frappe.db.exists("File", file_name))
        self.assertEqual(
            frappe.db.get_value("File", file_name, "content_hash"),
            fixture["content_hash"],
        )
        self.assertEqual(physical_path.read_bytes(), fixture["content"])
        self.assertEqual(
            frappe.db.count(
                "Ferum Privacy Event",
                {
                    "target_doctype": "Ferum Personnel Credential",
                    "target_name": credential,
                    "event_type": "Delete Credential File",
                },
            ),
            0,
        )
        self.assertEqual(
            frozenset(
                path
                for pattern in ("*.pending", "*.committed")
                for path in physical_path.parent.glob(f".privacy-retention-quarantine/{pattern}")
            ),
            fixture["quarantine_baseline"],
        )

    @staticmethod
    def _insert_committed_download_fixture(
        worker: str,
        credential: str,
        token: str,
        content: bytes,
        expires_on: date | None,
    ) -> Any:
        TestPrivacyRetentionTwoConnectionRace._insert_committed_worker(worker, token)
        frappe.set_user("Administrator")
        file_doc = save_file(
            f"download-race-{token}.png",
            content,
            "Ferum Contractor Worker",
            worker,
            is_private=1,
        )
        now = frappe.utils.now_datetime()
        frappe.db.sql(
            """
            insert into `tabFerum Personnel Credential`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 holder_type, holder, credential_type, credential_number_masked,
                 expires_on, no_expiry, document, malware_status,
                 malware_scan_reference, scanned_file_hash, scanned_at, scanned_by,
                 verification_status, privacy_basis_reference,
                 privacy_policy_reference, privacy_policy_hash, retention_status)
            values
                (%s, %s, %s, 'Administrator', 'Administrator', 0, 0,
                 'Ferum Contractor Worker', %s, 'Electrical Safety', '••••0001',
                 %s, %s, %s, 'Clean', 'TEST-DOWNLOAD-RACE-SCAN', %s, %s,
                 'Administrator', 'Verified', %s, %s, %s, 'Active')
            """,
            (
                credential,
                now,
                now,
                worker,
                expires_on,
                int(expires_on is None),
                file_doc.name,
                hashlib.sha256(content).hexdigest(),
                now,
                f"TEST-DOWNLOAD-RACE-{token}",
                POLICY_REFERENCE,
                POLICY_HASH,
            ),
        )
        set_encrypted_password(
            "Ferum Personnel Credential",
            credential,
            "TEST-DOWNLOAD-RACE-0001",
            "credential_number",
        )
        frappe.db.commit()
        return file_doc

    @staticmethod
    def _cleanup_committed_download_fixture(
        worker: str,
        credential: str,
        content_hash: str,
        physical_path: Path,
    ) -> None:
        frappe.db.rollback()
        frappe.db.sql(
            "delete from `tabFerum Privacy Event` where target_doctype = %s and target_name = %s",
            ("Ferum Personnel Credential", credential),
        )
        frappe.db.sql(
            "delete from `tabVersion` where ref_doctype = %s and docname = %s",
            ("Ferum Personnel Credential", credential),
        )
        frappe.db.sql(
            "delete from `tabComment` where reference_doctype = %s and reference_name in (%s, %s)",
            ("Ferum Personnel Credential", credential, worker),
        )
        frappe.db.sql(
            "delete from `__Auth` where doctype = %s and name = %s",
            ("Ferum Personnel Credential", credential),
        )
        frappe.db.sql(
            "delete from `tabFerum Personnel Credential` where name = %s",
            credential,
        )
        frappe.db.sql("delete from `tabFile` where content_hash = %s", content_hash)
        frappe.db.sql("delete from `tabFerum Contractor Worker` where name = %s", worker)
        frappe.db.commit()
        physical_path.unlink(missing_ok=True)


class TestPrivacyFileCreationTwoConnectionRace(FrappeTestCase):
    """Prove public hash aliases and Credential creation cannot both commit."""

    WAIT_SECONDS = 20

    def test_public_alias_started_first_forces_credential_recheck_and_rejection(self) -> None:
        site = str(frappe.local.site)
        token = uuid4().hex[:12]
        worker = f"CW-FILE-RACE-{token}"
        content = f"synthetic-file-race-{token}".encode()
        physical_paths: set[Path] = set()
        TestPrivacyRetentionTwoConnectionRace._insert_committed_worker(worker, token)
        frappe.set_user("Administrator")
        canonical = save_file(
            f"credential-race-{token}.png",
            content,
            "Ferum Contractor Worker",
            worker,
            is_private=1,
        )
        content_hash = str(canonical.content_hash)
        physical_paths.add(Path(canonical.get_full_path()).resolve())
        frappe.db.commit()
        self.addCleanup(
            self._cleanup_committed_file_race,
            worker,
            content_hash,
            physical_paths,
        )

        public_locked = Event()
        credential_attempted = Event()
        connection_ids: dict[str, int] = {}
        real_lock = privacy_file_guard.lock_file_content_hash_aliases

        def observed_lock(
            hash_value: str,
            *,
            canonical_file: str | None = None,
            file_url: str | None = None,
        ) -> tuple[str, ...]:
            if canonical_file:
                credential_attempted.set()
                return real_lock(
                    hash_value,
                    canonical_file=canonical_file,
                    file_url=file_url,
                )
            locked = real_lock(hash_value, file_url=file_url)
            public_locked.set()
            if not credential_attempted.wait(self.WAIT_SECONDS):
                raise AssertionError("Credential creation did not reach the shared File lock")
            return locked

        def create_public_alias() -> str:
            with TestPrivacyRetentionTwoConnectionRace._thread_site(site) as database:
                connection_ids["public"] = TestPrivacyRetentionTwoConnectionRace._connection_id(
                    database
                )
                public_file = save_file(
                    f"public-race-{token}.png",
                    content,
                    "Ferum Contractor Worker",
                    worker,
                    is_private=0,
                )
                physical_paths.add(Path(public_file.get_full_path()).resolve())
                database.commit()
                return str(public_file.name)

        def create_credential() -> str:
            if not public_locked.wait(self.WAIT_SECONDS):
                raise AssertionError("Public alias did not acquire the shared File lock")
            with TestPrivacyRetentionTwoConnectionRace._thread_site(site) as database:
                connection_ids["credential"] = TestPrivacyRetentionTwoConnectionRace._connection_id(
                    database
                )
                previous_flag = frappe.flags.get(PRIVACY_WRITE_FLAG)
                try:
                    frappe.flags[PRIVACY_WRITE_FLAG] = True
                    doc = frappe.get_doc(
                        {
                            "doctype": "Ferum Personnel Credential",
                            "holder_type": "Ferum Contractor Worker",
                            "holder": worker,
                            "credential_type": "Electrical Safety",
                            "credential_number": f"RACE-{token}",
                            "document": canonical.name,
                            "malware_status": "Pending",
                            "verification_status": "Draft",
                            "privacy_basis_reference": f"TEST-RACE-{token}",
                            "privacy_policy_reference": POLICY_REFERENCE,
                            "privacy_policy_hash": POLICY_HASH,
                            "no_expiry": 1,
                            "retention_status": "Active",
                        }
                    ).insert(ignore_permissions=True)
                    database.commit()
                    return str(doc.name)
                finally:
                    frappe.flags[PRIVACY_WRITE_FLAG] = previous_flag

        synthetic_settings = frappe._dict(activation_mode="Synthetic Test")
        with (
            patch.object(
                privacy_file_guard,
                "lock_file_content_hash_aliases",
                side_effect=observed_lock,
            ),
            patch.object(
                credential_controller,
                "active_privacy_settings",
                return_value=synthetic_settings,
            ),
            ThreadPoolExecutor(max_workers=2, thread_name_prefix="privacy-file-race") as pool,
        ):
            public_future = pool.submit(create_public_alias)
            credential_future = pool.submit(create_credential)
            public_name = public_future.result(timeout=self.WAIT_SECONDS)
            with self.assertRaises(frappe.PermissionError):
                credential_future.result(timeout=self.WAIT_SECONDS)

        frappe.db.rollback()
        self.assertNotEqual(connection_ids["public"], connection_ids["credential"])
        self.assertTrue(frappe.db.exists("File", public_name))
        self.assertEqual(
            frappe.db.count(
                "Ferum Personnel Credential",
                {"document": canonical.name},
            ),
            0,
        )

    @staticmethod
    def _cleanup_committed_file_race(
        worker: str,
        content_hash: str,
        physical_paths: set[Path],
    ) -> None:
        frappe.db.rollback()
        file_names = frappe.get_all(
            "File",
            filters={"content_hash": content_hash},
            pluck="name",
        )
        credentials = (
            frappe.get_all(
                "Ferum Personnel Credential",
                filters={"document": ["in", file_names]},
                pluck="name",
            )
            if file_names
            else []
        )
        for credential in credentials:
            frappe.db.sql(
                "delete from `__Auth` where doctype = %s and name = %s",
                ("Ferum Personnel Credential", credential),
            )
            frappe.db.sql(
                "delete from `tabFerum Personnel Credential` where name = %s",
                credential,
            )
        for file_name in file_names:
            file_doc = frappe.get_doc("File", file_name)
            physical_paths.add(Path(file_doc.get_full_path()).resolve())
            frappe.db.sql("delete from `tabFile` where name = %s", file_name)
        frappe.db.sql("delete from `tabFerum Contractor Worker` where name = %s", worker)
        frappe.db.commit()
        for path in physical_paths:
            path.unlink(missing_ok=True)
