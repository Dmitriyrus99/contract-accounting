"""Idempotent install/migrate integration for standard ERPNext adapters."""

from contract_accounting.setup.custom_fields import setup_custom_fields


def _setup_reference_data() -> None:
	from contract_accounting.setup.launch_template import ensure_reference_launch_template

	ensure_reference_launch_template()


def after_install() -> None:
	setup_custom_fields()
	_setup_reference_data()


def before_migrate() -> None:
	setup_custom_fields()


def after_migrate() -> None:
	_setup_reference_data()
