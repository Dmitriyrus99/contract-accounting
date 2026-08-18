from __future__ import annotations

import unittest

from contract_accounting.application.lifecycle_authorization import (
	DUAL_COMMAND_ROLES,
	EXECUTION_COMMAND_ROLES,
	LEGAL_COMMAND_ROLES,
	allowed_roles_for_command,
	is_command_allowed,
)
from contract_accounting.domain.lifecycle import LifecycleTransitionError


class TestLifecycleAuthorization(unittest.TestCase):
	def test_exact_legal_command_roles(self) -> None:
		self.assertEqual(
			LEGAL_COMMAND_ROLES,
			{
				"System Manager",
				"Юрист",
				"Руководитель проектов",
				"Генеральный директор",
			},
		)
		self.assertTrue(
			is_command_allowed(
				["Юрист"], legal_requested=True, execution_requested=False
			)
		)
		self.assertFalse(
			is_command_allowed(
				["Менеджер проектов"],
				legal_requested=True,
				execution_requested=False,
			)
		)

	def test_exact_execution_command_roles(self) -> None:
		self.assertEqual(
			EXECUTION_COMMAND_ROLES,
			{"System Manager", "Руководитель проектов", "Менеджер проектов"},
		)
		self.assertTrue(
			is_command_allowed(
				["Менеджер проектов"],
				legal_requested=False,
				execution_requested=True,
			)
		)
		self.assertFalse(
			is_command_allowed(
				["Юрист"], legal_requested=False, execution_requested=True
			)
		)

	def test_dual_axis_command_uses_narrow_allowlist(self) -> None:
		self.assertEqual(
			DUAL_COMMAND_ROLES,
			{"System Manager", "Руководитель проектов", "Генеральный директор"},
		)
		for denied_role in ("Юрист", "Менеджер проектов", "Бухгалтер"):
			with self.subTest(role=denied_role):
				self.assertFalse(
					is_command_allowed(
						[denied_role],
						legal_requested=True,
						execution_requested=True,
					)
				)

	def test_system_manager_is_allowed_for_every_command_shape(self) -> None:
		for legal_requested, execution_requested in ((True, False), (False, True), (True, True)):
			with self.subTest(
				legal=legal_requested,
				execution=execution_requested,
			):
				self.assertTrue(
					is_command_allowed(
						["System Manager"],
						legal_requested=legal_requested,
						execution_requested=execution_requested,
					)
				)

	def test_empty_command_shape_is_rejected(self) -> None:
		with self.assertRaises(LifecycleTransitionError):
			allowed_roles_for_command(
				legal_requested=False,
				execution_requested=False,
			)


if __name__ == "__main__":
	unittest.main()
