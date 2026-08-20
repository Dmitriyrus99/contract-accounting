"""Standalone tests for destructive Bench-gate preflight boundaries."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.bench_quality_gate import (
    EXPECTED_APPS,
    NON_PRODUCTION_CONFIRMATION,
    app_names,
    app_versions,
    compatible_node_bin,
    tree_digest,
)


class TestBenchQualityGate(unittest.TestCase):
    def test_node_selection_uses_approved_major_not_highest_installed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            for version in ("v22.20.0", "v22.22.3", "v24.15.0"):
                (home / ".nvm" / "versions" / "node" / version / "bin").mkdir(parents=True)

            selected = compatible_node_bin(home, "22")

            self.assertEqual(selected.parent.name, "v22.22.3")

    def test_tree_digest_binds_paths_and_bytes_but_ignores_runtime_caches(self) -> None:
        with (
            tempfile.TemporaryDirectory() as first_dir,
            tempfile.TemporaryDirectory() as second_dir,
        ):
            first, second = Path(first_dir), Path(second_dir)
            for root in (first, second):
                (root / "contract_accounting").mkdir()
                (root / "contract_accounting" / "__init__.py").write_text(
                    '__version__ = "0.20.0"\n', encoding="utf-8"
                )
                (root / "__pycache__").mkdir()
                (root / "__pycache__" / "ignored.pyc").write_bytes(b"different")
            self.assertEqual(tree_digest(first), tree_digest(second))
            (second / "contract_accounting" / "__init__.py").write_text(
                '__version__ = "0.20.1"\n', encoding="utf-8"
            )
            self.assertNotEqual(tree_digest(first), tree_digest(second))

    def test_app_inventory_parser_requires_the_exact_dedicated_bench(self) -> None:
        transcript = """
frappe              15.118.0 version-15
erpnext             15.119.2 version-15
contract_accounting 0.20.0   HEAD
"""
        self.assertEqual(app_names(transcript), EXPECTED_APPS)
        self.assertEqual(
            app_versions(transcript),
            {
                "frappe": "15.118.0",
                "erpnext": "15.119.2",
                "contract_accounting": "0.20.0",
            },
        )
        self.assertNotEqual(app_names(transcript + "ferum_custom 1.0.0 HEAD\n"), EXPECTED_APPS)

    def test_non_production_confirmation_is_exact_and_not_a_credential(self) -> None:
        self.assertEqual(
            NON_PRODUCTION_CONFIRMATION,
            "I CONFIRM THIS IS A DISPOSABLE NON-PRODUCTION SITE",
        )
        self.assertNotIn("password", NON_PRODUCTION_CONFIRMATION.lower())


if __name__ == "__main__":
    unittest.main()
