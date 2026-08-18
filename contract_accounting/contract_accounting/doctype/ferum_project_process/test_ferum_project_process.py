"""Bench runtime acceptance for the CA-11 BPM core vertical slice."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from contract_accounting.api.processes import (
	add_process_evidence,
	complete_project_stage,
	evaluate_stage_gate,
	generate_project_process,
	get_step_projection,
	publish_process_template,
	transition_process_step,
	validate_process_evidence,
)
from contract_accounting.contract_accounting.doctype.ferum_service_project.test_ferum_service_project import (
	_make_project,
)


class TestProjectProcess(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		self._previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.project = _make_project()
		self.project.project_manager = "Administrator"
		self.project.save(ignore_permissions=True)
		self._generation_keys: dict[str, str] = {}
		self.template, self.stage_templates, self.step_templates = self._make_template(version=1)
		publish_process_template(self.template.name)

	def tearDown(self) -> None:
		frappe.set_user(self._previous_user)
		super().tearDown()

	def test_generation_is_idempotent_and_published_v1_is_frozen(self) -> None:
		first = self._generate("version-freeze")
		second = self._generate("version-freeze")
		self.assertTrue(first["created"])
		self.assertFalse(second["created"])
		self.assertEqual(first["project_process"], second["project_process"])
		self.assertEqual((first["stage_count"], first["step_count"]), (2, 2))

		published_step = frappe.get_doc("Ferum Step Template", self.step_templates[0].name)
		published_step.title = "Forbidden mutation"
		with self.assertRaises(frappe.PermissionError):
			published_step.save(ignore_permissions=True)

		v2, _stages, _steps = self._make_template(
			version=2,
			code=self.template.code,
			supersedes=self.template.name,
		)
		publish_process_template(v2.name)
		process = frappe.get_doc("Ferum Project Process", first["project_process"])
		self.assertEqual(process.template_version, 1)
		self.assertEqual(process.process_template, self.template.name)
		self.assertIn('"version":1', process.template_snapshot)

	def test_completion_requires_validated_evidence_and_gate_opens_next_stage(self) -> None:
		result = self._generate("evidence-gate")
		stage = self._stage(result["project_process"], 1)
		step = self._step(stage.name)
		transition_process_step(step.name, "In Progress")
		with self.assertRaises(frappe.ValidationError):
			transition_process_step(step.name, "Completed")

		evidence = add_process_evidence(
			step.name,
			"Manual Confirmation",
			comment="Runtime completion proof",
			snapshot={"confirmed": True, "actor": "Administrator"},
		)
		validate_process_evidence(
			evidence["process_evidence"],
			"Validated",
			"Accepted runtime evidence",
		)
		transition_process_step(step.name, "Completed")
		todo_status = frappe.db.get_value(
			"ToDo",
			{
				"reference_type": "Ferum Project Process Step",
				"reference_name": step.name,
			},
			"status",
		)
		self.assertEqual(todo_status, "Closed")

		gate = evaluate_stage_gate(stage.name)
		self.assertEqual(gate["status"], "Passed")
		completion = complete_project_stage(stage.name)
		self.assertEqual(completion["status"], "Completed")
		self.assertIsNotNone(completion["next_stage"])
		next_stage = frappe.get_doc("Ferum Project Stage", completion["next_stage"])
		self.assertEqual(next_stage.status, "Active")
		self.assertEqual(self._step(next_stage.name).status, "Ready")

	def test_failed_gate_blocks_stage_transition(self) -> None:
		result = self._generate("failed-gate")
		stage = self._stage(result["project_process"], 1)
		gate = evaluate_stage_gate(stage.name)
		self.assertEqual(gate["status"], "Failed")
		self.assertEqual(gate["failed_criteria"][0]["status"], "Ready")
		with self.assertRaises(frappe.ValidationError):
			complete_project_stage(stage.name)
		self.assertEqual(frappe.db.get_value("Ferum Project Stage", stage.name, "status"), "Active")

	def test_relative_deadline_and_overdue_are_explicit_derived_projection(self) -> None:
		result = self._generate("deadline")
		step = self._step(self._stage(result["project_process"], 1).name)
		self.assertEqual(str(step.due_at)[:10], "2026-08-20")
		self.assertEqual(str(step.warning_at)[:10], "2026-08-19")
		self.assertEqual(str(step.escalation_at)[:10], "2026-08-24")
		unclassified = get_step_projection(step.name)
		self.assertEqual(unclassified["display_status"], "Ready")
		self.assertFalse(unclassified["is_overdue"])
		overdue = get_step_projection(step.name, as_of="2026-08-21 12:00:00")
		self.assertEqual(overdue["base_status"], "Ready")
		self.assertEqual(overdue["display_status"], "Overdue")
		self.assertTrue(overdue["is_overdue"])
		self.assertEqual(frappe.db.get_value(step.doctype, step.name, "status"), "Ready")

	def test_direct_instance_and_event_writes_are_denied(self) -> None:
		result = self._generate("typed-writer")
		step = self._step(self._stage(result["project_process"], 1).name)
		step.title = "Direct mutation"
		with self.assertRaises(frappe.PermissionError):
			step.save(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "Ferum Process Event",
					"event_type": "Forged",
					"source_doctype": step.doctype,
					"source_name": step.name,
					"service_project": self.project.name,
					"project_process": result["project_process"],
					"occurred_at": "2026-08-18 12:00:00",
					"actor": "Administrator",
					"payload_snapshot": "{}",
					"idempotency_key": uuid4().hex,
					"event_hash": "forged",
				}
			).insert(ignore_permissions=True)

	def _generate(self, suffix: str) -> dict[str, object]:
		generation_key = self._generation_keys.setdefault(
			suffix, f"CA11-{suffix}-{uuid4().hex[:8]}"
		)
		return generate_project_process(
			self.project.name,
			self.template.name,
			generation_key,
			"CA-11 runtime acceptance",
			"REQ-REV-1",
			triggered_at="2026-08-17 10:00:00",
			calendar_snapshot={
				"timezone": "Europe/Moscow",
				"revision": "CA11-RUNTIME-1",
				"holidays": ["2026-08-18"],
				"weekend_days": [5, 6],
				"cutoff_time": "18:00:00",
				"after_cutoff_policy": "Same Day",
			},
		)

	def _make_template(
		self,
		*,
		version: int,
		code: str | None = None,
		supersedes: str | None = None,
	):
		process_template = frappe.get_doc(
			{
				"doctype": "Ferum Process Template",
				"code": code or f"CA11-{uuid4().hex[:10]}",
				"title": f"CA-11 Runtime v{version}",
				"version": version,
				"process_type": "Other",
				"scope_rule": "{}",
				"effective_from": date(2026, 8, 17),
				"status": "Draft",
				"change_note": f"Runtime template version {version}",
				"supersedes": supersedes,
			}
		).insert(ignore_permissions=True)
		stages = []
		steps = []
		for sequence in (1, 2):
			stage = frappe.get_doc(
				{
					"doctype": "Ferum Stage Template",
					"process_template": process_template.name,
					"stage_code": f"STAGE-{sequence}",
					"title": f"Stage {sequence}",
					"sequence": sequence,
					"entry_rule": "{}",
					"exit_rule": "{}",
					"gate_policy": "{}",
					"default_owner_role": "Менеджер проектов",
					"active": 1,
				}
			).insert(ignore_permissions=True)
			stages.append(stage)
			step = frappe.get_doc(
				{
					"doctype": "Ferum Step Template",
					"stage_template": stage.name,
					"step_code": f"STEP-{sequence}",
					"title": f"Step {sequence}",
					"sequence": sequence,
					"action_type": "Manual Confirmation",
					"step_type": "Manual",
					"requirement_source_policy": "None",
					"requirement_match_rule": "{}",
					"responsible_role": "Менеджер проектов",
					"responsible_user": "Administrator",
					"deadline_type": "Relative" if sequence == 1 else "None",
					"trigger_event": "Project Started" if sequence == 1 else None,
					"offset_days": 2,
					"offset_unit": "Business Days",
					"warning_days": 1,
					"escalation_days": 2,
					"condition_rule": "{}",
					"activation_rule": "{}",
					"criticality": "Mandatory",
					"blocking": 1,
					"completion_evidence_type": "Manual Confirmation" if sequence == 1 else "None",
					"failure_action": "Escalate to Project Manager",
					"timeout_action": "Notify Department Head",
					"active": 1,
				}
			).insert(ignore_permissions=True)
			steps.append(step)
		return process_template, stages, steps

	@staticmethod
	def _stage(project_process: str, sequence: int):
		name = frappe.db.get_value(
			"Ferum Project Stage",
			{"project_process": project_process, "sequence": sequence},
			"name",
		)
		return frappe.get_doc("Ferum Project Stage", name)

	@staticmethod
	def _step(project_stage: str):
		name = frappe.db.get_value(
			"Ferum Project Process Step", {"project_stage": project_stage}, "name"
		)
		return frappe.get_doc("Ferum Project Process Step", name)
