from __future__ import annotations

import unittest
from copy import deepcopy
from datetime import date, datetime, timezone
from typing import Any

from contract_accounting.application.lifecycle_service import apply_lifecycle_transition
from contract_accounting.domain.lifecycle import (
	ExecutionStatus,
	LegalStatus,
	LifecycleState,
	TransitionContext,
)
from contract_accounting.infrastructure.frappe_lifecycle import (
	LIFECYCLE_AUDIT_DOCTYPE,
	LIFECYCLE_AUDIT_WRITER_FLAG,
	LIFECYCLE_WRITE_FLAG,
	SERVICE_PROJECT_DOCTYPE,
	FrappeLifecycleUnitOfWork,
)


PROJECT = "FSP-2026-00001"
NOW = datetime(2026, 8, 18, 8, 0, tzinfo=timezone.utc)


class FakeDatabase:
	def __init__(self, runtime: FakeFrappe) -> None:
		self.runtime = runtime
		self.save_points: dict[str, tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]] = {}
		self.lock_calls: list[tuple[str, str]] = []

	def savepoint(self, save_point: str) -> None:
		self.save_points[save_point] = (
			deepcopy(self.runtime.projects),
			deepcopy(self.runtime.audit_rows),
		)

	def rollback(self, *, save_point: str) -> None:
		projects, audit_rows = self.save_points[save_point]
		self.runtime.projects = projects
		self.runtime.audit_rows = audit_rows

	def get_value(
		self,
		doctype: str,
		name: str,
		fieldname: tuple[str, ...],
		*,
		as_dict: bool,
		for_update: bool,
	) -> dict[str, Any] | None:
		self.assert_contract(doctype, as_dict, for_update)
		self.lock_calls.append((doctype, name))
		row = self.runtime.projects.get(name)
		return {field: row.get(field) for field in fieldname} if row else None

	def assert_contract(self, doctype: str, as_dict: bool, for_update: bool) -> None:
		if doctype != SERVICE_PROJECT_DOCTYPE or not as_dict or not for_update:
			raise AssertionError("adapter must load Service Project as_dict under for_update lock")


class FakeProjectDocument:
	def __init__(self, runtime: FakeFrappe, name: str) -> None:
		self.runtime = runtime
		self.name = name
		for field, value in runtime.projects[name].items():
			setattr(self, field, value)

	def save(self, *, ignore_permissions: bool) -> None:
		if not ignore_permissions or not self.runtime.flags.get(LIFECYCLE_WRITE_FLAG):
			raise AssertionError("state write must use the guarded server path")
		self.runtime.projects[self.name] = {
			"legal_status": self.legal_status,
			"execution_status": self.execution_status,
			"suspended_from_status": self.suspended_from_status,
			"documented_termination_completion_exception": (
				self.documented_termination_completion_exception
			),
		}


class FakeAuditDocument:
	def __init__(self, runtime: FakeFrappe) -> None:
		self.runtime = runtime

	def insert(self, *, ignore_permissions: bool) -> None:
		if not ignore_permissions or not self.runtime.flags.get(LIFECYCLE_AUDIT_WRITER_FLAG):
			raise AssertionError("audit insert must use the dedicated writer flag")
		if self.runtime.fail_audit:
			raise RuntimeError("simulated Frappe audit failure")
		self.runtime.audit_rows.append(
			{
				key: value
				for key, value in vars(self).items()
				if key != "runtime"
			}
		)


class FakeFrappe:
	def __init__(self, state: LifecycleState) -> None:
		self.projects = {
			PROJECT: {
				"legal_status": state.legal_status.value,
				"execution_status": state.execution_status.value,
				"suspended_from_status": (
					state.suspended_from_status.value if state.suspended_from_status else None
				),
				"documented_termination_completion_exception": int(
					state.documented_termination_completion_exception
				),
			}
		}
		self.audit_rows: list[dict[str, Any]] = []
		self.flags: dict[str, Any] = {}
		self.fail_audit = False
		self.db = FakeDatabase(self)

	def get_doc(self, doctype: str, name: str) -> FakeProjectDocument:
		self.assert_doctype(doctype, SERVICE_PROJECT_DOCTYPE)
		return FakeProjectDocument(self, name)

	def new_doc(self, doctype: str) -> FakeAuditDocument:
		self.assert_doctype(doctype, LIFECYCLE_AUDIT_DOCTYPE)
		return FakeAuditDocument(self)

	def assert_doctype(self, actual: str, expected: str) -> None:
		if actual != expected:
			raise AssertionError(f"expected {expected}, got {actual}")


def context(**overrides: object) -> TransitionContext:
	values: dict[str, object] = {
		"actor": "test.user@example.com",
		"occurred_at": NOW,
		"correlation_id": "corr-frappe-001",
	}
	values.update(overrides)
	return TransitionContext(**values)  # type: ignore[arg-type]


class TestFrappeLifecycleAdapter(unittest.TestCase):
	def test_atomic_command_uses_lock_guarded_save_and_typed_audit(self) -> None:
		runtime = FakeFrappe(LifecycleState())
		result = apply_lifecycle_transition(
			FrappeLifecycleUnitOfWork(runtime),
			PROJECT,
			context(
				reason="Tender withdrawn",
				comment="Agreement was not concluded",
				effective_date=date(2026, 8, 18),
				evidence=("Project Document/CANCEL-0001",),
			),
			target_legal_status=LegalStatus.CANCELLED,
			target_execution_status=ExecutionStatus.STOPPED,
		)
		self.assertEqual(runtime.db.lock_calls, [(SERVICE_PROJECT_DOCTYPE, PROJECT)])
		self.assertEqual(runtime.projects[PROJECT]["legal_status"], "Cancelled")
		self.assertEqual(runtime.projects[PROJECT]["execution_status"], "Stopped")
		self.assertEqual(len(runtime.audit_rows), 2)
		self.assertEqual(
			{row["correlation_id"] for row in runtime.audit_rows},
			{"corr-frappe-001"},
		)
		self.assertEqual(
			{row["occurred_at"] for row in runtime.audit_rows},
			{NOW.replace(tzinfo=None)},
		)
		self.assertEqual(result.state.legal_status, LegalStatus.CANCELLED)
		self.assertIsNone(runtime.flags.get(LIFECYCLE_WRITE_FLAG))
		self.assertIsNone(runtime.flags.get(LIFECYCLE_AUDIT_WRITER_FLAG))

	def test_audit_failure_rolls_back_frappe_document_save(self) -> None:
		initial = LifecycleState()
		runtime = FakeFrappe(initial)
		runtime.fail_audit = True
		with self.assertRaisesRegex(RuntimeError, "Frappe audit failure"):
			apply_lifecycle_transition(
				FrappeLifecycleUnitOfWork(runtime),
				PROJECT,
				context(),
				target_legal_status=LegalStatus.ON_APPROVAL,
			)
		self.assertEqual(runtime.projects[PROJECT]["legal_status"], "Draft")
		self.assertEqual(runtime.audit_rows, [])

	def test_adapter_rejects_calls_outside_unit_of_work(self) -> None:
		runtime = FakeFrappe(LifecycleState())
		uow = FrappeLifecycleUnitOfWork(runtime)
		with self.assertRaisesRegex(RuntimeError, "active unit of work"):
			uow.lock_state(PROJECT)

	def test_missing_project_fails_closed(self) -> None:
		runtime = FakeFrappe(LifecycleState())
		del runtime.projects[PROJECT]
		with self.assertRaisesRegex(KeyError, PROJECT):
			apply_lifecycle_transition(
				FrappeLifecycleUnitOfWork(runtime),
				PROJECT,
				context(),
				target_legal_status=LegalStatus.ON_APPROVAL,
			)


if __name__ == "__main__":
	unittest.main()
