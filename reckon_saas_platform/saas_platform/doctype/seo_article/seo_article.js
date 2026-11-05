frappe.ui.form.on("SEO Article", {
	refresh(frm) {
		if (frm.is_new()) return;
		const set = (status) => {
			frm.set_value("status", status);
			frm.save();
		};
		if (frm.doc.status !== "Published") frm.add_custom_button(__("Publish"), () => set("Published"));
		if (frm.doc.status === "Published") {
			frm.add_custom_button(__("View on Website"), () => window.open("/blog/" + frm.doc.slug, "_blank"));
			frm.add_custom_button(__("Archive"), () => set("Archived"));
		}
		if (frm.doc.status === "Draft") frm.add_custom_button(__("Reject"), () => set("Rejected"));
		frm.dashboard.set_headline(
			frm.doc.status === "Draft" ? __("Draft: not on the website until you publish it. Read it first.") : ""
		);
	},
});
