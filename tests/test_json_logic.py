from __future__ import annotations

import unittest

from contract_accounting.domain.json_logic import (
	JsonLogicRuleError,
	evaluate_rule,
	validate_rule,
)


class JsonLogicTests(unittest.TestCase):
	def test_allowlisted_rule_is_deterministic(self) -> None:
		rule = {
			"and": [
				{"==": [{"var": "project.execution_status"}, "Launching"]},
				{"==": [{"var": "requirement.applicability"}, "Applicable"]},
			]
		}
		context = {
			"project": {"execution_status": "Launching"},
			"requirement": {"applicability": "Applicable"},
		}
		self.assertIs(evaluate_rule(rule, context), True)

	def test_unknown_operator_and_variable_fail_closed(self) -> None:
		with self.assertRaises(JsonLogicRuleError):
			validate_rule({"python": "__import__('os')"})
		with self.assertRaises(JsonLogicRuleError):
			validate_rule({"var": "user.password"})

	def test_missing_context_is_not_treated_as_false(self) -> None:
		with self.assertRaises(JsonLogicRuleError):
			evaluate_rule({"var": "project.unknown"}, {"project": {}})

	def test_nested_multi_operator_object_is_rejected(self) -> None:
		with self.assertRaises(JsonLogicRuleError):
			validate_rule({"==": [1, 1], "or": [True, False]})


if __name__ == "__main__":
	unittest.main()
