"""Standalone structural contract for native Privacy Event reference stores."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "contract_accounting" / "api" / "privacy_event_retention.py"
HOOKS = ROOT / "contract_accounting" / "hooks.py"
GUARDED_FILE = ROOT / "contract_accounting" / "infrastructure" / "guarded_file.py"

EXPECTED_STORES = {
    ("Version", "ref_doctype", "docname"),
    ("Comment", "reference_doctype", "reference_name"),
    ("Activity Log", "reference_doctype", "reference_name"),
    ("Communication", "reference_doctype", "reference_name"),
    ("Communication Link", "link_doctype", "link_name"),
    ("ToDo", "reference_type", "reference_name"),
    ("File", "attached_to_doctype", "attached_to_name"),
    ("DocShare", "share_doctype", "share_name"),
}


class PrivacyEventArtifactSchemaTest(unittest.TestCase):
    def test_inventory_is_exact_and_every_store_has_write_guards(self) -> None:
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        inventory = None
        for node in tree.body:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id == "NATIVE_REFERENCE_STORES":
                    inventory = set(ast.literal_eval(node.value))
                    break
        self.assertEqual(inventory, EXPECTED_STORES)

        hooks = HOOKS.read_text(encoding="utf-8")
        guard = "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact"
        for doctype, _doctype_field, _name_field in EXPECTED_STORES:
            self.assertIn(f'"{doctype}": {{', hooks)
        self.assertGreaterEqual(hooks.count(guard), len(EXPECTED_STORES) * 2)

    def test_purge_contract_has_graph_holds_exact_paths_and_durable_recovery(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        for required in (
            "_locked_native_artifact_inventory",
            "_native_artifact_inventory",
            "_lock_file_artifact_identities",
            "pending.add((doctype, artifact_name))",
            "_has_blocking_hold(hold_targets)",
            "where file_url in",
            "or thumbnail_url in",
            "_publish_pending_physical_deletion",
            "frappe.db.before_commit.add",
            "frappe.db.after_commit.add",
            "frappe.db.after_rollback.add",
            "recover_privacy_event_artifact_deletions",
            "Remote Privacy Event File",
        ):
            self.assertIn(required, source)

        guarded_file = GUARDED_FILE.read_text(encoding="utf-8")
        event_lock = "lock_privacy_event_artifact(self)"
        alias_lock = "preflight_new_file_alias(self)"
        self.assertLess(guarded_file.index(event_lock), guarded_file.index(alias_lock))


if __name__ == "__main__":
    unittest.main()
