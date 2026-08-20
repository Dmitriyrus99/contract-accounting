"""Standalone safety contract for the owned synthetic demo/UAT bootstrap."""

from __future__ import annotations

import hashlib
import inspect
import re
import unittest
from unittest.mock import patch

from contract_accounting.demo_uat import bootstrap as bootstrap_module
from contract_accounting.demo_uat.bootstrap import (
    _BINARY_FIXTURES,
    BOOTSTRAP_CONFIRMATION_TOKEN,
    NAMESPACE,
    _create_or_validate,
    _owned_record_specs,
    _privacy_state_fingerprint,
    _validate_manifest_binding_contract,
    binary_fixture_descriptors,
    owned_record_rows,
)
from contract_accounting.demo_uat.runtime import DemoUATRuntimeError


class DemoUATBootstrapContractTest(unittest.TestCase):
    def test_public_entrypoint_never_accepts_caller_bindings(self) -> None:
        signature = inspect.signature(bootstrap_module.bootstrap)
        self.assertEqual(list(signature.parameters), ["confirmation_token"])
        self.assertIsNone(signature.parameters["confirmation_token"].default)
        self.assertEqual(
            BOOTSTRAP_CONFIRMATION_TOKEN,
            "BOOTSTRAP_CONTRACT_ACCOUNTING_DEMO_UAT_V1",
        )

    def test_every_owned_record_is_deterministic_namespaced_and_reset_described(self) -> None:
        specs = _owned_record_specs()
        rows = owned_record_rows()
        expected = {(spec.doctype, spec.name) for spec in specs} | {
            ("File", fixture.record_name) for fixture in _BINARY_FIXTURES
        }
        self.assertEqual(expected, {(row["doctype"], row["name"]) for row in rows})
        self.assertEqual(len(rows), len({row["external_id"] for row in rows}))
        self.assertEqual(
            list(range(1, len(rows) + 1)),
            [row["creation_order"] for row in rows],
        )
        self.assertEqual(
            list(range(len(rows), 0, -1)),
            [row["deletion_order"] for row in rows],
        )
        for spec in specs:
            if spec.doctype == "User":
                self.assertTrue(spec.name.startswith("ca-demo-v1-"))
                self.assertTrue(spec.name.endswith("@example.invalid"))
            else:
                self.assertTrue(spec.name.startswith(NAMESPACE))

    def test_users_are_disabled_have_exact_roles_and_cannot_send_welcome_mail(self) -> None:
        users = [spec for spec in _owned_record_specs() if spec.doctype == "User"]
        self.assertEqual(4, len(users))
        self.assertEqual(
            ["Инженер", "Инженер", "Руководитель проектов", "Офис-менеджер"],
            [spec.values["roles"][0]["role"] for spec in users],
        )
        for spec in users:
            self.assertEqual(0, spec.values["enabled"])
            self.assertEqual(0, spec.values["send_welcome_email"])
            self.assertNotIn("password", " ".join(spec.values).lower())

    def test_addresses_link_only_to_owned_synthetic_customer(self) -> None:
        specs = _owned_record_specs()
        customer = next(spec for spec in specs if spec.doctype == "Customer")
        addresses = [spec for spec in specs if spec.doctype == "Address"]
        self.assertEqual(2, len(addresses))
        for address in addresses:
            self.assertEqual(
                [{"link_doctype": "Customer", "link_name": customer.name}],
                address.values["links"],
            )
            self.assertIn("not a real address", address.values["address_line1"])

    def test_private_fixture_literals_and_hashes_match_manifest_contract(self) -> None:
        descriptors = binary_fixture_descriptors()
        self.assertEqual(2, len(descriptors))
        for fixture, descriptor in zip(_BINARY_FIXTURES, descriptors, strict=True):
            self.assertEqual(
                fixture.content_sha256,
                hashlib.sha256(fixture.content).hexdigest(),
            )
            self.assertEqual(fixture.content.decode("utf-8"), descriptor["content_literal"])
            self.assertTrue(descriptor["is_private"])
            self.assertEqual("UTF-8 without BOM", descriptor["content_encoding"])
            self.assertEqual("bootstrap-owned prerequisite", descriptor["materialization"])

    def test_create_or_validate_is_idempotent_and_fails_on_drift(self) -> None:
        spec = next(spec for spec in _owned_record_specs() if spec.doctype == "Currency")

        class _Document:
            def __init__(self, values):
                self.values = dict(values)
                self.name = ""

            def insert(self, *, ignore_permissions: bool, set_name: str):
                self.name = set_name
                database[(self.values["doctype"], set_name)] = self
                return self

            def get(self, fieldname: str):
                return self.values.get(fieldname)

        class _DB:
            @staticmethod
            def exists(doctype: str, name: str) -> bool:
                return (doctype, name) in database

        class _Frappe:
            db = _DB()

            @staticmethod
            def get_doc(doctype, name=None):
                if isinstance(doctype, dict):
                    return _Document(doctype)
                return database[(doctype, name)]

        database: dict[tuple[str, str], _Document] = {}
        frappe = _Frappe()
        self.assertTrue(_create_or_validate(frappe, spec))
        self.assertFalse(_create_or_validate(frappe, spec))
        database[(spec.doctype, spec.name)].values["symbol"] = "DRIFT"
        with self.assertRaisesRegex(DemoUATRuntimeError, "record drift"):
            _create_or_validate(frappe, spec)

    def test_binding_contract_rejects_missing_extra_and_wrong_doctypes(self) -> None:
        base = {
            key: {"doctype": doctype}
            for key, doctype in bootstrap_module._BASE_BINDING_DOCTYPES.items()
        }
        valid_manifest = {"required_bindings": base, "business_graph": {}}
        _validate_manifest_binding_contract(valid_manifest)
        for changed in (
            {key: value for key, value in base.items() if key != "company"},
            {**base, "production_company": {"doctype": "Company"}},
            {**base, "company": {"doctype": "Customer"}},
        ):
            with self.assertRaises(DemoUATRuntimeError):
                _validate_manifest_binding_contract(
                    {"required_bindings": changed, "business_graph": {}}
                )
        with self.assertRaisesRegex(DemoUATRuntimeError, "binary fixture contract"):
            _validate_manifest_binding_contract(
                {
                    "required_bindings": base,
                    "business_graph": {"binary_fixtures": [{"record_name": "DRIFT"}]},
                }
            )

    def test_source_contains_no_secret_or_real_pii_literals(self) -> None:
        source = inspect.getsource(bootstrap_module)
        self.assertIsNone(
            re.search(
                r"(?im)^\s*(?:new_password|password|api_key|api_secret|auth_token)\s*=",
                source,
            )
        )
        emails = re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", source, re.I)
        self.assertTrue(all(email.endswith("@example.invalid") for email in emails), emails)
        self.assertIsNone(re.search(r"(?:\+7|\b8)\D{0,3}\d{3}\D{0,3}\d{3}", source))
        self.assertIsNone(re.search(r"\b\d{3}-\d{3}-\d{3} \d{2}\b", source))
        self.assertNotIn("ignore_mandatory", source)
        self.assertNotIn("ignore_links", source)

    def test_confirmation_site_and_administrator_guards_run_before_manifest_or_writes(self) -> None:
        calls: list[str] = []

        class _DB:
            def savepoint(self, _name: str) -> None:
                calls.append("savepoint")

        class _Frappe:
            db = _DB()
            local = type("Local", (), {"site": "ca01.localhost"})()
            session = type("Session", (), {"user": "Administrator"})()

        with (
            patch.object(bootstrap_module, "get_frappe", return_value=_Frappe()),
            patch.object(
                bootstrap_module, "load_manifest", side_effect=lambda: calls.append("manifest")
            ),
        ):
            with self.assertRaises(DemoUATRuntimeError):
                bootstrap_module.bootstrap("wrong")
        self.assertEqual([], calls)

        bad_site = _Frappe()
        bad_site.local = type("Local", (), {"site": "ca01.localhost.evil"})()
        with (
            patch.object(bootstrap_module, "get_frappe", return_value=bad_site),
            patch.object(
                bootstrap_module, "load_manifest", side_effect=lambda: calls.append("manifest")
            ),
        ):
            with self.assertRaises(DemoUATRuntimeError):
                bootstrap_module.bootstrap(BOOTSTRAP_CONFIRMATION_TOKEN)
        self.assertEqual([], calls)

        bad_user = _Frappe()
        bad_user.session = type("Session", (), {"user": "demo-admin@example.invalid"})()
        with (
            patch.object(bootstrap_module, "get_frappe", return_value=bad_user),
            patch.object(
                bootstrap_module, "load_manifest", side_effect=lambda: calls.append("manifest")
            ),
        ):
            with self.assertRaises(DemoUATRuntimeError):
                bootstrap_module.bootstrap(BOOTSTRAP_CONFIRMATION_TOKEN)
        self.assertEqual([], calls)

    def test_standalone_bootstrap_is_prohibited_before_manifest_or_savepoint(self) -> None:
        calls: list[str] = []

        class _DB:
            def savepoint(self, _name: str) -> None:
                calls.append("savepoint")

        class _Flags(dict):
            pass

        class _Frappe:
            db = _DB()
            flags = _Flags()
            local = type("Local", (), {"site": "ca01.localhost"})()
            session = type("Session", (), {"user": "Administrator"})()

        with (
            patch.object(bootstrap_module, "get_frappe", return_value=_Frappe()),
            patch.object(
                bootstrap_module, "load_manifest", side_effect=lambda: calls.append("manifest")
            ),
            self.assertRaisesRegex(DemoUATRuntimeError, "standalone bootstrap is prohibited"),
        ):
            bootstrap_module.bootstrap(BOOTSTRAP_CONFIRMATION_TOKEN)
        self.assertEqual([], calls)

    def test_verifier_binding_resolution_is_explicitly_read_only(self) -> None:
        source = inspect.getsource(bootstrap_module.validate_bootstrap)
        self.assertIn("ensure_references=False", source)
        self.assertNotIn("_ensure_billing_cycle_reference_bindings", source)
        resolver = inspect.getsource(bootstrap_module._resolve_billing_cycle_reference_bindings)
        self.assertNotIn("insert(", resolver)
        self.assertNotIn("ensure_reference_billing_cycle_template", resolver)

    def test_privacy_fingerprint_is_order_independent_and_drift_sensitive(self) -> None:
        state = {"enabled": 0, "activation_mode": "Disabled", "configuration_revision": 3}
        self.assertEqual(
            _privacy_state_fingerprint(state),
            _privacy_state_fingerprint(dict(reversed(list(state.items())))),
        )
        self.assertNotEqual(
            _privacy_state_fingerprint(state),
            _privacy_state_fingerprint({**state, "configuration_revision": 4}),
        )


if __name__ == "__main__":
    unittest.main()
