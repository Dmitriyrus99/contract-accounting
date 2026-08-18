"""Frappe application metadata for Contract Accounting."""

app_name = "contract_accounting"
app_title = "Contract Accounting"
app_publisher = "Ferum"
app_description = "Contract root, lifecycle and accounting orchestration for ERPNext v15"
app_email = "dmitriyr071@gmail.com"
app_license = "Proprietary"

required_apps = ["erpnext"]

fixtures = [
	{
		"dt": "Role",
		"filters": [
			[
				"name",
				"in",
				[
					"Генеральный директор",
					"Руководитель проектов",
					"Менеджер проектов",
					"Юрист",
					"Бухгалтер",
					"Инженер",
				],
			]
		],
	}
]
