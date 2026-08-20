from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = ROOT / "contract_accounting" / "contract_accounting" / "doctype"


def schema(folder: str) -> dict[str, object]:
    return json.loads(
        (DOCTYPE_ROOT / folder / f"{folder}.json").read_text(encoding="utf-8")
    )


def fields(document: dict[str, object]) -> dict[str, dict[str, object]]:
    return {row["fieldname"]: row for row in document["fields"]}


class InspectionSchemaTests(unittest.TestCase):
    def test_ca12_has_one_parent_and_two_typed_children(self) -> None:
        inspection = schema("ferum_inspection")
        self.assertEqual(inspection["name"], "Ferum Inspection")
        self.assertNotEqual(inspection.get("istable"), 1)
        self.assertEqual(schema("ferum_inspection_checklist_item")["istable"], 1)
        self.assertEqual(schema("ferum_inspection_team_member")["istable"], 1)

    def test_inspection_separates_context_fact_report_and_approvals(self) -> None:
        by_name = fields(schema("ferum_inspection"))
        for fieldname, target in {
            "service_project": "Ferum Service Project",
            "project_process": "Ferum Project Process",
            "process_step": "Ferum Project Process Step",
            "project_object": "Ferum Project Object",
            "object_system": "Ferum Object System",
            "report_document": "Ferum Project Document",
        }.items():
            self.assertEqual(by_name[fieldname]["options"], target)
        self.assertEqual(
            by_name["status"]["options"].splitlines(),
            ["Planned", "In Progress", "Completed", "Approved", "Cancelled"],
        )
        self.assertEqual(
            by_name["customer_approval"]["options"].splitlines(),
            ["Pending", "Sent", "Approved", "Rejected"],
        )
        self.assertEqual(by_name["items"]["options"], "Ferum Inspection Checklist Item")
        self.assertEqual(by_name["team"]["options"], "Ferum Inspection Team Member")
        self.assertEqual(
            by_name["completion_evidence"]["options"], "Ferum Execution Evidence"
        )

    def test_checklist_is_structured_by_system_and_component(self) -> None:
        item = fields(schema("ferum_inspection_checklist_item"))
        self.assertEqual(item["object_system"]["options"], "Ferum Object System")
        self.assertTrue(
            {
                "component_code",
                "component_name",
                "question",
                "result",
                "finding",
            }.issubset(item)
        )
        self.assertEqual(
            item["result"]["options"].splitlines(),
            ["", "Pass", "Observation", "Defect", "Not Applicable"],
        )

    def test_api_is_typed_and_outputs_reuse_finding_and_project_document(self) -> None:
        source = (ROOT / "contract_accounting" / "api" / "inspections.py").read_text(
            encoding="utf-8"
        )
        self.assertEqual(source.count('@frappe.whitelist(methods=["POST"])'), 6)
        self.assertEqual(source.count("@frappe.whitelist()"), 1)
        self.assertIn('"doctype": "Ferum Finding"', source)
        self.assertIn('"doctype": "Ferum Project Document"', source)
        self.assertNotIn('"doctype": "Ferum Defect"', source)

    def test_reference_launch_graph_is_exact_and_history_safe(self) -> None:
        source = (
            ROOT / "contract_accounting" / "setup" / "launch_template.py"
        ).read_text(encoding="utf-8")
        for code in (
            "INITIATION",
            "CUSTOMER_ONBOARDING",
            "EXECUTION_MODEL",
            "PERSONNEL_READINESS",
            "SITE_MOBILIZATION",
            "INITIAL_INSPECTION",
            "HANDOVER_TO_OPERATIONS",
        ):
            self.assertIn(f'"code": "{code}"', source)
        self.assertEqual(source.count('"code": "'), 7)
        self.assertIn('"PERSONNEL_READY"', source)
        launch = (ROOT / "contract_accounting" / "api" / "launch.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("CONFIRM_NO_HISTORY_BACKFILL", launch)
        self.assertIn("NO_AUTOMATIC_COMPLETED_OR_NOT_APPLICABLE_BACKFILL", launch)
        self.assertNotIn('"status": "Completed"', source)

    def test_personnel_gate_dispatches_live_fail_closed_assertions(self) -> None:
        processes = (ROOT / "contract_accounting" / "api" / "processes.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('step.template_step_code == "PERSONNEL_READY"', processes)
        self.assertIn("assert_project_personnel_ready", processes)
        self.assertIn("assert_personnel_not_applicable", processes)
        self.assertIn('target_status in {"Completed", "Not Applicable"}', processes)


if __name__ == "__main__":
    unittest.main()
