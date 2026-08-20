"""One fail-closed authorization boundary for user-supplied File references."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _


def get_authorized_file(name: str, *, require_content_hash: bool = True) -> Any:
    if not name or not frappe.db.exists("File", name):
        frappe.throw(_("File не найден."), frappe.DoesNotExistError)
    file_doc = frappe.get_doc("File", name)
    file_doc.check_permission("read")
    if require_content_hash and not file_doc.content_hash:
        frappe.throw(_("File требует content_hash."))
    return file_doc
