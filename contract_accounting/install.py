"""Idempotent install/migrate integration for standard ERPNext adapters."""

from contract_accounting.setup.custom_fields import setup_custom_fields


def after_install() -> None:
	setup_custom_fields()


def before_migrate() -> None:
	setup_custom_fields()
