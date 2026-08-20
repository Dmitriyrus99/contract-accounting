"""Bench runtime acceptance for CA-12 launch/Inspection without default fixtures."""

from __future__ import annotations

from base64 import b64decode
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today
from frappe.utils.file_manager import save_file

from contract_accounting.api.inspections import (
    approve_inspection,
    complete_inspection,
    create_inspection_from_step,
    get_inspection_trace,
    start_inspection,
)
from contract_accounting.api.launch import (
    CONFIRMATION_TOKEN,
    generate_reference_launch_process,
    get_launch_assessment,
)
from contract_accounting.api.lifecycle import change_status
from contract_accounting.api.processes import (
    add_process_evidence,
    complete_project_stage,
    evaluate_stage_gate,
    generate_project_process,
    publish_process_template,
    transition_process_step,
    validate_process_evidence,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
    _make_address,
    _make_project,
)
from contract_accounting.setup.launch_template import ensure_reference_launch_template


class TestFerumInspection(FrappeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.project = _make_project()
        self.project.project_manager = "Administrator"
        self.project.save(ignore_permissions=True)
        change_status(self.project.name, target_legal_status="On Approval")
        change_status(self.project.name, target_legal_status="Approved")
        self.service_object = frappe.get_doc(
            {
                "doctype": "Ferum Service Object",
                "object_name": f"CA-12 Object {uuid4().hex[:10]}",
                "customer": self.project.customer,
                "address": _make_address(self.project.customer, "CA-12 runtime address"),
            }
        ).insert(ignore_permissions=True)
        self.system = frappe.get_doc(
            {
                "doctype": "Ferum Object System",
                "service_object": self.service_object.name,
                "system_type": "APS",
                "system_name": f"CA-12 APS {uuid4().hex[:10]}",
                "equipment_count": 3,
            }
        ).insert(ignore_permissions=True)
        self.project_object = frappe.get_doc(
            {
                "doctype": "Ferum Project Object",
                "service_project": self.project.name,
                "service_object": self.service_object.name,
                "effective_from": today(),
            }
        ).insert(ignore_permissions=True)

    def tearDown(self) -> None:
        frappe.set_user(self._previous_user)
        super().tearDown()

    def test_reference_graph_is_idempotent_and_assessment_never_invents_history(
        self,
    ) -> None:
        before_processes = frappe.db.count(
            "Ferum Project Process", {"service_project": self.project.name}
        )
        first = ensure_reference_launch_template()
        second = ensure_reference_launch_template()
        self.assertEqual(first, second)
        self.assertEqual(frappe.db.count("Ferum Stage Template", {"process_template": first}), 7)
        self.assertEqual(
            frappe.db.count(
                "Ferum Step Template",
                {
                    "stage_template": [
                        "in",
                        frappe.get_all(
                            "Ferum Stage Template",
                            filters={"process_template": first},
                            pluck="name",
                        ),
                    ]
                },
            ),
            25,
        )
        assessment = get_launch_assessment(self.project.name)
        self.assertTrue(assessment["eligible_for_generation"])
        self.assertEqual(
            assessment["history_policy"],
            "NO_AUTOMATIC_COMPLETED_OR_NOT_APPLICABLE_BACKFILL",
        )
        self.assertEqual(
            frappe.db.count("Ferum Project Process", {"service_project": self.project.name}),
            before_processes,
        )

    def test_reference_graph_rejects_non_key_field_drift(self) -> None:
        template = ensure_reference_launch_template()
        stage = frappe.db.get_value(
            "Ferum Stage Template", {"process_template": template}, "name"
        )
        step = frappe.db.get_value(
            "Ferum Step Template", {"stage_template": stage}, "name"
        )
        original = frappe.db.get_value("Ferum Step Template", step, "failure_action")
        frappe.db.set_value(
            "Ferum Step Template", step, "failure_action", "Synthetic drift"
        )
        try:
            with self.assertRaisesRegex(frappe.ValidationError, "failure_action"):
                ensure_reference_launch_template()
        finally:
            frappe.db.set_value("Ferum Step Template", step, "failure_action", original)

    def test_reference_generation_is_explicit_and_personnel_gate_is_fail_closed(
        self,
    ) -> None:
        ensure_reference_launch_template()
        with self.assertRaises(frappe.ValidationError):
            generate_reference_launch_process(
                self.project.name,
                f"CA12-NO-CONFIRM-{uuid4().hex}",
                "REQ-CA12-1",
                "yes",
            )
        result = generate_reference_launch_process(
            self.project.name,
            f"CA12-LAUNCH-{uuid4().hex}",
            "REQ-CA12-1",
            CONFIRMATION_TOKEN,
        )
        self.assertTrue(result["created"])
        self.assertFalse(result["history_backfilled"])
        self.assertEqual((result["stage_count"], result["step_count"]), (7, 25))
        personnel = frappe.get_doc(
            "Ferum Project Process Step",
            frappe.db.get_value(
                "Ferum Project Process Step",
                {
                    "project_process": result["project_process"],
                    "template_step_code": "PERSONNEL_READY",
                },
                "name",
            ),
        )
        self.project.reload()
        self.project.requires_contractor = 1
        self.project.save(ignore_permissions=True)
        with self.assertRaisesRegex(frappe.ValidationError, "нельзя обойти"):
            transition_process_step(
                personnel.name, "Not Applicable", not_applicable_reason="Owner waiver"
            )
        self.assertEqual(
            frappe.db.get_value(personnel.doctype, personnel.name, "status"), "Planned"
        )
        self.project.reload()
        self.project.requires_contractor = 0
        self.project.save(ignore_permissions=True)
        transition_process_step(
            personnel.name,
            "Not Applicable",
            not_applicable_reason="No contractor or credential requirement",
        )
        self.assertEqual(
            frappe.db.get_value(personnel.doctype, personnel.name, "status"), "Not Applicable"
        )

    def test_inspection_derives_report_finding_photo_and_validated_step_evidence(
        self,
    ) -> None:
        step = self._inspection_step()
        created = create_inspection_from_step(
            step.name,
            self.project_object.name,
            today(),
            f"CA12-INSP-{uuid4().hex}",
            object_system=self.system.name,
            template_version_snapshot={"template": "CA12-RUNTIME", "version": 1},
            items=[
                {
                    "item_code": "APS-PANEL",
                    "object_system": self.system.name,
                    "component_code": "PANEL-01",
                    "component_name": "Fire alarm panel",
                    "question": "Panel condition",
                }
            ],
        )
        inspection_name = created["inspection"]
        started_at = datetime(2026, 8, 18, 12, 0, 1)
        with patch(
            "contract_accounting.api.inspections.now_datetime",
            return_value=started_at,
        ):
            start_inspection(
                inspection_name,
                {
                    "captured_at": "2026-08-18T12:00:00+03:00",
                    "systems": [{"name": self.system.name, "equipment_count": 3}],
                },
            )
        file_doc = save_file(
            "ca12-inspection.txt",
            b64decode("Q0EtMTIgcnVudGltZSBl"),
            "Ferum Inspection",
            inspection_name,
            is_private=1,
        )
        with patch(
            "contract_accounting.api.inspections.now_datetime",
            return_value=started_at - timedelta(seconds=1),
        ):
            completed = complete_inspection(
                inspection_name,
                "Ready With Findings",
                "Panel defect recorded with exact source result.",
                [
                    {
                        "item_code": "APS-PANEL",
                        "result": "Defect",
                        "severity": "High",
                        "finding_title": "Panel fault",
                        "observation": "Fault indicator is active.",
                        "photo_file": file_doc.name,
                    }
                ],
                [{"evidence_type": "Report", "file": file_doc.name}],
            )
        inspection = frappe.get_doc("Ferum Inspection", inspection_name)
        self.assertEqual(inspection.actual_end, inspection.actual_start)
        self.assertEqual(completed["finding_count"], 1)
        self.assertEqual(completed["photo_evidence_count"], 1)
        self.assertTrue(completed["report_document"])
        second = complete_inspection(
            inspection_name,
            "Ready With Findings",
            "ignored idempotent repeat",
            [],
            [],
        )
        self.assertFalse(second["created"])
        approve_inspection(inspection_name)
        trace = get_inspection_trace(inspection_name)
        self.assertEqual(trace["status"], "Approved")
        self.assertEqual((len(trace["findings"]), len(trace["photo_evidence"])), (1, 1))
        self.assertIn(
            "APS-PANEL",
            trace["findings"][0]["name"]
            and frappe.db.get_value("Ferum Finding", trace["findings"][0]["name"], "description"),
        )

        evidence = add_process_evidence(
            step.name,
            "Inspection",
            source_doctype="Ferum Inspection",
            source_name=inspection_name,
        )
        validate_process_evidence(
            evidence["process_evidence"], "Validated", "Approved Inspection accepted"
        )
        transition_process_step(step.name, "In Progress")
        transition_process_step(step.name, "Completed")
        self.assertEqual(frappe.db.get_value(step.doctype, step.name, "status"), "Completed")

    def test_final_launch_gate_activates_project_through_lifecycle_api(self) -> None:
        for legal_status in ("Signing", "Signed", "In Force"):
            change_status(self.project.name, target_legal_status=legal_status)
        change_status(self.project.name, target_execution_status="Launching")
        step = self._simple_process_step(
            process_type="Launch",
            action_type="Operational Handover",
            evidence_type="Manual Confirmation",
        )
        transition_process_step(step.name, "In Progress")
        evidence = add_process_evidence(
            step.name,
            "Manual Confirmation",
            snapshot={"operational_handover": True},
        )
        validate_process_evidence(
            evidence["process_evidence"], "Validated", "Operational handover accepted"
        )
        transition_process_step(step.name, "Completed")
        gate = evaluate_stage_gate(step.project_stage)
        self.assertEqual(gate["status"], "Passed")
        completion = complete_project_stage(step.project_stage)
        self.assertEqual(completion["process_status"], "Completed")
        self.assertEqual(
            frappe.db.get_value("Ferum Service Project", self.project.name, "execution_status"),
            "Active",
        )
        self.assertTrue(
            frappe.db.exists(
                "Ferum Lifecycle Audit Event",
                {
                    "service_project": self.project.name,
                    "dimension": "execution_status",
                    "from_status": "Launching",
                    "to_status": "Active",
                },
            )
        )

    def _inspection_step(self):
        return self._simple_process_step(
            process_type="Inspection",
            action_type="Initial Inspection",
            evidence_type="Inspection",
        )

    def _simple_process_step(
        self,
        *,
        process_type: str,
        action_type: str,
        evidence_type: str,
    ):
        template = frappe.get_doc(
            {
                "doctype": "Ferum Process Template",
                "code": f"CA12-INSP-{uuid4().hex[:10]}",
                "title": "CA-12 Inspection Runtime",
                "version": 1,
                "process_type": process_type,
                "scope_rule": {},
                "status": "Draft",
                "change_note": "Runtime fixture",
            }
        ).insert(ignore_permissions=True)
        stage = frappe.get_doc(
            {
                "doctype": "Ferum Stage Template",
                "process_template": template.name,
                "stage_code": "INSPECTION",
                "title": "Inspection",
                "sequence": 1,
                "entry_rule": {},
                "exit_rule": {},
                "gate_policy": {},
                "default_owner_role": "Менеджер проектов",
                "active": 1,
            }
        ).insert(ignore_permissions=True)
        frappe.get_doc(
            {
                "doctype": "Ferum Step Template",
                "stage_template": stage.name,
                "step_code": "INSPECT_RUNTIME",
                "title": "Conduct Inspection",
                "sequence": 1,
                "action_type": action_type,
                "step_type": "Inspection" if process_type == "Inspection" else "Manual",
                "requirement_source_policy": "None",
                "requirement_match_rule": {},
                "responsible_role": "Менеджер проектов",
                "responsible_user": "Administrator",
                "deadline_type": "None",
                "condition_rule": {},
                "activation_rule": {},
                "criticality": "Mandatory",
                "blocking": 1,
                "completion_evidence_type": evidence_type,
                "active": 1,
            }
        ).insert(ignore_permissions=True)
        publish_process_template(template.name)
        process = generate_project_process(
            self.project.name,
            template.name,
            f"CA12-{process_type.upper()}-PROC-{uuid4().hex}",
            f"CA-12 {process_type} runtime",
            "REQ-CA12-INSPECTION-1",
        )
        name = frappe.db.get_value(
            "Ferum Project Process Step",
            {"project_process": process["project_process"]},
            "name",
        )
        return frappe.get_doc("Ferum Project Process Step", name)
