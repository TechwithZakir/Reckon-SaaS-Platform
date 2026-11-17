// A tenant's reports open on its own company. Some stock reports default to the system Company when their
// script loads; the server already limits the data, this keeps the filter honest on screen.
(function () {
	function align() {
		const company = frappe.boot && frappe.boot.reckon_tenant_company;
		const report = frappe.query_report;
		if (!company || !report || !report.get_filter_value || !report.filters) return;
		let current = null;
		try { current = report.get_filter_value("company"); } catch (e) { return; }
		if (current && current !== company) report.set_filter_value("company", company);
	}
	$(document).on("startup", () => {
		frappe.router.on("change", () => {
			if (frappe.get_route()[0] === "query-report") setTimeout(align, 1200);
		});
	});
})();

// A tenant reads its own Company; the server refuses to create or change it, so the form says so instead of offering Save.
$(document).on("startup", () => {
	if (!(frappe.boot && frappe.boot.reckon_tenant_company)) return;
	frappe.ui.form.on("Company", {
		refresh(frm) {
			if (frm.is_new()) {
				frappe.show_alert({ message: __("Your company is set up for you."), indicator: "blue" });
				frappe.set_route("List", "Company");
				return;
			}
			if (frappe.boot.reckon_company_admin) {
				// The company admin updates contact and registration details; the books' settings stay with Reckon support.
				const editable = ["email", "phone_no", "fax", "website", "company_description", "registration_details", "tax_id",
					"date_of_incorporation", "date_of_commencement", "company_logo", "default_letter_head"];
				(frm.meta.fields || []).forEach((df) => {
					if (!editable.includes(df.fieldname) && !["Section Break", "Column Break", "Tab Break", "HTML", "Button"].includes(df.fieldtype)) {
						frm.set_df_property(df.fieldname, "read_only", 1);
					}
				});
				frm.dashboard && frm.dashboard.set_headline(__("You can update your contact and registration details. Other settings are managed by Reckon."));
				return;
			}
			frm.disable_save();
			frm.set_read_only();
			frm.dashboard && frm.dashboard.set_headline(__("Your company details are managed by Reckon. Contact support to change them."));
		},
	});
	frappe.listview_settings["Company"] = Object.assign(frappe.listview_settings["Company"] || {}, {
		onload(listview) { listview.page.clear_primary_action && listview.page.clear_primary_action(); },
	});
});
