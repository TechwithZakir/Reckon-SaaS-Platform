frappe.ui.form.on("SaaS Plan", {
	refresh(frm) {
		if (frm.is_new() || !frappe.user.has_role("System Manager")) {
			return;
		}
		frm.add_custom_button(__("Sync to Paddle"), () => {
			frappe.confirm(
				__(
					"Create this plan's product and price in Paddle ({0} {1}, {2})? If the price, currency or cycle changed since the last sync, the old Paddle price is archived; card subscriptions already running keep it.",
					[frm.doc.currency, format_currency(frm.doc.price, frm.doc.currency), frm.doc.billing_cycle]
				),
				() =>
					frappe
						.call({
							method: "reckon_saas_platform.paddle.sync_plan",
							args: { plan: frm.doc.name },
							freeze: true,
							freeze_message: __("Syncing to Paddle..."),
						})
						.then((r) => {
							const m = r.message || {};
							frappe.show_alert({
								message: m.created
									? __("Paddle price {0} created.", [m.price_id])
									: __("Already in sync: {0}", [m.price_id]),
								indicator: "green",
							});
							frm.reload_doc();
						})
			);
		});
	},
});
