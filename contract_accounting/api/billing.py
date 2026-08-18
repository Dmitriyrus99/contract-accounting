"""Typed CA-06 billing commands over standard ERPNext accounting documents."""

from __future__ import annotations

import json
from typing import Any, Final
from uuid import uuid4

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime

from contract_accounting.api.documents import (
	change_digital_copy_status,
	change_project_document_status,
)
from contract_accounting.contract_accounting.doctype.ferum_billing_artifact.ferum_billing_artifact import (
	ARTIFACT_UPDATE_FLAG,
	ARTIFACT_WRITER_FLAG,
)
from contract_accounting.contract_accounting.doctype.ferum_billing_event.ferum_billing_event import (
	BILLING_EVENT_WRITER_FLAG,
)
from contract_accounting.contract_accounting.doctype.ferum_billing_output.ferum_billing_output import (
	ACTIVE_STATUSES,
	OUTPUT_TRANSITION_CONTEXT_FLAG,
	OUTPUT_UPDATE_FLAG,
	OUTPUT_WRITER_FLAG,
	snapshot_for_source,
)


OUTPUT_DOCTYPE: Final[str] = "Ferum Billing Output"
ARTIFACT_DOCTYPE: Final[str] = "Ferum Billing Artifact"
EVENT_DOCTYPE: Final[str] = "Ferum Billing Event"
BASIS_DOCTYPE: Final[str] = "Ferum Billing Basis Item"
_BILLING_ROLES: Final[frozenset[str]] = frozenset({"Бухгалтер", "System Manager"})


@frappe.whitelist()
def get_unbilled_accepted_work(
	service_project: str,
	period_start: str,
	period_end: str,
) -> list[dict[str, Any]]:
	"""Return permission-filtered accepted results not claimed by an active Output."""

	project = _authorized_project(service_project)
	start, end = getdate(period_start), getdate(period_end)
	if end < start:
		frappe.throw(_("period_end не может быть раньше period_start."))
	refs: list[tuple[str, str]] = []
	for row in frappe.get_list(
		"Ferum Maintenance Visit",
		filters={
			"service_project": project.name,
			"acceptance_status": "Accepted",
			"billing_eligible": 1,
			"actual_end": ["between", [str(start), f"{end} 23:59:59"]],
		},
		fields=["name"],
		limit_page_length=0,
	):
		refs.append(("Ferum Maintenance Visit", row.name))
	for row in frappe.get_list(
		"Ferum Service Request",
		filters={
			"service_project": project.name,
			"status": ["in", ["Resolved", "Closed"]],
			"actual_end": ["between", [str(start), f"{end} 23:59:59"]],
		},
		fields=["name"],
		limit_page_length=0,
	):
		refs.append(("Ferum Service Request", row.name))
	result = []
	for doctype, name in refs:
		claim = f"{doctype}::{name}"
		if frappe.db.exists(BASIS_DOCTYPE, {"active_claim_key": claim}):
			continue
		try:
			snapshot = snapshot_for_source(doctype, name, project.name)
		except frappe.ValidationError:
			continue
		result.append(snapshot)
	return result


@frappe.whitelist(methods=["POST"])
def create_billing_output(
	service_project: str,
	sales_invoice: str,
	output_type: str,
	document_date: str,
	period_start: str,
	period_end: str,
	source_refs: str | list[dict[str, str]],
	upd_status: str | None = None,
) -> dict[str, Any]:
	"""Create a Draft Output with server-derived immutable basis rows."""

	_require_billing_role()
	save_point = _savepoint("create")
	try:
		doc = _new_output(
			service_project=service_project,
			sales_invoice=sales_invoice,
			output_type=output_type,
			document_date=document_date,
			period_start=period_start,
			period_end=period_end,
			source_refs=_source_refs(source_refs),
			upd_status=upd_status,
		)
		correlation = uuid4().hex
		_event(doc, "Created", "Billing Output created", correlation)
		return _output_result(doc, correlation)
	except BaseException:
		frappe.db.rollback(save_point=save_point)
		raise


@frappe.whitelist(methods=["POST"])
def register_billing_artifact(
	billing_output: str,
	artifact_type: str,
	file_name: str,
	reason: str,
	generation_mode: str | None = None,
	snapshot_schema_version: int | str = 1,
) -> dict[str, Any]:
	"""Publish one immutable File version and apply its legal lifecycle effect."""

	_require_billing_role()
	reason = _required(reason, "reason")
	save_point = _savepoint("artifact")
	try:
		output = _locked_output(billing_output)
		_validate_output_write(output)
		_validate_file(file_name)
		if artifact_type == "Generated" and generation_mode == "Final":
			if output.status != "Draft":
				frappe.throw(_("Final Generated Artifact требует Draft Output."))
		elif artifact_type == "Signed Scan":
			if output.status not in {"Issued", "Signed"}:
				frappe.throw(_("Signed Scan требует Issued/Signed Output."))

		previous = frappe.db.get_value(
			ARTIFACT_DOCTYPE,
			{
				"billing_output": output.name,
				"artifact_type": artifact_type,
				"is_current": 1,
			},
			"name",
			for_update=True,
		)
		if previous:
			previous_doc = frappe.get_doc(ARTIFACT_DOCTYPE, previous)
			previous_doc.is_current = 0
			previous_doc.current_key = None
			_with_flag(ARTIFACT_UPDATE_FLAG, lambda: previous_doc.save(ignore_permissions=True))

		artifact = frappe.new_doc(ARTIFACT_DOCTYPE)
		artifact.billing_output = output.name
		artifact.artifact_type = artifact_type
		artifact.generation_mode = generation_mode
		artifact.file = file_name
		artifact.is_signed = int(artifact_type == "Signed Scan")
		artifact.is_current = 1
		artifact.supersedes_artifact = previous
		artifact.snapshot_schema_version = int(snapshot_schema_version)
		_with_flag(ARTIFACT_WRITER_FLAG, lambda: artifact.insert(ignore_permissions=True))

		if artifact_type == "Generated" and generation_mode == "Final":
			output.status = "Generated"
			output.final_artifact_status = "Ready"
			_save_output(output, "Generated")
			event_type = "Generated"
		elif artifact_type == "Signed Scan":
			if output.status == "Issued":
				output.status = "Signed"
				output.signed_at = now_datetime()
				output.signed_by = frappe.session.user
				_save_output(output, "Signed")
			event_type = "Signed"
		else:
			event_type = "Artifact Added"

		correlation = uuid4().hex
		_event(
			output,
			event_type,
			reason,
			correlation,
			related_artifact=artifact.name,
		)
		if artifact_type == "Signed Scan" and output.document_number:
			_project_document_projection(output, artifact, signed=True)
		return {
			**_output_result(output, correlation),
			"artifact": artifact.name,
			"artifact_version": artifact.version,
		}
	except BaseException:
		frappe.db.rollback(save_point=save_point)
		raise


@frappe.whitelist(methods=["POST"])
def issue_billing_output(
	billing_output: str,
	document_number: str,
	reason: str,
) -> dict[str, Any]:
	"""Freeze an Output only after a Final artifact and submitted invoice exist."""

	_require_billing_role()
	reason = _required(reason, "reason")
	save_point = _savepoint("issue")
	try:
		output = _locked_output(billing_output)
		_validate_output_write(output)
		if output.status != "Generated":
			frappe.throw(_("Issue требует Generated Output."))
		artifact_name = frappe.db.get_value(
			ARTIFACT_DOCTYPE,
			{
				"billing_output": output.name,
				"artifact_type": "Generated",
				"generation_mode": "Final",
				"is_current": 1,
			},
			"name",
			for_update=True,
		)
		if not artifact_name:
			frappe.throw(_("Issue требует current Final Artifact."))
		output.document_number = _required(document_number, "document_number")
		output.status = "Issued"
		output.issued_at = now_datetime()
		output.issued_by = frappe.session.user
		_save_output(output, "Issued")
		correlation = uuid4().hex
		_event(output, "Issued", reason, correlation, related_artifact=artifact_name)
		_project_document_projection(
			output,
			frappe.get_doc(ARTIFACT_DOCTYPE, artifact_name),
			signed=False,
		)
		return _output_result(output, correlation)
	except BaseException:
		frappe.db.rollback(save_point=save_point)
		raise


@frappe.whitelist(methods=["POST"])
def cancel_billing_output(billing_output: str, reason: str) -> dict[str, Any]:
	"""Release active basis claims without deleting the historical snapshot."""

	_require_billing_role()
	reason = _required(reason, "reason")
	save_point = _savepoint("cancel")
	try:
		output = _locked_output(billing_output)
		_validate_output_write(output)
		if output.status not in ACTIVE_STATUSES:
			frappe.throw(_("Только active Billing Output можно отменить."))
		_release_claims(output)
		output.status = "Cancelled"
		if output.final_artifact_status in {"Pending", "Failed"}:
			output.final_artifact_status = "Obsolete"
		_save_output(output, "Cancelled")
		correlation = uuid4().hex
		_event(output, "Cancelled", reason, correlation)
		return _output_result(output, correlation)
	except BaseException:
		frappe.db.rollback(save_point=save_point)
		raise


@frappe.whitelist(methods=["POST"])
def supersede_billing_output(
	billing_output: str,
	reason: str,
	source_refs: str | list[dict[str, str]] | None = None,
) -> dict[str, Any]:
	"""Atomically supersede an issued output and create a claimed Correction draft."""

	_require_billing_role()
	reason = _required(reason, "reason")
	save_point = _savepoint("supersede")
	try:
		old = _locked_output(billing_output)
		_validate_output_write(old)
		if old.status not in {"Issued", "Signed"}:
			frappe.throw(_("Supersede требует Issued/Signed Output."))
		refs = (
			_source_refs(source_refs)
			if source_refs is not None
			else [
				{"source_doctype": row.source_doctype, "source_name": row.source_name}
				for row in old.basis_items
			]
		)
		_release_claims(old)
		old.status = "Superseded"
		_save_output(old, "Superseded")
		new = _new_output(
			service_project=old.service_project,
			sales_invoice=old.sales_invoice,
			output_type="Correction",
			document_date=str(getdate()),
			period_start=str(old.period_start),
			period_end=str(old.period_end),
			source_refs=refs,
			supersedes=old.name,
		)
		old.superseded_by = new.name
		_save_output(old, "Superseded")
		correlation = uuid4().hex
		_event(old, "Superseded", reason, correlation, related_output=new.name)
		_event(new, "Corrected", reason, correlation, related_output=old.name)
		return {
			"superseded_output": old.name,
			"correction_output": new.name,
			"correlation_id": correlation,
		}
	except BaseException:
		frappe.db.rollback(save_point=save_point)
		raise


@frappe.whitelist()
def get_billing_trace(billing_output: str) -> dict[str, Any]:
	output = _locked_output(billing_output, lock=False)
	output.check_permission("read")
	return {
		"billing_output": output.name,
		"service_project": output.service_project,
		"sales_invoice": output.sales_invoice,
		"status": output.status,
		"basis_hash": output.basis_hash,
		"basis": [
			{
				"source_doctype": row.source_doctype,
				"source_name": row.source_name,
				"source_hash": row.source_hash,
				"inclusion_state": row.inclusion_state,
			}
			for row in output.basis_items
		],
		"artifacts": frappe.get_list(
			ARTIFACT_DOCTYPE,
			filters={"billing_output": output.name},
			fields=["name", "artifact_type", "generation_mode", "version", "is_current", "project_document"],
			order_by="artifact_type asc, version asc",
		),
		"events": frappe.get_list(
			EVENT_DOCTYPE,
			filters={"billing_output": output.name},
			fields=["event_type", "timestamp", "actor", "reason", "correlation_id", "related_output", "related_artifact"],
			order_by="timestamp asc, creation asc",
		),
	}


def _new_output(
	*,
	service_project: str,
	sales_invoice: str,
	output_type: str,
	document_date: str,
	period_start: str,
	period_end: str,
	source_refs: list[dict[str, str]],
	upd_status: str | None = None,
	supersedes: str | None = None,
) -> Any:
	project = _authorized_project(service_project)
	frappe.db.get_value("Sales Invoice", sales_invoice, "name", for_update=True)
	doc = frappe.new_doc(OUTPUT_DOCTYPE)
	doc.service_project = project.name
	doc.sales_invoice = sales_invoice
	doc.output_type = output_type
	doc.upd_status = upd_status
	doc.document_date = document_date
	doc.period_start = period_start
	doc.period_end = period_end
	doc.supersedes = supersedes
	if not source_refs:
		frappe.throw(_("source_refs не может быть пустым."))
	for ref in source_refs:
		frappe.db.get_value(ref["source_doctype"], ref["source_name"], "name", for_update=True)
		snapshot = snapshot_for_source(
			ref["source_doctype"], ref["source_name"], project.name
		)
		doc.append("basis_items", snapshot)
	_with_flag(OUTPUT_WRITER_FLAG, lambda: doc.insert(ignore_permissions=True))
	return doc


def _project_document_projection(output: Any, artifact: Any, *, signed: bool) -> None:
	if artifact.project_document:
		return
	document_type = {
		"Act": "Act",
		"UPD": "UPD",
		"Invoice Print": "Invoice",
		"Invoice Factura": "Invoice",
		"Correction": "Other",
	}[output.output_type]
	doc = frappe.get_doc(
		{
			"doctype": "Ferum Project Document",
			"source_doctype": ARTIFACT_DOCTYPE,
			"source_name": artifact.name,
			"document_type": document_type,
			"document_number": output.document_number,
			"document_date": output.document_date,
			"version": f"{'Signed' if signed else 'Generated'}-{artifact.version}",
			"issuer_doctype": "Company",
			"issuer": output.company,
			"recipient_doctype": "Customer",
			"recipient": output.customer,
			"file": artifact.file,
			"billing_reference_doctype": ARTIFACT_DOCTYPE,
			"billing_reference_name": artifact.name,
		}
	).insert(ignore_permissions=True)
	change_digital_copy_status(
		doc.name,
		"Uploaded",
		"CA-06 Billing Artifact projection",
		file_name=artifact.file,
	)
	change_digital_copy_status(
		doc.name,
		"Signed" if signed else "Verified",
		"CA-06 Billing Artifact accepted",
		evidence_file=artifact.file,
	)
	change_project_document_status(doc.name, "Active", "CA-06 closing document issued")
	artifact.project_document = doc.name
	_with_flag(ARTIFACT_UPDATE_FLAG, lambda: artifact.save(ignore_permissions=True))


def _release_claims(output: Any) -> None:
	for row in output.basis_items:
		row.active_claim_key = None
		row.inclusion_state = "Reversed"


def _save_output(output: Any, target_status: str) -> None:
	previous_update = frappe.flags.get(OUTPUT_UPDATE_FLAG)
	previous_context = frappe.flags.get(OUTPUT_TRANSITION_CONTEXT_FLAG)
	frappe.flags[OUTPUT_UPDATE_FLAG] = True
	frappe.flags[OUTPUT_TRANSITION_CONTEXT_FLAG] = {"target_status": target_status}
	try:
		output.save(ignore_permissions=True)
	finally:
		frappe.flags[OUTPUT_UPDATE_FLAG] = previous_update
		frappe.flags[OUTPUT_TRANSITION_CONTEXT_FLAG] = previous_context


def _event(
	output: Any,
	event_type: str,
	reason: str,
	correlation_id: str,
	*,
	related_output: str | None = None,
	related_artifact: str | None = None,
) -> None:
	event = frappe.new_doc(EVENT_DOCTYPE)
	event.billing_output = output.name
	event.event_type = event_type
	event.related_invoice = output.sales_invoice
	event.related_output = related_output
	event.related_artifact = related_artifact
	event.timestamp = now_datetime()
	event.actor = frappe.session.user
	event.reason = reason
	event.correlation_id = correlation_id
	event.metadata_json = json.dumps(
		{
			"status": output.status,
			"basis_hash": output.basis_hash,
			"document_number": output.document_number,
			"final_artifact_status": output.final_artifact_status,
		},
		ensure_ascii=False,
		default=str,
	)
	_with_flag(BILLING_EVENT_WRITER_FLAG, lambda: event.insert(ignore_permissions=True))


def _locked_output(name: str, *, lock: bool = True) -> Any:
	name = _required(name, "billing_output")
	row = frappe.db.get_value(
		OUTPUT_DOCTYPE,
		name,
		"name",
		for_update=lock,
	)
	if not row:
		frappe.throw(_("Billing Output не найден."), frappe.DoesNotExistError)
	return frappe.get_doc(OUTPUT_DOCTYPE, name)


def _authorized_project(name: str) -> Any:
	name = _required(name, "service_project")
	if not frappe.db.exists("Ferum Service Project", name):
		frappe.throw(_("Service Project не найден."), frappe.DoesNotExistError)
	doc = frappe.get_doc("Ferum Service Project", name)
	doc.check_permission("read")
	return doc


def _validate_output_write(output: Any) -> None:
	output.check_permission("write")


def _validate_file(name: str) -> None:
	if not frappe.db.get_value("File", name, "content_hash"):
		frappe.throw(_("Artifact требует File с content_hash."))


def _source_refs(value: str | list[dict[str, str]] | None) -> list[dict[str, str]]:
	parsed = frappe.parse_json(value) if isinstance(value, str) else value
	if not isinstance(parsed, list):
		frappe.throw(_("source_refs должен быть JSON-массивом."))
	refs = []
	for item in parsed:
		if not isinstance(item, dict):
			frappe.throw(_("Каждый source_ref должен быть объектом."))
		refs.append(
			{
				"source_doctype": _required(item.get("source_doctype"), "source_doctype"),
				"source_name": _required(item.get("source_name"), "source_name"),
			}
		)
	return refs


def _require_billing_role() -> None:
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles(frappe.session.user)).intersection(_BILLING_ROLES):
		frappe.throw(_("Роль не разрешает CA-06 billing command."), frappe.PermissionError)


def _required(value: Any, fieldname: str) -> str:
	text = str(value or "").strip()
	if not text:
		frappe.throw(_("{0} обязателен.").format(fieldname))
	return text


def _savepoint(label: str) -> str:
	name = f"ca_billing_{label}_{uuid4().hex}"
	frappe.db.savepoint(name)
	return name


def _with_flag(flag: str, callback: Any) -> Any:
	previous = frappe.flags.get(flag)
	frappe.flags[flag] = True
	try:
		return callback()
	finally:
		frappe.flags[flag] = previous


def _output_result(output: Any, correlation_id: str) -> dict[str, Any]:
	return {
		"billing_output": output.name,
		"status": output.status,
		"basis_hash": output.basis_hash,
		"basis_count": len(output.basis_items),
		"correlation_id": correlation_id,
	}
