"""Temporary synthetic-only browser credentials for demo/UAT reruns.

These helpers are intentionally narrow:
- only the two manifest-bound Engineer users are touched;
- only on active ``*.localhost`` sites;
- only with exact confirmation tokens;
- password material is written to a temporary WSL-local file, never to source.
"""

from __future__ import annotations

from pathlib import Path
from secrets import token_urlsafe
from typing import Any, Final

from contract_accounting.demo_uat.runtime import (
    DemoUATRuntimeError,
    get_frappe,
    require_administrator,
    require_exact_token,
    require_local_site,
)

PREPARE_BROWSER_CONFIRMATION_TOKEN: Final[str] = "PREPARE_CONTRACT_ACCOUNTING_DEMO_BROWSER_UAT_V1"
CLEANUP_BROWSER_CONFIRMATION_TOKEN: Final[str] = "CLEANUP_CONTRACT_ACCOUNTING_DEMO_BROWSER_UAT_V1"
TEMP_PASSWORD_PATH: Final[Path] = Path("/tmp/ca01_synthetic_browser_password")
ENGINEER_USERS: Final[tuple[str, str]] = (
    "ca-demo-v1-own-engineer@example.invalid",
    "ca-demo-v1-foreign-engineer@example.invalid",
)
DESK_HOME_PAGE: Final[str] = "workspace"
SETUP_WIZARD_APPS: Final[tuple[str, str]] = ("frappe", "erpnext")


def prepare_browser_users(
    confirmation_token: str | None = None,
    *,
    password: str | None = None,
) -> dict[str, Any]:
    require_exact_token(
        confirmation_token,
        PREPARE_BROWSER_CONFIRMATION_TOKEN,
        "prepare_browser_users",
    )
    frappe = get_frappe()
    site = require_local_site(frappe)
    require_administrator(frappe)
    temp_password = password or f"Tmp-{token_urlsafe(18)}"
    try:
        from frappe.utils.password import update_password

        frappe.db.sql(
            """
            update `tabInstalled Application`
            set is_setup_complete = 1
            where app_name in (%s, %s)
            """,
            SETUP_WIZARD_APPS,
        )
        if not frappe.db.get_single_value("System Settings", "setup_complete"):
            frappe.db.set_single_value("System Settings", "setup_complete", 1)
        if frappe.db.get_default("desktop:home_page") == "setup-wizard":
            frappe.db.set_default("desktop:home_page", DESK_HOME_PAGE)
        for user in ENGINEER_USERS:
            if not frappe.db.exists("User", user):
                raise DemoUATRuntimeError(f"browser user is missing: {user}")
            frappe.db.set_value("User", user, "enabled", 1, update_modified=False)
            update_password(user=user, pwd=temp_password)
        TEMP_PASSWORD_PATH.write_text(temp_password, encoding="utf-8")
        TEMP_PASSWORD_PATH.chmod(0o600)
        frappe.db.commit()
        return {
            "status": "BROWSER_USERS_PREPARED",
            "site": site,
            "users": list(ENGINEER_USERS),
            "password_path": str(TEMP_PASSWORD_PATH),
            "setup_complete": int(frappe.db.get_single_value("System Settings", "setup_complete")),
            "desktop_home_page": frappe.db.get_default("desktop:home_page"),
            "setup_wizard_apps": list(SETUP_WIZARD_APPS),
        }
    except Exception:
        frappe.db.rollback()
        raise


def cleanup_browser_users(confirmation_token: str | None = None) -> dict[str, Any]:
    require_exact_token(
        confirmation_token,
        CLEANUP_BROWSER_CONFIRMATION_TOKEN,
        "cleanup_browser_users",
    )
    frappe = get_frappe()
    site = require_local_site(frappe)
    require_administrator(frappe)
    try:
        for user in ENGINEER_USERS:
            if frappe.db.exists("User", user):
                frappe.db.set_value("User", user, "enabled", 0, update_modified=False)
        if TEMP_PASSWORD_PATH.exists():
            TEMP_PASSWORD_PATH.unlink()
        frappe.db.commit()
        return {
            "status": "BROWSER_USERS_CLEANED",
            "site": site,
            "users": list(ENGINEER_USERS),
            "password_path_removed": not TEMP_PASSWORD_PATH.exists(),
        }
    except Exception:
        frappe.db.rollback()
        raise
