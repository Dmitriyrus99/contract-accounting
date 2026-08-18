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
				"Офис-менеджер",
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

	def test_ca02_requirement_and_obligation_link_to_service_project(self) -> None:
		for doctype in ("ferum_contract_requirement", "ferum_contract_obligation"):
			with self.subTest(doctype=doctype):
				by_name = fields(schema(doctype))
				self.assertEqual(by_name["service_project"]["fieldtype"], "Link")
				self.assertEqual(
					by_name["service_project"]["options"], "Ferum Service Project"
				)
				self.assertEqual(by_name["service_project"]["reqd"], 1)

	def test_ca02_source_boundary_and_exact_routing_choices(self) -> None:
		requirement = fields(schema("ferum_contract_requirement"))
		self.assertEqual(requirement["source_document_reference"]["fieldtype"], "Data")
		self.assertNotEqual(
			requirement["source_document_reference"].get("options"),
			"Ferum Project Document",
		)
		self.assertEqual(
			requirement["routing_decision"]["options"].splitlines(),
			[
				"",
				"Recurring Obligation",
				"One-time Process Step",
				"Informational",
				"Not Applicable",
			],
		)

	def test_ca02_obligation_has_typed_context_and_child_recurrence(self) -> None:
		obligation = fields(schema("ferum_contract_obligation"))
		links = {
			"requirement": "Ferum Contract Requirement",
			"project_object": "Ferum Project Object",
			"object_system": "Ferum Object System",
		}
		for fieldname, target in links.items():
			with self.subTest(fieldname=fieldname):
				self.assertEqual(obligation[fieldname]["fieldtype"], "Link")
				self.assertEqual(obligation[fieldname]["options"], target)
				self.assertEqual(obligation[fieldname]["reqd"], 1)
		self.assertEqual(obligation["recurrence"]["fieldtype"], "Table")
		self.assertEqual(
			obligation["recurrence"]["options"], "Ferum Obligation Recurrence Rule"
		)
		self.assertEqual(schema("ferum_obligation_recurrence_rule")["istable"], 1)
		for fieldname in ("deadline_rule", "acceptance_rule", "evidence_rule"):
			self.assertEqual(obligation[fieldname]["fieldtype"], "JSON")

	def test_ca03_schedule_has_obligation_period_provenance(self) -> None:
		schedule = fields(schema("ferum_maintenance_schedule"))
		self.assertEqual(schedule["contract_obligation"]["options"], "Ferum Contract Obligation")
		self.assertEqual(schedule["contract_obligation"]["reqd"], 1)
		for fieldname in (
			"period_key",
			"planned_date",
			"window_start",
			"window_end",
			"due_date",
		):
			self.assertEqual(schedule[fieldname]["reqd"], 1)
		controller = (
			DOCTYPE_ROOT
			/ "ferum_maintenance_schedule"
			/ "ferum_maintenance_schedule.py"
		).read_text(encoding="utf-8")
		self.assertIn('"ca_sched_period_uniq"', controller)

	def test_ca03_visit_separates_plan_fact_review_and_acceptance(self) -> None:
		visit = fields(schema("ferum_maintenance_visit"))
		self.assertEqual(visit["maintenance_schedule"]["options"], "Ferum Maintenance Schedule")
		self.assertEqual(visit["contract_obligation"]["options"], "Ferum Contract Obligation")
		self.assertEqual(visit["planned_date"]["fieldtype"], "Date")
		self.assertEqual(visit["actual_start"]["fieldtype"], "Datetime")
		self.assertEqual(visit["actual_end"]["fieldtype"], "Datetime")
		self.assertEqual(visit["checklist"]["options"], "Ferum Visit Checklist Item")
		self.assertEqual(visit["evidence"]["options"], "Ferum Execution Evidence")
		self.assertEqual(visit["review_status"]["read_only"], 1)
		self.assertEqual(visit["acceptance_status"]["read_only"], 1)
		self.assertEqual(schema("ferum_visit_checklist_item")["istable"], 1)
		self.assertEqual(schema("ferum_execution_evidence")["istable"], 1)

	def test_ca03_service_request_is_independent_unplanned_fact(self) -> None:
		request = fields(schema("ferum_service_request"))
		self.assertNotIn("maintenance_schedule", request)
		self.assertEqual(request["service_project"]["options"], "Ferum Service Project")
		self.assertEqual(request["project_object"]["options"], "Ferum Project Object")
		self.assertEqual(request["service_object"]["read_only"], 1)
		self.assertEqual(request["customer"]["read_only"], 1)
		self.assertEqual(request["evidence"]["options"], "Ferum Execution Evidence")

	def test_ca03_mutating_commands_are_post_only(self) -> None:
		source = (ROOT / "contract_accounting" / "api" / "execution.py").read_text(
			encoding="utf-8"
		)
		self.assertEqual(source.count('@frappe.whitelist(methods=["POST"])'), 5)
		self.assertEqual(source.count("@frappe.whitelist()"), 1)

	def test_ca04_has_one_finding_doctype_and_no_defect_doctype(self) -> None:
		self.assertTrue((DOCTYPE_ROOT / "ferum_finding").is_dir())
		self.assertFalse((DOCTYPE_ROOT / "ferum_defect").exists())
		finding = fields(schema("ferum_finding"))
		self.assertEqual(
			finding["category"]["options"].splitlines(),
			["Observation", "Defect", "Nonconformity", "Risk"],
		)
		self.assertEqual(finding["category"]["reqd"], 1)

	def test_ca04_finding_has_dynamic_source_and_derived_context(self) -> None:
		finding = fields(schema("ferum_finding"))
		self.assertEqual(finding["source_doctype"]["options"], "DocType")
		self.assertEqual(finding["source_name"]["fieldtype"], "Dynamic Link")
		self.assertEqual(finding["source_name"]["options"], "source_doctype")
		for fieldname in (
			"service_project",
			"project_object",
			"service_object",
			"object_system",
			"found_at",
			"found_by",
			"detected_context_snapshot",
		):
			self.assertEqual(finding[fieldname]["read_only"], 1)

	def test_ca04_separates_confirmation_resolution_and_execution(self) -> None:
		finding = fields(schema("ferum_finding"))
		self.assertEqual(
			finding["confirmation_status"]["options"].splitlines(),
			["Pending", "Confirmed", "Rejected"],
		)
		self.assertEqual(
			finding["status"]["options"].splitlines(),
			["Open", "In Resolution", "Resolved", "Closed", "Rejected"],
		)
		self.assertEqual(finding["evidence"]["options"], "Ferum Execution Evidence")
		self.assertEqual(
			finding["execution_links"]["options"], "Ferum Finding Execution Link"
		)
		link = fields(schema("ferum_finding_execution_link"))
		self.assertEqual(link["target_name"]["fieldtype"], "Dynamic Link")
		self.assertEqual(link["target_name"]["options"], "target_doctype")
		self.assertEqual(link["source_event_key"]["reqd"], 1)

	def test_ca04_commands_are_post_only_and_report_is_read_only(self) -> None:
		source = (ROOT / "contract_accounting" / "api" / "findings.py").read_text(
			encoding="utf-8"
		)
		self.assertEqual(source.count('@frappe.whitelist(methods=["POST"])'), 5)
		self.assertEqual(source.count("@frappe.whitelist()"), 1)
		self.assertIn("ALLOWED_SOURCE_DOCTYPES", (
			DOCTYPE_ROOT / "ferum_finding" / "ferum_finding.py"
		).read_text(encoding="utf-8"))

	def test_ca04_photo_evidence_keeps_file_as_binary_ssot(self) -> None:
		photo = fields(schema("ferum_photo_evidence"))
		self.assertEqual(photo["source_name"]["fieldtype"], "Dynamic Link")
		self.assertEqual(photo["source_name"]["options"], "source_doctype")
		self.assertEqual(photo["file"]["fieldtype"], "Link")
		self.assertEqual(photo["file"]["options"], "File")
		self.assertEqual(photo["content_hash"]["read_only"], 1)
		self.assertEqual(
			photo["review_status"]["options"].splitlines(),
			["Pending", "Accepted", "Rejected"],
		)

	def test_ca05_project_document_has_exact_normative_types(self) -> None:
		document = fields(schema("ferum_project_document"))
		self.assertEqual(
			document["document_type"]["options"].splitlines(),
			[
				"Contract",
				"Technical Specification",
				"Estimate",
				"Procurement Documentation",
				"Supplementary Agreement",
				"Act",
				"Invoice",
				"UPD",
				"Guarantee",
				"Correspondence",
				"Other",
			],
		)
		for fieldname in ("document_number", "document_date", "version"):
			self.assertEqual(document[fieldname]["reqd"], 1)

	def test_ca05_uses_service_project_as_root_and_file_as_binary_ssot(self) -> None:
		document = fields(schema("ferum_project_document"))
		self.assertEqual(document["service_project"]["options"], "Ferum Service Project")
		self.assertNotIn("contract", document)
		self.assertEqual(document["file"]["fieldtype"], "Link")
		self.assertEqual(document["file"]["options"], "File")
		self.assertEqual(document["content_hash"]["read_only"], 1)
		self.assertEqual(document["billing_reference_name"]["fieldtype"], "Dynamic Link")

	def test_ca05_digital_and_original_axes_are_independent_and_guarded(self) -> None:
		document = fields(schema("ferum_project_document"))
		self.assertEqual(
			document["digital_copy_status"]["options"].splitlines(),
			["Missing", "Uploaded", "Verified", "Signed", "Rejected", "Superseded", "Not Required"],
		)
		self.assertEqual(
			document["original_status"]["options"].splitlines(),
			["Not Requested", "Requested", "In Transit", "Received", "Archived", "Not Required"],
		)
		self.assertEqual(document["digital_copy_status"]["read_only"], 1)
		self.assertEqual(document["original_status"]["read_only"], 1)
		controller = (
			DOCTYPE_ROOT / "ferum_project_document" / "ferum_project_document.py"
		).read_text(encoding="utf-8")
		self.assertIn("DIGITAL_TRANSITIONS", controller)
		self.assertIn("ORIGINAL_TRANSITIONS", controller)

	def test_ca05_event_and_related_link_schemas_are_typed(self) -> None:
		event = schema("ferum_project_document_event")
		by_name = fields(event)
		self.assertEqual(by_name["project_document"]["options"], "Ferum Project Document")
		self.assertEqual(
			by_name["dimension"]["options"].splitlines(),
			["Document", "Digital Copy", "Original"],
		)
		self.assertTrue(all(field.get("read_only") == 1 for field in by_name.values()))
		for permission in event["permissions"]:  # type: ignore[index,union-attr]
			self.assertNotIn("create", permission)
			self.assertNotIn("write", permission)
			self.assertNotIn("delete", permission)
		link = schema("ferum_document_link")
		self.assertEqual(link["istable"], 1)
		self.assertEqual(fields(link)["linked_name"]["fieldtype"], "Dynamic Link")

	def test_ca05_mutations_are_post_only_and_file_delete_is_guarded(self) -> None:
		source = (ROOT / "contract_accounting" / "api" / "documents.py").read_text(
			encoding="utf-8"
		)
		self.assertEqual(source.count('@frappe.whitelist(methods=["POST"])'), 3)
		self.assertEqual(source.count("@frappe.whitelist()"), 1)
		hooks = (ROOT / "contract_accounting" / "hooks.py").read_text(encoding="utf-8")
		self.assertIn('"File": {', hooks)
		self.assertIn("prevent_locked_file_delete", hooks)

	def test_ca06_output_is_documentary_layer_over_standard_sales_invoice(self) -> None:
		output = fields(schema("ferum_billing_output"))
		self.assertEqual(output["sales_invoice"]["options"], "Sales Invoice")
		self.assertEqual(
			output["output_type"]["options"].splitlines(),
			["Invoice Print", "Act", "UPD", "Invoice Factura", "Correction"],
		)
		self.assertEqual(output["basis_items"]["options"], "Ferum Billing Basis Item")
		self.assertFalse((DOCTYPE_ROOT / "ferum_sales_invoice").exists())
		self.assertFalse((DOCTYPE_ROOT / "ferum_payment_entry").exists())
		self.assertFalse((DOCTYPE_ROOT / "ferum_gl_entry").exists())

	def test_ca06_basis_rows_are_typed_immutable_snapshots(self) -> None:
		basis = schema("ferum_billing_basis_item")
		self.assertEqual(basis["istable"], 1)
		by_name = fields(basis)
		for fieldname in (
			"source_doctype",
			"source_name",
			"period_key",
			"amount_snapshot",
			"source_snapshot_json",
			"source_hash",
			"active_claim_key",
		):
			self.assertEqual(by_name[fieldname]["read_only"], 1)
		self.assertEqual(by_name["source_name"]["fieldtype"], "Dynamic Link")
		self.assertEqual(by_name["active_claim_key"]["unique"], 1)

	def test_ca06_artifact_versions_standard_file_and_projects_to_registry(self) -> None:
		artifact = fields(schema("ferum_billing_artifact"))
		self.assertEqual(artifact["file"]["fieldtype"], "Link")
		self.assertEqual(artifact["file"]["options"], "File")
		self.assertEqual(artifact["project_document"]["options"], "Ferum Project Document")
		self.assertEqual(artifact["version"]["read_only"], 1)
		self.assertEqual(artifact["current_key"]["unique"], 1)

	def test_ca06_billing_event_is_insert_only(self) -> None:
		event = schema("ferum_billing_event")
		by_name = fields(event)
		self.assertTrue(
			{"billing_output", "event_type", "actor", "timestamp", "correlation_id", "metadata_json"}.issubset(by_name)
		)
		self.assertTrue(all(field.get("read_only") == 1 for field in by_name.values()))
		for permission in event["permissions"]:  # type: ignore[index,union-attr]
			self.assertNotIn("create", permission)
			self.assertNotIn("write", permission)
			self.assertNotIn("delete", permission)

	def test_ca06_commands_are_typed_and_mutations_are_post_only(self) -> None:
		source = (ROOT / "contract_accounting" / "api" / "billing.py").read_text(
			encoding="utf-8"
		)
		self.assertEqual(source.count('@frappe.whitelist(methods=["POST"])'), 5)
		self.assertEqual(source.count("@frappe.whitelist()"), 2)
		self.assertNotIn("GL Entry", source)
		self.assertNotIn("Payment Entry", source)

	def test_ca06_installs_narrow_sales_invoice_project_adapter(self) -> None:
		setup = (ROOT / "contract_accounting" / "setup" / "custom_fields.py").read_text(
			encoding="utf-8"
		)
		hooks = (ROOT / "contract_accounting" / "hooks.py").read_text(encoding="utf-8")
		self.assertIn('"Sales Invoice": [', setup)
		self.assertIn('"fieldname": "ferum_service_project"', setup)
		self.assertIn("after_install =", hooks)
		self.assertIn("before_migrate =", hooks)
		self.assertIn("prevent_active_output_cancel", hooks)

	def test_ca07_summary_is_read_only_rebuildable_projection(self) -> None:
		document = schema("ferum_project_finance_summary")
		by_name = fields(document)
		for fieldname in (
			"recognized_revenue_without_vat",
			"invoiced_with_vat",
			"paid_with_vat",
			"outstanding_with_vat",
			"material_cost_without_vat",
			"contractor_cost_without_vat",
			"other_cost_without_vat",
			"profit_without_vat",
			"profitability_percent",
			"source_fingerprint",
		):
			self.assertEqual(by_name[fieldname]["read_only"], 1)
		self.assertEqual(by_name["service_project"]["unique"], 1)
		for permission in document["permissions"]:  # type: ignore[index,union-attr]
			self.assertNotIn("create", permission)
			self.assertNotIn("write", permission)
			self.assertNotIn("delete", permission)

	def test_ca07_material_expense_is_adjunct_not_stock_ledger(self) -> None:
		material = fields(schema("ferum_material_expense"))
		self.assertEqual(material["service_project"]["options"], "Ferum Service Project")
		self.assertEqual(material["contract_obligation"]["options"], "Ferum Contract Obligation")
		self.assertEqual(material["purchase_invoice"]["options"], "Purchase Invoice")
		self.assertEqual(material["stock_entry"]["options"], "Stock Entry")
		self.assertEqual(material["purchase_invoice_claim_key"]["unique"], 1)
		self.assertEqual(
			material["status"]["options"].splitlines(), ["Draft", "Approved", "Cancelled"]
		)

	def test_ca07_contractor_settlement_separates_management_and_accounting(self) -> None:
		settlement = fields(schema("ferum_contractor_settlement"))
		self.assertEqual(settlement["supplier"]["options"], "Supplier")
		self.assertEqual(settlement["purchase_invoice"]["options"], "Purchase Invoice")
		self.assertEqual(settlement["payment_entry"]["options"], "Payment Entry")
		self.assertEqual(settlement["purchase_invoice_claim_key"]["unique"], 1)
		self.assertEqual(
			settlement["status"]["options"].splitlines(),
			["Draft", "Approved", "Settled", "Cancelled"],
		)
		self.assertNotIn("contractor_assignment", settlement)

	def test_ca07_installs_purchase_invoice_adapter_and_hooks_standard_events(self) -> None:
		setup = (ROOT / "contract_accounting" / "setup" / "custom_fields.py").read_text(
			encoding="utf-8"
		)
		hooks = (ROOT / "contract_accounting" / "hooks.py").read_text(encoding="utf-8")
		self.assertIn('"Purchase Invoice": [', setup)
		self.assertEqual(setup.count('"fieldname": "ferum_service_project"'), 2)
		self.assertIn('"Purchase Invoice": {', hooks)
		self.assertIn('"Payment Entry": {', hooks)
		self.assertIn("enqueue_accounting_rebuild", hooks)
		self.assertIn("prevent_recognized_cost_cancel", hooks)

	def test_ca07_api_has_typed_mutations_and_read_only_projections(self) -> None:
		source = (ROOT / "contract_accounting" / "api" / "finance.py").read_text(
			encoding="utf-8"
		)
		self.assertEqual(source.count('@frappe.whitelist(methods=["POST"])'), 6)
		self.assertEqual(source.count("@frappe.whitelist()"), 3)
		self.assertIn("source_fingerprint", source)
		self.assertIn("assert_purchase_invoice_available", source)
		self.assertNotIn('frappe.new_doc("GL Entry")', source)
		self.assertNotIn('frappe.get_doc({"doctype": "Payment Entry"', source)

	def test_ca07_keeps_obligation_and_billing_dimensions_derived(self) -> None:
		summary = fields(schema("ferum_project_finance_summary"))
		self.assertEqual(summary["obligation_dimension_json"]["fieldtype"], "JSON")
		self.assertEqual(summary["billing_cycle_dimension_json"]["fieldtype"], "JSON")
		self.assertEqual(summary["obligation_dimension_json"]["read_only"], 1)
		self.assertEqual(summary["billing_cycle_dimension_json"]["read_only"], 1)


if __name__ == "__main__":
	unittest.main()
