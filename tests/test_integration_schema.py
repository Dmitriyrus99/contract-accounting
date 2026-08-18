"""Static CA-15 integration contract checks without a Frappe runtime."""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class IntegrationSchemaTests(unittest.TestCase):
	def test_all_traceability_rows_have_acceptance_and_owner(self) -> None:
		with (ROOT / "07_traceability.csv").open(encoding="utf-8-sig", newline="") as handle:
			rows = list(csv.DictReader(handle))
		self.assertEqual(len(rows), 557)
		self.assertEqual(len({row["req_id"] for row in rows}), 557)
		self.assertFalse([row["req_id"] for row in rows if not row["acceptance_criterion"].strip()])
		self.assertFalse([row["req_id"] for row in rows if not row["owner_role"].strip()])
		ca15 = [row for row in rows if row["req_id"].startswith(("TCA-A-19-", "TCA-A-20-", "TCA-B-36-"))]
		self.assertEqual(len(ca15), 51)

	def test_named_workspaces_are_standard_pages_with_role_boundaries(self) -> None:
		pages = {
			"ferum_contract_360": "Контракт 360°",
			"ferum_operations": "Операционная работа",
			"ferum_director_control": "Центр контроля директора",
		}
		for folder, title in pages.items():
			payload = json.loads(
				(ROOT / "contract_accounting" / "contract_accounting" / "page" / folder / f"{folder}.json").read_text(encoding="utf-8")
			)
			self.assertEqual(payload["doctype"], "Page")
			self.assertEqual(payload["standard"], "Yes")
			self.assertEqual(payload["title"], title)
			self.assertTrue(payload["roles"])
		roles = json.loads(
			(ROOT / "contract_accounting" / "contract_accounting" / "page" / "ferum_director_control" / "ferum_director_control.json").read_text(encoding="utf-8")
		)["roles"]
		self.assertNotIn("Менеджер проектов", {row["role"] for row in roles})
		operations_roles = json.loads(
			(ROOT / "contract_accounting" / "contract_accounting" / "page" / "ferum_operations" / "ferum_operations.json").read_text(encoding="utf-8")
		)["roles"]
		self.assertEqual(
			{row["role"] for row in operations_roles},
			{
				"System Manager",
				"Владелец процесса",
				"Руководитель проектов",
				"Менеджер проектов",
				"Инженер",
				"Бухгалтер",
				"Офис-менеджер",
			},
		)
		operations_js = (
			ROOT / "contract_accounting" / "contract_accounting" / "page" / "ferum_operations" / "ferum_operations.js"
		).read_text(encoding="utf-8")
		self.assertIn("get_operations_capabilities", operations_js)
		self.assertIn("capabilities.launch_control", operations_js)
		project = json.loads(
			(ROOT / "contract_accounting" / "contract_accounting" / "doctype" / "ferum_service_project" / "ferum_service_project.json").read_text(encoding="utf-8")
		)
		for role in ("Инженер", "Офис-менеджер"):
			permission = next(
				row for row in project["permissions"]
				if row["role"] == role and not row.get("permlevel")
			)
			self.assertEqual(permission.get("read"), 1)
			self.assertEqual(permission.get("report"), 1)
			self.assertFalse({"create", "write", "delete", "export"} & permission.keys())
		permissions = (ROOT / "contract_accounting" / "infrastructure" / "operations_permissions.py").read_text(encoding="utf-8")
		self.assertIn('SCOPED_ROLES: Final[frozenset[str]] = frozenset({"Инженер", "Офис-менеджер"})', permissions)
		self.assertIn("Ferum Project Document", permissions)
		self.assertIn("Ferum Project Process Step", permissions)

	def test_director_projection_sources_are_read_only_for_director(self) -> None:
		sources = (
			"ferum_contract_requirement",
			"ferum_contract_obligation",
			"ferum_contract_execution_stage",
			"ferum_service_object",
			"ferum_project_object",
			"ferum_object_system",
			"ferum_maintenance_schedule",
			"ferum_maintenance_visit",
			"ferum_service_request",
			"ferum_finding",
			"ferum_project_document",
			"ferum_contractor_assignment",
			"ferum_project_process",
			"ferum_project_stage",
			"ferum_project_process_step",
			"ferum_stage_gate",
			"ferum_photo_evidence",
			"ferum_process_event",
		)
		for source in sources:
			payload = json.loads(
				(ROOT / "contract_accounting" / "contract_accounting" / "doctype" / source / f"{source}.json").read_text(encoding="utf-8")
			)
			director = next(
				row for row in payload["permissions"]
				if row["role"] == "Генеральный директор"
			)
			self.assertEqual(director.get("read"), 1, payload["name"])
			self.assertEqual(director.get("report"), 1, payload["name"])
			self.assertFalse(
				{"create", "write", "delete"} & {key for key, value in director.items() if value == 1},
				payload["name"],
			)

	def test_integration_api_is_read_only_and_keeps_import_batch_inactive(self) -> None:
		source = (ROOT / "contract_accounting" / "api" / "integration.py").read_text(encoding="utf-8")
		self.assertIn("READ_ONLY_DRY_RUN", source)
		self.assertIn("READ_ONLY_NO_CACHE_NO_SECOND_SSOT", source)
		self.assertIn("INACTIVE_NOT_PRODUCTION_PROVEN_PENDING_MG-CA-023", source)
		self.assertNotIn(".insert(", source)
		self.assertNotIn(".save(", source)
		self.assertNotIn("set_value(", source)


if __name__ == "__main__":
	unittest.main()
