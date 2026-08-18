frappe.pages["ferum-project-launches"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Запуск проектов"), single_column: true });
	wrapper.ca14 = { page, body: $('<div class="ca14-launches"></div>').appendTo(page.main) };
	wrapper.ca14.flag = page.add_field({
		fieldname: "flag", label: __("Отклонение"), fieldtype: "Select",
		options: "\noverdue\nblocked\nmissing_contractor\nwaiting_customer\nmissing_credentials",
		change: () => refresh_launches(wrapper),
	});
	page.set_primary_action(__("Обновить"), () => refresh_launches(wrapper), "refresh");
};

frappe.pages["ferum-project-launches"].on_page_show = refresh_launches;

async function refresh_launches(wrapper) {
	await frappe.require("/assets/contract_accounting/js/ca14_workspaces.js");
	const state = wrapper.ca14;
	state.body.html(`<div class="text-muted">${__("Loading project launches...")}</div>`);
	const response = await frappe.call({ method: "contract_accounting.api.workspaces.get_launch_projects", args: { flag: state.flag.get_value() } });
	const payload = response.message;
	const kpis = ["project_count", "overdue", "blocked", "missing_contractor", "waiting_customer", "missing_credentials"]
		.map((name) => `<div class="ca14-kpi"><strong>${payload.kpi[name] || 0}</strong><span>${contract_accounting.ca14.escape(name.replaceAll("_", " "))}</span></div>`)
		.join("");
	state.body.html(`<div class="ca14-grid">${kpis}</div><div class="ca14-project-list"></div>`);
	contract_accounting.ca14.install_styles(state.body);
	const list = state.body.find(".ca14-project-list");
	for (const project of payload.projects) {
		const card = $('<div class="mb-3"></div>').appendTo(list);
		contract_accounting.ca14.render_launch_card(card, project);
		card.find("h4").addClass("ca14-source").on("click", () => contract_accounting.ca14.open_source(project.drilldown));
	}
	if (!payload.projects.length) list.html(`<div class="ca14-card ca14-muted">${__("No projects match the filter")}</div>`);
}
