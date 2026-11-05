frappe.ui.form.on("SaaS Platform Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Check SEO Now"), () => {
			frappe
				.call({ method: "reckon_saas_platform.seo.refresh_seo_now", freeze: true })
				.then((r) => {
					const m = r.message || {};
					frappe.show_alert({
						message: __("{0} pages checked, {1} problem(s).", [m.pages || 0, m.issues || 0]),
						indicator: m.issues ? "orange" : "green",
					});
					frm.reload_doc();
				});
		});
		frm.add_custom_button(__("Reset Rate Limits"), () => {
			frappe.confirm(
				__("Clear the signup and verification counters for every IP address now?"),
				() =>
					frappe
						.call({
							method: "reckon_saas_platform.saas.reset_signup_rate_limits",
							freeze: true,
						})
						.then((r) => {
							frappe.show_alert({
								message: __("Cleared {0} rate limit counter(s).", [r.message || 0]),
								indicator: "green",
							});
						})
			);
		});
	},
});
