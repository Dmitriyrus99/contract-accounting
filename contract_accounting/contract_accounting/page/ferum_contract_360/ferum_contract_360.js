frappe.pages["ferum-contract-360"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Контракт 360°"), single_column: true });
	wrapper.ca15 = { page, body: $('<div class="ca15-contract"></div>').appendTo(page.main) };
	wrapper.ca15.project = page.add_field({
		fieldname: "service_project", label: __("Service Project"), fieldtype: "Link", options: "Ferum Service Project",
		change: () => refresh_contract_360(wrapper),
	});
	page.set_primary_action(__("Обновить"), () => refresh_contract_360(wrapper), "refresh");
};

frappe.pages["ferum-contract-360"].on_page_show = function (wrapper) {
	const route = frappe.get_route();
	if (route[1]) wrapper.ca15.project.set_value(route[1]);
	else refresh_contract_360(wrapper);
};

async function refresh_contract_360(wrapper) {
	await frappe.require("/assets/contract_accounting/js/ca15_workspaces.js");
	const project = wrapper.ca15.project.get_value();
	if (!project) {
		wrapper.ca15.body.html(`<div class="ca15-card ca15-muted">${__("Select Service Project")}</div>`);
		contract_accounting.ca15.install_styles(wrapper.ca15.body);
		return;
	}
	wrapper.ca15.body.html(`<div class="text-muted">${__("Loading end-to-end trace...")}</div>`);
	const response = await frappe.call({ method: "contract_accounting.api.integration.get_end_to_end_trace", args: { service_project: project } });
	contract_accounting.ca15.render_segments(wrapper.ca15.body, response.message);
}
