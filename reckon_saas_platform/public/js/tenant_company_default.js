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
