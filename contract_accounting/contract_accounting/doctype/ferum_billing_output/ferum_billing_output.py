"""Documentary Billing Output over standard ERPNext Sales Invoice."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, get_datetime


DOCTYPE: Final[str] = "Ferum Billing Output"
OUTPUT_WRITER_FLAG: Final[str] = "contract_accounting_billing_output_writer"
OUTPUT_UPDATE_FLAG: Final[str] = "contract_accounting_billing_output_update"
OUTPUT_TRANSITION_CONTEXT_FLAG: Final[str] = "contract_accounting_billing_transition_context"
ACTIVE_STATUSES: Final[frozenset[str]] = frozenset({"Draft", "Generated", "Issued", "Signed"})
TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Draft": frozenset({"Generated", "Cancelled"}),
	"Generated": frozenset({"Issued", "Cancelled"}),
	"Issued": frozenset({"Signed", "Superseded", "Cancelled"}),
	"Signed": frozenset({"Superseded", "Cancelled"}),
	"Superseded": frozenset(),
	"Cancelled": frozenset(),
}
ALLOWED_BASIS_DOCTYPES: Final[frozenset[str]] = frozenset(
	{"Ferum Maintenance Visit", "Ferum Service Request"}
)

_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
	"service_project",
	"company",
	"customer",
	"sales_invoice",
	"output_type",
	"upd_status",
	"document_date",
	"period_start",
	"period_end",
	"currency",
	"invoice_grand_total_snapshot",
	"supersedes",
)
_CONTROLLED_FIELDS: Final[tuple[str, ...]] = (
	"status",
	"document_number",
	"basis_items",
	"basis_hash",
	"basis_amount",
	"final_artifact_status",
	"issued_at",
	"issued_by",
	"signed_at",
	"signed_by",
	"superseded_by",
)


class FerumBillingOutput(Document):
	def before_insert(self) -> None:
		if not frappe.flags.get(OUTPUT_WRITER_FLAG):
			frappe.throw(_("Billing Output создаётся только typed writer CA-06."), frappe.PermissionError)

	def validate(self) -> None:
		self._derive_context()
		self._validate_period()
		self._validate_type()
		self._validate_invoice()
		self._validate_basis()
		self._freeze_identity()
		self._guard_controlled_fields()
		self._validate_transition()

	def on_trash(self) -> None:
		frappe.throw(_("Billing Output не удаляется; используйте cancel/supersede."), frappe.PermissionError)

	def _derive_context(self) -> None:
		project = frappe.db.get_value(
			"Ferum Service Project",
			self.service_project,
			("company", "customer", "currency"),
			as_dict=True,
		)
		if not project:
			frappe.throw(_("Billing Output Service Project не найден."))
		for fieldname, value in {
			"company": project.company,
			"customer": project.customer,
			"currency": project.currency,
		}.items():
			self.set(fieldname, value)

	def _validate_period(self) -> None:
		if getdate(self.period_end) < getdate(self.period_start):
			frappe.throw(_("Billing period end не может быть раньше start."))

	def _validate_type(self) -> None:
		if self.output_type == "UPD":
			if self.upd_status not in {"1", "2"}:
				frappe.throw(_("UPD требует status 1 или 2."))
		elif self.upd_status:
			frappe.throw(_("upd_status допустим только для UPD."))

	def _validate_invoice(self) -> None:
		invoice = frappe.db.get_value(
			"Sales Invoice",
			self.sales_invoice,
			("docstatus", "company", "customer", "currency", "grand_total", "ferum_service_project"),
			as_dict=True,
		)
		if not invoice:
			frappe.throw(_("Billing Output Sales Invoice не найден."))
		if cint(invoice.docstatus) != 1:
			frappe.throw(_("Billing Output требует submitted Sales Invoice."))
		if (
			invoice.company != self.company
			or invoice.customer != self.customer
			or invoice.currency != self.currency
			or invoice.ferum_service_project != self.service_project
		):
			frappe.throw(_("Sales Invoice context не совпадает с Billing Output."))
		before = self.get_doc_before_save()
		if before is None:
			self.invoice_grand_total_snapshot = invoice.grand_total
		elif flt(self.invoice_grand_total_snapshot) != flt(before.invoice_grand_total_snapshot):
			frappe.throw(_("Invoice total snapshot immutable."))

	def _validate_basis(self) -> None:
		if not self.basis_items:
			frappe.throw(_("Billing Output требует непустой Billing Basis."))
		before = self.get_doc_before_save()
		if before and before.status in {"Issued", "Signed", "Superseded", "Cancelled"}:
			if _basis_payload(self.basis_items) != _basis_payload(before.basis_items):
				frappe.throw(_("Issued Billing Basis immutable."))
			return
		seen: set[str] = set()
		for row in self.basis_items:
			key = f"{row.source_doctype}::{row.source_name}"
			if key in seen:
				frappe.throw(_("Billing Basis не допускает duplicate source."))
			seen.add(key)
			expected = snapshot_for_source(row.source_doctype, row.source_name, self.service_project)
			if not (getdate(self.period_start) <= getdate(expected["result_date"]) <= getdate(self.period_end)):
				frappe.throw(_("Billing Basis source вне периода Output."))
			for fieldname, value in expected.items():
				if _canonical_basis_value(fieldname, row.get(fieldname)) != _canonical_basis_value(
					fieldname, value
				):
					frappe.throw(_("Billing Basis snapshot определяется accepted source."))
			row.inclusion_state = "Included"
			row.active_claim_key = key if self.status in ACTIVE_STATUSES else None
		self.basis_amount = sum(flt(row.amount_snapshot) for row in self.basis_items)
		self.basis_hash = hashlib.sha256(
			json.dumps(_basis_payload(self.basis_items), ensure_ascii=False, sort_keys=True).encode()
		).hexdigest()

	def _freeze_identity(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			return
		if any(self.get(field) != before.get(field) for field in _IDENTITY_FIELDS):
			frappe.throw(_("Billing Output identity immutable."))

	def _guard_controlled_fields(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if self.status != "Draft":
				frappe.throw(_("Новый Billing Output создаётся в Draft."))
			return
		changed = [field for field in _CONTROLLED_FIELDS if self.get(field) != before.get(field)]
		if changed and not frappe.flags.get(OUTPUT_UPDATE_FLAG):
			frappe.throw(_("Billing Output меняется только командами CA-06."), frappe.PermissionError)

	def _validate_transition(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.status == self.status:
			return
		context = frappe.flags.get(OUTPUT_TRANSITION_CONTEXT_FLAG) or {}
		if context.get("target_status") != self.status:
			frappe.throw(_("Billing transition context отсутствует."))
		if self.status not in TRANSITIONS.get(before.status, frozenset()):
			frappe.throw(_("Недопустимый Billing Output transition."))
		if self.status == "Issued":
			if not self.document_number or not self.issued_at or not self.issued_by:
				frappe.throw(_("Issued требует number и server stamps."))
		if self.status == "Signed" and (not self.signed_at or not self.signed_by):
			frappe.throw(_("Signed требует server stamps."))


def snapshot_for_source(source_doctype: str, source_name: str, service_project: str) -> dict[str, Any]:
	if source_doctype not in ALLOWED_BASIS_DOCTYPES:
		frappe.throw(_("Billing Basis source DocType не разрешён."))
	if not frappe.db.exists(source_doctype, source_name):
		frappe.throw(_("Billing Basis source не найден."))
	source = frappe.get_doc(source_doctype, source_name)
	source.check_permission("read")
	if source.service_project != service_project:
		frappe.throw(_("Billing Basis source относится к другому Service Project."))
	if source_doctype == "Ferum Maintenance Visit":
		if source.acceptance_status != "Accepted" or not cint(source.billing_eligible):
			frappe.throw(_("Maintenance Visit не принят или не billing eligible."))
		result_date = source.actual_end
		acceptance_actor = source.accepted_by
		acceptance_time = source.accepted_on
		period_key = source.period_key
	else:
		if source.status not in {"Resolved", "Closed"}:
			frappe.throw(_("Service Request не является принятым результатом."))
		if source.work_result not in {"Completed", "Partially Completed"} or not source.evidence:
			frappe.throw(_("Service Request требует выполненный result и evidence."))
		result_date = source.actual_end
		acceptance_actor = source.modified_by
		acceptance_time = source.modified
		period_key = getdate(source.actual_end).strftime("%Y-%m") if source.actual_end else None
	if not result_date or not acceptance_actor or not acceptance_time or not period_key:
		frappe.throw(_("Accepted source не содержит complete acceptance provenance."))
	obligation = (
		frappe.db.get_value(
			"Ferum Contract Obligation",
			source.contract_obligation,
			("quantity", "uom", "price_component", "currency"),
			as_dict=True,
		)
		if source.get("contract_obligation")
		else None
	)
	project_currency = frappe.db.get_value("Ferum Service Project", service_project, "currency")
	snapshot = {
		"source_doctype": source_doctype,
		"source_name": source_name,
		"contract_obligation": source.get("contract_obligation"),
		"project_object": source.project_object,
		"service_object": source.service_object,
		"object_system": source.get("object_system"),
		"result_date": str(get_datetime(result_date)),
		"period_key": period_key,
		"quantity_snapshot": flt(obligation.quantity if obligation else 1),
		"uom_snapshot": obligation.uom if obligation else None,
		"amount_snapshot": flt(obligation.price_component if obligation else 0),
		"currency": obligation.currency if obligation else project_currency,
		"acceptance_actor": acceptance_actor,
		"acceptance_time": str(get_datetime(acceptance_time)),
	}
	source_payload = {
		"source_doctype": source_doctype,
		"source_name": source_name,
		"status": source.status,
		"work_result": source.get("work_result"),
		"result_date": snapshot["result_date"],
		"acceptance_actor": acceptance_actor,
		"acceptance_time": snapshot["acceptance_time"],
		"evidence": [
			{"evidence_type": row.evidence_type, "file": row.file}
			for row in (source.get("evidence") or [])
		],
	}
	snapshot_json = json.dumps(source_payload, ensure_ascii=False, sort_keys=True)
	snapshot["source_snapshot_json"] = snapshot_json
	snapshot["source_hash"] = hashlib.sha256(snapshot_json.encode()).hexdigest()
	return snapshot


def _basis_payload(rows: list[Any]) -> list[dict[str, Any]]:
	fields = (
		"source_doctype", "source_name", "contract_obligation", "project_object", "service_object",
		"object_system", "result_date", "period_key", "quantity_snapshot", "uom_snapshot",
		"amount_snapshot", "currency", "acceptance_actor", "acceptance_time",
		"source_snapshot_json", "source_hash",
	)
	return [
		{field: _canonical_basis_value(field, row.get(field)) for field in fields}
		for row in rows
	]


def _canonical_basis_value(fieldname: str, value: Any) -> Any:
	if value is None or value == "":
		return None
	if fieldname in {"result_date", "acceptance_time"}:
		return str(get_datetime(value))
	if fieldname in {"quantity_snapshot", "amount_snapshot"}:
		return flt(value)
	if fieldname == "source_snapshot_json":
		payload = json.loads(value) if isinstance(value, str) else value
		return json.dumps(payload, ensure_ascii=False, sort_keys=True)
	return value


def on_doctype_update() -> None:
	frappe.db.add_index(DOCTYPE, ["service_project", "status", "period_end"], "ca_billing_output_project_idx")
	frappe.db.add_index(DOCTYPE, ["sales_invoice", "status"], "ca_billing_output_invoice_idx")
	frappe.db.add_unique(
		DOCTYPE,
		["company", "output_type", "document_number"],
		"ca_billing_output_legal_number_uniq",
	)
