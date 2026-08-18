frappe.pages["ferum-operations"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Операционная работа"), single_column: true });
	wrapper.ca15 = { page, body: $('<div class="ca15-operations"></div>').appendTo(page.main) };
	page.set_primary_action(__("Обновить"), () => refresh_operations(wrapper), "refresh");
};

frappe.pages["ferum-operations"].on_page_show = refresh_operations;

async function refresh_operations(wrapper) {
	await frappe.require("/assets/contract_accounting/js/ca15_workspaces.js");
	const [actionsResponse, capabilitiesResponse] = await Promise.all([
		frappe.call({ method: "contract_accounting.api.workspaces.get_my_actions" }),
		frappe.call({ method: "contract_accounting.api.workspaces.get_operations_capabilities" }),
	]);
	const actions = actionsResponse.message;
	const capabilities = capabilitiesResponse.message;
	const launches = capabilities.launch_control
		? (await frappe.call({ method: "contract_accounting.api.workspaces.get_launch_projects" })).message
		: null;
	const launchCards = launches ? `
		<div class="ca15-card ca15-source" data-route="ferum-project-launches"><h4>${__("Запуск проектов")}</h4><strong>${launches.kpi.project_count}</strong><div class="ca15-muted">${__("Projects in launch control")}</div></div>
		<div class="ca15-card"><h4>${__("Blocked")}</h4><strong>${launches.kpi.blocked || 0}</strong></div>` : `
		<div class="ca15-card"><h4>${__("Запуск проектов")}</h4><span class="ca15-pill">${__("Restricted")}</span><div class="ca15-muted">${__("Available to project launch roles")}</div></div>`;
	wrapper.ca15.body.html(`<div class="ca15-grid">
		<div class="ca15-card ca15-source" data-route="ferum-my-actions"><h4>${__("Мои действия")}</h4><strong>${actions.pagination.total}</strong><div class="ca15-muted">${__("Actionable source records")}</div></div>
		${launchCards}
		<div class="ca15-card"><h4>${__("Overdue")}</h4><strong>${actions.kpi.by_time.Overdue || 0}</strong></div>
	</div>`);
	contract_accounting.ca15.install_styles(wrapper.ca15.body);
	wrapper.ca15.body.find("[data-route]").on("click", (event) => frappe.set_route($(event.currentTarget).data("route")));
}
