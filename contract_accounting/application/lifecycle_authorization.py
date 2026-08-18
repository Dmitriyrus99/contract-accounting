"""Role authorization policy for CA-01 lifecycle commands."""

from __future__ import annotations

from collections.abc import Iterable

from contract_accounting.domain.lifecycle import LifecycleTransitionError


LEGAL_COMMAND_ROLES = frozenset(
	{"System Manager", "Юрист", "Руководитель проектов", "Генеральный директор"}
)
EXECUTION_COMMAND_ROLES = frozenset(
	{"System Manager", "Руководитель проектов", "Менеджер проектов"}
)
DUAL_COMMAND_ROLES = frozenset(
	{"System Manager", "Руководитель проектов", "Генеральный директор"}
)


def allowed_roles_for_command(
	*,
	legal_requested: bool,
	execution_requested: bool,
) -> frozenset[str]:
	"""Return the exact role allowlist for one requested command shape."""

	if legal_requested and execution_requested:
		return DUAL_COMMAND_ROLES
	if legal_requested:
		return LEGAL_COMMAND_ROLES
	if execution_requested:
		return EXECUTION_COMMAND_ROLES
	raise LifecycleTransitionError(
		"a lifecycle command must request legal and/or execution transition"
	)


def is_command_allowed(
	user_roles: Iterable[str],
	*,
	legal_requested: bool,
	execution_requested: bool,
) -> bool:
	"""Check role membership without weakening document-level permissions."""

	allowed = allowed_roles_for_command(
		legal_requested=legal_requested,
		execution_requested=execution_requested,
	)
	return bool(set(user_roles).intersection(allowed))
