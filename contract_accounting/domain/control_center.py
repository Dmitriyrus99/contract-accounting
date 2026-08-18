"""Pure ordering and risk rules for CA-10 source-linked exceptions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


class ControlCenterRuleError(ValueError):
	"""Raised when a derived exception loses its primary-source contract."""


@dataclass(frozen=True, slots=True)
class ExceptionItem:
	rule: str
	title: str
	severity: str
	service_project: str
	source_doctype: str
	source_name: str
	source_field: str | None = None
	owner: str | None = None
	age_days: int = 0
	due_at: str | None = None
	details: dict[str, object] | None = None

	def __post_init__(self) -> None:
		if self.severity not in SEVERITY_ORDER:
			raise ControlCenterRuleError(f"unsupported severity: {self.severity}")
		for label, value in (
			("rule", self.rule),
			("service_project", self.service_project),
			("source_doctype", self.source_doctype),
			("source_name", self.source_name),
		):
			if not str(value or "").strip():
				raise ControlCenterRuleError(f"{label} is required")
		if self.age_days < 0:
			raise ControlCenterRuleError("age_days cannot be negative")

	@property
	def source_key(self) -> str:
		field = f":{self.source_field}" if self.source_field else ""
		return f"{self.source_doctype}:{self.source_name}{field}"

	def as_dict(self) -> dict[str, object]:
		result = asdict(self)
		result["source_key"] = self.source_key
		result["drilldown"] = {
			"doctype": self.source_doctype,
			"name": self.source_name,
		}
		return result


def sort_exceptions(items: list[ExceptionItem]) -> list[dict[str, object]]:
	"""Order intervention work deterministically by severity, age and source."""

	return [
		item.as_dict()
		for item in sorted(
			items,
			key=lambda item: (
				SEVERITY_ORDER[item.severity],
				-item.age_days,
				item.rule,
				item.source_key,
			),
		)
	]


def risk_flag(items: list[ExceptionItem]) -> str:
	if any(item.severity == "Critical" for item in items):
		return "Critical"
	if items:
		return "Attention"
	return "Normal"


def age_in_days(value: date | datetime, as_of: date) -> int:
	start = value.date() if isinstance(value, datetime) else value
	return max((as_of - start).days, 0)
