// SaaS CRM: the platform's signups and subscriptions as Reckon CRM leads and deals.
// Work on the records themselves happens in CRM (/crm); this page is the overview.
frappe.pages["saas-crm"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("CRM Pipeline"), single_column: true });
	const METHOD = "reckon_saas_platform.crm_sync.";
	const esc = (value) => frappe.utils.escape_html(value == null ? "" : String(value));
	const money = (value, currency) => format_currency(value || 0, currency || frappe.defaults.get_default("currency"));
	const crmLink = (path) => `/crm/${path}`;

	if (!document.getElementById("sc-style")) {
		const style = document.createElement("style");
		style.id = "sc-style";
		style.textContent = `
		.sc-wrap{max-width:1100px;margin:0 auto;display:grid;gap:18px}
		.sc-banner{background:var(--bg-orange,#fff4e0);border-radius:12px;padding:12px 16px;font-size:13px}
		.sc-row{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(160px,1fr))}
		.sc-card{border:1px solid var(--border-color,#e5e7eb);border-radius:12px;padding:12px 14px;background:var(--card-bg,#fff)}
		.sc-card .sc-k{font-size:12px;color:var(--text-muted);display:flex;align-items:center;gap:6px}
		.sc-card .sc-v{font-size:22px;font-weight:600;margin-top:4px;font-variant-numeric:tabular-nums}
		.sc-card .sc-s{font-size:12px;color:var(--text-muted);font-variant-numeric:tabular-nums}
		.sc-dot{width:8px;height:8px;border-radius:50%;display:inline-block;background:var(--gray-500)}
		.sc-h{font-size:14px;font-weight:600;margin:0 0 8px;display:flex;justify-content:space-between;align-items:baseline}
		.sc-h a{font-size:12px;font-weight:500}
		.sc-table{width:100%;border-collapse:collapse;font-size:13px}
		.sc-table td,.sc-table th{padding:7px 8px;border-bottom:1px solid var(--border-color,#eee);text-align:left}
		.sc-table th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--text-muted);font-weight:600}
		.sc-table td.num{text-align:right;font-variant-numeric:tabular-nums}
		.sc-empty{color:var(--text-muted);font-size:13px;padding:6px 0}
		.sc-overdue{color:var(--red-600,#c62828);font-weight:600}`;
		document.head.appendChild(style);
	}

	const dotColor = (color) => `var(--${color || "gray"}-500)`;
	const $body = $(page.body);
	page.set_primary_action(__("Sync Signups to CRM"), () => sync(), "refresh");
	page.add_inner_button(__("Open CRM"), () => (window.location.href = "/crm"));
	page.add_inner_button(__("CRM Settings"), () => frappe.set_route("Form", "SaaS Platform Settings"));

	function sync() {
		frappe.call({ method: METHOD + "sync_now", freeze: true, freeze_message: __("Syncing signups to CRM") }).then((r) => {
			const m = r.message || {};
			frappe.show_alert({
				message: __("{0} lead(s) and {1} deal(s) synced, {2} error(s).", [m.leads || 0, m.deals || 0, m.errors || 0]),
				indicator: m.errors ? "orange" : "green",
			});
			load();
		});
	}

	function stageCards(rows, withValue) {
		if (!rows.length) return `<div class="sc-empty">${esc(__("Nothing here yet."))}</div>`;
		return `<div class="sc-row">${rows
			.map(
				(r) => `<div class="sc-card">
					<div class="sc-k"><span class="sc-dot" style="background:${dotColor(r.color)}"></span>${esc(r.status)}</div>
					<div class="sc-v">${esc(r.count)}</div>
					<div class="sc-s">${withValue ? esc(money(r.value)) + " / " + esc(__("year")) : esc(__(r.type))}</div>
				</div>`
			)
			.join("")}</div>`;
	}

	function render(data) {
		if (!data.crm_installed) {
			$body.html(`<div class="sc-wrap"><div class="sc-banner">${esc(
				__("Install Frappe CRM and Reckon CRM on this site. Signups and subscriptions then appear here as leads and deals.")
			)}</div></div>`);
			page.clear_primary_action();
			return;
		}
		const today = frappe.datetime.get_today();
		const banners = [];
		if (!data.sync_enabled) banners.push(__("Send Signups to CRM is off in SaaS Platform Settings; new signups are not added."));
		if (data.unsynced) banners.push(__("{0} registration(s) are not in CRM yet. Use Sync Signups to CRM.", [data.unsynced]));
		if (!data.reckon_crm_installed) banners.push(__("Install Reckon CRM to schedule field visits on these leads and deals."));

		const recent = data.recent.length
			? `<table class="sc-table"><thead><tr><th>${esc(__("Deal"))}</th><th>${esc(__("Organization"))}</th><th>${esc(
					__("Module")
			  )}</th><th>${esc(__("Stage"))}</th><th class="num">${esc(__("Value / year"))}</th></tr></thead><tbody>${data.recent
					.map(
						(d) => `<tr><td><a href="${crmLink("deals/" + encodeURIComponent(d.name))}">${esc(d.name)}</a></td><td>${esc(
							d.organization
						)}</td><td>${esc(d.reckon_saas_module)}</td><td>${esc(d.status)}</td><td class="num">${esc(
							money(d.deal_value, d.currency)
						)}</td></tr>`
					)
					.join("")}</tbody></table>`
			: `<div class="sc-empty">${esc(__("No deals yet. A deal opens when a signup's workspace is provisioned."))}</div>`;

		const visits = data.visits.length
			? `<table class="sc-table"><thead><tr><th>${esc(__("Date"))}</th><th>${esc(__("Visit"))}</th><th>${esc(
					__("For")
			  )}</th><th>${esc(__("Assigned To"))}</th></tr></thead><tbody>${data.visits
					.map((v) => {
						const path = (v.reference_doctype === "CRM Deal" ? "deals/" : "leads/") + encodeURIComponent(v.reference_name);
						const late = v.planned_date < today;
						return `<tr><td class="${late ? "sc-overdue" : ""}">${esc(frappe.datetime.str_to_user(v.planned_date))}${
							late ? " · " + esc(__("overdue")) : ""
						}</td><td>${esc(v.visit_type)}</td><td><a href="${crmLink(path)}">${esc(v.reference_name)}</a></td><td>${esc(
							v.assigned_to
						)}</td></tr>`;
					})
					.join("")}</tbody></table>`
			: `<div class="sc-empty">${esc(
					data.reckon_crm_installed ? __("No field visits due today.") : __("Field visits need Reckon CRM.")
			  )}</div>`;

		$body.html(`<div class="sc-wrap">
			${banners.map((b) => `<div class="sc-banner">${esc(b)}</div>`).join("")}
			<section><h4 class="sc-h">${esc(__("Signup leads by stage"))}<a href="${crmLink("leads")}">${esc(
			__("Open leads")
		)}</a></h4>${stageCards(data.leads, false)}</section>
			<section><h4 class="sc-h">${esc(__("Subscription deals by stage"))}<a href="${crmLink("deals")}">${esc(
			__("Open deals")
		)}</a></h4>${stageCards(data.deals, true)}</section>
			<section><h4 class="sc-h">${esc(__("Field visits due"))}${
			data.reckon_crm_installed ? `<a href="${crmLink("visits")}">${esc(__("All visits"))}</a>` : ""
		}</h4>${visits}</section>
			<section><h4 class="sc-h">${esc(__("Recently updated deals"))}</h4>${recent}</section>
		</div>`);
	}

	function load() {
		frappe.call({ method: METHOD + "get_overview" }).then((r) => render(r.message || {}));
	}

	wrapper.saas_crm_load = load;
	load();
};

// Coming back to the page refreshes it; the first show is already loading.
frappe.pages["saas-crm"].on_page_show = function (wrapper) {
	if (wrapper.saas_crm_shown && wrapper.saas_crm_load) wrapper.saas_crm_load();
	wrapper.saas_crm_shown = true;
};
