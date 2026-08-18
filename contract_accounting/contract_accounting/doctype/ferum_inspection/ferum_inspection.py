"""Initial/repeat inspection fact with frozen context and guarded lifecycle."""

from __future__ import annotations

import json
from typing import Final

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime

DOCTYPE: Final[str] = "Ferum Inspection"
INSPECTION_WRITE_FLAG: Final[str] = "contract_accounting_inspection_write"
STATUS_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "Planned": frozenset({"In Progress", "Cancelled"}),
    "In Progress": frozenset({"Completed", "Cancelled"}),
    "Completed": frozenset({"Approved"}),
    "Approved": frozenset(),
    "Cancelled": frozenset(),
}
TEAM_MEMBER_DOCTYPES: Final[frozenset[str]] = frozenset(
    {"User", "Employee", "Ferum Contractor Worker"}
)
_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "service_project",
    "project_process",
    "process_step",
    "project_object",
    "service_object",
    "object_system",
    "inspection_type",
    "planned_date",
    "template_version_snapshot",
    "idempotency_key",
)


class FerumInspection(Document):
    def validate(self) -> None:
        self._derive_context()
        self._validate_process_step()
        self._validate_json_snapshots()
        self._validate_team()
        self._validate_items()
        self._validate_transition()
        self._validate_state_contract()
        self._freeze_identity()
        self._freeze_approved_fact()

    def on_trash(self) -> None:
        frappe.throw(
            _("Inspection является фактом; отмените вместо удаления."),
            frappe.PermissionError,
        )

    def _derive_context(self) -> None:
        membership = frappe.db.get_value(
            "Ferum Project Object",
            self.project_object,
            ("service_project", "service_object"),
            as_dict=True,
        )
        if not membership:
            frappe.throw(_("Project Object не найден."))
        context = {
            "service_project": membership.service_project,
            "service_object": membership.service_object,
        }
        for fieldname, value in context.items():
            if self.get(fieldname) and self.get(fieldname) != value:
                frappe.throw(_("Inspection context определяется Project Object."))
            self.set(fieldname, value)
        if self.object_system:
            service_object = frappe.db.get_value(
                "Ferum Object System", self.object_system, "service_object"
            )
            if service_object != self.service_object:
                frappe.throw(_("Primary Object System не входит в Service Object."))

    def _validate_process_step(self) -> None:
        if not self.process_step:
            if self.project_process:
                frappe.throw(_("project_process без process_step не разрешён."))
            return
        step = frappe.db.get_value(
            "Ferum Project Process Step",
            self.process_step,
            ("service_project", "project_process", "action_type", "step_snapshot"),
            as_dict=True,
        )
        if not step or step.service_project != self.service_project:
            frappe.throw(_("Inspection Process Step относится к другому проекту."))
        if "inspection" not in str(step.action_type or "").lower():
            frappe.throw(_("Inspection создаётся только из Inspection Process Step."))
        if self.project_process and self.project_process != step.project_process:
            frappe.throw(_("Inspection Project Process не совпадает с Process Step."))
        self.project_process = step.project_process

    def _validate_json_snapshots(self) -> None:
        for fieldname in (
            "template_version_snapshot",
            "system_inventory_snapshot",
            "report_snapshot",
        ):
            value = self.get(fieldname)
            try:
                parsed = json.loads(value) if isinstance(value, str) else value
            except (TypeError, ValueError):
                frappe.throw(_("{0} должен быть JSON object.").format(fieldname))
            if not isinstance(parsed, dict):
                frappe.throw(_("{0} должен быть JSON object.").format(fieldname))
            self.set(fieldname, frappe.as_json(parsed))

    def _validate_team(self) -> None:
        members: set[tuple[str, str]] = set()
        for row in self.get("team") or []:
            if row.member_doctype not in TEAM_MEMBER_DOCTYPES:
                frappe.throw(_("Inspection team member DocType не разрешён."))
            if not frappe.db.exists(row.member_doctype, row.member):
                frappe.throw(_("Inspection team member не найден."))
            key = (row.member_doctype, row.member)
            if key in members:
                frappe.throw(_("Inspection team member продублирован."))
            members.add(key)
            if row.member_doctype == "Ferum Contractor Worker":
                frappe.throw(
                    _("Contractor Worker team data заблокированы до MG-CA-015.")
                )

    def _validate_items(self) -> None:
        codes: set[str] = set()
        for row in self.get("items") or []:
            code = (row.item_code or "").strip().upper()
            if not code or code in codes:
                frappe.throw(_("Inspection item_code обязателен и уникален."))
            codes.add(code)
            row.item_code = code
            service_object = frappe.db.get_value(
                "Ferum Object System", row.object_system, "service_object"
            )
            if service_object != self.service_object:
                frappe.throw(_("Checklist Object System не входит в Service Object."))
            if row.result in {"Observation", "Defect"} and (
                not (row.finding_title or "").strip()
                or not (row.observation or "").strip()
            ):
                frappe.throw(_("Observation/Defect требует title и result detail."))
            if row.photo_file:
                file_row = frappe.db.get_value(
                    "File",
                    row.photo_file,
                    ("content_hash", "attached_to_doctype", "attached_to_name"),
                    as_dict=True,
                )
                if not file_row or not file_row.content_hash:
                    frappe.throw(_("Inspection photo File требует content_hash."))
                if not self.is_new() and (
                    file_row.attached_to_doctype,
                    file_row.attached_to_name,
                ) != (DOCTYPE, self.name):
                    frappe.throw(
                        _("Inspection photo File должен быть прикреплён к Inspection.")
                    )

    def _validate_transition(self) -> None:
        before = self.get_doc_before_save()
        if before is None:
            if self.status != "Planned":
                frappe.throw(_("Новый Inspection создаётся только в Planned."))
            return
        if not frappe.flags.get(INSPECTION_WRITE_FLAG):
            managed = (
                "status",
                "actual_start",
                "actual_end",
                "snapshot_at",
                "outcome",
                "report_snapshot",
                "report_document",
                "manager_approved_at",
                "manager_approved_by",
                "customer_approval",
                "customer_sent_at",
                "customer_sent_by",
                "customer_decided_at",
                "customer_decided_by",
                "cancellation_reason",
                "items",
                "completion_evidence",
            )
            if any(
                self._signature(field) != self._signature(field, before)
                for field in managed
            ):
                frappe.throw(
                    _("Inspection lifecycle меняется только typed command."),
                    frappe.PermissionError,
                )
        old, new = before.status, self.status
        if old != new and new not in STATUS_TRANSITIONS.get(old, frozenset()):
            frappe.throw(
                _("Недопустимый Inspection transition: {0} → {1}.").format(old, new)
            )

    def _validate_state_contract(self) -> None:
        if self.status in {"In Progress", "Completed", "Approved"}:
            if not self.actual_start or not self.snapshot_at:
                frappe.throw(
                    _("Started Inspection требует actual_start и snapshot_at.")
                )
            inventory = json.loads(self.system_inventory_snapshot or "{}")
            if not inventory:
                frappe.throw(
                    _("Started Inspection требует непустой inventory snapshot.")
                )
        if self.status in {"Completed", "Approved"}:
            if (
                not self.actual_end
                or not self.outcome
                or not (self.summary or "").strip()
            ):
                frappe.throw(_("Completed Inspection требует end, outcome и summary."))
            if get_datetime(self.actual_end) < get_datetime(self.actual_start):
                frappe.throw(
                    _("Inspection actual_end не может быть раньше actual_start.")
                )
            if not self.items or any(not row.result for row in self.items):
                frappe.throw(
                    _("Completed Inspection требует полностью заполненный checklist.")
                )
            if not self.completion_evidence or not self.report_document:
                frappe.throw(
                    _("Completed Inspection требует evidence и report document.")
                )
            for row in self.completion_evidence:
                content_hash = frappe.db.get_value("File", row.file, "content_hash")
                if not content_hash or row.content_hash != content_hash:
                    frappe.throw(
                        _(
                            "Inspection evidence должен ссылаться на File и его exact hash."
                        )
                    )
            if not json.loads(self.report_snapshot or "{}"):
                frappe.throw(_("Completed Inspection требует report snapshot."))
        if self.status == "Approved" and (
            not self.manager_approved_at or not self.manager_approved_by
        ):
            frappe.throw(_("Approved Inspection требует manager actor/time."))
        if self.status == "Cancelled" and not (self.cancellation_reason or "").strip():
            frappe.throw(_("Cancelled Inspection требует reason."))

    def _freeze_identity(self) -> None:
        before = self.get_doc_before_save()
        if before is None:
            return
        changed = [
            field for field in _IDENTITY_FIELDS if self.get(field) != before.get(field)
        ]
        if changed:
            frappe.throw(
                _("Inspection provenance неизменяема: {0}.").format(", ".join(changed))
            )

    def _freeze_approved_fact(self) -> None:
        before = self.get_doc_before_save()
        if before is None or before.status != "Approved":
            return
        allowed = {
            "customer_approval",
            "customer_sent_at",
            "customer_sent_by",
            "customer_decided_at",
            "customer_decided_by",
        }
        changed = [
            field.fieldname
            for field in self.meta.fields
            if field.fieldname not in allowed
            and self._signature(field.fieldname)
            != self._signature(field.fieldname, before)
        ]
        if changed:
            frappe.throw(_("Approved Inspection fact immutable."))

    def _signature(self, fieldname: str, document: Document | None = None) -> str:
        document = document or self
        value = document.get(fieldname)
        if isinstance(value, list):
            value = [row.as_dict(no_nulls=False) for row in value]
        return frappe.as_json(value)


def on_doctype_update() -> None:
    frappe.db.add_unique(DOCTYPE, ["idempotency_key"], "ca_inspection_idempotency_uniq")
    frappe.db.add_index(
        DOCTYPE, ["service_project", "status"], "ca_inspection_project_status_idx"
    )
    frappe.db.add_index(
        DOCTYPE,
        ["project_object", "inspection_type", "status"],
        "ca_inspection_object_type_idx",
    )
    frappe.db.add_index(DOCTYPE, ["process_step"], "ca_inspection_process_step_idx")
