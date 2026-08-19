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
		],
	}
}

doc_events = {
	"File": {
		"on_trash": "contract_accounting.infrastructure.project_document_file_guard.prevent_locked_file_delete"
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
}

permission_query_conditions = {
	"Ferum Contractor Assignment": "contract_accounting.infrastructure.contractor_permissions.get_permission_query_conditions",
	"Ferum Service Project": "contract_accounting.infrastructure.operations_permissions.get_permission_query_conditions",
}

has_permission = {
	"Ferum Contractor Assignment": "contract_accounting.infrastructure.contractor_permissions.has_permission",
	"Ferum Service Project": "contract_accounting.infrastructure.operations_permissions.has_permission",
}
