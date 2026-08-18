from __future__ import annotations

import unittest
from datetime import date, datetime

from contract_accounting.domain.control_center import (
	ControlCenterRuleError,
	ExceptionItem,
	age_in_days,
	risk_flag,
	sort_exceptions,
)


class TestControlCenterRules(unittest.TestCase):
	def test_exception_requires_primary_source(self) -> None:
		with self.assertRaisesRegex(ControlCenterRuleError, "source_name"):
			ExceptionItem(
				rule="Missing Source",
				title="invalid",
				severity="High",
				service_project="FSP-1",
				source_doctype="Ferum Finding",
				source_name="",
			)

	def test_sort_is_severity_age_and_source_deterministic(self) -> None:
		items = [
			ExceptionItem("Review", "Review", "High", "P1", "Visit", "V2", age_days=2),
			ExceptionItem("Review", "Review", "Critical", "P1", "Visit", "V3"),
			ExceptionItem("Review", "Review", "High", "P1", "Visit", "V1", age_days=7),
		]
		self.assertEqual(
			[item["source_name"] for item in sort_exceptions(items)],
			["V3", "V1", "V2"],
		)

	def test_risk_flag_uses_highest_severity(self) -> None:
		low = ExceptionItem("Info", "Info", "Low", "P1", "Doc", "D1")
		high = ExceptionItem("Risk", "Risk", "High", "P1", "Doc", "D2")
		critical = ExceptionItem("Stop", "Stop", "Critical", "P1", "Doc", "D3")
		self.assertEqual(risk_flag([]), "Normal")
		self.assertEqual(risk_flag([low]), "Attention")
		self.assertEqual(risk_flag([low, high]), "Attention")
		self.assertEqual(risk_flag([high, critical]), "Critical")

	def test_age_is_non_negative_for_date_and_datetime(self) -> None:
		as_of = date(2026, 8, 18)
		self.assertEqual(age_in_days(date(2026, 8, 1), as_of), 17)
		self.assertEqual(age_in_days(datetime(2026, 8, 20, 10), as_of), 0)


if __name__ == "__main__":
	unittest.main()
