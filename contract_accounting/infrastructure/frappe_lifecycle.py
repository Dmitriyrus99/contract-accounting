"""Frappe v15 persistence adapter for the CA-01 lifecycle application service.

The module has no top-level Frappe import. Production code passes the imported
``frappe`` module to :class:`FrappeLifecycleUnitOfWork`; unit tests use a small
compatible fake. This keeps domain and transaction tests runnable outside bench.
"""

from __future__ import annotations

import json
from types import TracebackType
from typing import Any, Protocol, Self
from uuid import uuid4

from contract_accounting.domain.lifecycle import (
	ExecutionStatus,
	LegalStatus,
	LifecycleAuditEvent,
	LifecycleState,
)

SERVICE_PROJECT_DOCTYPE = "Ferum Service Project"
LIFECYCLE_AUDIT_DOCTYPE = "Ferum Lifecycle Audit Event"
LIFECYCLE_WRITE_FLAG = "contract_accounting_lifecycle_write"
LIFECYCLE_AUDIT_WRITER_FLAG = "contract_accounting_lifecycle_audit_writer"

_STATE_FIELDS = (
	"legal_status",
	"execution_status",
	"suspended_from_status",
	"documented_termination_completion_exception",
)


class _DatabasePort(Protocol):
	def savepoint(self, save_point: str) -> None: ...

	def rollback(self, *, save_point: str) -> None: ...

	def get_value(
		self,
		doctype: str,
		name: str,
		fieldname: tuple[str, ...],
		*,
		as_dict: bool,
		for_update: bool,
	) -> Any: ...


class _FrappePort(Protocol):
	db: _DatabasePort
	flags: Any

	def get_doc(self, doctype: str, name: str) -> Any: ...

	def new_doc(self, doctype: str) -> Any: ...


class FrappeLifecycleUnitOfWork:
	"""Savepoint-backed Frappe implementation of ``LifecycleUnitOfWork``.

	The adapter intentionally does not commit. Frappe owns the outer request/job
	transaction. A failure rolls this command back to its private savepoint and is
	re-raised so the caller cannot mistake a partial write for success.
	"""

	def __init__(self, frappe_module: _FrappePort) -> None:
		self._frappe = frappe_module
		self._save_point: str | None = None

	def __enter__(self) -> Self:
		if self._save_point is not None:
			raise RuntimeError("Lifecycle unit of work is already active")
		self._save_point = f"ca_lifecycle_{uuid4().hex}"
		self._frappe.db.savepoint(self._save_point)
		return self

	def __exit__(
		self,
		exc_type: type[BaseException] | None,
		exc_value: BaseException | None,
		traceback: TracebackType | None,
	) -> bool | None:
		try:
			if exc_type is not None and self._save_point is not None:
				self._frappe.db.rollback(save_point=self._save_point)
		finally:
			self._save_point = None
		return None

	def lock_state(self, service_project: str) -> LifecycleState:
		self._require_active()
		row = self._frappe.db.get_value(
			SERVICE_PROJECT_DOCTYPE,
			service_project,
			_STATE_FIELDS,
			as_dict=True,
			for_update=True,
		)
		if not row:
			raise KeyError(f"{SERVICE_PROJECT_DOCTYPE} {service_project} does not exist")
		return LifecycleState(
			legal_status=LegalStatus(row["legal_status"]),
			execution_status=ExecutionStatus(row["execution_status"]),
			suspended_from_status=(
				ExecutionStatus(row["suspended_from_status"])
				if row.get("suspended_from_status")
				else None
			),
			documented_termination_completion_exception=bool(
				row.get("documented_termination_completion_exception")
			),
		)

	def save_state(self, service_project: str, state: LifecycleState) -> None:
		self._require_active()
		doc = self._frappe.get_doc(SERVICE_PROJECT_DOCTYPE, service_project)
		doc.legal_status = state.legal_status.value
		doc.execution_status = state.execution_status.value
		doc.suspended_from_status = (
			state.suspended_from_status.value if state.suspended_from_status else None
		)
		doc.documented_termination_completion_exception = int(
			state.documented_termination_completion_exception
		)
		previous = self._frappe.flags.get(LIFECYCLE_WRITE_FLAG)
		self._frappe.flags[LIFECYCLE_WRITE_FLAG] = True
		try:
			doc.save(ignore_permissions=True)
		finally:
			self._frappe.flags[LIFECYCLE_WRITE_FLAG] = previous

	def append_audit_events(
		self,
		service_project: str,
		events: tuple[LifecycleAuditEvent, ...],
	) -> None:
		self._require_active()
		for event in events:
			doc = self._frappe.new_doc(LIFECYCLE_AUDIT_DOCTYPE)
			doc.service_project = service_project
			doc.dimension = event.dimension
			doc.from_status = event.from_status
			doc.to_status = event.to_status
			doc.actor = event.actor
			# Frappe stores Datetime values as naive values in the site timezone.
			# The API creates this aware timestamp in that same site timezone; keep
			# the displayed wall time while removing the unsupported SQL offset.
			doc.occurred_at = event.occurred_at.replace(tzinfo=None)
			doc.reason = event.reason
			doc.comment = event.comment
			doc.effective_date = event.effective_date
			doc.evidence_json = json.dumps(
				event.evidence,
				ensure_ascii=False,
				default=str,
			)
			doc.termination_basis = event.termination_basis
			doc.related_document = event.related_document
			doc.documented_termination_completion_exception = int(
				event.documented_termination_completion_exception
			)
			doc.correlation_id = event.correlation_id
			previous = self._frappe.flags.get(LIFECYCLE_AUDIT_WRITER_FLAG)
			self._frappe.flags[LIFECYCLE_AUDIT_WRITER_FLAG] = True
			try:
				doc.insert(ignore_permissions=True)
			finally:
				self._frappe.flags[LIFECYCLE_AUDIT_WRITER_FLAG] = previous

	def _require_active(self) -> None:
		if self._save_point is None:
			raise RuntimeError("Lifecycle persistence requires an active unit of work")
