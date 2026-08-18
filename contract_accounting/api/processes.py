"""Typed CA-11 commands for versioned process generation, evidence and gates."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime, time
from typing import Any, Final, TypeVar
from uuid import uuid4

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from contract_accounting.domain.deadline import (
	CalendarSnapshot,
	DeadlineRule,
	DeadlineRuleError,
	calculate_deadline,
)
from contract_accounting.domain.json_logic import JsonLogicRuleError, evaluate_rule
from contract_accounting.domain.process import (
	ProcessRuleError,
	canonical_snapshot,
	derive_step_state,
	failed_blocking_steps,
	validate_step_transition,
)
from contract_accounting.infrastructure.process_guard import (
	EVENT_WRITER_FLAG,
	EVIDENCE_WRITER_FLAG,
	GATE_WRITER_FLAG,
	PROCESS_TRANSITION_FLAG,
	PROCESS_WRITER_FLAG,
	TEMPLATE_PUBLISH_FLAG,
	parse_json_object,
	parse_rule,
)

_T = TypeVar("_T")
_TEMPLATE_ROLES: Final[frozenset[str]] = frozenset(
	{"Владелец процесса", "Руководитель проектов", "System Manager"}
)
_PROCESS_ROLES: Final[frozenset[str]] = frozenset(
	{"Владелец процесса", "Менеджер проектов", "Руководитель проектов", "System Manager"}
)
_OVERRIDE_ROLES: Final[frozenset[str]] = frozenset(
	{"Руководитель проектов", "System Manager"}
)
_TEMPLATE_FIELDS: Final[tuple[str, ...]] = (
	"code", "title", "version", "process_type", "company", "scope_rule",
	"effective_from", "effective_to", "change_note", "supersedes",
)
_STAGE_FIELDS: Final[tuple[str, ...]] = (
	"stage_code", "title", "description", "sequence", "purpose", "entry_rule",
	"exit_rule", "default_owner_role", "gate_policy", "parallelism", "active",
)
_STEP_FIELDS: Final[tuple[str, ...]] = (
	"step_code", "title", "description", "sequence", "action_type", "step_type",
	"requirement_source_policy", "requirement_match_rule", "input_description",
	"responsible_role", "responsible_user", "approver_role", "depends_on_step_codes",
	"deadline_type", "absolute_due_at", "trigger_event", "offset_days", "offset_unit",
	"calendar_reference", "warning_days", "escalation_days", "condition_rule",
	"activation_rule", "criticality", "blocking", "completion_evidence_type",
	"failure_action", "timeout_action", "active",
)
_JSON_SNAPSHOT_FIELDS: Final[frozenset[str]] = frozenset(
	{
		"scope_rule",
		"entry_rule",
		"exit_rule",
		"gate_policy",
		"requirement_match_rule",
		"condition_rule",
		"activation_rule",
	}
)


@frappe.whitelist(methods=["POST"])
def publish_process_template(process_template: str) -> dict[str, Any]:
	"""Freeze one complete graph; subsequent changes require a new version."""

	_require_role(_TEMPLATE_ROLES, "publish Process Template")
	doc = _authorized("Ferum Process Template", process_template, "write")
	if doc.status != "Draft":
		frappe.throw(_("Только Draft Process Template можно публиковать."))
	stages = frappe.get_all(
		"Ferum Stage Template",
		filters={"process_template": doc.name, "active": 1},
		fields=["name", "stage_code", "sequence"],
		order_by="sequence asc, name asc",
	)
	if not stages:
		frappe.throw(_("Process Template требует минимум одну active stage."))
	step_count = 0
	for stage in stages:
		steps = frappe.get_all(
			"Ferum Step Template",
			filters={"stage_template": stage.name, "active": 1},
			fields=["name", "step_code", "depends_on_step_codes"],
			order_by="sequence asc, name asc",
		)
		if not steps:
			frappe.throw(_("Каждая active stage требует минимум один active step."))
		_validate_dependency_graph(steps)
		step_count += len(steps)
	previous = frappe.flags.get(TEMPLATE_PUBLISH_FLAG)
	frappe.flags[TEMPLATE_PUBLISH_FLAG] = True
	try:
		doc.status = "Published"
		doc.published_at = now_datetime()
		doc.published_by = frappe.session.user
		doc.save(ignore_permissions=True)
	finally:
		frappe.flags[TEMPLATE_PUBLISH_FLAG] = previous
	return {
		"process_template": doc.name,
		"status": doc.status,
		"version": doc.version,
		"stage_count": len(stages),
		"step_count": step_count,
	}


@frappe.whitelist(methods=["POST"])
def generate_project_process(
	service_project: str,
	process_template: str,
	generation_key: str,
	generation_reason: str,
	requirement_revision: str,
	triggered_at: str | None = None,
	calendar_snapshot: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
	"""Create one frozen process graph, or return the exact idempotent instance."""

	_require_role(_PROCESS_ROLES, "generate Project Process")
	key = _required(generation_key, "generation_key")
	reason = _required(generation_reason, "generation_reason")
	revision = _required(requirement_revision, "requirement_revision")
	existing = frappe.db.get_value(
		"Ferum Project Process",
		{"generation_key": key},
		("name", "service_project", "process_template"),
		as_dict=True,
	)
	if existing:
		if (existing.service_project, existing.process_template) != (
			service_project,
			process_template,
		):
			frappe.throw(_("generation_key уже принадлежит другому process context."))
		return _process_result(existing.name, created=False)

	project = _authorized("Ferum Service Project", service_project, "read")
	template = _authorized("Ferum Process Template", process_template, "read")
	if template.status != "Published":
		frappe.throw(_("Generation требует Published Process Template."))
	project_context = _project_context(project)
	if not _matches(parse_rule(template.scope_rule, "scope_rule"), {"project": project_context}):
		frappe.throw(_("Process Template scope не применим к Service Project."))
	stages = frappe.get_all(
		"Ferum Stage Template",
		filters={"process_template": template.name, "active": 1},
		fields=["name"],
		order_by="sequence asc, name asc",
	)
	if not stages:
		frappe.throw(_("Published template graph пуст."))
	calendar = _calendar(calendar_snapshot) if calendar_snapshot else None
	trigger = get_datetime(triggered_at) if triggered_at else None
	save_point = f"ca11_generate_{uuid4().hex}"
	frappe.db.savepoint(save_point)
	try:
		process_snapshot, _hash = canonical_snapshot(
			{"template": _snapshot(template, _TEMPLATE_FIELDS), "stage_names": [row.name for row in stages]}
		)
		process = frappe.get_doc(
			{
				"doctype": "Ferum Project Process",
				"service_project": project.name,
				"process_template": template.name,
				"process_type": template.process_type,
				"template_version": template.version,
				"template_snapshot": process_snapshot,
				"generation_key": key,
				"generated_at": now_datetime(),
				"generated_by": frappe.session.user,
				"status": "Active",
				"started_on": now_datetime(),
				"generation_reason": reason,
				"requirement_revision": revision,
			}
		)
		_with_flag(PROCESS_WRITER_FLAG, True, lambda: process.insert(ignore_permissions=True))
		created_stages: list[Any] = []
		step_count = 0
		for stage_index, stage_row in enumerate(stages):
			stage_template = frappe.get_doc("Ferum Stage Template", stage_row.name)
			stage_snapshot, _stage_hash = canonical_snapshot(
				_snapshot(stage_template, _STAGE_FIELDS)
			)
			stage = frappe.get_doc(
				{
					"doctype": "Ferum Project Stage",
					"service_project": project.name,
					"project_process": process.name,
					"stage_template": stage_template.name,
					"stage_code": stage_template.stage_code,
					"title": stage_template.title,
					"stage_snapshot": stage_snapshot,
					"sequence": stage_template.sequence,
					"status": "Active" if stage_index == 0 else "Planned",
					"actual_start": now_datetime() if stage_index == 0 else None,
					"owner_role": stage_template.default_owner_role,
					"entry_result": "{}",
					"exit_result": "{}",
				}
			)
			_with_flag(
				PROCESS_WRITER_FLAG,
				True,
				lambda stage=stage: stage.insert(ignore_permissions=True),
			)
			created_stages.append(stage)
			step_count += _generate_stage_steps(
				project=project,
				process=process,
				stage=stage,
				stage_template=stage_template,
				project_context=project_context,
				trigger=trigger,
				calendar=calendar,
				activate=stage_index == 0,
			)
			_create_gate(stage)
		_with_flag(
			PROCESS_TRANSITION_FLAG,
			True,
			lambda: _set_process_active_stage(process, created_stages[0].name),
		)
		_event(
			event_type="Process Generated",
			source_doctype=process.doctype,
			source_name=process.name,
			service_project=project.name,
			project_process=process.name,
			payload={"generation_key": key, "stage_count": len(created_stages), "step_count": step_count},
			idempotency_key=f"process-generated:{key}",
		)
		return _process_result(process.name, created=True)
	except BaseException:
		frappe.db.rollback(save_point=save_point)
		raise


@frappe.whitelist(methods=["POST"])
def add_process_evidence(
	process_step: str,
	evidence_type: str,
	source_doctype: str | None = None,
	source_name: str | None = None,
	evidence_file: str | None = None,
	comment: str | None = None,
	snapshot: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
	"""Capture immutable provenance; validation is a separate command."""

	step = _authorized_step(process_step)
	_require_step_executor(step)
	if evidence_type != step.completion_evidence_type or evidence_type == "None":
		frappe.throw(_("Evidence type не совпадает с completion_evidence_type шага."))
	if source_doctype and source_name:
		source = _authorized(source_doctype, source_name, "read")
		if evidence_type == "Inspection":
			if source_doctype != "Ferum Inspection" or source.status != "Approved":
				frappe.throw(_("Inspection evidence требует Approved Ferum Inspection."))
			if source.process_step != step.name:
				frappe.throw(_("Inspection evidence относится к другому Process Step."))
		source_modified = source.modified
	else:
		source_modified = None
	if evidence_file:
		file_hash = frappe.db.get_value("File", evidence_file, "content_hash")
		if not file_hash:
			frappe.throw(_("Evidence File требует content_hash."))
	else:
		file_hash = None
	snapshot_object = _json_object(snapshot, "snapshot")
	payload = {
		"process_step": step.name,
		"evidence_type": evidence_type,
		"source_doctype": source_doctype,
		"source_name": source_name,
		"source_modified": source_modified,
		"evidence_file": evidence_file,
		"file_hash": file_hash,
		"snapshot": snapshot_object,
		"captured_by": frappe.session.user,
	}
	snapshot_json, content_hash = canonical_snapshot(payload)
	evidence_key = f"{step.name}:{evidence_type}:{source_doctype or '-'}:{source_name or content_hash}"
	existing = frappe.db.get_value(
		"Ferum Process Evidence", {"evidence_key": evidence_key}, "name"
	)
	if existing:
		return {"process_evidence": existing, "created": False}
	doc = frappe.get_doc(
		{
			"doctype": "Ferum Process Evidence",
			"process_step": step.name,
			"evidence_type": evidence_type,
			"source_doctype": source_doctype,
			"source_name": source_name,
			"evidence_file": evidence_file,
			"captured_at": now_datetime(),
			"captured_by": frappe.session.user,
			"content_hash": content_hash,
			"snapshot": snapshot_json,
			"comment": comment,
			"is_completion_evidence": 1,
			"evidence_key": evidence_key,
		}
	)
	_with_flag(EVIDENCE_WRITER_FLAG, True, lambda: doc.insert(ignore_permissions=True))
	return {"process_evidence": doc.name, "created": True, "validation_status": doc.validation_status}


@frappe.whitelist(methods=["POST"])
def validate_process_evidence(
	process_evidence: str,
	decision: str,
	comment: str,
) -> dict[str, Any]:
	if decision not in {"Validated", "Rejected"}:
		frappe.throw(_("Evidence decision должен быть Validated или Rejected."))
	evidence = _authorized("Ferum Process Evidence", process_evidence, "read")
	step = _authorized_step(evidence.process_step)
	_require_step_approver(step)
	if evidence.validation_status != "Draft":
		frappe.throw(_("Evidence уже рассмотрено."))
	evidence.validation_status = decision
	evidence.validated_at = now_datetime()
	evidence.validated_by = frappe.session.user
	evidence.comment = _required(comment, "comment")
	_with_flag(EVIDENCE_WRITER_FLAG, True, lambda: evidence.save(ignore_permissions=True))
	_event(
		event_type=f"Evidence {decision}",
		source_doctype=evidence.doctype,
		source_name=evidence.name,
		service_project=step.service_project,
		project_process=step.project_process,
		payload={"process_step": step.name, "decision": decision},
	)
	return {"process_evidence": evidence.name, "validation_status": decision}


@frappe.whitelist(methods=["POST"])
def transition_process_step(
	process_step: str,
	target_status: str,
	reason: str | None = None,
	not_applicable_reason: str | None = None,
) -> dict[str, Any]:
	"""Move only the base FSM; Overdue remains a derived projection."""

	locked = frappe.db.get_value(
		"Ferum Project Process Step",
		process_step,
		("name", "status"),
		as_dict=True,
		for_update=True,
	)
	if not locked:
		frappe.throw(_("Project Process Step не найден."), frappe.DoesNotExistError)
	step = _authorized_step(process_step)
	_require_step_actor(step, target_status)
	if target_status in {"Completed", "Not Applicable"} and (
		step.template_step_code == "PERSONNEL_READY"
		or step.action_type == "Personnel Readiness"
	):
		frappe.throw(
			_("PERSONNEL READY заблокирован до закрытия MG-CA-015; обход через Completed/Not Applicable запрещён.")
		)
	if target_status in {"Ready", "In Progress"}:
		_require_dependencies_complete(step)
		_require_step_condition(step)
	has_evidence = bool(
		frappe.db.exists(
			"Ferum Process Evidence",
			{
				"process_step": step.name,
				"evidence_type": step.completion_evidence_type,
				"validation_status": "Validated",
				"is_completion_evidence": 1,
			},
		)
	)
	try:
		validate_step_transition(
			locked.status,
			target_status,
			reason=reason,
			not_applicable_reason=not_applicable_reason,
			has_required_evidence=has_evidence,
			required_evidence_type=step.completion_evidence_type,
		)
	except ProcessRuleError as exc:
		frappe.throw(_("Недопустимый Process Step transition: {0}.").format(str(exc)))
	step.status = target_status
	step.display_status = target_status
	step.is_overdue = 0
	step.overdue_since = None
	step.transition_reason = reason
	step.not_applicable_reason = not_applicable_reason if target_status == "Not Applicable" else None
	if target_status == "Completed":
		step.completed_at = now_datetime()
		step.completed_by = frappe.session.user
	_with_flag(PROCESS_TRANSITION_FLAG, True, lambda: step.save(ignore_permissions=True))
	_sync_todo(step)
	_event(
		event_type="Step Transition",
		source_doctype=step.doctype,
		source_name=step.name,
		service_project=step.service_project,
		project_process=step.project_process,
		payload={"from_status": locked.status, "to_status": target_status, "reason": reason},
	)
	return {"process_step": step.name, "status": step.status, "display_status": step.display_status}


@frappe.whitelist()
def get_step_projection(process_step: str, as_of: str | None = None) -> dict[str, Any]:
	step = _authorized_step(process_step)
	as_of_value = get_datetime(as_of) if as_of else None
	state = derive_step_state(
		step.status,
		due_at=get_datetime(step.due_at) if step.due_at else None,
		as_of=as_of_value,
	)
	return {
		"process_step": step.name,
		"base_status": state.base_status,
		"is_overdue": state.is_overdue,
		"overdue_since": state.overdue_since,
		"display_status": state.display_status,
		"due_at": step.due_at,
		"warning_at": step.warning_at,
		"escalation_at": step.escalation_at,
		"time_rules": "explicit_as_of" if as_of_value else "disabled_pending_MG-CA-013",
	}


@frappe.whitelist(methods=["POST"])
def evaluate_stage_gate(project_stage: str) -> dict[str, Any]:
	_require_role(_PROCESS_ROLES, "evaluate Stage Gate")
	stage = _authorized("Ferum Project Stage", project_stage, "read")
	steps = frappe.get_all(
		"Ferum Project Process Step",
		filters={"project_stage": stage.name},
		fields=["name", "template_step_code", "title", "blocking", "status"],
		order_by="name asc",
	)
	failed = failed_blocking_steps([dict(row) for row in steps])
	stage_snapshot = _json_object(stage.stage_snapshot, "stage_snapshot")
	exit_rule = stage_snapshot.get("exit_rule") or {}
	if exit_rule:
		project = frappe.get_doc("Ferum Service Project", stage.service_project)
		context = {
			"project": _project_context(project),
			"gate": {
				"blocking_count": sum(bool(row.blocking) for row in steps),
				"failed_count": len(failed),
			},
		}
		try:
			if not bool(evaluate_rule(exit_rule, context)):
				failed.append({"rule": "stage_exit_rule", "status": "Failed"})
		except JsonLogicRuleError as exc:
			failed.append({"rule": "stage_exit_rule", "status": "Error", "reason": str(exc)})
	status = "Failed" if failed else "Passed"
	gate = _gate(stage)
	gate.status = status
	gate.evaluated_at = now_datetime()
	gate.evaluated_by = frappe.session.user
	gate.criteria = json.dumps(
		{"blocking_steps": [dict(row) for row in steps], "exit_rule": exit_rule},
		ensure_ascii=False,
		default=str,
	)
	gate.failed_criteria = json.dumps(failed, ensure_ascii=False, default=str)
	_with_flag(GATE_WRITER_FLAG, True, lambda: gate.save(ignore_permissions=True))
	return {"stage_gate": gate.name, "status": gate.status, "failed_criteria": failed}


@frappe.whitelist(methods=["POST"])
def override_stage_gate(stage_gate: str, reason: str, evidence: str) -> dict[str, Any]:
	_require_role(_OVERRIDE_ROLES, "override Stage Gate")
	gate = _authorized("Ferum Stage Gate", stage_gate, "read")
	evidence_doc = _authorized("Ferum Process Evidence", evidence, "read")
	if evidence_doc.validation_status != "Validated":
		frappe.throw(_("Gate override требует Validated Process Evidence."))
	evidence_step_process = frappe.db.get_value(
		"Ferum Project Process Step", evidence_doc.process_step, "project_process"
	)
	if evidence_step_process != gate.project_process:
		frappe.throw(_("Gate override evidence относится к другому process."))
	gate.status = "Overridden"
	gate.override_reason = _required(reason, "reason")
	gate.override_authority = frappe.session.user
	gate.override_evidence = evidence_doc.name
	gate.evaluated_at = now_datetime()
	gate.evaluated_by = frappe.session.user
	_with_flag(GATE_WRITER_FLAG, True, lambda: gate.save(ignore_permissions=True))
	return {"stage_gate": gate.name, "status": gate.status}


@frappe.whitelist(methods=["POST"])
def complete_project_stage(project_stage: str) -> dict[str, Any]:
	_require_role(_PROCESS_ROLES, "complete Project Stage")
	stage = _authorized("Ferum Project Stage", project_stage, "read")
	if stage.status != "Active":
		frappe.throw(_("Только Active Project Stage можно завершить."))
	gate = _gate(stage)
	if gate.status not in {"Passed", "Overridden"}:
		frappe.throw(_("Stage Gate не разрешает переход к следующей стадии."))
	process = frappe.get_doc("Ferum Project Process", stage.project_process)
	next_name = frappe.db.get_value(
		"Ferum Project Stage",
		{"project_process": process.name, "sequence": [">", stage.sequence]},
		"name",
		order_by="sequence asc",
	)
	if not next_name and process.process_type == "Launch":
		_require_role(_OVERRIDE_ROLES, "complete Launch Process")
		project_status = frappe.db.get_value(
			"Ferum Service Project", process.service_project, "execution_status"
		)
		if project_status != "Launching":
			frappe.throw(_("Launch Process completion требует execution_status=Launching."))
	stage.status = "Completed"
	stage.actual_end = now_datetime()
	stage.exit_result = json.dumps({"gate": gate.name, "status": gate.status})
	_with_flag(PROCESS_TRANSITION_FLAG, True, lambda: stage.save(ignore_permissions=True))
	if next_name:
		next_stage = frappe.get_doc("Ferum Project Stage", next_name)
		next_stage.status = "Active"
		next_stage.actual_start = now_datetime()
		_with_flag(PROCESS_TRANSITION_FLAG, True, lambda: next_stage.save(ignore_permissions=True))
		_activate_stage_steps(next_stage.name)
		process.active_stage = next_stage.name
	else:
		process.status = "Completed"
		process.completed_on = now_datetime()
		process.active_stage = None
	_with_flag(PROCESS_TRANSITION_FLAG, True, lambda: process.save(ignore_permissions=True))
	if not next_name and process.process_type == "Launch":
		from contract_accounting.api.lifecycle import change_status

		change_status(
			process.service_project,
			target_execution_status="Active",
			reason="All blocking stages of the versioned Launch Process completed",
			comment=f"Launch process {process.name}; final gate {gate.name}",
			evidence=[gate.name],
		)
	_event(
		event_type="Stage Completed",
		source_doctype=stage.doctype,
		source_name=stage.name,
		service_project=stage.service_project,
		project_process=stage.project_process,
		payload={"gate": gate.name, "next_stage": next_name},
	)
	return {
		"project_stage": stage.name,
		"status": stage.status,
		"next_stage": next_name,
		"process_status": process.status,
	}


def _generate_stage_steps(
	*,
	project: Any,
	process: Any,
	stage: Any,
	stage_template: Any,
	project_context: dict[str, Any],
	trigger: datetime | None,
	calendar: CalendarSnapshot | None,
	activate: bool,
) -> int:
	step_names = frappe.get_all(
		"Ferum Step Template",
		filters={"stage_template": stage_template.name, "active": 1},
		pluck="name",
		order_by="sequence asc, name asc",
	)
	count = 0
	for name in step_names:
		template = frappe.get_doc("Ferum Step Template", name)
		requirements: list[Any | None] = [None]
		if template.requirement_source_policy == "Approved One-time Requirement":
			requirements = _matching_requirements(project.name, template)
			if not requirements and template.criticality == "Mandatory":
				frappe.throw(_("Mandatory Step Template не нашёл approved one-time Requirement."))
		for requirement in requirements:
			context = {
				"project": project_context,
				"requirement": _requirement_context(requirement),
			}
			if not _matches(parse_rule(template.activation_rule, "activation_rule"), context):
				continue
			deadline = _step_deadline(template, trigger, calendar)
			snapshot, _snapshot_hash = canonical_snapshot(_snapshot(template, _STEP_FIELDS))
			instance_key = ":".join(
				[process.generation_key, template.step_code, requirement.name if requirement else "-"]
			)
			dependencies = _dependency_codes(template.depends_on_step_codes)
			status = "Ready" if activate and not dependencies else "Planned"
			step = frappe.get_doc(
				{
					"doctype": "Ferum Project Process Step",
					"service_project": project.name,
					"project_process": process.name,
					"project_stage": stage.name,
					"step_template": template.name,
					"template_step_code": template.step_code,
					"title": template.title,
					"step_snapshot": snapshot,
					"instance_key": instance_key,
					"contract_requirement": requirement.name if requirement else None,
					"action_type": template.action_type,
					"input_description": template.input_description,
					"responsible_role": template.responsible_role,
					"responsible_user": template.responsible_user or project.project_manager,
					"approver_role": template.approver_role,
					"depends_on_step_codes": "\n".join(dependencies),
					"deadline_type": template.deadline_type,
					**deadline,
					"condition_rule": template.condition_rule,
					"activation_rule": template.activation_rule,
					"criticality": template.criticality,
					"blocking": template.blocking,
					"completion_evidence_type": template.completion_evidence_type,
					"failure_action": template.failure_action,
					"timeout_action": template.timeout_action,
					"status": status,
					"display_status": status,
				}
			)
			_with_flag(
				PROCESS_WRITER_FLAG,
				True,
				lambda step=step: step.insert(ignore_permissions=True),
			)
			_sync_todo(step)
			count += 1
	return count


def _step_deadline(
	template: Any,
	trigger: datetime | None,
	calendar: CalendarSnapshot | None,
) -> dict[str, Any]:
	if template.deadline_type == "None":
		return {}
	if template.deadline_type == "Absolute":
		return {"due_at": template.absolute_due_at}
	if trigger is None or calendar is None:
		frappe.throw(_("Relative deadline требует explicit trigger и immutable calendar snapshot."))
	try:
		result = calculate_deadline(
			triggered_at=trigger,
			rule=DeadlineRule(
				offset_days=template.offset_days,
				offset_unit=template.offset_unit,
				warning_days=template.warning_days,
				escalation_days=template.escalation_days,
			),
			calendar=calendar,
		)
	except DeadlineRuleError as exc:
		frappe.throw(_("Relative deadline не рассчитан: {0}.").format(str(exc)))
	return {
		"triggered_at": result.triggered_at.replace(tzinfo=None),
		"due_at": result.due_at.replace(tzinfo=None),
		"warning_at": result.warning_at.replace(tzinfo=None),
		"escalation_at": result.escalation_at.replace(tzinfo=None),
		"calendar_snapshot_hash": result.snapshot_hash,
	}


def _calendar(value: str | dict[str, Any]) -> CalendarSnapshot:
	payload = _json_object(value, "calendar_snapshot")
	try:
		return CalendarSnapshot(
			timezone=str(payload["timezone"]),
			revision=str(payload["revision"]),
			holidays=frozenset(date.fromisoformat(item) for item in payload.get("holidays", [])),
			weekend_days=frozenset(int(item) for item in payload.get("weekend_days", [5, 6])),
			cutoff_time=time.fromisoformat(payload.get("cutoff_time", "23:59:59")),
			after_cutoff_policy=str(payload.get("after_cutoff_policy", "Same Day")),
		)
	except (KeyError, TypeError, ValueError, DeadlineRuleError) as exc:
		frappe.throw(_("Некорректный immutable calendar snapshot: {0}.").format(str(exc)))
		raise AssertionError from exc


def _matching_requirements(service_project: str, template: Any) -> list[Any]:
	rule = parse_rule(template.requirement_match_rule, "requirement_match_rule")
	rows = frappe.get_all(
		"Ferum Contract Requirement",
		filters={
			"service_project": service_project,
			"assessment_status": "Approved",
			"applicability": "Applicable",
			"routing_decision": "One-time Process Step",
		},
		pluck="name",
		order_by="name asc",
	)
	result = []
	for name in rows:
		doc = frappe.get_doc("Ferum Contract Requirement", name)
		if _matches(rule, {"requirement": _requirement_context(doc)}):
			result.append(doc)
	return result


def _requirement_context(doc: Any | None) -> dict[str, Any]:
	if doc is None:
		return {}
	return {
		"name": doc.name,
		"requirement_type": doc.requirement_type,
		"requirement_source": doc.requirement_source,
		"applicability": doc.applicability,
		"routing_decision": doc.routing_decision,
		"value_data": doc.value_data,
		"value_number": doc.value_number,
		"value_check": bool(doc.value_check),
	}


def _project_context(project: Any) -> dict[str, Any]:
	return {
		"name": project.name,
		"company": project.company,
		"customer": project.customer,
		"legal_status": project.legal_status,
		"execution_status": project.execution_status,
		"procurement_law": project.procurement_law,
	}


def _matches(rule: dict[str, Any], context: dict[str, Any]) -> bool:
	if not rule:
		return True
	try:
		return bool(evaluate_rule(rule, context))
	except JsonLogicRuleError as exc:
		frappe.throw(_("JSON Logic evaluation failed closed: {0}.").format(str(exc)))
		raise AssertionError from exc


def _create_gate(stage: Any) -> Any:
	gate = frappe.get_doc(
		{
			"doctype": "Ferum Stage Gate",
			"service_project": stage.service_project,
			"project_process": stage.project_process,
			"project_stage": stage.name,
			"gate_code": "EXIT",
			"title": f"{stage.title} Exit Gate",
			"evaluation_mode": "All Blocking Steps",
			"status": "Not Evaluated",
			"criteria": "{}",
			"failed_criteria": "[]",
		}
	)
	_with_flag(GATE_WRITER_FLAG, True, lambda: gate.insert(ignore_permissions=True))
	stage.primary_exit_gate = gate.name
	_with_flag(PROCESS_TRANSITION_FLAG, True, lambda: stage.save(ignore_permissions=True))
	return gate


def _gate(stage: Any) -> Any:
	name = stage.primary_exit_gate or frappe.db.get_value(
		"Ferum Stage Gate", {"project_stage": stage.name, "gate_code": "EXIT"}, "name"
	)
	if not name:
		return _create_gate(stage)
	return frappe.get_doc("Ferum Stage Gate", name)


def _activate_stage_steps(project_stage: str) -> None:
	for name in frappe.get_all(
		"Ferum Project Process Step",
		filters={"project_stage": project_stage, "status": "Planned"},
		pluck="name",
	):
		step = frappe.get_doc("Ferum Project Process Step", name)
		if _dependency_codes(step.depends_on_step_codes):
			continue
		step.status = "Ready"
		step.display_status = "Ready"
		_with_flag(
			PROCESS_TRANSITION_FLAG,
			True,
			lambda step=step: step.save(ignore_permissions=True),
		)
		_sync_todo(step)


def _require_dependencies_complete(step: Any) -> None:
	for code in _dependency_codes(step.depends_on_step_codes):
		statuses = frappe.get_all(
			"Ferum Project Process Step",
			filters={"project_process": step.project_process, "template_step_code": code},
			pluck="status",
		)
		if not statuses or any(status not in {"Completed", "Not Applicable"} for status in statuses):
			frappe.throw(_("Step dependency не завершена: {0}.").format(code))


def _require_step_condition(step: Any) -> None:
	rule = parse_rule(step.condition_rule, "condition_rule")
	if not rule:
		return
	project = frappe.get_doc("Ferum Service Project", step.service_project)
	requirement = (
		frappe.get_doc("Ferum Contract Requirement", step.contract_requirement)
		if step.contract_requirement
		else None
	)
	context = {
		"project": _project_context(project),
		"requirement": _requirement_context(requirement),
		"step": {"status": step.status, "criticality": step.criticality, "blocking": bool(step.blocking)},
	}
	if not _matches(rule, context):
		frappe.throw(_("Process Step condition не выполнено."))


def _sync_todo(step: Any) -> None:
	if not step.responsible_user:
		return
	filters = {
		"reference_type": step.doctype,
		"reference_name": step.name,
		"allocated_to": step.responsible_user,
	}
	name = frappe.db.get_value("ToDo", filters, "name")
	if step.status in {"Completed", "Not Applicable", "Cancelled"}:
		if name:
			frappe.db.set_value("ToDo", name, "status", "Closed", update_modified=False)
		return
	if step.status not in {"Ready", "In Progress", "Waiting External", "Waiting Approval", "Blocked"}:
		return
	if not name:
		frappe.get_doc(
			{
				"doctype": "ToDo",
				"allocated_to": step.responsible_user,
				"assigned_by": frappe.session.user,
				"reference_type": step.doctype,
				"reference_name": step.name,
				"description": step.title,
				"status": "Open",
				"date": step.due_at,
			}
		).insert(ignore_permissions=True)


def _event(
	*,
	event_type: str,
	source_doctype: str,
	source_name: str,
	service_project: str,
	project_process: str | None,
	payload: dict[str, Any],
	idempotency_key: str | None = None,
) -> None:
	payload_json, event_hash = canonical_snapshot(payload)
	event = frappe.get_doc(
		{
			"doctype": "Ferum Process Event",
			"event_type": event_type,
			"source_doctype": source_doctype,
			"source_name": source_name,
			"service_project": service_project,
			"project_process": project_process,
			"occurred_at": now_datetime(),
			"actor": frappe.session.user,
			"payload_snapshot": payload_json,
			"idempotency_key": idempotency_key or uuid4().hex,
			"event_hash": event_hash,
		}
	)
	_with_flag(EVENT_WRITER_FLAG, True, lambda: event.insert(ignore_permissions=True))


def _require_step_actor(step: Any, target_status: str) -> None:
	if target_status == "Completed" and step.approver_role:
		if step.status != "Waiting Approval":
			frappe.throw(_("Step с approver завершается только из Waiting Approval."))
		_require_role(frozenset({step.approver_role, "System Manager"}), "approve step")
		return
	if frappe.session.user == "Administrator" or set(frappe.get_roles()).intersection(_PROCESS_ROLES):
		return
	if step.responsible_user == frappe.session.user or step.responsible_role in frappe.get_roles():
		return
	frappe.throw(_("Пользователь не является исполнителем Process Step."), frappe.PermissionError)


def _require_step_executor(step: Any) -> None:
	if frappe.session.user == "Administrator" or set(frappe.get_roles()).intersection(_PROCESS_ROLES):
		return
	if step.responsible_user == frappe.session.user or step.responsible_role in frappe.get_roles():
		return
	frappe.throw(_("Пользователь не является исполнителем Process Step."), frappe.PermissionError)


def _require_step_approver(step: Any) -> None:
	roles = {"Руководитель проектов", "System Manager"}
	if step.approver_role:
		roles.add(step.approver_role)
	_require_role(frozenset(roles), "validate Process Evidence")


def _authorized_step(name: str) -> Any:
	return _authorized("Ferum Project Process Step", name, "read")


def _authorized(doctype: str, name: str, permission_type: str) -> Any:
	if not frappe.db.exists(doctype, name):
		frappe.throw(_("{0} не найден: {1}.").format(doctype, name), frappe.DoesNotExistError)
	doc = frappe.get_doc(doctype, name)
	doc.check_permission(permission_type)
	return doc


def _process_result(name: str, *, created: bool) -> dict[str, Any]:
	process = frappe.get_doc("Ferum Project Process", name)
	return {
		"project_process": process.name,
		"created": created,
		"status": process.status,
		"template_version": process.template_version,
		"active_stage": process.active_stage,
		"stage_count": frappe.db.count("Ferum Project Stage", {"project_process": process.name}),
		"step_count": frappe.db.count("Ferum Project Process Step", {"project_process": process.name}),
	}


def _set_process_active_stage(process: Any, name: str) -> None:
	process.active_stage = name
	process.save(ignore_permissions=True)


def _snapshot(document: Any, fields: tuple[str, ...]) -> dict[str, Any]:
	result: dict[str, Any] = {}
	for field in fields:
		value = document.get(field)
		if field in _JSON_SNAPSHOT_FIELDS:
			value = _json_object(value, field)
		result[field] = value
	return result


def _dependency_codes(value: str | None) -> list[str]:
	return sorted(
		{
			item.strip().upper()
			for item in (value or "").replace("\n", ",").split(",")
			if item.strip()
		}
	)


def _validate_dependency_graph(steps: list[Any]) -> None:
	codes = {str(row.step_code).upper() for row in steps}
	dependencies = {
		str(row.step_code).upper(): _dependency_codes(row.depends_on_step_codes)
		for row in steps
	}
	unknown = sorted({item for values in dependencies.values() for item in values if item not in codes})
	if unknown:
		frappe.throw(_("Unknown dependency step codes: {0}.").format(", ".join(unknown)))
	visiting: set[str] = set()
	visited: set[str] = set()

	def visit(code: str) -> None:
		if code in visiting:
			frappe.throw(_("Process Template dependency cycle обнаружен."))
		if code in visited:
			return
		visiting.add(code)
		for dependency in dependencies[code]:
			visit(dependency)
		visiting.remove(code)
		visited.add(code)

	for code in sorted(codes):
		visit(code)


def _json_object(value: str | dict[str, Any] | None, fieldname: str) -> dict[str, Any]:
	return parse_json_object(value, fieldname)


def _required(value: str | None, fieldname: str) -> str:
	text = (value or "").strip()
	if not text:
		frappe.throw(_("{0} обязателен.").format(fieldname))
	return text


def _require_role(roles: frozenset[str], operation: str) -> None:
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles()).intersection(roles):
		frappe.throw(_("Недостаточно прав: {0}.").format(operation), frappe.PermissionError)


def _with_flag(flag: str, value: Any, callback: Callable[[], _T]) -> _T:
	previous = frappe.flags.get(flag)
	frappe.flags[flag] = value
	try:
		return callback()
	finally:
		frappe.flags[flag] = previous
