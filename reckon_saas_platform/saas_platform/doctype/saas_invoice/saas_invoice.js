frappe.ui.form.on("SaaS Invoice", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("View Invoice"), () => window.location.assign("/invoice/" + frm.doc.access_key));
		frm.add_custom_button(__("Send Again"), () =>
			frappe
				.call({ method: "reckon_saas_platform.invoices.resend", args: { name: frm.doc.name }, freeze: true })
				.then((r) => {
					const m = r.message || {};
					frappe.show_alert({
						message: __("Email: {0}, SMS: {1}", [m.email ? __("sent") : __("not sent"), m.sms ? __("sent") : __("not sent")]),
						indicator: m.email || m.sms ? "green" : "orange",
					});
					frm.reload_doc();
				})
		);
		frappe.call({ method: "reckon_saas_platform.invoices.whatsapp_link", args: { name: frm.doc.name } }).then((r) => {
			if (r.message) frm.add_custom_button(__("Send on WhatsApp"), () => window.location.assign(r.message));
		});
	},
});
