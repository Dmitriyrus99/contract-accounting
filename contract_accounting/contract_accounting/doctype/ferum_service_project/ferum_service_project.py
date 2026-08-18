"""Controller for the CA-01 contract root and dual-status projection."""

from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document

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


class FerumServiceProject(Document):
	def validate(self) -> None:
		"""Reject direct lifecycle edits and validate the persisted status pair."""

		self._guard_lifecycle_fields()
		self._validate_lifecycle_projection()
		self._validate_contract_dates()

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


def on_doctype_update() -> None:
	"""One executable contract number is unique within Company and date."""

	frappe.db.add_unique(DOCTYPE, ["company", "contract_number", "contract_date"])
