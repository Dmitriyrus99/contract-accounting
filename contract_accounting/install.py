"""Idempotent install/migrate integration for standard ERPNext adapters."""

from contract_accounting.setup.custom_fields import setup_custom_fields


def _ensure_desk_home_page() -> None:
	"""Prevent completed sites from retaining Frappe's setup-wizard home page.

	Frappe deliberately omits the Desk toolbar while ``home_page`` is
	``setup-wizard``.  A newly created site can retain that default after its
	setup is complete; install and migrate must normalise this stale value.
	"""
	import frappe

	if (
		frappe.db.get_single_value("System Settings", "setup_complete")
		and frappe.db.get_default("desktop:home_page") == "setup-wizard"
	):
		frappe.db.set_default("desktop:home_page", "workspace")


def _setup_reference_data() -> None:
	from contract_accounting.setup.billing_cycle_template import (
		ensure_reference_billing_cycle_template,
	)
	from contract_accounting.setup.calendar_fixture import ensure_production_calendar_fixture
	from contract_accounting.setup.erpnext_reference_data import ensure_erpnext_reference_data
	from contract_accounting.setup.launch_template import (
		ensure_reference_launch_template,
	)

	ensure_erpnext_reference_data()
	ensure_production_calendar_fixture()
	ensure_reference_launch_template()
	ensure_reference_billing_cycle_template()


def after_install() -> None:
	setup_custom_fields()
	_ensure_desk_home_page()
	_setup_reference_data()


def before_migrate() -> None:
	setup_custom_fields()


def after_migrate() -> None:
	_ensure_desk_home_page()
	_setup_reference_data()
