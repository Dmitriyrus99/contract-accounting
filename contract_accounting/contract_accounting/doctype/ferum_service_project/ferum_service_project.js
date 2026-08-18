frappe.ui.form.on("Ferum Service Project", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		const allowed = ["System Manager", "Владелец процесса", "Руководитель проектов", "Менеджер проектов"];
		if (!allowed.some((role) => frappe.user.has_role(role)) && frappe.session.user !== "Administrator") {
			frm.fields_dict.launch_view.$wrapper.html(`<div class="text-muted">${__("Project Launch view is not available for this role.")}</div>`);
			return;
		}
		frappe.require("/assets/contract_accounting/js/ca14_workspaces.js").then(() => {
			const target = frm.fields_dict.launch_view.$wrapper;
			target.html(`<div class="text-muted">${__("Loading Project Launch...")}</div>`);
			frappe
				.call({
					method: "contract_accounting.api.workspaces.get_project_launch_view",
					args: { service_project: frm.doc.name },
				})
				.then((response) => {
					contract_accounting.ca14.render_launch_card(target, response.message, true);
				})
				.catch(() => target.empty());
		});
	},
});
