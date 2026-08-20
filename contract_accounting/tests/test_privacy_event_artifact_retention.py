"""Runtime boundaries for native Privacy Event reference-store retention."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cint
from frappe.utils.file_manager import save_file

from contract_accounting.api import privacy_event_retention


class TestPrivacyEventNativeArtifactRetention(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.committed_names: dict[str, set[str]] = {}
        self.physical_paths: set[Path] = set()
        self.interrupted_paths: set[Path] = set()
        self.addCleanup(self._cleanup_committed_fixture)
        self._adopt_interrupted_synthetic_fixture()

    def tearDown(self) -> None:
        frappe.set_user(self.previous_user)
        super().tearDown()

    def test_all_native_reference_stores_and_local_bytes_are_purged(self) -> None:
        event = self._insert_event(anonymized=False)
        direct_communication = self._insert_row(
            "Communication",
            reference_doctype=privacy_event_retention.EVENT_DOCTYPE,
            reference_name=event,
            subject="synthetic PII subject",
            content="synthetic PII communication",
        )
        linked_communication = self._insert_row(
            "Communication",
            subject="synthetic linked PII",
            content="synthetic linked communication",
        )
        communication_link = self._insert_row(
            "Communication Link",
            parent=linked_communication,
            parenttype="Communication",
            parentfield="timeline_links",
            link_doctype=privacy_event_retention.EVENT_DOCTYPE,
            link_name=event,
        )
        todo = self._insert_row(
            "ToDo",
            reference_type=privacy_event_retention.EVENT_DOCTYPE,
            reference_name=event,
            description="synthetic PII assignment",
        )
        nested_todo = self._insert_row(
            "ToDo",
            reference_type="Communication",
            reference_name=linked_communication,
            description="synthetic transitive PII assignment",
        )
        version = self._insert_row(
            "Version",
            ref_doctype=privacy_event_retention.EVENT_DOCTYPE,
            docname=event,
            data='{"pii":"synthetic"}',
        )
        comment = self._insert_row(
            "Comment",
            reference_doctype=privacy_event_retention.EVENT_DOCTYPE,
            reference_name=event,
            comment_type="Info",
            content="synthetic PII comment",
        )
        communication_comment = self._insert_row(
            "Comment",
            reference_doctype="Communication",
            reference_name=linked_communication,
            comment_type="Info",
            content="synthetic transitive PII comment",
        )
        activity = self._insert_row(
            "Activity Log",
            reference_doctype=privacy_event_retention.EVENT_DOCTYPE,
            reference_name=event,
            subject="synthetic PII activity",
        )
        share = self._insert_row(
            "DocShare",
            share_doctype=privacy_event_retention.EVENT_DOCTYPE,
            share_name=event,
            user="Administrator",
            read=1,
        )
        direct_file = self._save_file(event, privacy_event_retention.EVENT_DOCTYPE, "direct")
        communication_file = self._save_file(linked_communication, "Communication", "linked")
        todo_file = self._save_file(todo, "ToDo", "todo")
        nested_todo_file = self._save_file(nested_todo, "ToDo", "nested-todo")
        self.assertEqual(len(self.physical_paths), 4, "save_file оставил source-path orphan")
        file_share = self._insert_row(
            "DocShare",
            share_doctype="File",
            share_name=nested_todo_file,
            user="Administrator",
            read=1,
        )
        generated_comments = tuple(
            frappe.db.get_all(
                "Comment",
                filters={
                    "reference_doctype": ["in", ["Communication", "ToDo"]],
                    "reference_name": ["in", [linked_communication, todo, nested_todo]],
                },
                pluck="name",
            )
        )
        self.committed_names.setdefault("Comment", set()).update(generated_comments)
        frappe.db.commit()

        with patch.object(privacy_event_retention.frappe, "get_all", return_value=[event]):
            self.assertEqual(privacy_event_retention.anonymize_expired_privacy_events(), 1)
        frappe.db.commit()

        minimized = frappe.db.get_value(
            privacy_event_retention.EVENT_DOCTYPE,
            event,
            ("target_name", "actor", "reason", "payload_json", "anonymized_at"),
            as_dict=True,
        )
        self.assertFalse(minimized.target_name)
        self.assertFalse(minimized.actor)
        self.assertFalse(minimized.reason)
        self.assertFalse(minimized.payload_json)
        self.assertTrue(minimized.anonymized_at)
        for doctype, names in {
            "Communication": (direct_communication, linked_communication),
            "Communication Link": (communication_link,),
            "ToDo": (todo, nested_todo),
            "Version": (version,),
            "Comment": (comment, communication_comment, *generated_comments),
            "Activity Log": (activity,),
            "DocShare": (share, file_share),
            "File": (direct_file, communication_file, todo_file, nested_todo_file),
        }.items():
            for name in names:
                self.assertFalse(frappe.db.exists(doctype, name), (doctype, name))
        self.assertTrue(all(not path.exists() for path in self.physical_paths))
        self.assertFalse(list(privacy_event_retention._quarantine_root().glob("*.pending")))
        self.assertFalse(list(privacy_event_retention._quarantine_root().glob("*.committed")))

    def test_anonymized_or_missing_event_rejects_every_native_reference_shape(self) -> None:
        event = self._insert_event(anonymized=True)
        communication = self._insert_row("Communication", subject="parent", content="parent")
        todo = self._insert_row("ToDo", description="parent")
        docs = [
            frappe._dict(
                doctype=doctype,
                **{doctype_field: privacy_event_retention.EVENT_DOCTYPE, name_field: event},
            )
            for doctype, doctype_field, name_field in privacy_event_retention.NATIVE_REFERENCE_STORES
        ]
        docs.extend(
            (
                frappe._dict(
                    doctype="Communication",
                    reference_doctype=None,
                    reference_name=None,
                    timeline_links=[
                        frappe._dict(
                            link_doctype=privacy_event_retention.EVENT_DOCTYPE,
                            link_name=event,
                        )
                    ],
                ),
                frappe._dict(
                    doctype="File",
                    attached_to_doctype="Communication",
                    attached_to_name=communication,
                ),
                frappe._dict(
                    doctype="File",
                    attached_to_doctype="ToDo",
                    attached_to_name=todo,
                ),
            )
        )
        frappe.db.set_value(
            "Communication",
            communication,
            {"reference_doctype": privacy_event_retention.EVENT_DOCTYPE, "reference_name": event},
            update_modified=False,
        )
        frappe.db.set_value(
            "ToDo",
            todo,
            {"reference_type": privacy_event_retention.EVENT_DOCTYPE, "reference_name": event},
            update_modified=False,
        )
        for doc in docs:
            with self.assertRaises(frappe.PermissionError):
                privacy_event_retention.lock_privacy_event_artifact(doc)
        missing = frappe._dict(
            doctype="DocShare",
            share_doctype=privacy_event_retention.EVENT_DOCTYPE,
            share_name=f"MISSING-{uuid4().hex}",
        )
        with self.assertRaises(frappe.PermissionError):
            privacy_event_retention.lock_privacy_event_artifact(missing)

        transitive = frappe._dict(
            doctype="Comment",
            reference_doctype="Communication",
            reference_name=communication,
        )
        with self.assertRaises(frappe.PermissionError):
            privacy_event_retention.lock_privacy_event_artifact(transitive)

    def test_exact_shared_local_url_preserves_surviving_row_and_bytes(self) -> None:
        event = self._insert_event(anonymized=False)
        artifact = self._save_file(event, privacy_event_retention.EVENT_DOCTYPE, "shared-url")
        self.assertEqual(len(self.physical_paths), 1, "save_file оставил source-path orphan")
        identity = frappe.db.get_value(
            "File",
            artifact,
            ("file_name", "file_url", "content_hash", "is_private"),
            as_dict=True,
        )
        alias = self._insert_row(
            "File",
            file_name=f"survivor-{uuid4().hex}.txt",
            file_url=identity.file_url,
            content_hash=identity.content_hash,
            is_private=identity.is_private,
            attached_to_doctype=None,
            attached_to_name=None,
        )
        path = next(
            path for path in self.physical_paths if path.name == Path(identity.file_url).name
        )
        self.physical_paths.remove(path)
        frappe.db.commit()

        with patch.object(privacy_event_retention.frappe, "get_all", return_value=[event]):
            self.assertEqual(privacy_event_retention.anonymize_expired_privacy_events(), 1)
        frappe.db.commit()

        self.assertFalse(frappe.db.exists("File", artifact))
        self.assertTrue(frappe.db.exists("File", alias))
        self.assertTrue(path.is_file())
        self.physical_paths.add(path)

    def test_pending_file_hold_blocks_event_and_every_artifact_purge(self) -> None:
        event = self._insert_event(anonymized=False)
        file_name = self._save_file(event, privacy_event_retention.EVENT_DOCTYPE, "held")
        hold = self._insert_row(
            "Ferum Privacy Legal Hold",
            target_doctype="File",
            target_name=file_name,
            reason="Synthetic File hold blocks native artifact purge",
            review_on=frappe.utils.add_days(frappe.utils.nowdate(), 30),
            status="Pending",
            requested_by="Administrator",
            requested_at=frappe.utils.now_datetime(),
            policy_reference="FR-05",
            policy_hash="synthetic",
        )
        frappe.db.commit()
        with patch.object(privacy_event_retention.frappe, "get_all", return_value=[event]):
            self.assertEqual(privacy_event_retention.anonymize_expired_privacy_events(), 0)
        self.assertFalse(
            frappe.db.get_value(privacy_event_retention.EVENT_DOCTYPE, event, "anonymized_at")
        )
        self.assertTrue(frappe.db.exists("File", file_name))
        self.assertTrue(frappe.db.exists("Ferum Privacy Legal Hold", hold))

    def _insert_event(self, *, anonymized: bool) -> str:
        name = f"FPRVE-TEST-{uuid4().hex[:12]}"
        old = frappe.utils.now_datetime() - timedelta(days=365 * 4)
        self._insert_row(
            privacy_event_retention.EVENT_DOCTYPE,
            name=name,
            event_type="Synthetic Native Store Retention",
            target_doctype="Ferum Privacy Settings",
            target_name=None if anonymized else "Ferum Privacy Settings",
            actor=None if anonymized else "Administrator",
            reason=None if anonymized else "Synthetic event contains removable PII",
            occurred_at=old,
            policy_reference="FR-05",
            policy_hash="synthetic",
            payload_json=None if anonymized else '{"pii":"synthetic"}',
            correlation_key=uuid4().hex,
            anonymized_at=frappe.utils.now_datetime() if anonymized else None,
            anonymization_hash="a" * 64 if anonymized else None,
        )
        return name

    def _save_file(self, attached_to_name: str, attached_to_doctype: str, label: str) -> str:
        filename = f"privacy-event-{label}-{uuid4().hex}.txt"
        comments_before = set(
            frappe.db.get_all(
                "Comment",
                filters={
                    "reference_doctype": attached_to_doctype,
                    "reference_name": attached_to_name,
                },
                pluck="name",
            )
        )
        file_doc = save_file(
            filename,
            f"synthetic PII bytes {label}".encode(),
            attached_to_doctype,
            attached_to_name,
            is_private=1,
        )
        source_path = (
            Path(
                frappe.get_site_path("private" if cint(file_doc.is_private) else "public", "files")
            )
            / filename
        )
        canonical_path = Path(file_doc.get_full_path()).resolve()
        self.assertNotEqual(
            canonical_path.name,
            filename,
            "regression fixture не создал source-path collision",
        )
        self.assertFalse(source_path.exists(), "занятый manager source path остался orphan")
        self.assertTrue(canonical_path.is_file())
        self.committed_names.setdefault("File", set()).add(str(file_doc.name))
        comments_after = set(
            frappe.db.get_all(
                "Comment",
                filters={
                    "reference_doctype": attached_to_doctype,
                    "reference_name": attached_to_name,
                },
                pluck="name",
            )
        )
        self.committed_names.setdefault("Comment", set()).update(comments_after - comments_before)
        stem = Path(filename).stem
        for root in (
            Path(frappe.get_site_path("public", "files")),
            Path(frappe.get_site_path("private", "files")),
        ):
            self.physical_paths.update(path.resolve() for path in root.glob(f"{stem}*.txt"))
        return str(file_doc.name)

    def _insert_row(self, doctype: str, name: str | None = None, **values):
        name = name or f"TEST-{doctype.replace(' ', '-').upper()}-{uuid4().hex[:12]}"
        now = frappe.utils.now_datetime()
        columns = {
            "name": name,
            "creation": now,
            "modified": now,
            "modified_by": "Administrator",
            "owner": "Administrator",
            "docstatus": 0,
            "idx": 0,
            **values,
        }
        fieldnames = tuple(columns)
        placeholders = ", ".join(["%s"] * len(fieldnames))
        quoted = ", ".join(f"`{fieldname}`" for fieldname in fieldnames)
        frappe.db.sql(
            f"insert into `tab{doctype}` ({quoted}) values ({placeholders})",  # nosec B608
            tuple(columns[fieldname] for fieldname in fieldnames),
        )
        self.committed_names.setdefault(doctype, set()).add(str(name))
        return str(name)

    def _cleanup_committed_fixture(self) -> None:
        frappe.db.rollback()
        for doctype in (
            "Communication Link",
            "Version",
            "Comment",
            "Activity Log",
            "DocShare",
            "ToDo",
            "Communication",
            "File",
            "Ferum Privacy Legal Hold",
            privacy_event_retention.EVENT_DOCTYPE,
        ):
            names = tuple(self.committed_names.get(doctype, ()))
            if names:
                frappe.db.delete(doctype, {"name": ["in", names]})
        frappe.db.commit()
        for path in self.physical_paths | self.interrupted_paths:
            path.unlink(missing_ok=True)

    def _adopt_interrupted_synthetic_fixture(self) -> None:
        """Recover only proven orphan rows/bytes from an interrupted test run."""

        rows = frappe.db.sql(
            """
            select name, reference_name, content from `tabComment`
             where reference_doctype = %s and reference_name like 'FPRVE-TEST-%%'
            """,
            privacy_event_retention.EVENT_DOCTYPE,
        )
        for name, event_name, content in rows:
            if not frappe.db.exists(privacy_event_retention.EVENT_DOCTYPE, event_name) and (
                "privacy-event-" in str(content or "")
            ):
                self.committed_names.setdefault("Comment", set()).add(str(name))

        for root, prefix in (
            (Path(frappe.get_site_path("public", "files")), "/files/"),
            (Path(frappe.get_site_path("private", "files")), "/private/files/"),
        ):
            for path in root.glob("privacy-event-*"):
                file_url = f"{prefix}{path.name}"
                if not frappe.db.exists("File", {"file_url": file_url}) and path.is_file():
                    if path.read_bytes().startswith(b"synthetic PII bytes "):
                        self.interrupted_paths.add(path.resolve())
