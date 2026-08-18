"""Typed Service Request provenance, successor and approval commands."""

from __future__ import annotations

from typing import Any, Final

import frappe
from frappe import _
from frappe.utils import now_datetime, today

from contract_accounting.api.documents import change_digital_copy_status
from contract_accounting.contract_accounting.doctype.ferum_service_request.ferum_service_request import (
	DOCTYPE,
	SUCCESSOR_WRITER_FLAG,
)

_MANAGER_ROLES: Final[frozenset[str]] = frozenset(
	{"Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_SUCCESSOR_KINDS: Final[frozenset[str]] = frozenset({"Paid Work", "Remaining"})


@frappe.whitelist(methods=["POST"])
def create_paid_work_request(service_request: str) -> dict[str, Any]:
	"""Create one idempotent Additional Work successor without pricing or invoice writes."""

	source = _locked_request(service_request)
	if source.status in {"Closed", "Cancelled"}:
		frappe.throw(_("Terminal Service Request не может создать Paid Work successor."))
	if source.request_type == "Additional Work":
		frappe.throw(_("Additional Work не может рекурсивно создавать Paid Work successor."))
	successor, created = _get_or_create_successor(
		source,
		kind="Paid Work",
		request_type="Additional Work",
		subject=f"Additional Work: {source.subject}",
		description=f"Created from {source.name}.\n{source.description}".strip(),
	)
	return _successor_result(source, successor, created)


@frappe.whitelist(methods=["POST"])
def partial_close_request(
	service_request: str,
	remaining_subject: str,
	remaining_description: str,
) -> dict[str, Any]:
	"""Atomically close a partially resolved request and create its one remaining successor."""

	source = _locked_request(service_request)
	existing = _successor(source.name, "Remaining")
	if existing:
		return _successor_result(source, existing, created=False)
	if source.status != "Resolved" or source.work_result != "Partially Completed":
		frappe.throw(_("Remaining successor требует Resolved + Partially Completed source."))
	subject = _required_text(remaining_subject, "remaining_subject")
	description = _required_text(remaining_description, "remaining_description")
	savepoint = f"ca_request_partial_{frappe.generate_hash(length=12)}"
	frappe.db.savepoint(savepoint)
	try:
		successor, created = _get_or_create_successor(
			source,
			kind="Remaining",
			request_type=source.request_type,
			subject=subject,
			description=description,
		)
		source.resolution = (
			f"{source.resolution or ''}\nPartially accepted; remaining: {successor.name}"
		).strip()
		source.status = "Closed"
		source.save()
		return _successor_result(source, successor, created)
	except BaseException:
		frappe.db.rollback(save_point=savepoint)
		raise


@frappe.whitelist(methods=["POST"])
def register_customer_approval_evidence(
	service_request: str,
	file_name: str,
) -> dict[str, Any]:
	"""Register exact Additional Work approval as Project Document over standard File."""

	request = _locked_request(service_request)
	if request.request_type != "Additional Work" or request.status in {"Closed", "Cancelled"}:
		frappe.throw(_("Customer approval регистрируется для active Additional Work Request."))
	file_row = frappe.db.get_value(
		"File",
		file_name,
		("name", "content_hash", "attached_to_doctype", "attached_to_name"),
		as_dict=True,
	)
	if (
		not file_row
		or not file_row.content_hash
		or file_row.attached_to_doctype != DOCTYPE
		or file_row.attached_to_name != request.name
	):
		frappe.throw(_("Approval evidence должен быть exact File текущего Service Request."))
	document_number = f"CUSTOMER-APPROVAL-{request.name}"
	existing = frappe.db.get_value(
		"Ferum Project Document",
		{
			"source_doctype": DOCTYPE,
			"source_name": request.name,
			"document_number": document_number,
		},
		"name",
	)
	if existing:
		document = frappe.get_doc("Ferum Project Document", existing)
		if document.file != file_name:
			frappe.throw(_("Customer approval уже зарегистрировано с другим File."))
		return _approval_result(document, created=False)
	document = frappe.get_doc(
		{
			"doctype": "Ferum Project Document",
			"document_type": "Correspondence",
			"document_number": document_number,
			"document_date": today(),
			"version": "1",
			"source_doctype": DOCTYPE,
			"source_name": request.name,
			"file": file_name,
			"owner_user": frappe.session.user,
			"confidentiality": "Confidential",
		}
	).insert()
	change_digital_copy_status(
		document.name,
		"Uploaded",
		"Customer approval evidence registered for Additional Work Request.",
		file_name=file_name,
	)
	document.reload()
	return _approval_result(document, created=True)


@frappe.whitelist()
def get_request_successors(service_request: str) -> dict[str, Any]:
	"""Return derived reverse links; the source Request stores no second mirror."""

	request = frappe.get_doc(DOCTYPE, _required_text(service_request, "service_request"))
	request.check_permission("read")
	rows = frappe.get_list(
		DOCTYPE,
		filters={"source_request": request.name},
		fields=["name", "successor_kind", "exception_key", "status", "subject"],
		order_by="successor_kind asc, creation asc",
	)
	return {"source_request": request.name, "successors": [dict(row) for row in rows]}


def _locked_request(name: str) -> Any:
	_require_manager()
	name = _required_text(name, "service_request")
	locked = frappe.db.get_value(DOCTYPE, name, "name", for_update=True)
	if not locked:
		frappe.throw(_("Service Request не найден."), frappe.DoesNotExistError)
	document = frappe.get_doc(DOCTYPE, name)
	document.check_permission("write")
	return document


def _get_or_create_successor(
	source: Any,
	*,
	kind: str,
	request_type: str,
	subject: str,
	description: str,
) -> tuple[Any, bool]:
	if kind not in _SUCCESSOR_KINDS:
		frappe.throw(_("Некорректный successor kind."))
	existing = _successor(source.name, kind)
	if existing:
		return existing, False
	key = _exception_key(source.name, kind)
	document = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"service_project": source.service_project,
			"project_object": source.project_object,
			"object_system": source.object_system,
			"contract_obligation": source.contract_obligation,
			"subject": subject,
			"description": description,
			"source_type": "Internal",
			"source_reference": source.name,
			"source_request": source.name,
			"successor_kind": kind,
			"exception_key": key,
			"request_type": request_type,
			"priority": source.priority,
			"requested_at": now_datetime(),
		}
	)
	previous = frappe.flags.get(SUCCESSOR_WRITER_FLAG)
	frappe.flags[SUCCESSOR_WRITER_FLAG] = True
	try:
		document.insert()
	finally:
		frappe.flags[SUCCESSOR_WRITER_FLAG] = previous
	return document, True


def _successor(source_request: str, kind: str) -> Any | None:
	name = frappe.db.get_value(
		DOCTYPE,
		{"source_request": source_request, "successor_kind": kind},
		"name",
	)
	return frappe.get_doc(DOCTYPE, name) if name else None


def _exception_key(source_request: str, kind: str) -> str:
	return f"paid:{source_request}" if kind == "Paid Work" else f"remaining:{source_request}"


def _successor_result(source: Any, successor: Any, created: bool) -> dict[str, Any]:
	return {
		"source_request": source.name,
		"source_status": source.status,
		"successor": successor.name,
		"successor_status": successor.status,
		"successor_kind": successor.successor_kind,
		"created": created,
	}


def _approval_result(document: Any, created: bool) -> dict[str, Any]:
	return {
		"project_document": document.name,
		"digital_copy_status": document.digital_copy_status,
		"file": document.file,
		"created": created,
	}


def _require_manager() -> None:
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles(frappe.session.user)).intersection(_MANAGER_ROLES):
		frappe.throw(_("Роль не разрешает Service Request exception command."), frappe.PermissionError)


def _required_text(value: str | None, fieldname: str) -> str:
	text = (value or "").strip()
	if not text:
		frappe.throw(_("{0} обязателен.").format(fieldname))
	return text
