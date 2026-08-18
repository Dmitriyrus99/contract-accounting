frappe.pages["ferum-director-control"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Центр контроля директора"), single_column: true });
	wrapper.ca15 = { page, body: $('<div class="ca15-director"></div>').appendTo(page.main) };
	wrapper.ca15.company = page.add_field({ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", change: () => refresh_director(wrapper) });
	page.set_primary_action(__("Обновить"), () => refresh_director(wrapper), "refresh");
};

frappe.pages["ferum-director-control"].on_page_show = refresh_director;

async function refresh_director(wrapper) {
	await frappe.require("/assets/contract_accounting/js/ca15_workspaces.js");
	const response = await frappe.call({ method: "contract_accounting.api.contract_360.get_director_control_center", args: { company: wrapper.ca15.company.get_value() } });
	const payload = response.message;
	const rows = payload.exceptions.slice(0, 50).map((item, index) => `<div class="ca15-card ca15-source mb-2" data-index="${index}"><strong>${contract_accounting.ca15.escape(item.severity)} · ${contract_accounting.ca15.escape(item.title)}</strong><div class="ca15-muted">${contract_accounting.ca15.escape(item.service_project)} · ${contract_accounting.ca15.escape(item.source_doctype)} ${contract_accounting.ca15.escape(item.source_name)}</div></div>`).join("");
	wrapper.ca15.body.html(`<div class="ca15-grid"><div class="ca15-card"><h4>${__("Projects")}</h4><strong>${payload.kpi.project_count}</strong></div><div class="ca15-card"><h4>${__("Exceptions")}</h4><strong>${payload.kpi.exception_count}</strong></div></div>${rows || `<div class="ca15-card ca15-muted">${__("No intervention exceptions")}</div>`}`);
	contract_accounting.ca15.install_styles(wrapper.ca15.body);
	wrapper.ca15.body.find("[data-index]").on("click", (event) => contract_accounting.ca15.open(payload.exceptions[Number($(event.currentTarget).data("index"))].drilldown));
}
