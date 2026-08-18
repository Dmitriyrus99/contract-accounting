"""Physical uniqueness for Finding execution provenance."""

from __future__ import annotations

import frappe


DOCTYPE = "Ferum Finding Execution Link"


def on_doctype_update() -> None:
	frappe.db.add_unique(
		DOCTYPE,
		["parent", "source_event_key"],
		"ca_finding_exec_event_uniq",
	)
	frappe.db.add_unique(
		DOCTYPE,
		["parent", "target_doctype", "target_name"],
		"ca_finding_exec_target_uniq",
	)
