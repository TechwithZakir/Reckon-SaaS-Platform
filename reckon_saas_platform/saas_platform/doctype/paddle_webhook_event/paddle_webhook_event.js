frappe.ui.form.on("Paddle Webhook Event", {
	refresh(frm) {
		if (frm.doc.status === "Failed" && frappe.user.has_role("System Manager")) {
			frm.add_custom_button(__("Process Again"), () =>
				frappe
					.call({
						method: "reckon_saas_platform.paddle.reprocess_event",
						args: { event_id: frm.doc.name },
						freeze: true,
					})
					.then(() => frm.reload_doc())
			);
		}
	},
});
