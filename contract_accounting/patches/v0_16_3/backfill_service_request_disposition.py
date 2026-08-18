"""Backfill honest request text and exact typed provenance where it is provable."""

from __future__ import annotations

import frappe
from frappe import _

SOURCE_DOCTYPE_BY_TYPE = {
	"Finding": "Ferum Finding",
	"Maintenance Visit": "Ferum Maintenance Visit",
}


def execute() -> None:
	if not frappe.db.table_exists("Ferum Service Request"):
		return
	for row in frappe.get_all(
		"Ferum Service Request",
		fields=[
			"name",
			"request_type",
			"subject",
			"description",
			"source_type",
			"source_doctype",
			"source_name",
			"source_reference",
		],
		order_by="creation asc",
	):
		updates = {}
		if not (row.subject or "").strip():
			updates["subject"] = f"[MIGRATION REVIEW REQUIRED] {row.request_type}: {row.name}"
		if not (row.description or "").strip():
			updates["description"] = (
				f"Legacy Service Request {row.name} has no structured description; manual review required."
			)
		expected = SOURCE_DOCTYPE_BY_TYPE.get(row.source_type)
		if expected:
			source_name = row.source_name or row.source_reference
			if not source_name or not frappe.db.exists(expected, source_name):
				frappe.throw(
					_("Service Request {0}: typed source {1}/{2} не доказан.").format(
						row.name, expected, source_name or "<empty>"
					)
				)
			if row.source_doctype and row.source_doctype != expected:
				frappe.throw(
					_("Service Request {0}: source DocType конфликтует с source_type.").format(
						row.name
					)
				)
			updates.update(
				{
					"source_doctype": expected,
					"source_name": source_name,
					"source_reference": source_name,
				}
			)
		if updates:
			frappe.db.set_value(
				"Ferum Service Request",
				row.name,
				updates,
				update_modified=False,
			)
