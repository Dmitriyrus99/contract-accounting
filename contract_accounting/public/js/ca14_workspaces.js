frappe.provide("contract_accounting.ca14");

Object.assign(contract_accounting.ca14, {
	escape(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	},

	badge(label, tone = "gray") {
		return `<span class="indicator-pill ${tone}">${this.escape(label)}</span>`;
	},

	open_source(drilldown) {
		if (!drilldown?.route) return;
		sessionStorage.setItem("ca14:return", JSON.stringify(drilldown.context || {}));
		frappe.set_route(...drilldown.route);
	},

	install_styles(target) {
		if (target.find(".ca14-styles").length) return;
		target.prepend(`<style class="ca14-styles">
			.ca14-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:12px 0}
			.ca14-kpi,.ca14-card{border:1px solid var(--border-color);border-radius:8px;background:var(--card-bg);padding:14px}
			.ca14-kpi strong{display:block;font-size:22px}.ca14-muted{color:var(--text-muted)}
			.ca14-progress{height:8px;background:var(--gray-200);border-radius:8px;overflow:hidden}.ca14-progress>i{display:block;height:100%;background:var(--primary);border-radius:8px}
			.ca14-stage{border-top:1px solid var(--border-color);padding:10px 0}.ca14-stage:first-child{border-top:0}
			.ca14-step{display:grid;grid-template-columns:minmax(220px,1fr) 150px 170px;gap:10px;padding:7px 0;align-items:center}
			.ca14-source{cursor:pointer;color:var(--text-color)}.ca14-source:hover{text-decoration:underline}
			.ca14-blocker{border-left:3px solid var(--red-500);padding:5px 9px;margin:5px 0;background:var(--red-50)}
			@media(max-width:768px){.ca14-step{grid-template-columns:1fr}}
		</style>`);
	},

	render_launch_card(target, project, show_link = false) {
		this.install_styles(target);
		const flags = Object.entries(project.flags || {})
			.filter(([, value]) => value)
			.map(([name]) => this.badge(name.replaceAll("_", " "), name === "blocked" ? "red" : "orange"))
			.join(" ");
		const blockers = (project.blocking_conditions || [])
			.map((row) => `<div class="ca14-blocker"><strong>${this.escape(row.code)}</strong> — ${this.escape(row.title)}</div>`)
			.join("");
		const stages = (project.stages || [])
			.map((stage) => {
				const steps = stage.steps
					.map((step) => `<div class="ca14-step ca14-source" data-doctype="${this.escape(step.drilldown.doctype)}" data-name="${this.escape(step.drilldown.name)}">
						<span>${this.escape(step.title)}</span><span>${this.badge(step.status, step.is_overdue ? "red" : "gray")}</span><span class="ca14-muted">${this.escape(step.due_at || __("No deadline"))}</span>
					</div>`)
					.join("");
				return `<details class="ca14-stage" ${stage.status === "Active" ? "open" : ""}>
					<summary><strong>${this.escape(stage.title)}</strong> — ${stage.progress_percent}% · ${this.escape(stage.status)} ${stage.gate ? `· Gate ${this.escape(stage.gate.status)}` : ""}</summary>
					<div class="ca14-progress"><i style="width:${stage.progress_percent}%"></i></div>${steps}
				</details>`;
			})
			.join("");
		target.html(`<div class="ca14-card">
			<div class="d-flex justify-content-between align-items-start"><div><h4>${this.escape(project.contract_number || project.service_project)}</h4><div class="ca14-muted">${this.escape(project.customer)} · ${this.escape(project.execution_status)}</div></div><strong>${project.progress_percent}%</strong></div>
			<div class="ca14-progress my-3"><i style="width:${project.progress_percent}%"></i></div><div>${flags}</div>
			${blockers ? `<h5 class="mt-4">${__("Blocking conditions")}</h5>${blockers}` : ""}
			<div class="mt-3">${stages || `<div class="ca14-muted">${__("Launch process has not been generated")}</div>`}</div>
			${show_link ? `<button class="btn btn-default btn-sm mt-3 ca14-open-launches">${__("Open Project Launches")}</button>` : ""}
		</div>`);
		target.find(".ca14-source").on("click", (event) => {
			const row = $(event.currentTarget);
			this.open_source({ route: ["Form", row.data("doctype"), row.data("name")], context: { return_route: "ferum-project-launches", service_project: project.service_project } });
		});
		target.find(".ca14-open-launches").on("click", () => frappe.set_route("ferum-project-launches"));
	},
});
