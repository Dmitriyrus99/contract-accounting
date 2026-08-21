"""Idempotently install the narrow Sales Invoice project adapter."""

from __future__ import annotations

from typing import Final

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS: Final[dict[str, list[dict[str, object]]]] = {
	"Sales Invoice": [
		{
			"fieldname": "ferum_service_project",
			"label": "Ferum Service Project",
			"fieldtype": "Link",
			"options": "Ferum Service Project",
			"insert_after": "project",
			"in_standard_filter": 1,
		},
	],
	"Purchase Invoice": [
		{
			"fieldname": "ferum_service_project",
			"label": "Ferum Service Project",
			"fieldtype": "Link",
			"options": "Ferum Service Project",
			"insert_after": "project",
			"in_standard_filter": 1,
		},
	],
}


def setup_custom_fields() -> None:
	create_custom_fields(CUSTOM_FIELDS, update=True)
