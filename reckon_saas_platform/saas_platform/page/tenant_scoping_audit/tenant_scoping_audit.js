// Which doctypes each module opens to tenants, and which have no company scope. Read-only; vendor staff only.
frappe.pages["tenant-scoping-audit"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Tenant Scoping Audit"), single_column: true });
	page.set_primary_action(__("Refresh"), () => load(), "refresh");
	const $body = $('<div class="rsa-audit" style="padding:8px 20px 32px"></div>').appendTo(page.main);
	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

	function render(data) {
		const status = data.total_open
			? `<span class="indicator-pill red">${esc(__("{0} open", [data.total_open]))}</span>`
			: `<span class="indicator-pill green">${esc(__("Every module is scoped"))}</span>`;
		$body.html(`<p class="text-muted">${esc(__("A doctype tenants can open needs a row filter and a permission rule, or a declared read-only reference."))}</p>
			<p>${status}</p>
			<table class="table table-bordered" style="max-width:900px"><thead><tr><th>${esc(__("Module"))}</th><th>${esc(__("Opened to tenants"))}</th>
			<th>${esc(__("Read-only reference"))}</th><th>${esc(__("Open"))}</th></tr></thead><tbody>${data.modules.map((m) => `<tr>
				<td>${esc(m.module)}</td><td>${m.opened}</td><td>${m.reference}</td>
				<td>${m.open.length ? m.open.map((o) => `<div><b>${esc(o.doctype)}</b> <span class="text-muted">${esc(o.why)}</span></div>`).join("") : `<span class="text-muted">${esc(__("None"))}</span>`}</td></tr>`).join("")}
			</tbody></table>`);
	}
	function load() {
		frappe.call({ method: "reckon_saas_platform.api_scoping_audit.get_audit", type: "GET" }).then((r) => render(r.message));
	}
	load();
};
