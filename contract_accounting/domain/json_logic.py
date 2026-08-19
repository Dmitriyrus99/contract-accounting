"""Small fail-closed JSON Logic subset for CA-11 activation and gate rules."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final


class JsonLogicRuleError(ValueError):
	"""Raised when a rule leaves the approved deterministic subset."""


ALLOWED_OPERATORS: Final[frozenset[str]] = frozenset(
	{"and", "or", "!", "==", "!=", ">", ">=", "<", "<=", "in", "var"}
)
ALLOWED_VARIABLE_PREFIXES: Final[tuple[str, ...]] = (
	"project.",
	"requirement.",
	"step.",
	"gate.",
)
MAX_DEPTH: Final[int] = 12


def validate_rule(rule: object, *, depth: int = 0) -> None:
	"""Validate one expression without executing source text or Python code."""

	if depth > MAX_DEPTH:
		raise JsonLogicRuleError("rule nesting exceeds the approved limit")
	if rule in (None, True, False) or isinstance(rule, (str, int, float)):
		return
	if isinstance(rule, list):
		for item in rule:
			validate_rule(item, depth=depth + 1)
		return
	if not isinstance(rule, Mapping) or len(rule) != 1:
		raise JsonLogicRuleError("rule must be a single-operator JSON object")
	operator, arguments = next(iter(rule.items()))
	if operator not in ALLOWED_OPERATORS:
		raise JsonLogicRuleError(f"operator is not allowed: {operator}")
	if operator == "var":
		if not isinstance(arguments, str) or not arguments.startswith(
			ALLOWED_VARIABLE_PREFIXES
		):
			raise JsonLogicRuleError(f"variable is not allowed: {arguments}")
		return
	validate_rule(arguments, depth=depth + 1)


def evaluate_rule(rule: object, context: Mapping[str, object]) -> Any:
	"""Evaluate only the validated allowlist; no eval/exec or attribute access."""

	validate_rule(rule)
	if rule is None:
		return True
	if isinstance(rule, (str, int, float, bool)):
		return rule
	if isinstance(rule, list):
		return [evaluate_rule(item, context) for item in rule]
	if not isinstance(rule, Mapping):
		raise JsonLogicRuleError("validated rule is not a JSON object")
	operator, raw_arguments = next(iter(rule.items()))
	if operator == "var":
		return _resolve(str(raw_arguments), context)
	arguments = raw_arguments if isinstance(raw_arguments, list) else [raw_arguments]
	values = [evaluate_rule(item, context) for item in arguments]
	if operator == "and":
		return all(bool(item) for item in values)
	if operator == "or":
		return any(bool(item) for item in values)
	if operator == "!":
		_require_arity(operator, values, 1)
		return not bool(values[0])
	if operator == "in":
		_require_arity(operator, values, 2)
		try:
			return values[0] in values[1]
		except TypeError as exc:
			raise JsonLogicRuleError("right operand of in is not a container") from exc
	_require_arity(operator, values, 2)
	left, right = values
	try:
		if operator == "==":
			return left == right
		if operator == "!=":
			return left != right
		if operator == ">":
			return left > right
		if operator == ">=":
			return left >= right
		if operator == "<":
			return left < right
		return left <= right
	except TypeError as exc:
		raise JsonLogicRuleError(f"incompatible operands for {operator}") from exc


def _resolve(path: str, context: Mapping[str, object]) -> object:
	current: object = context
	for segment in path.split("."):
		if not isinstance(current, Mapping) or segment not in current:
			raise JsonLogicRuleError(f"variable is absent from context: {path}")
		current = current[segment]
	return current


def _require_arity(operator: str, values: list[Any], expected: int) -> None:
	if len(values) != expected:
		raise JsonLogicRuleError(
			f"operator {operator} requires {expected} arguments, got {len(values)}"
		)
