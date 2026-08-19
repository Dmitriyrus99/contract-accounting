from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = ROOT / "contract_accounting" / "contract_accounting" / "doctype"
CA11_DOCTYPES = {
    "ferum_process_template": "Ferum Process Template",
    "ferum_stage_template": "Ferum Stage Template",
    "ferum_step_template": "Ferum Step Template",
    "ferum_project_process": "Ferum Project Process",
    "ferum_project_stage": "Ferum Project Stage",
    "ferum_project_process_step": "Ferum Project Process Step",
    "ferum_stage_gate": "Ferum Stage Gate",
    "ferum_process_evidence": "Ferum Process Evidence",
    "ferum_process_event": "Ferum Process Event",
}


def schema(folder: str) -> dict[str, object]:
    return json.loads(
        (DOCTYPE_ROOT / folder / f"{folder}.json").read_text(encoding="utf-8")
    )


def fields(value: dict[str, object]) -> dict[str, dict[str, object]]:
    return {item["fieldname"]: item for item in value["fields"]}


class ProcessSchemaTests(unittest.TestCase):
    def test_ca11_uses_nine_separate_parent_doctypes(self) -> None:
        for folder, name in CA11_DOCTYPES.items():
            value = schema(folder)
            self.assertEqual(value["name"], name)
            self.assertNotEqual(value.get("istable"), 1)
            self.assertTrue((DOCTYPE_ROOT / folder / f"{folder}.py").is_file())

    def test_template_graph_has_exact_parent_links_and_safe_rules(self) -> None:
        stage = fields(schema("ferum_stage_template"))
        step = fields(schema("ferum_step_template"))
        self.assertEqual(stage["process_template"]["options"], "Ferum Process Template")
        self.assertEqual(step["stage_template"]["options"], "Ferum Stage Template")
        self.assertEqual(step["condition_rule"]["fieldtype"], "JSON")
        self.assertEqual(step["activation_rule"]["fieldtype"], "JSON")
        logic = (ROOT / "contract_accounting" / "domain" / "json_logic.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("ALLOWED_OPERATORS", logic)
        self.assertNotIn("eval(", logic)
        self.assertNotIn("exec(", logic)

    def test_step_base_status_excludes_persisted_overdue(self) -> None:
        step = fields(schema("ferum_project_process_step"))
        self.assertEqual(
            step["status"]["options"].splitlines(),
            [
                "Planned",
                "Ready",
                "In Progress",
                "Waiting External",
                "Waiting Approval",
                "Blocked",
                "Completed",
                "Not Applicable",
                "Cancelled",
            ],
        )
        self.assertNotIn("Overdue", step["status"]["options"].splitlines())
        self.assertEqual(step["is_overdue"]["read_only"], 1)
        self.assertEqual(step["display_status"]["read_only"], 1)

    def test_evidence_enum_and_process_ssot_todo_boundary(self) -> None:
        template = fields(schema("ferum_step_template"))
        self.assertEqual(
            template["completion_evidence_type"]["options"].splitlines(),
            [
                "None",
                "Document",
                "File",
                "Email",
                "Outgoing Letter",
                "Incoming Letter",
                "Call Record",
                "Meeting Record",
                "Photo",
                "Approval",
                "ERP Document",
                "Payment",
                "Inspection",
                "Manual Confirmation",
            ],
        )
        source = (ROOT / "contract_accounting" / "api" / "processes.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"doctype": "ToDo"', source)
        self.assertNotIn('"doctype": "Ferum Process Task"', source)

    def test_api_surface_is_typed_and_version_is_current(self) -> None:
        source = (ROOT / "contract_accounting" / "api" / "processes.py").read_text(
            encoding="utf-8"
        )
        self.assertEqual(source.count('@frappe.whitelist(methods=["POST"])'), 8)
        self.assertEqual(source.count("@frappe.whitelist()"), 1)
        self.assertIn(
            'version = "0.19.0"',
            (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
        )
        roles = json.loads(
            (ROOT / "contract_accounting" / "fixtures" / "role.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("Владелец процесса", {row["name"] for row in roles})


if __name__ == "__main__":
    unittest.main()
