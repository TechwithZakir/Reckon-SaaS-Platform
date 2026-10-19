frappe.ui.form.on("SaaS Platform Settings", {
	refresh(frm) {
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
