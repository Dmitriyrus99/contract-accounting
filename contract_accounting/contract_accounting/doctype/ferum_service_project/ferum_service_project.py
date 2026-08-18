"""Controller for the CA-01 contract root and dual-status projection."""

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from contract_accounting.domain.lifecycle import (
	ExecutionStatus,
	LegalStatus,
	LifecycleState,
	LifecycleTransitionError,
)
from contract_accounting.infrastructure.frappe_lifecycle import LIFECYCLE_WRITE_FLAG


DOCTYPE: Final[str] = "Ferum Service Project"
_LIFECYCLE_FIELDS: Final[tuple[str, ...]] = (
	"legal_status",
	"execution_status",
	"suspended_from_status",
	"documented_termination_completion_exception",
)
CONTRACT_AMENDMENT_APPLY_FLAG: Final[str] = "contract_accounting_amendment_apply"
_AMENDMENT_CONTROLLED_FIELDS: Final[tuple[str, ...]] = (
	"effective_from",
	"effective_to",
	"contract_amount_with_vat",
	"contract_amount_without_vat",
	"vat_amount",
	"payment_terms",
	"payment_due_days",
	"performance_security_percent",
	"quality_guarantee_terms",
	"source_advance",
	"financial_plan",
)
_FROZEN_LEGAL_STATUSES: Final[frozenset[str]] = frozenset(
	{
		LegalStatus.SIGNED.value,
		LegalStatus.IN_FORCE.value,
		LegalStatus.CANCELLED.value,
		LegalStatus.TERMINATED.value,
		LegalStatus.EXPIRED.value,
	}
)


class FerumServiceProject(Document):
	def validate(self) -> None:
		"""Reject direct lifecycle edits and validate the persisted status pair."""

		self._guard_lifecycle_fields()
		self._guard_signed_contract_terms()
		self._validate_lifecycle_projection()
		self._validate_contract_dates()
		self._validate_financial_plan()

	def _guard_lifecycle_fields(self) -> None:
		if frappe.flags.get(LIFECYCLE_WRITE_FLAG):
			return
		if self.is_new():
			if any(
				(
					self.get("legal_status") != LegalStatus.DRAFT.value,
					self.get("execution_status") != ExecutionStatus.NOT_STARTED.value,
					bool(self.get("suspended_from_status")),
					bool(self.get("documented_termination_completion_exception")),
				)
			):
				frappe.throw(
					_(
						"Ferum Service Project создаётся только в состоянии "
						"Draft + Not Started; lifecycle меняют server-side команды CA-01."
					)
				)
			return
		if any(self.has_value_changed(fieldname) for fieldname in _LIFECYCLE_FIELDS):
			frappe.throw(
				_(
					"Поля legal_status/execution_status изменяются только server-side "
					"командами CA-01; прямая правка запрещена."
			)
		)

	def _validate_lifecycle_projection(self) -> None:
		try:
			LifecycleState(
				legal_status=LegalStatus(self.get("legal_status")),
				execution_status=ExecutionStatus(self.get("execution_status")),
				suspended_from_status=(
					ExecutionStatus(self.get("suspended_from_status"))
					if self.get("suspended_from_status")
					else None
				),
				documented_termination_completion_exception=bool(
					self.get("documented_termination_completion_exception")
				),
			)
		except (LifecycleTransitionError, ValueError) as exc:
			frappe.throw(_("Недопустимая lifecycle-проекция: {0}").format(str(exc)))

	def _validate_contract_dates(self) -> None:
		if self.get("effective_from") and self.get("effective_to"):
			if self.effective_from > self.effective_to:
				frappe.throw(_("effective_from не может быть позже effective_to."))

	def _guard_signed_contract_terms(self) -> None:
		if self.is_new() or frappe.flags.get(CONTRACT_AMENDMENT_APPLY_FLAG):
			return
		before = self.get_doc_before_save()
		if before is None or before.get("legal_status") not in _FROZEN_LEGAL_STATUSES:
			return
		changed = [
			fieldname
			for fieldname in _AMENDMENT_CONTROLLED_FIELDS
			if self.has_value_changed(fieldname)
		]
		if changed:
			frappe.throw(
				_("После Signed/In Force условия меняются только Amendment: {0}.").format(
					", ".join(changed)
				)
			)

	def _validate_financial_plan(self) -> None:
		for row in self.get("financial_plan") or []:
			if row.period_start and row.period_end:
				if getdate(row.period_start) > getdate(row.period_end):
					frappe.throw(_("Financial Plan: period_start позже period_end."))
			if row.currency != self.currency:
				frappe.throw(_("Financial Plan currency должна совпадать с валютой договора."))
			for fieldname in (
				"revenue_plan",
				"cost_plan",
				"cash_in_plan",
				"cash_out_plan",
				"tax_plan",
			):
				if flt(row.get(fieldname)) < 0:
					frappe.throw(_("Financial Plan: {0} не может быть отрицательным.").format(fieldname))
			if row.source_stage:
				stage_project = frappe.db.get_value(
					"Ferum Contract Execution Stage", row.source_stage, "service_project"
				)
				if stage_project != self.name:
					frappe.throw(_("Financial Plan source_stage относится к другому договору."))
			if row.contract_amendment:
				amendment_project = frappe.db.get_value(
					"Ferum Contract Amendment", row.contract_amendment, "service_project"
				)
				if amendment_project != self.name:
					frappe.throw(_("Financial Plan Amendment относится к другому договору."))


def on_doctype_update() -> None:
	"""One executable contract number is unique within Company and date."""

	frappe.db.add_unique(DOCTYPE, ["company", "contract_number", "contract_date"])
