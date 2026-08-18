frappe.pages["ferum-my-actions"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Мои действия"), single_column: true });
	wrapper.ca14 = { page, body: $('<div class="ca14-actions"></div>').appendTo(page.main) };
	for (const [fieldname, label, options] of [
		["time_bucket", __("Срок"), "\nOverdue\nToday\nUpcoming\nUnscheduled"],
		["state_bucket", __("Состояние"), "\nBlocked\nWaiting External\nWaiting Approval\nActionable"],
	]) {
		wrapper.ca14[fieldname] = page.add_field({ fieldname, label, fieldtype: "Select", options, change: () => refresh_actions(wrapper) });
	}
	page.set_primary_action(__("Обновить"), () => refresh_actions(wrapper), "refresh");
};

frappe.pages["ferum-my-actions"].on_page_show = refresh_actions;

async function refresh_actions(wrapper) {
	await frappe.require("/assets/contract_accounting/js/ca14_workspaces.js");
	const state = wrapper.ca14;
	state.body.html(`<div class="text-muted">${__("Loading actions...")}</div>`);
	const response = await frappe.call({
		method: "contract_accounting.api.workspaces.get_my_actions",
		args: { time_bucket: state.time_bucket.get_value(), state_bucket: state.state_bucket.get_value() },
	});
	const payload = response.message;
	contract_accounting.ca14.install_styles(state.body);
	const kpis = ["Overdue", "Today", "Upcoming", "Blocked", "Waiting External"]
		.map((name) => `<div class="ca14-kpi"><strong>${payload.kpi.by_time[name] ?? payload.kpi.by_state[name] ?? 0}</strong><span>${contract_accounting.ca14.escape(name)}</span></div>`)
		.join("");
	const rows = payload.actions
		.map((row) => `<div class="ca14-card mb-2 ca14-action-row" data-index="${payload.actions.indexOf(row)}">
			<div class="d-flex justify-content-between"><strong>${contract_accounting.ca14.escape(row.title)}</strong><span>${contract_accounting.ca14.badge(row.time_bucket, row.is_overdue ? "red" : "gray")}</span></div>
			<div class="ca14-muted">${contract_accounting.ca14.escape(row.project_label)} · ${contract_accounting.ca14.escape(row.status)} · ${contract_accounting.ca14.escape(row.due_at || __("No deadline"))}</div>
			${row.delivery_todos.length ? `<small>${__("Delivered by ToDo")}: ${row.delivery_todos.map(contract_accounting.ca14.escape).join(", ")}</small>` : ""}
		</div>`)
		.join("");
	state.body.html(`<div class="ca14-grid">${kpis}</div>${rows || `<div class="ca14-card ca14-muted">${__("No assigned actions")}</div>`}`);
	contract_accounting.ca14.install_styles(state.body);
	state.body.find(".ca14-action-row").on("click", (event) => contract_accounting.ca14.open_source(payload.actions[Number($(event.currentTarget).data("index"))].drilldown));
}
