"""Runtime regressions for local-path aliases and File/retention serialization."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from threading import Event
from typing import Any, Iterator
from unittest.mock import patch
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file
from frappe.utils.password import set_encrypted_password

from contract_accounting.api import privacy_retention
from contract_accounting.contract_accounting.doctype.ferum_personnel_credential import (
    ferum_personnel_credential as credential_controller,
)
from contract_accounting.domain.privacy import (
    POLICY_HASH,
    POLICY_REFERENCE,
    SYNTHETIC_RETENTION_CONFIRMATION,
)
from contract_accounting.infrastructure import privacy_file_guard
from contract_accounting.infrastructure.privacy_file_guard import (
    credential_file_aliases,
    is_credential_file_alias,
    validate_credential_alias_set,
    validate_credential_file_alias,
)


class TestPrivacyLocalFileUrlIdentity(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")

    def tearDown(self) -> None:
        frappe.set_user(self.previous_user)
        super().tearDown()

    def test_identical_local_file_url_remains_protected_after_hash_drift(self) -> None:
        canonical, alias = self._private_copy_pair()
        credential = self._insert_raw_credential(canonical.name)
        drift_hash = uuid4().hex * 2
        frappe.db.set_value(
            "File",
            alias.name,
            "content_hash",
            drift_hash,
            update_modified=False,
        )

        aliases = credential_file_aliases(canonical.name)
        self.assertEqual({row.name for row in aliases}, {canonical.name, alias.name})
        self.assertTrue(is_credential_file_alias(alias.name))
        self.assertFalse(frappe.get_doc("File", alias.name).is_downloadable())
        self.assertEqual(
            frappe.db.get_value("Ferum Personnel Credential", credential, "document"),
            canonical.name,
        )

        attempted = frappe.get_doc("File", alias.name)
        attempted.file_url = f"/private/files/drift-{uuid4().hex}.png"
        with self.assertRaisesRegex(frappe.PermissionError, "immutable"):
            validate_credential_file_alias(attempted)

    def test_public_or_public_marked_same_local_path_is_rejected_despite_hash_drift(
        self,
    ) -> None:
        canonical, alias = self._private_copy_pair()
        drift_hash = uuid4().hex * 2
        frappe.db.set_value(
            "File",
            alias.name,
            {"content_hash": drift_hash, "is_private": 0},
            update_modified=False,
        )
        proposed = frappe._dict(document=canonical.name)
        with self.assertRaises(frappe.PermissionError):
            validate_credential_alias_set(proposed)

        frappe.db.set_value(
            "File",
            alias.name,
            "is_private",
            1,
            update_modified=False,
        )
        self._insert_raw_credential(canonical.name)
        public_candidate = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": f"public-drift-{uuid4().hex}.png",
                "file_url": canonical.file_url,
                "content_hash": drift_hash,
                "is_private": 0,
                "attached_to_doctype": "User",
                "attached_to_name": "Administrator",
            }
        )
        public_candidate.flags.copy_from_existing_file = True
        with self.assertRaises(frappe.PermissionError):
            public_candidate.insert(ignore_permissions=True)

    def _private_copy_pair(self):
        content = f"synthetic-local-url-{uuid4().hex}".encode()
        canonical = save_file(
            f"credential-local-url-{uuid4().hex}.png",
            content,
            "User",
            "Administrator",
            is_private=1,
        )
        alias = canonical.create_attachment_copy(
            "User",
            "Administrator",
            attached_to_field="user_image",
            ignore_permissions=True,
        )
        self.addCleanup(Path(canonical.get_full_path()).resolve().unlink, missing_ok=True)
        self.assertNotEqual(canonical.name, alias.name)
        self.assertEqual(canonical.file_url, alias.file_url)
        return canonical, alias

    @staticmethod
    def _insert_raw_credential(document: str) -> str:
        name = f"FPCR-DRIFT-{uuid4().hex[:12]}"
        now = frappe.utils.now_datetime()
        frappe.db.sql(
            """
            insert into `tabFerum Personnel Credential`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 holder_type, holder, credential_type, document, malware_status,
                 verification_status, no_expiry, privacy_basis_reference,
                 privacy_policy_reference, privacy_policy_hash, retention_status)
            values
                (%s, %s, %s, 'Administrator', 'Administrator', 0, 0,
                 'Employee', 'SYNTHETIC-DRIFT', 'Electrical Safety', %s, 'Pending',
                 'Draft', 1, 'TEST-DRIFT', %s, %s, 'Active')
            """,
            (name, now, now, document, POLICY_REFERENCE, POLICY_HASH),
        )
        return name


class TestPrivateAliasRetentionTwoConnectionRace(FrappeTestCase):
    """A deduplicated private alias must not survive destructive retention."""

    WAIT_SECONDS = 20

    def setUp(self) -> None:
        # Register this before FrappeTestCase so its transaction cleanup runs
        # first; any framework rollback restoration is then removed last.
        self.final_physical_cleanup: set[Path] = set()
        self.addCleanup(self._remove_final_physical_residue)
        super().setUp()

    def test_private_dedupe_waiting_on_retention_leaves_no_broken_row_or_path(self) -> None:
        site = str(frappe.local.site)
        token = uuid4().hex[:12]
        worker = f"CW-PRIVATE-RACE-{token}"
        credential = f"FPCR-PRIVATE-RACE-{token}"
        content = f"synthetic-private-retention-race-{token}".encode()
        old_date = date.today() - timedelta(days=365 * 4)
        self._insert_committed_worker(worker, token, old_date)
        canonical_name, content_hash, file_url, original_path = self._create_committed_file(
            site,
            token,
            worker,
            content,
        )
        self.final_physical_cleanup.add(original_path)
        self._insert_committed_credential(
            credential,
            worker,
            canonical_name,
            old_date,
        )
        self.addCleanup(
            self._cleanup_committed_race,
            worker,
            credential,
            content_hash,
            file_url,
            original_path,
        )

        action = {
            "action": "Delete Credential File",
            "target_doctype": "Ferum Personnel Credential",
            "target_name": credential,
            "file": canonical_name,
            "file_aliases": [canonical_name],
            "base_date": str(old_date),
            "blocked_by_legal_hold": False,
        }
        retention_locked = Event()
        alias_lock_entered = Event()
        alias_lock_returned = Event()
        connection_ids: dict[str, int] = {}
        real_revalidate = privacy_retention._lock_and_revalidate_action
        real_alias_target_lock = privacy_file_guard.lock_privacy_target
        quarantine_dir = original_path.parent / ".privacy-retention-quarantine"
        residue_before = self._retention_residue(quarantine_dir)

        def observed_revalidation(action_to_check: dict[str, Any], as_of: date):
            current = real_revalidate(action_to_check, as_of)
            if current and current["target_name"] == credential:
                retention_locked.set()
                if not alias_lock_entered.wait(self.WAIT_SECONDS):
                    raise AssertionError("Private alias did not enter the Credential lock")
                if alias_lock_returned.is_set():
                    raise AssertionError("Private alias bypassed the retained Credential lock")
            return current

        def observed_alias_target_lock(target_doctype: str, target_name: str) -> bool:
            is_race_credential = (
                target_doctype == "Ferum Personnel Credential" and target_name == credential
            )
            if is_race_credential:
                alias_lock_entered.set()
            locked = real_alias_target_lock(target_doctype, target_name)
            if is_race_credential:
                alias_lock_returned.set()
            return locked

        def execute_retention() -> dict[str, Any]:
            with self._thread_site(site) as database:
                connection_ids["retention"] = self._connection_id(database)
                result = privacy_retention.execute_privacy_retention(
                    str(date.today()),
                    SYNTHETIC_RETENTION_CONFIRMATION,
                    "Two-connection private alias retention regression",
                )
                database.commit()
                return result

        def create_private_alias() -> tuple[str, str | None]:
            if not retention_locked.wait(self.WAIT_SECONDS):
                raise AssertionError("Retention did not acquire the Credential lock")
            with self._thread_site(site) as database:
                connection_ids["alias"] = self._connection_id(database)
                try:
                    alias = save_file(
                        f"credential-private-alias-{token}.png",
                        content,
                        "Ferum Contractor Worker",
                        worker,
                        is_private=1,
                    )
                except frappe.PermissionError:
                    database.rollback()
                    return ("denied", None)
                database.commit()
                return ("committed", str(alias.name))

        synthetic_settings = frappe._dict(activation_mode="Synthetic Test")
        with (
            patch.object(privacy_retention, "_build_plan", return_value=[action]),
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
                "_lock_and_revalidate_action",
                side_effect=observed_revalidation,
            ),
            patch.object(
                privacy_file_guard,
                "lock_privacy_target",
                side_effect=observed_alias_target_lock,
            ),
            ThreadPoolExecutor(max_workers=2, thread_name_prefix="private-alias-race") as pool,
        ):
            retention_future = pool.submit(execute_retention)
            alias_future = pool.submit(create_private_alias)
            result = retention_future.result(timeout=self.WAIT_SECONDS)
            alias_outcome, alias_name = alias_future.result(timeout=self.WAIT_SECONDS)

        frappe.db.rollback()
        self.assertNotEqual(connection_ids["retention"], connection_ids["alias"])
        self.assertTrue(alias_lock_entered.is_set())
        self.assertTrue(alias_lock_returned.is_set())
        self.assertEqual(result["executed"], 1)
        retained = frappe.get_doc("Ferum Personnel Credential", credential)
        self.assertFalse(retained.document)
        self.assertEqual(retained.retention_status, "File Removed")
        identity_rows = frappe.get_all(
            "File",
            or_filters={"content_hash": content_hash, "file_url": file_url},
            fields=["name", "content_hash", "file_url", "is_private"],
        )
        self.assertEqual((alias_outcome, alias_name), ("denied", None))
        self.assertFalse(identity_rows)
        surviving_paths: set[Path] = set()
        for row in identity_rows:
            file_doc = frappe.get_doc("File", row.name)
            path = Path(file_doc.get_full_path()).resolve()
            surviving_paths.add(path)
            self.final_physical_cleanup.add(path)
            self.assertTrue(file_doc.exists_on_disk())
            self.assertEqual(path.read_bytes(), content)
            self.assertTrue(row.is_private)
        self.assertFalse(original_path.exists() and original_path not in surviving_paths)
        self.assertEqual(self._retention_residue(quarantine_dir), residue_before)

    @staticmethod
    def _retention_residue(directory: Path) -> frozenset[Path]:
        if not directory.exists():
            return frozenset()
        return frozenset(
            path.resolve()
            for pattern in ("*.pending", "*.committed")
            for path in directory.glob(pattern)
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

    @classmethod
    def _create_committed_file(
        cls,
        site: str,
        token: str,
        worker: str,
        content: bytes,
    ) -> tuple[str, str, str, Path]:
        def create() -> tuple[str, str, str, Path]:
            with cls._thread_site(site) as database:
                file_doc = save_file(
                    f"credential-private-race-{token}.png",
                    content,
                    "Ferum Contractor Worker",
                    worker,
                    is_private=1,
                )
                result = (
                    str(file_doc.name),
                    str(file_doc.content_hash),
                    str(file_doc.file_url),
                    Path(file_doc.get_full_path()).resolve(),
                )
                database.commit()
                return result

        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="canonical-file") as pool:
            return pool.submit(create).result(timeout=cls.WAIT_SECONDS)

    @staticmethod
    def _insert_committed_worker(worker: str, token: str, created: date) -> None:
        timestamp = datetime.combine(created, datetime.min.time())
        frappe.db.sql(
            """
            insert into `tabFerum Contractor Worker`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 supplier, worker_external_id, display_name, status,
                 privacy_basis_reference, privacy_policy_reference,
                 privacy_policy_hash, retention_status)
            values
                (%s, %s, %s, 'Administrator', 'Administrator', 0, 0,
                 %s, %s, %s, 'Archived', %s, %s, %s, 'Active')
            """,
            (
                worker,
                timestamp,
                timestamp,
                f"RACE-SUPPLIER-{token}",
                f"RACE-EXT-{token}",
                f"Private Race Worker {token}",
                f"TEST-RACE-{token}",
                POLICY_REFERENCE,
                POLICY_HASH,
            ),
        )
        frappe.db.commit()

    @staticmethod
    def _insert_committed_credential(
        credential: str,
        worker: str,
        document: str,
        created: date,
    ) -> None:
        timestamp = datetime.combine(created, datetime.min.time())
        frappe.db.sql(
            """
            insert into `tabFerum Personnel Credential`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 holder_type, holder, credential_type, document, malware_status,
                 verification_status, no_expiry, privacy_basis_reference,
                 privacy_policy_reference, privacy_policy_hash, retention_status)
            values
                (%s, %s, %s, 'Administrator', 'Administrator', 0, 0,
                 'Ferum Contractor Worker', %s, 'Electrical Safety', %s, 'Pending',
                 'Draft', 1, 'TEST-PRIVATE-RACE', %s, %s, 'Active')
            """,
            (
                credential,
                timestamp,
                timestamp,
                worker,
                document,
                POLICY_REFERENCE,
                POLICY_HASH,
            ),
        )
        set_encrypted_password(
            "Ferum Personnel Credential",
            credential,
            f"SYNTHETIC-{credential}",
            fieldname="credential_number",
        )
        frappe.db.commit()

    @staticmethod
    def _cleanup_committed_race(
        worker: str,
        credential: str,
        content_hash: str,
        file_url: str,
        original_path: Path,
    ) -> None:
        frappe.db.rollback()
        frappe.db.sql(
            "delete from `tabFerum Privacy Event` where target_doctype = %s and target_name = %s",
            ("Ferum Personnel Credential", credential),
        )
        frappe.db.sql(
            "delete from `__Auth` where doctype = %s and name = %s",
            ("Ferum Personnel Credential", credential),
        )
        frappe.db.sql(
            "delete from `tabFerum Personnel Credential` where name = %s",
            credential,
        )
        for file_name in frappe.get_all(
            "File",
            or_filters={"content_hash": content_hash, "file_url": file_url},
            pluck="name",
        ):
            frappe.db.sql("delete from `tabFile` where name = %s", file_name)
        frappe.db.sql("delete from `tabFerum Contractor Worker` where name = %s", worker)
        frappe.db.commit()
        original_path.unlink(missing_ok=True)

    def _remove_final_physical_residue(self) -> None:
        for path in self.final_physical_cleanup:
            path.unlink(missing_ok=True)
