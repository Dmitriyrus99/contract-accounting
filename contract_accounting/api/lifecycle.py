"""Whitelisted server commands for the CA-01 dual-status lifecycle."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import frappe
from frappe import _
from frappe.utils import cint, getdate

from contract_accounting.application.lifecycle_service import (
	apply_lifecycle_transition,
	resume_project_execution,
	suspend_project_execution,
)
from contract_accounting.application.lifecycle_authorization import (
	allowed_roles_for_command,
)
from contract_accounting.domain.lifecycle import (
	ExecutionStatus,
	LegalStatus,
	LifecycleTransitionError,
	TransitionContext,
	TransitionResult,
)
from contract_accounting.infrastructure.frappe_lifecycle import (
	SERVICE_PROJECT_DOCTYPE,
	FrappeLifecycleUnitOfWork,
)


@frappe.whitelist(methods=["POST"])
def change_status(
	service_project: str,
	target_legal_status: str | None = None,
	target_execution_status: str | None = None,
	reason: str | None = None,
	comment: str | None = None,
	effective_date: str | date | None = None,
	evidence: str | list[str] | tuple[str, ...] | None = None,
	termination_basis: str | None = None,
	related_document: str | None = None,
	documented_termination_completion_exception: int | str | bool = False,
) -> dict[str, Any]:
	"""Apply one legal/execution transition through the guarded atomic path."""

	_validate_write_access(service_project)
	try:
		allowed_roles = allowed_roles_for_command(
			legal_requested=bool(target_legal_status),
			execution_requested=bool(target_execution_status),
		)
	except LifecycleTransitionError as exc:
		frappe.throw(_("Lifecycle transition отклонён: {0}").format(str(exc)))
	_require_roles(allowed_roles)
	context = _context(
		reason=reason,
		comment=comment,
		effective_date=effective_date,
		evidence=evidence,
		termination_basis=termination_basis,
		related_document=related_document,
	)
	try:
		result = apply_lifecycle_transition(
			FrappeLifecycleUnitOfWork(frappe),
			service_project,
			context,
			target_legal_status=(
				LegalStatus(target_legal_status) if target_legal_status else None
			),
			target_execution_status=(
				ExecutionStatus(target_execution_status)
				if target_execution_status
				else None
			),
			documented_termination_completion_exception=bool(
				cint(documented_termination_completion_exception)
			),
		)
	except (LifecycleTransitionError, ValueError, KeyError) as exc:
		frappe.throw(_("Lifecycle transition отклонён: {0}").format(str(exc)))
	return _result(result)


@frappe.whitelist(methods=["POST"])
def suspend(
	service_project: str,
	reason: str,
	effective_date: str | date,
	evidence: str | list[str] | tuple[str, ...] | None = None,
	comment: str | None = None,
) -> dict[str, Any]:
	"""Suspend Launching/Active and persist its exact predecessor."""

	_validate_write_access(service_project)
	_require_roles(
		allowed_roles_for_command(legal_requested=False, execution_requested=True)
	)
	try:
		result = suspend_project_execution(
			FrappeLifecycleUnitOfWork(frappe),
			service_project,
			_context(
				reason=reason,
				comment=comment,
				effective_date=effective_date,
				evidence=evidence,
			),
		)
	except (LifecycleTransitionError, ValueError, KeyError) as exc:
		frappe.throw(_("Suspend отклонён: {0}").format(str(exc)))
	return _result(result)


@frappe.whitelist(methods=["POST"])
def resume(
	service_project: str,
	reason: str | None = None,
	comment: str | None = None,
	evidence: str | list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
	"""Resume only to the persisted Launching/Active predecessor."""

	_validate_write_access(service_project)
	_require_roles(
		allowed_roles_for_command(legal_requested=False, execution_requested=True)
	)
	try:
		result = resume_project_execution(
			FrappeLifecycleUnitOfWork(frappe),
			service_project,
			_context(reason=reason, comment=comment, evidence=evidence),
		)
	except (LifecycleTransitionError, ValueError, KeyError) as exc:
		frappe.throw(_("Resume отклонён: {0}").format(str(exc)))
	return _result(result)


def _validate_write_access(service_project: str) -> None:
	if not isinstance(service_project, str) or not service_project.strip():
		frappe.throw(_("service_project обязателен."))
	if not frappe.db.exists(SERVICE_PROJECT_DOCTYPE, service_project):
		frappe.throw(
			_("Ferum Service Project {0} не найден.").format(service_project),
			frappe.DoesNotExistError,
		)
	doc = frappe.get_doc(SERVICE_PROJECT_DOCTYPE, service_project)
	if not frappe.has_permission(SERVICE_PROJECT_DOCTYPE, ptype="write", doc=doc):
		frappe.throw(_("Недостаточно прав на Ferum Service Project."), frappe.PermissionError)


def _require_roles(allowed_roles: frozenset[str]) -> None:
	user_roles = set(frappe.get_roles(frappe.session.user))
	if not user_roles.intersection(allowed_roles):
		frappe.throw(
			_("Роль пользователя не разрешает эту lifecycle-команду."),
			frappe.PermissionError,
		)


def _context(
	*,
	reason: str | None = None,
	comment: str | None = None,
	effective_date: str | date | None = None,
	evidence: str | list[str] | tuple[str, ...] | None = None,
	termination_basis: str | None = None,
	related_document: str | None = None,
) -> TransitionContext:
	return TransitionContext(
		actor=frappe.session.user,
		occurred_at=_aware_now(),
		reason=_optional_text(reason),
		comment=_optional_text(comment),
		effective_date=getdate(effective_date) if effective_date else None,
		evidence=_evidence(evidence),
		termination_basis=_optional_text(termination_basis),
		related_document=_optional_text(related_document),
	)


def _aware_now() -> datetime:
	timezone_name = frappe.db.get_single_value("System Settings", "time_zone") or "UTC"
	try:
		timezone = ZoneInfo(timezone_name)
	except ZoneInfoNotFoundError:
		frappe.throw(_("Неизвестная системная timezone: {0}").format(timezone_name))
		raise AssertionError("frappe.throw must raise")
	return datetime.now(timezone)


def _evidence(value: str | list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
	if value is None or value == "":
		return ()
	parsed: Any = frappe.parse_json(value) if isinstance(value, str) else value
	if not isinstance(parsed, (list, tuple)):
		frappe.throw(_("evidence должен быть JSON-массивом строк."))
	items = tuple(str(item).strip() for item in parsed if str(item).strip())
	if len(items) != len(parsed):
		frappe.throw(_("evidence не может содержать пустые значения."))
	return items


def _optional_text(value: str | None) -> str | None:
	text = (value or "").strip()
	return text or None


def _result(result: TransitionResult) -> dict[str, Any]:
	return {
		"legal_status": result.state.legal_status.value,
		"execution_status": result.state.execution_status.value,
		"suspended_from_status": (
			result.state.suspended_from_status.value
			if result.state.suspended_from_status
			else None
		),
		"correlation_id": result.audit_events[0].correlation_id,
		"audit_event_count": len(result.audit_events),
	}
