from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DemoUATBrowserRuntimeContractTest(unittest.TestCase):
    def test_playwright_core_is_pinned_exactly_in_repo(self) -> None:
        package_json = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        package_lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))

        self.assertEqual(
            package_json["devDependencies"]["playwright-core"],
            "1.62.1",
        )
        self.assertEqual(
            package_lock["packages"][""]["devDependencies"]["playwright-core"],
            "1.62.1",
        )
        self.assertEqual(
            package_lock["packages"]["node_modules/playwright-core"]["version"],
            "1.62.1",
        )

    def test_browser_harness_uses_repo_dependency_not_output_node_modules(self) -> None:
        for filename in (
            "scripts/demo_uat_browser_fullstack_acl.js",
            "scripts/demo_uat_browser_diagnostic_list.js",
        ):
            source = (ROOT / filename).read_text(encoding="utf-8")
            self.assertIn('require("playwright-core")', source)
            self.assertNotIn("output/playwright/fullstack_runtime/node_modules", source)
            self.assertNotIn("createRequire(", source)


if __name__ == "__main__":
    unittest.main()
