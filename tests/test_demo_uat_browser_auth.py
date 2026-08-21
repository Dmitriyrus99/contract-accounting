"""Static contract for synthetic browser-auth helpers."""

from __future__ import annotations

import unittest
from pathlib import Path

from contract_accounting.demo_uat import browser_auth


class DemoUATBrowserAuthContractTest(unittest.TestCase):
    def test_confirmation_tokens_are_exact(self) -> None:
        self.assertEqual(
            browser_auth.PREPARE_BROWSER_CONFIRMATION_TOKEN,
            "PREPARE_CONTRACT_ACCOUNTING_DEMO_BROWSER_UAT_V1",
        )
        self.assertEqual(
            browser_auth.CLEANUP_BROWSER_CONFIRMATION_TOKEN,
            "CLEANUP_CONTRACT_ACCOUNTING_DEMO_BROWSER_UAT_V1",
        )

    def test_temp_password_path_is_exact_tmp_location(self) -> None:
        self.assertEqual(
            browser_auth.TEMP_PASSWORD_PATH, Path("/tmp/ca01_synthetic_browser_password")
        )

    def test_exact_engineer_scope_is_two_manifest_users_only(self) -> None:
        self.assertEqual(
            browser_auth.ENGINEER_USERS,
            (
                "ca-demo-v1-own-engineer@example.invalid",
                "ca-demo-v1-foreign-engineer@example.invalid",
            ),
        )

    def test_browser_prep_normalizes_desk_home_route(self) -> None:
        self.assertEqual(browser_auth.DESK_HOME_PAGE, "workspace")
        self.assertEqual(browser_auth.SETUP_WIZARD_APPS, ("frappe", "erpnext"))
        source = Path(browser_auth.__file__).read_text(encoding="utf-8")
        self.assertIn("update `tabInstalled Application`", source)
        self.assertIn("where app_name in (%s, %s)", source)
        self.assertIn("SETUP_WIZARD_APPS", source)
        self.assertIn('frappe.db.get_single_value("System Settings", "setup_complete")', source)
        self.assertIn('frappe.db.set_single_value("System Settings", "setup_complete", 1)', source)
        self.assertIn('frappe.db.get_default("desktop:home_page") == "setup-wizard"', source)
        self.assertIn('frappe.db.set_default("desktop:home_page", DESK_HOME_PAGE)', source)


if __name__ == "__main__":
    unittest.main()
