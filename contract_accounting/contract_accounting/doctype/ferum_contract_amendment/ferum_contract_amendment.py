"""Effective-dated, append-only amendment of Service Project contract terms."""

from __future__ import annotations

import json
from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate, now_datetime

DOCTYPE: Final[str] = "Ferum Contract Amendment"
PROJECT_DOCTYPE: Final[str] = "Ferum Service Project"
CONTRACT_AMENDMENT_APPLY_FLAG: Final[str] = "contract_accounting_amendment_apply"

STATE_DRAFT: Final[str] = "Draft"
STATE_UNDER_REVIEW: Final[str] = "Under Review"
STATE_APPROVED: Final[str] = "Approved"
STATE_APPLIED: Final[str] = "Applied"
STATE_REJECTED: Final[str] = "Rejected"
TERMINAL_STATES: Final[frozenset[str]] = frozenset({STATE_APPLIED, STATE_REJECTED})

TRANSITIONS: Final[dict[str, frozenset[str]]] = {
	STATE_DRAFT: frozenset({STATE_UNDER_REVIEW}),
	STATE_UNDER_REVIEW: frozenset({STATE_APPROVED, STATE_REJECTED}),
	STATE_APPROVED: frozenset({STATE_APPLIED}),
	STATE_APPLIED: frozenset(),
	STATE_REJECTED: frozenset(),
}
TRANSITION_ROLES: Final[dict[tuple[str, str], frozenset[str]]] = {
	(STATE_DRAFT, STATE_UNDER_REVIEW): frozenset({"Юрист", "System Manager"}),
	(STATE_UNDER_REVIEW, STATE_APPROVED): frozenset(
		{"Генеральный директор", "System Manager"}
	),
	(STATE_UNDER_REVIEW, STATE_REJECTED): frozenset(
		{"Генеральный директор", "System Manager"}
	),
	(STATE_APPROVED, STATE_APPLIED): frozenset({"Генеральный директор", "System Manager"}),
}

AMENDABLE_PROJECT_FIELDS: Final[frozenset[str]] = frozenset(
	{
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
	}
)

_FROZEN_FIELDS: Final[tuple[str, ...]] = (
	"service_project",
	"amendment_number",
	"amendment_date",
	"effective_from",
	"change_type",
	"source_document_reference",
	"changes",
	"comment",
)


class FerumContractAmendment(Document):
	def validate(self) -> None:
		self._validate_dates()
		self._validate_transition()
		self._validate_changes()
		self._freeze_terminal_record()

	def on_update(self) -> None:
		before = self.get_doc_before_save()
		if (
			before is not None
			and before.get("approval_status") == STATE_APPROVED
			and self.get("approval_status") == STATE_APPLIED
		):
			self._apply_to_service_project()

	def on_trash(self) -> None:
		if self.get("approval_status") != STATE_DRAFT:
			frappe.throw(_("Удаление Amendment разрешено только в Draft."), frappe.PermissionError)

	def _validate_dates(self) -> None:
		if self.get("amendment_date") and self.get("effective_from"):
			if getdate(self.effective_from) < getdate(self.amendment_date):
				frappe.throw(_("effective_from не может быть раньше amendment_date."))

	def _validate_transition(self) -> None:
		before = self.get_doc_before_save()
		if before is None:
			if self.get("approval_status") != STATE_DRAFT:
				frappe.throw(_("Новый Amendment создаётся только в Draft."))
			return
		old = before.get("approval_status")
		new = self.get("approval_status")
		if old != new and new not in TRANSITIONS.get(old, frozenset()):
			frappe.throw(_("Недопустимый Amendment transition: {0} → {1}.").format(old, new))
		if old != new and frappe.session.user != "Administrator":
			allowed_roles = TRANSITION_ROLES.get((old, new), frozenset())
			if not set(frappe.get_roles(frappe.session.user)).intersection(allowed_roles):
				frappe.throw(
					_("Недостаточно прав для Amendment transition {0} → {1}.").format(old, new),
					frappe.PermissionError,
				)

	def _validate_changes(self) -> None:
		if self.get("approval_status") in {STATE_APPROVED, STATE_APPLIED} and not self.get("changes"):
			frappe.throw(_("Approved/Applied Amendment должен содержать change rows."))
		seen: set[str] = set()
		for row in self.get("changes") or []:
			fieldname = (row.get("fieldname") or "").strip()
			if fieldname not in AMENDABLE_PROJECT_FIELDS:
				frappe.throw(_("Поле {0} не входит в Amendment allowlist.").format(fieldname))
			if fieldname in seen:
				frappe.throw(_("Поле {0} повторяется в Amendment.").format(fieldname))
			seen.add(fieldname)
			try:
				json.loads(row.get("old_value_json") or "null")
				json.loads(row.get("new_value_json") or "null")
			except json.JSONDecodeError as exc:
				frappe.throw(_("Old/New value должны быть валидным JSON: {0}.").format(str(exc)))

	def _freeze_terminal_record(self) -> None:
		before = self.get_doc_before_save()
		if before is None or before.get("approval_status") not in TERMINAL_STATES:
			return
		changed = [field for field in _FROZEN_FIELDS if self.get(field) != before.get(field)]
		if changed or self.get("approval_status") != before.get("approval_status"):
			frappe.throw(_("Терминальный Amendment неизменяем; создайте новую запись."))

	def _apply_to_service_project(self) -> None:
		project = frappe.get_doc(PROJECT_DOCTYPE, self.service_project)
		before_snapshot: dict[str, object] = {}
		after_snapshot: dict[str, object] = {}
		for row in self.get("changes") or []:
			fieldname = row.fieldname
			current = project.get(fieldname)
			expected = json.loads(row.old_value_json or "null")
			if _json_value(current) != expected:
				frappe.throw(
					_("Amendment conflict: {0} уже изменено ({1} != {2}).").format(
						fieldname, _json_value(current), expected
					)
				)
			before_snapshot[fieldname] = _json_value(current)
			new_value = json.loads(row.new_value_json or "null")
			project.set(fieldname, new_value)
			after_snapshot[fieldname] = new_value

		previous = frappe.flags.get(CONTRACT_AMENDMENT_APPLY_FLAG)
		frappe.flags[CONTRACT_AMENDMENT_APPLY_FLAG] = True
		try:
			project.save(ignore_permissions=True)
		finally:
			frappe.flags[CONTRACT_AMENDMENT_APPLY_FLAG] = previous

		self.db_set(
			"before_snapshot_json",
			json.dumps(before_snapshot, ensure_ascii=False, sort_keys=True),
			update_modified=False,
		)
		self.db_set(
			"after_snapshot_json",
			json.dumps(after_snapshot, ensure_ascii=False, sort_keys=True),
			update_modified=False,
		)
		self.db_set("applied_at", get_datetime(now_datetime()), update_modified=False)
		self.db_set("applied_by", frappe.session.user, update_modified=False)


def _json_value(value: object) -> object:
	if hasattr(value, "isoformat"):
		return value.isoformat()  # type: ignore[union-attr]
	return value


def on_doctype_update() -> None:
	frappe.db.add_unique(DOCTYPE, ["service_project", "amendment_number"])
	frappe.db.add_index(DOCTYPE, ["service_project", "approval_status"])
