"""Effective-dated operational assignment, deliberately separate from pricing."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

DOCTYPE: Final[str] = "Ferum Contractor Assignment"
ASSIGNMENT_WRITER_FLAG: Final[str] = "contract_accounting_assignment_writer"
ASSIGNMENT_TRANSITION_FLAG: Final[str] = "contract_accounting_assignment_transition"
ACTIVE_STATUSES: Final[frozenset[str]] = frozenset({"Approved", "Suspended"})
TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	"Draft": frozenset({"Approved", "Cancelled"}),
	"Approved": frozenset({"Suspended", "Completed", "Cancelled"}),
	"Suspended": frozenset({"Approved", "Completed", "Cancelled"}),
	"Completed": frozenset(),
	"Cancelled": frozenset(),
}
READINESS_POLICY_INACTIVE: Final[str] = "Policy Inactive"


class FerumContractorAssignment(Document):
	def before_insert(self) -> None:
		self._require_writer()

	def validate(self) -> None:
		self._require_writer()
		self._derive_project_context()
		self._validate_scope()
		self._validate_executor()
		self._validate_dates()
		self._validate_commercial_terms()
		self._validate_transition()
		self._validate_no_overlap()
		self._freeze_after_approval()
		self._derive_readiness()
		self.overlap_guard_key = self._overlap_guard_key()

	def on_trash(self) -> None:
		if self.status != "Draft" or not frappe.flags.get(ASSIGNMENT_WRITER_FLAG):
			frappe.throw(_("Assignment удаляется только typed writer в Draft."), frappe.PermissionError)

	@staticmethod
	def _require_writer() -> None:
		if not frappe.flags.get(ASSIGNMENT_WRITER_FLAG):
			frappe.throw(_("Contractor Assignment меняется только командами CA-08."), frappe.PermissionError)

	def _derive_project_context(self) -> None:
		project = frappe.db.get_value(
			"Ferum Service Project", self.service_project, ("company", "effective_from", "effective_to"), as_dict=True
		)
		if not project:
			frappe.throw(_("Contractor Assignment Service Project не найден."))
		self.company = project.company

	def _validate_scope(self) -> None:
		membership = frappe.db.get_value(
			"Ferum Project Object", self.project_object,
			("service_project", "service_object", "effective_from", "effective_to"), as_dict=True,
		)
		if not membership or membership.service_project != self.service_project:
			frappe.throw(_("Project Object не принадлежит Service Project Assignment."))
		if self.object_system:
			service_object = frappe.db.get_value("Ferum Object System", self.object_system, "service_object")
			if service_object != membership.service_object:
				frappe.throw(_("Object System не принадлежит Project Object Assignment."))
		if self.contract_obligation:
			obligation = frappe.db.get_value(
				"Ferum Contract Obligation", self.contract_obligation,
				("service_project", "project_object", "object_system", "work_type"), as_dict=True,
			)
			if not obligation or obligation.service_project != self.service_project:
				frappe.throw(_("Contract Obligation не принадлежит Service Project Assignment."))
			for fieldname in ("project_object", "object_system", "work_type"):
				value = getattr(obligation, fieldname, None)
				if value and value != self.get(fieldname):
					frappe.throw(
						_("Assignment.{0} не совпадает с Contract Obligation.").format(fieldname)
					)

	def _validate_executor(self) -> None:
		if self.execution_mode == "Internal":
			if not self.employee or self.supplier or self.contractor_worker:
				frappe.throw(_("Internal Assignment требует Employee и запрещает Supplier."))
			employee_company = frappe.db.get_value("Employee", self.employee, "company")
			if employee_company != self.company:
				frappe.throw(_("Employee относится к другой Company."))
		elif self.execution_mode == "Contractor":
			if not self.supplier or self.employee:
				frappe.throw(_("Contractor Assignment требует Supplier и запрещает Employee."))
			if self.contractor_worker:
				if not frappe.db.get_single_value("Ferum Privacy Settings", "enabled"):
					frappe.throw(
						_("Contractor Worker заблокирован: FR-05 policy inactive."),
						frappe.PermissionError,
					)
				worker = frappe.db.get_value(
					"Ferum Contractor Worker",
					self.contractor_worker,
					("supplier", "status"),
					as_dict=True,
				)
				if not worker or worker.supplier != self.supplier or worker.status != "Active":
					frappe.throw(_("Contractor Worker должен быть Active и принадлежать Supplier."))
		else:
			frappe.throw(_("Assignment execution_mode не поддерживается."))

	def _validate_dates(self) -> None:
		start = getdate(self.effective_from)
		end = getdate(self.effective_to) if self.effective_to else date.max
		if end < start:
			frappe.throw(_("Assignment effective_to раньше effective_from."))
		project = frappe.db.get_value(
			"Ferum Service Project", self.service_project, ("effective_from", "effective_to"), as_dict=True
		)
		if project.effective_from and start < getdate(project.effective_from):
			frappe.throw(_("Assignment начинается раньше договора."))
		if project.effective_to and end > getdate(project.effective_to):
			frappe.throw(_("Assignment заканчивается позже договора."))
		membership = frappe.db.get_value(
			"Ferum Project Object", self.project_object, ("effective_from", "effective_to"), as_dict=True
		)
		if membership.effective_from and start < getdate(membership.effective_from):
			frappe.throw(_("Assignment начинается раньше Project Object membership."))
		if membership.effective_to and end > getdate(membership.effective_to):
			frappe.throw(_("Assignment заканчивается позже Project Object membership."))

	def _validate_commercial_terms(self) -> None:
		if not self.commercial_terms:
			return
		terms = frappe.db.get_value(
			"Ferum Contractor Commercial Terms", self.commercial_terms,
			("contractor_assignment", "status"), as_dict=True,
		)
		if not terms or terms.contractor_assignment != self.name or terms.status != "Approved":
			frappe.throw(_("Assignment commercial terms должны быть Approved и ссылаться обратно."))

	def _validate_transition(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if self.status != "Draft":
				frappe.throw(_("Новый Assignment создаётся в Draft."))
			return
		if before.status == self.status:
			return
		if frappe.flags.get(ASSIGNMENT_TRANSITION_FLAG) != self.status:
			frappe.throw(_("Assignment transition context отсутствует."))
		if self.status not in TRANSITIONS.get(before.status, frozenset()):
			frappe.throw(_("Недопустимый Assignment transition."))

	def _validate_no_overlap(self) -> None:
		if self.status not in ACTIVE_STATUSES:
			return
		start = getdate(self.effective_from)
		end = getdate(self.effective_to) if self.effective_to else date.max
		for row in frappe.get_all(
			DOCTYPE,
			filters={
				"service_project": self.service_project,
				"status": ["in", sorted(ACTIVE_STATUSES)],
				"name": ["!=", self.name or ""],
			},
			fields=[
				"name", "execution_mode", "supplier", "employee", "project_object",
				"object_system", "work_type", "effective_from", "effective_to",
			],
		):
			if self._dimension(row) != self._dimension(self):
				continue
			other_start = getdate(row.effective_from)
			other_end = getdate(row.effective_to) if row.effective_to else date.max
			if start <= other_end and other_start <= end:
				frappe.throw(_("Assignment period пересекается с {0}.").format(row.name))

	def _freeze_after_approval(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.status == "Draft":
			return
		allowed = {
			"status", "commercial_terms", "credentials_readiness", "status_reason",
			"approved_at", "approved_by", "completed_at", "completed_by",
			"cancelled_at", "cancelled_by", "overlap_guard_key", "readiness_reason",
			"readiness_fingerprint", "readiness_confirmed_fingerprint",
			"readiness_confirmed_at", "readiness_confirmed_by",
		}
		for field in self.meta.fields:
			if field.fieldname in allowed or field.fieldtype in {"Section Break", "Column Break", "Tab Break"}:
				continue
			if self.get(field.fieldname) != before.get(field.fieldname):
				frappe.throw(_("Approved Assignment identity immutable."))


	def _derive_readiness(self) -> None:
		from contract_accounting.application.personnel_readiness import evaluate_assignment

		result = evaluate_assignment(self)
		self.credentials_readiness = result.status
		self.readiness_reason = result.reason
		self.readiness_fingerprint = result.fingerprint
		if self.readiness_confirmed_fingerprint != result.fingerprint:
			self.readiness_confirmed_fingerprint = None
			self.readiness_confirmed_at = None
			self.readiness_confirmed_by = None

	def _overlap_guard_key(self) -> str | None:
		if self.status not in ACTIVE_STATUSES:
			return None
		payload = "|".join((*self._dimension(self), str(self.effective_from), str(self.effective_to or "")))
		return hashlib.sha256(payload.encode()).hexdigest()

	@staticmethod
	def _dimension(row: object) -> tuple[str, ...]:
		get = row.get if hasattr(row, "get") else lambda field: getattr(row, field, None)
		executor = get("employee") if get("execution_mode") == "Internal" else get("supplier")
		return (
			str(get("execution_mode") or ""), str(executor or ""), str(get("project_object") or ""),
			str(get("object_system") or ""), str(get("work_type") or ""),
		)


def on_doctype_update() -> None:
	frappe.db.add_index(DOCTYPE, ["service_project", "status", "effective_from"], "ca_assignment_project_idx")
	frappe.db.add_index(DOCTYPE, ["supplier", "status"], "ca_assignment_supplier_idx")
