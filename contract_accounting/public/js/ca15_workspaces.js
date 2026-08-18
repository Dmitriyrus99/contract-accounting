window.contract_accounting = window.contract_accounting || {};

contract_accounting.ca15 = {
	escape(value) {
		return frappe.utils.escape_html(value === null || value === undefined ? "" : String(value));
	},
	install_styles(target) {
		if (target.find(".ca15-style").length) return;
		target.prepend(`<style class="ca15-style">
			.ca15-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-bottom:16px}
			.ca15-card{border:1px solid var(--border-color);border-radius:8px;padding:12px;background:var(--card-bg)}
			.ca15-card h4{margin:0 0 8px}.ca15-muted{color:var(--text-muted)}
			.ca15-source{cursor:pointer}.ca15-source:hover{text-decoration:underline}
			.ca15-pill{display:inline-block;padding:2px 8px;border-radius:12px;background:var(--subtle-fg);margin:2px}
		</style>`);
	},
	open(source) {
		if (source?.doctype && source?.name) frappe.set_route("Form", source.doctype, source.name);
	},
	render_segments(target, payload) {
		this.install_styles(target);
		const html = payload.segments.map((segment) => `<section class="ca15-card">
			<h4>${this.escape(segment.label)} <span class="ca15-pill">${segment.access === "granted" ? segment.count : __("Restricted")}</span></h4>
			<div class="ca15-muted">${segment.access === "granted" ? __("Exact source records") : __("Hidden by role policy")}</div>
			${segment.items.slice(0, 8).map((item, index) => `<div class="ca15-source" data-segment="${this.escape(segment.key)}" data-index="${index}">${this.escape(item.source_doctype)} · ${this.escape(item.source_name)}</div>`).join("")}
		</section>`).join("");
		target.html(`<div class="ca15-grid">${html}</div><div class="ca15-card"><strong>${__("Projection policy")}</strong>: ${this.escape(payload.policies.projection)}<br><strong>Import Batch</strong>: ${this.escape(payload.policies.import_batch)}</div>`);
		this.install_styles(target);
		target.find(".ca15-source").on("click", (event) => {
			const row = $(event.currentTarget);
			const segment = payload.segments.find((item) => item.key === row.data("segment"));
			this.open(segment.items[Number(row.data("index"))].drilldown);
		});
	},
};
