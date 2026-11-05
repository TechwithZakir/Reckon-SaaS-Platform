frappe.ui.form.on("SEO Suggestion", {
	refresh(frm) {
		if (frm.is_new()) return;
		const set = (status) => {
			frm.set_value("status", status);
			frm.save();
		};
		if (frm.doc.status !== "Approved") frm.add_custom_button(__("Approve"), () => set("Approved"));
		if (frm.doc.status !== "Rejected") frm.add_custom_button(__("Reject"), () => set("Rejected"));
		frm.dashboard.set_headline(
			frm.doc.status === "Pending"
				? __("Nothing changes on the website until you approve this.")
				: ""
		);
	},
});
