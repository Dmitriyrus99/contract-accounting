"""Whitelisted CA-05 commands for project-document lifecycle and custody."""

from __future__ import annotations

import json
from typing import Any, Final
from uuid import uuid4

import frappe
from frappe import _
from frappe.utils import now_datetime

from contract_accounting.contract_accounting.doctype.ferum_project_document.ferum_project_document import (
	DIGITAL_TRANSITIONS,
	DOCUMENT_EVENT_DOCTYPE,
	DOCUMENT_EVENT_WRITER_FLAG,
	DOCUMENT_TRANSITION_CONTEXT_FLAG,
	DOCUMENT_TRANSITIONS,
	DOCUMENT_WRITE_FLAG,
	ORIGINAL_TRANSITIONS,
	PROJECT_DOCUMENT_DOCTYPE,
)
from contract_accounting.infrastructure.file_access import get_authorized_file

_DOCUMENT_ROLES: Final[frozenset[str]] = frozenset(
	{"Юрист", "Бухгалтер", "Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_DIGITAL_ROLES: Final[frozenset[str]] = frozenset(
	{"Юрист", "Бухгалтер", "Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_ORIGINAL_ROLES: Final[frozenset[str]] = frozenset(
	{
		"Офис-менеджер",
		"Юрист",
		"Менеджер проектов",
		"Руководитель проектов",
		"System Manager",
	}
)


@frappe.whitelist(methods=["POST"])
def change_project_document_status(
	project_document: str,
	target_status: str,
	reason: str,
	evidence_file: str | None = None,
	stamp_reference: str | None = None,
) -> dict[str, Any]:
	"""Move the registry-card lifecycle without changing either copy axis."""

	return _transition(
		project_document=project_document,
		dimension="Document",
		fieldname="status",
		target_status=target_status,
		matrix=DOCUMENT_TRANSITIONS,
		roles=_DOCUMENT_ROLES,
		reason=reason,
		evidence_file=evidence_file,
		stamp_reference=stamp_reference,
	)


@frappe.whitelist(methods=["POST"])
def change_digital_copy_status(
	project_document: str,
	target_status: str,
	reason: str,
	file_name: str | None = None,
	evidence_file: str | None = None,
	basis: str | None = None,
) -> dict[str, Any]:
	"""Move only the digital-copy axis and keep File as the binary SSOT."""

	updates: dict[str, Any] = {}
	if file_name:
		_validate_file(file_name)
		updates["file"] = file_name
	if target_status == "Not Required":
		updates["digital_not_required_basis"] = _required_text(basis, "basis")
	return _transition(
		project_document=project_document,
		dimension="Digital Copy",
		fieldname="digital_copy_status",
		target_status=target_status,
		matrix=DIGITAL_TRANSITIONS,
		roles=_DIGITAL_ROLES,
		reason=reason,
		evidence_file=evidence_file,
		updates=updates,
	)


@frappe.whitelist(methods=["POST"])
def change_original_status(
	project_document: str,
	target_status: str,
	reason: str,
	evidence_file: str | None = None,
	basis: str | None = None,
	expected_at: str | None = None,
	shipment_date: str | None = None,
	tracking_number: str | None = None,
	storage_location: str | None = None,
) -> dict[str, Any]:
	"""Move only paper-original custody and stamp facts on the server."""

	now = now_datetime()
	updates: dict[str, Any] = {}
	if target_status == "Requested":
		updates["original_requested_at"] = now
		updates["original_expected_at"] = expected_at
	elif target_status == "In Transit":
		updates["original_shipment_date"] = shipment_date or now
		updates["original_tracking_number"] = _required_text(
			tracking_number, "tracking_number"
		)
	elif target_status == "Received":
		updates["original_received_at"] = now
		updates["original_received_by"] = frappe.session.user
	elif target_status == "Archived":
		updates["original_archived_at"] = now
		updates["original_archived_by"] = frappe.session.user
		updates["original_storage_location"] = _required_text(
			storage_location, "storage_location"
		)
	elif target_status == "Not Required":
		updates["original_not_required_basis"] = _required_text(basis, "basis")
	return _transition(
		project_document=project_document,
		dimension="Original",
		fieldname="original_status",
		target_status=target_status,
		matrix=ORIGINAL_TRANSITIONS,
		roles=_ORIGINAL_ROLES,
		reason=reason,
		evidence_file=evidence_file,
		updates=updates,
	)


@frappe.whitelist()
def get_project_document_timeline(project_document: str) -> list[dict[str, Any]]:
	"""Return the immutable status history after normal read authorization."""

	doc = _get_authorized_document(project_document, "read")
	return frappe.get_all(
		DOCUMENT_EVENT_DOCTYPE,
		filters={"project_document": doc.name},
		fields=[
			"name",
			"dimension",
			"from_status",
			"to_status",
			"actor",
			"occurred_at",
			"reason",
			"evidence_file",
			"stamp_reference",
			"correlation_id",
			"snapshot_json",
		],
		order_by="occurred_at asc, creation asc",
	)


def _transition(
	*,
	project_document: str,
	dimension: str,
	fieldname: str,
	target_status: str,
	matrix: dict[str, frozenset[str]],
	roles: frozenset[str],
	reason: str,
	evidence_file: str | None,
	stamp_reference: str | None = None,
	updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
	_require_role(roles)
	reason = _required_text(reason, "reason")
	if evidence_file:
		_validate_file(evidence_file)
	name = _required_text(project_document, "project_document")
	save_point = f"ca_document_{uuid4().hex}"
	frappe.db.savepoint(save_point)
	try:
		locked = frappe.db.get_value(
			PROJECT_DOCUMENT_DOCTYPE,
			name,
			("name", fieldname),
			as_dict=True,
			for_update=True,
		)
		if not locked:
			frappe.throw(_("Project Document не найден."), frappe.DoesNotExistError)
		doc = _get_authorized_document(name, "write")
		old_status = locked.get(fieldname)
		if target_status not in matrix.get(old_status, frozenset()):
			frappe.throw(_("Недопустимый Project Document transition."))
		for update_field, value in (updates or {}).items():
			doc.set(update_field, value)
		doc.set(fieldname, target_status)
		context = {
			"dimension": dimension,
			"evidence_file": evidence_file,
			"stamp_reference": stamp_reference,
		}
		previous_write = frappe.flags.get(DOCUMENT_WRITE_FLAG)
		previous_context = frappe.flags.get(DOCUMENT_TRANSITION_CONTEXT_FLAG)
		frappe.flags[DOCUMENT_WRITE_FLAG] = True
		frappe.flags[DOCUMENT_TRANSITION_CONTEXT_FLAG] = context
		try:
			doc.save(ignore_permissions=True)
		finally:
			frappe.flags[DOCUMENT_WRITE_FLAG] = previous_write
			frappe.flags[DOCUMENT_TRANSITION_CONTEXT_FLAG] = previous_context

		correlation_id = uuid4().hex
		_event(
			doc=doc,
			dimension=dimension,
			old_status=old_status,
			new_status=target_status,
			reason=reason,
			evidence_file=evidence_file,
			stamp_reference=stamp_reference,
			correlation_id=correlation_id,
		)
		return {
			"project_document": doc.name,
			"status": doc.status,
			"digital_copy_status": doc.digital_copy_status,
			"original_status": doc.original_status,
			"correlation_id": correlation_id,
		}
	except BaseException:
		frappe.db.rollback(save_point=save_point)
		raise


def _event(
	*,
	doc: Any,
	dimension: str,
	old_status: str,
	new_status: str,
	reason: str,
	evidence_file: str | None,
	stamp_reference: str | None,
	correlation_id: str,
) -> None:
	event = frappe.new_doc(DOCUMENT_EVENT_DOCTYPE)
	event.project_document = doc.name
	event.dimension = dimension
	event.from_status = old_status
	event.to_status = new_status
	event.actor = frappe.session.user
	event.occurred_at = now_datetime()
	event.reason = reason
	event.evidence_file = evidence_file
	event.stamp_reference = stamp_reference
	event.correlation_id = correlation_id
	event.snapshot_json = json.dumps(
		{
			"status": doc.status,
			"digital_copy_status": doc.digital_copy_status,
			"original_status": doc.original_status,
			"file": doc.file,
			"content_hash": doc.content_hash,
			"original_requested_at": doc.original_requested_at,
			"original_received_at": doc.original_received_at,
			"original_archived_at": doc.original_archived_at,
			"original_storage_location": doc.original_storage_location,
		},
		ensure_ascii=False,
		default=str,
	)
	previous = frappe.flags.get(DOCUMENT_EVENT_WRITER_FLAG)
	frappe.flags[DOCUMENT_EVENT_WRITER_FLAG] = True
	try:
		event.insert(ignore_permissions=True)
	finally:
		frappe.flags[DOCUMENT_EVENT_WRITER_FLAG] = previous


def _get_authorized_document(name: str, permission_type: str) -> Any:
	if not frappe.db.exists(PROJECT_DOCUMENT_DOCTYPE, name):
		frappe.throw(_("Project Document не найден."), frappe.DoesNotExistError)
	doc = frappe.get_doc(PROJECT_DOCUMENT_DOCTYPE, name)
	doc.check_permission(permission_type)
	return doc


def _validate_file(name: str) -> None:
	get_authorized_file(name)


def _require_role(allowed: frozenset[str]) -> None:
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles(frappe.session.user)).intersection(allowed):
		frappe.throw(_("Роль не разрешает CA-05 document command."), frappe.PermissionError)


def _required_text(value: str | None, fieldname: str) -> str:
	text = (value or "").strip()
	if not text:
		frappe.throw(_("{0} обязателен.").format(fieldname))
	return text
