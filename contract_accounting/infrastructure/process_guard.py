"""Shared typed-writer and immutable-template guards for CA-11."""

from __future__ import annotations

import json
from typing import Any, Final

import frappe
from frappe import _

from contract_accounting.domain.json_logic import JsonLogicRuleError, validate_rule

TEMPLATE_PUBLISH_FLAG: Final[str] = "ca11_template_publish"
PROCESS_WRITER_FLAG: Final[str] = "ca11_process_writer"
PROCESS_TRANSITION_FLAG: Final[str] = "ca11_process_transition"
EVIDENCE_WRITER_FLAG: Final[str] = "ca11_evidence_writer"
EVENT_WRITER_FLAG: Final[str] = "ca11_event_writer"
GATE_WRITER_FLAG: Final[str] = "ca11_gate_writer"


def parse_rule(value: Any, fieldname: str) -> dict[str, Any]:
	if value in (None, "", {}):
		return {}
	try:
		parsed = value if isinstance(value, dict) else json.loads(value)
	except (TypeError, ValueError):
		frappe.throw(_("{0} должен быть JSON object.").format(fieldname))
	if not isinstance(parsed, dict):
		frappe.throw(_("{0} должен быть JSON object.").format(fieldname))
	if not parsed:
		return {}
	try:
		validate_rule(parsed)
	except JsonLogicRuleError as exc:
		frappe.throw(_("Недопустимое {0}: {1}.").format(fieldname, str(exc)))
	return parsed


def parse_json_object(value: Any, fieldname: str) -> dict[str, Any]:
	if value in (None, "", {}):
		return {}
	try:
		parsed = value if isinstance(value, dict) else json.loads(value)
	except (TypeError, ValueError):
		frappe.throw(_("{0} должен быть JSON object.").format(fieldname))
	if not isinstance(parsed, dict):
		frappe.throw(_("{0} должен быть JSON object.").format(fieldname))
	return parsed


def require_writer(flag: str, operation: str) -> None:
	if not frappe.flags.get(flag):
		frappe.throw(
			_("{0} разрешена только typed writer CA-11.").format(operation),
			frappe.PermissionError,
		)


def require_template_draft(template_name: str) -> None:
	status = frappe.db.get_value("Ferum Process Template", template_name, "status")
	if status != "Draft":
		frappe.throw(_("Published Process Template graph неизменяем."), frappe.PermissionError)


def reject_direct_managed_update(document: Any, label: str) -> None:
	if document.get_doc_before_save() is not None and not frappe.flags.get(
		PROCESS_TRANSITION_FLAG
	):
		frappe.throw(
			_("{0} изменяется только typed command CA-11.").format(label),
			frappe.PermissionError,
		)
