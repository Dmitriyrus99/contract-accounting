from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

from contract_accounting import __version__
from contract_accounting.domain.lifecycle import ExecutionStatus, LegalStatus


ROOT = Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = ROOT / "contract_accounting" / "contract_accounting" / "doctype"


def schema(name: str) -> dict[str, object]:
	path = DOCTYPE_ROOT / name / f"{name}.json"
	return json.loads(path.read_text(encoding="utf-8"))


def fields(document: dict[str, object]) -> dict[str, dict[str, object]]:
	return {
		field["fieldname"]: field
		for field in document["fields"]  # type: ignore[index,union-attr]
	}


class TestFrappeSchema(unittest.TestCase):
	def test_service_project_contains_exact_approved_status_enums(self) -> None:
		document = schema("ferum_service_project")
		by_name = fields(document)
		legal = by_name["legal_status"]
		execution = by_name["execution_status"]
		self.assertEqual(legal["options"].splitlines(), [item.value for item in LegalStatus])
		self.assertEqual(
			execution["options"].splitlines(),
			[item.value for item in ExecutionStatus],
		)
		self.assertEqual(legal["default"], "Draft")
		self.assertEqual(execution["default"], "Not Started")
		self.assertEqual(legal["read_only"], 1)
		self.assertEqual(execution["read_only"], 1)

	def test_internal_lifecycle_projection_fields_are_not_user_editable(self) -> None:
		by_name = fields(schema("ferum_service_project"))
		for fieldname in (
			"suspended_from_status",
			"documented_termination_completion_exception",
		):
			with self.subTest(fieldname=fieldname):
				self.assertEqual(by_name[fieldname]["read_only"], 1)
				self.assertEqual(by_name[fieldname]["hidden"], 1)

	def test_contract_identity_is_required_for_new_root(self) -> None:
		by_name = fields(schema("ferum_service_project"))
		for fieldname in (
			"project_name",
			"company",
			"customer",
			"contract_number",
			"contract_date",
			"contract_subject",
			"currency",
		):
			with self.subTest(fieldname=fieldname):
				self.assertEqual(by_name[fieldname]["reqd"], 1)

	def test_lifecycle_audit_schema_is_insert_only_and_complete(self) -> None:
		document = schema("ferum_lifecycle_audit_event")
		by_name = fields(document)
		required = {
			"service_project",
			"dimension",
			"from_status",
			"to_status",
			"actor",
			"occurred_at",
			"reason",
			"comment",
			"effective_date",
			"evidence_json",
			"termination_basis",
			"related_document",
			"documented_termination_completion_exception",
			"correlation_id",
		}
		self.assertTrue(required.issubset(by_name))
		self.assertTrue(all(by_name[name].get("read_only") == 1 for name in required))
		self.assertEqual(by_name["correlation_id"].get("search_index"), 1)
		for permission in document["permissions"]:  # type: ignore[index,union-attr]
			self.assertNotIn("create", permission)
			self.assertNotIn("write", permission)
			self.assertNotIn("delete", permission)
		controller = (
			DOCTYPE_ROOT
			/ "ferum_lifecycle_audit_event"
			/ "ferum_lifecycle_audit_event.py"
		).read_text(encoding="utf-8")
		self.assertIn('["service_project", "occurred_at"]', controller)
		self.assertNotIn('["correlation_id"]', controller)

	def test_role_fixture_and_permission_levels_match_ca01_boundaries(self) -> None:
		role_path = ROOT / "contract_accounting" / "fixtures" / "role.json"
		roles = json.loads(role_path.read_text(encoding="utf-8"))
		self.assertEqual(
			{role["name"] for role in roles},
			{
				"Генеральный директор",
				"Руководитель проектов",
				"Менеджер проектов",
				"Юрист",
				"Бухгалтер",
				"Инженер",
			},
		)
		document = schema("ferum_service_project")
		by_name = fields(document)
		self.assertEqual(by_name["contract_number"]["permlevel"], 1)
		self.assertEqual(by_name["launch_date"]["permlevel"], 2)
		self.assertEqual(by_name["contract_amount_with_vat"]["permlevel"], 3)
		permissions = document["permissions"]  # type: ignore[index]
		lawyer_legal = [
			row
			for row in permissions  # type: ignore[union-attr]
			if row.get("role") == "Юрист" and row.get("permlevel") == 1
		]
		manager_execution = [
			row
			for row in permissions  # type: ignore[union-attr]
			if row.get("role") == "Менеджер проектов" and row.get("permlevel") == 2
		]
		accountant_finance = [
			row
			for row in permissions  # type: ignore[union-attr]
			if row.get("role") == "Бухгалтер" and row.get("permlevel") == 3
		]
		self.assertEqual(lawyer_legal[0]["write"], 1)
		self.assertEqual(manager_execution[0]["write"], 1)
		self.assertEqual(accountant_finance[0]["write"], 1)

	def test_app_declares_erpnext_and_contract_accounting_module(self) -> None:
		hooks = (ROOT / "contract_accounting" / "hooks.py").read_text(encoding="utf-8")
		modules = (ROOT / "contract_accounting" / "modules.txt").read_text(encoding="utf-8")
		self.assertIn('required_apps = ["erpnext"]', hooks)
		self.assertEqual(modules.strip(), "Contract Accounting")
		with (ROOT / "pyproject.toml").open("rb") as pyproject_file:
			pyproject = tomllib.load(pyproject_file)
		self.assertEqual(pyproject["project"]["name"], "contract_accounting")
		self.assertEqual(pyproject["project"]["version"], __version__)

	def test_all_lifecycle_endpoints_are_post_only(self) -> None:
		api_path = ROOT / "contract_accounting" / "api" / "lifecycle.py"
		source = api_path.read_text(encoding="utf-8")
		self.assertEqual(source.count('@frappe.whitelist(methods=["POST"])'), 3)
		self.assertNotIn("@frappe.whitelist()", source)

	def test_clean_target_schema_has_no_second_contract_ssot(self) -> None:
		self.assertFalse((DOCTYPE_ROOT / "ferum_contract").exists())
		self.assertFalse((DOCTYPE_ROOT / "ferum_project_contract_link").exists())
		for path in DOCTYPE_ROOT.rglob("*.json"):
			document = json.loads(path.read_text(encoding="utf-8"))
			for field in document.get("fields", []):
				self.assertNotIn(
					field.get("options"),
					{"Ferum Contract", "Ferum Project Contract Link"},
					f"legacy SSOT link in {path}: {field.get('fieldname')}",
				)

	def test_ca01_related_doctypes_link_directly_to_service_project(self) -> None:
		required_links = {
			"ferum_contract_amendment": "service_project",
			"ferum_contract_execution_stage": "service_project",
			"ferum_contract_security": "service_project",
			"ferum_project_object": "service_project",
		}
		for doctype, fieldname in required_links.items():
			with self.subTest(doctype=doctype):
				by_name = fields(schema(doctype))
				self.assertEqual(by_name[fieldname]["fieldtype"], "Link")
				self.assertEqual(by_name[fieldname]["options"], "Ferum Service Project")
				self.assertEqual(by_name[fieldname]["reqd"], 1)

	def test_object_navigation_uses_membership_not_direct_project_link(self) -> None:
		service_object = fields(schema("ferum_service_object"))
		self.assertNotIn("service_project", service_object)
		project_object = fields(schema("ferum_project_object"))
		self.assertEqual(project_object["service_object"]["options"], "Ferum Service Object")
		self.assertEqual(project_object["effective_from"]["reqd"], 1)
		object_system = fields(schema("ferum_object_system"))
		self.assertEqual(object_system["service_object"]["options"], "Ferum Service Object")
		self.assertTrue(
			{
				"APS",
				"SOUE",
				"Smoke Control",
				"Internal Fire Water",
				"ACS",
				"CCTV",
			}.issubset(set(object_system["system_type"]["options"].splitlines()))
		)

	def test_financial_plan_is_child_table_of_service_project(self) -> None:
		project = fields(schema("ferum_service_project"))
		self.assertEqual(project["financial_plan"]["fieldtype"], "Table")
		self.assertEqual(
			project["financial_plan"]["options"],
			"Ferum Contract Financial Plan Row",
		)
		row = schema("ferum_contract_financial_plan_row")
		self.assertEqual(row["istable"], 1)
		self.assertTrue(
			{
				"revenue_plan",
				"cost_plan",
				"cash_in_plan",
				"cash_out_plan",
				"tax_plan",
				"source_stage",
			}.issubset(fields(row))
		)

	def test_amendment_is_structured_append_only_contract_change(self) -> None:
		amendment = fields(schema("ferum_contract_amendment"))
		self.assertEqual(amendment["changes"]["options"], "Ferum Contract Amendment Change")
		self.assertEqual(amendment["before_snapshot_json"]["read_only"], 1)
		self.assertEqual(amendment["after_snapshot_json"]["read_only"], 1)
		change = schema("ferum_contract_amendment_change")
		self.assertEqual(change["istable"], 1)
		self.assertTrue(
			{"fieldname", "old_value_json", "new_value_json"}.issubset(fields(change))
		)


if __name__ == "__main__":
	unittest.main()
