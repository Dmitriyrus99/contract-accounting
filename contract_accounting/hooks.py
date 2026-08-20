"""Frappe application metadata for Contract Accounting."""

app_name = "contract_accounting"
app_title = "Contract Accounting"
app_publisher = "Ferum"
app_description = "Contract root, lifecycle and accounting orchestration for ERPNext v15"
app_email = "dmitriyr071@gmail.com"
app_license = "Proprietary"

required_apps = ["erpnext"]

after_install = "contract_accounting.install.after_install"
before_migrate = "contract_accounting.install.before_migrate"
after_migrate = "contract_accounting.install.after_migrate"

override_doctype_class = {
	"File": "contract_accounting.infrastructure.guarded_file.ContractAccountingFile"
}

write_file = "contract_accounting.infrastructure.privacy_file_guard.write_file"

fixtures = [
	{
		"dt": "Role",
		"filters": [
			[
				"name",
				"in",
				[
					"Генеральный директор",
					"Владелец процесса",
					"Руководитель проектов",
					"Менеджер проектов",
					"Юрист",
					"Бухгалтер",
					"Инженер",
					"Офис-менеджер",
					"Подрядчик",
					"Менеджер персональных данных",
					"Ответственный за ПДн",
					"Ответственный за ИБ",
					"Проверяющий допуски",
					"Тендерный специалист",
				],
			]
		],
	}
]

scheduler_events = {
	"cron": {
		"*/15 * * * *": [
			"contract_accounting.scheduler.notifications.process_deadline_notifications",
			"contract_accounting.scheduler.notifications.process_deadline_digest",
			"contract_accounting.api.privacy_controls.expire_break_glass",
			"contract_accounting.api.privacy.expire_personnel_credentials",
			"contract_accounting.api.privacy_retention.retry_committed_physical_deletions",
			"contract_accounting.api.privacy_event_retention.anonymize_expired_privacy_events",
		],
	}
}

doc_events = {
	"*": {
		"before_validate": "contract_accounting.infrastructure.privacy_attachment_guard.lock_credential_attachment_references",
	},
	"Version": {
		"before_validate": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
		"before_insert": [
			"contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
			"contract_accounting.demo_uat.reset.prevent_reset_commit_artifact",
		],
	},
	"Comment": {
		"before_validate": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
		"before_insert": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
	},
	"Activity Log": {
		"before_validate": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
		"before_insert": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
	},
	"Communication": {
		"before_validate": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
		"before_insert": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
	},
	"Communication Link": {
		"before_validate": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
		"before_insert": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
	},
	"ToDo": {
		"before_validate": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
		"before_insert": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
	},
	"File": {
		"before_validate": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
		"before_insert": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
	},
	"DocShare": {
		"before_validate": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
		"before_insert": "contract_accounting.api.privacy_event_retention.lock_privacy_event_artifact",
	},
	"Sales Invoice": {
		"validate": "contract_accounting.infrastructure.sales_invoice_guard.validate_project_context",
		"before_cancel": "contract_accounting.infrastructure.sales_invoice_guard.prevent_active_output_cancel",
		"on_submit": "contract_accounting.infrastructure.finance_hooks.enqueue_accounting_rebuild",
		"on_cancel": "contract_accounting.infrastructure.finance_hooks.enqueue_accounting_rebuild",
	},
	"Purchase Invoice": {
		"validate": "contract_accounting.infrastructure.purchase_invoice_guard.validate_project_context",
		"before_cancel": "contract_accounting.infrastructure.purchase_invoice_guard.prevent_recognized_cost_cancel",
		"on_submit": "contract_accounting.infrastructure.finance_hooks.enqueue_accounting_rebuild",
		"on_cancel": "contract_accounting.infrastructure.finance_hooks.enqueue_accounting_rebuild",
	},
	"Payment Entry": {
		"on_submit": "contract_accounting.infrastructure.finance_hooks.enqueue_accounting_rebuild",
		"on_cancel": "contract_accounting.infrastructure.finance_hooks.enqueue_accounting_rebuild",
	},
	"Ferum Personnel Credential": {
		"validate": "contract_accounting.infrastructure.privacy_file_guard.validate_credential_alias_set",
	},
	"Ferum Contractor Assignment": {
		"before_validate": "contract_accounting.infrastructure.privacy_target_lock.lock_assignment_privacy_target",
	},
}

permission_query_conditions = {
	"File": "contract_accounting.infrastructure.privacy_file_guard.get_permission_query_conditions",
	"Ferum Contractor Assignment": "contract_accounting.infrastructure.contractor_permissions.get_permission_query_conditions",
	"Ferum Contract Obligation": "contract_accounting.infrastructure.project_graph_permissions.contract_obligation_query",
	"Ferum Finding": "contract_accounting.infrastructure.project_graph_permissions.finding_query",
	"Ferum Inspection": "contract_accounting.infrastructure.project_graph_permissions.inspection_query",
	"Ferum Maintenance Schedule": "contract_accounting.infrastructure.project_graph_permissions.maintenance_schedule_query",
	"Ferum Maintenance Visit": "contract_accounting.infrastructure.project_graph_permissions.maintenance_visit_query",
	"Ferum Material Expense": "contract_accounting.infrastructure.project_graph_permissions.material_expense_query",
	"Ferum Object System": "contract_accounting.infrastructure.project_graph_permissions.object_system_query",
	"Ferum Photo Evidence": "contract_accounting.infrastructure.project_graph_permissions.photo_evidence_query",
	"Ferum Process Evidence": "contract_accounting.infrastructure.project_graph_permissions.process_evidence_query",
	"Ferum Project Document": "contract_accounting.infrastructure.project_graph_permissions.project_document_query",
	"Ferum Project Document Event": "contract_accounting.infrastructure.project_graph_permissions.project_document_event_query",
	"Ferum Project Object": "contract_accounting.infrastructure.project_graph_permissions.project_object_query",
	"Ferum Project Process": "contract_accounting.infrastructure.project_graph_permissions.project_process_query",
	"Ferum Project Process Step": "contract_accounting.infrastructure.project_graph_permissions.project_process_step_query",
	"Ferum Project Stage": "contract_accounting.infrastructure.project_graph_permissions.project_stage_query",
	"Ferum Service Object": "contract_accounting.infrastructure.project_graph_permissions.service_object_query",
	"Ferum Service Project": "contract_accounting.infrastructure.operations_permissions.get_permission_query_conditions",
	"Ferum Service Request": "contract_accounting.infrastructure.project_graph_permissions.service_request_query",
	"Ferum Stage Gate": "contract_accounting.infrastructure.project_graph_permissions.stage_gate_query",
	"Ferum Contractor Worker": "contract_accounting.infrastructure.privacy_permissions.get_worker_permission_query_conditions",
	"Ferum Personnel Credential": "contract_accounting.infrastructure.privacy_permissions.get_credential_permission_query_conditions",
}

has_permission = {
	"Ferum Contractor Assignment": "contract_accounting.infrastructure.contractor_permissions.has_permission",
	"Ferum Contract Obligation": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Finding": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Inspection": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Maintenance Schedule": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Maintenance Visit": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Material Expense": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Object System": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Photo Evidence": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Process Evidence": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Project Document": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Project Document Event": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Project Object": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Project Process": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Project Process Step": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Project Stage": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Service Object": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Service Project": "contract_accounting.infrastructure.operations_permissions.has_permission",
	"Ferum Service Request": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Stage Gate": "contract_accounting.infrastructure.project_graph_permissions.has_project_graph_permission",
	"Ferum Contractor Worker": "contract_accounting.infrastructure.privacy_permissions.has_worker_permission",
	"Ferum Personnel Credential": "contract_accounting.infrastructure.privacy_permissions.has_credential_permission",
	"File": "contract_accounting.infrastructure.privacy_file_guard.has_permission",
}
