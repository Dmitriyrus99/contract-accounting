"""After-commit rebuild scheduling for standard ERPNext accounting events."""

from __future__ import annotations

from typing import Any

import frappe


def enqueue_accounting_rebuild(doc: Any, method: str | None = None) -> None:
	for service_project in sorted(_affected_projects(doc)):
		frappe.enqueue(
			"contract_accounting.api.finance.recalculate_project",
			queue="short",
			enqueue_after_commit=True,
			job_id=f"ca-finance-{frappe.scrub(service_project)}",
			service_project=service_project,
		)


def _affected_projects(doc: Any) -> set[str]:
	projects: set[str] = set()
	direct = doc.get("ferum_service_project")
	if direct:
		projects.add(str(direct))
	if doc.doctype != "Payment Entry":
		return projects
	for row in doc.get("references") or []:
		if row.reference_doctype not in {"Sales Invoice", "Purchase Invoice"}:
			continue
		project = frappe.db.get_value(
			row.reference_doctype,
			row.reference_name,
			"ferum_service_project",
		)
		if project:
			projects.add(str(project))
	return projects
