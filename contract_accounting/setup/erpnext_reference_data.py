"""Idempotent ERPNext reference rows required by Contract Accounting."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.contacts.doctype.address_template.address_template import (
    get_default_address_template,
)
from frappe.geo.doctype.country.country import import_country_and_currency
from frappe.utils import add_months, getdate, today


def ensure_erpnext_reference_data() -> None:
    """Install the minimal ERPNext masters used by tests and demo bootstrap."""

    ensure_system_timezone("Europe/Moscow")
    if not frappe.db.exists("Country", "Russia"):
        import_country_and_currency()
    if not frappe.db.exists("Country", "Russia"):
        frappe.get_doc(
            {
                "doctype": "Country",
                "country_name": "Russia",
                "code": "RU",
                "date_format": "dd.mm.yyyy",
                "time_format": "HH:mm:ss",
                "time_zones": "Europe/Moscow",
            }
        ).insert(ignore_permissions=True)
    _validate_country()
    ensure_address_template("Russia")
    ensure_field_named("Gender", "gender", "Male")
    ensure_root("Territory", "territory_name", "All Territories")
    ensure_leaf("Territory", "territory_name", "Russia")
    ensure_leaf("Customer Group", "customer_group_name", "Commercial")
    ensure_root("Supplier Group", "supplier_group_name", "All Supplier Groups")
    ensure_leaf("Supplier Group", "supplier_group_name", "Services")
    ensure_root("Item Group", "item_group_name", "All Item Groups")
    ensure_uom("Nos", must_be_whole_number=1)
    ensure_price_list("Standard Selling", currency="RUB", selling=1)
    ensure_fiscal_year_for(getdate(today()))
    ensure_fiscal_year_for(add_months(getdate(today()), 1))
    ensure_prompt_named("Warehouse Type", "Transit")


def ensure_system_timezone(timezone: str) -> None:
    current = frappe.db.get_single_value("System Settings", "time_zone")
    if not current:
        frappe.db.set_single_value("System Settings", "time_zone", timezone)
        return
    if current != timezone:
        frappe.throw(
            _("System Settings timezone must be {0}; current value is {1}.").format(
                timezone, current
            )
        )


def ensure_root(doctype: str, title_field: str, name: str) -> None:
    if not frappe.db.exists(doctype, name):
        frappe.get_doc(
            {
                "doctype": doctype,
                title_field: name,
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        return
    actual = frappe.db.get_value(doctype, name, ("is_group", title_field), as_dict=True)
    if not actual or int(actual.is_group or 0) != 1 or actual.get(title_field) != name:
        frappe.throw(
            _("{0} {1} differs from the Contract Accounting root reference row.").format(
                doctype, name
            )
        )


def ensure_leaf(doctype: str, title_field: str, name: str) -> None:
    if not frappe.db.exists(doctype, name):
        frappe.get_doc(
            {
                "doctype": doctype,
                title_field: name,
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        return
    actual = frappe.db.get_value(doctype, name, ("is_group", title_field), as_dict=True)
    if not actual or int(actual.is_group or 0) != 0 or actual.get(title_field) != name:
        frappe.throw(
            _("{0} {1} differs from the Contract Accounting reference row.").format(doctype, name)
        )


def ensure_prompt_named(doctype: str, name: str) -> None:
    if not frappe.db.exists(doctype, name):
        frappe.get_doc(
            {
                "doctype": doctype,
                "__newname": name,
            }
        ).insert(ignore_permissions=True)
        return
    actual_name = frappe.db.get_value(doctype, name, "name")
    if actual_name != name:
        frappe.throw(
            _("{0} {1} differs from the Contract Accounting reference row.").format(doctype, name)
        )


def ensure_field_named(doctype: str, fieldname: str, name: str) -> None:
    if not frappe.db.exists(doctype, name):
        frappe.get_doc(
            {
                "doctype": doctype,
                fieldname: name,
            }
        ).insert(ignore_permissions=True)
        return
    actual = frappe.db.get_value(doctype, name, fieldname)
    if actual != name:
        frappe.throw(
            _("{0} {1} differs from the Contract Accounting reference row.").format(doctype, name)
        )


def ensure_uom(name: str, *, must_be_whole_number: int) -> None:
    if not frappe.db.exists("UOM", name):
        frappe.get_doc(
            {
                "doctype": "UOM",
                "uom_name": name,
                "enabled": 1,
                "must_be_whole_number": must_be_whole_number,
            }
        ).insert(ignore_permissions=True)
        return
    actual = frappe.db.get_value(
        "UOM",
        name,
        ("uom_name", "enabled", "must_be_whole_number"),
        as_dict=True,
    )
    if (
        not actual
        or actual.uom_name != name
        or int(actual.enabled or 0) != 1
        or int(actual.must_be_whole_number or 0) != must_be_whole_number
    ):
        frappe.throw(_("UOM {0} differs from the Contract Accounting reference row.").format(name))


def ensure_price_list(name: str, *, currency: str, selling: int) -> None:
    if not frappe.db.exists("Price List", name):
        frappe.get_doc(
            {
                "doctype": "Price List",
                "price_list_name": name,
                "currency": currency,
                "selling": selling,
                "buying": 0 if selling else 1,
                "enabled": 1,
            }
        ).insert(ignore_permissions=True)
        return
    actual = frappe.db.get_value(
        "Price List",
        name,
        ("price_list_name", "currency", "selling", "enabled"),
        as_dict=True,
    )
    if (
        not actual
        or actual.price_list_name != name
        or actual.currency != currency
        or int(actual.selling or 0) != selling
        or int(actual.enabled or 0) != 1
    ):
        frappe.throw(
            _("Price List {0} differs from the Contract Accounting reference row.").format(name)
        )


def ensure_fiscal_year_for(target_date) -> None:
    target = getdate(target_date)
    if frappe.db.exists(
        "Fiscal Year",
        {
            "disabled": 0,
            "year_start_date": ["<=", target],
            "year_end_date": [">=", target],
        },
    ):
        return
    name = str(target.year)
    start = getdate(f"{name}-01-01")
    end = getdate(f"{name}-12-31")
    if not frappe.db.exists("Fiscal Year", name):
        frappe.get_doc(
            {
                "doctype": "Fiscal Year",
                "year": name,
                "year_start_date": start,
                "year_end_date": end,
                "disabled": 0,
            }
        ).insert(ignore_permissions=True)
        return
    actual = frappe.db.get_value(
        "Fiscal Year",
        name,
        ("year_start_date", "year_end_date", "disabled"),
        as_dict=True,
    )
    if (
        not actual
        or int(actual.disabled or 0) != 0
        or getdate(actual.year_start_date) > target
        or getdate(actual.year_end_date) < target
    ):
        frappe.throw(
            _("Fiscal Year {0} does not cover the Contract Accounting reference date.").format(name)
        )


def ensure_address_template(country: str) -> None:
    template = get_default_address_template()
    if not frappe.db.exists("Address Template", country):
        frappe.get_doc(
            {
                "doctype": "Address Template",
                "country": country,
                "is_default": 1,
                "template": template,
            }
        ).insert(ignore_permissions=True)
        return
    actual = frappe.db.get_value(
        "Address Template",
        country,
        ("country", "is_default", "template"),
        as_dict=True,
    )
    if (
        not actual
        or actual.country != country
        or int(actual.is_default or 0) != 1
        or actual.template != template
    ):
        frappe.throw(
            _("Address Template {0} differs from the Contract Accounting reference row.").format(
                country
            )
        )


def _validate_country() -> None:
    actual = frappe.db.get_value("Country", "Russia", ("country_name",), as_dict=True)
    if not actual or actual.country_name != "Russia":
        frappe.throw(_("Country Russia is missing or differs from the reference row."))
