// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.query_reports["Missing Station Data"] = {
	filters: [
		{ fieldname: "reporting_period", label: __("Month"), fieldtype: "Link", options: "Reporting Period", reqd: 1,
			get_query: () => ({ filters: { period_type: "Monthly" } }) },
		{ fieldname: "region", label: __("Region"), fieldtype: "Link", options: "LOC Region" },
		{ fieldname: "sales_office", label: __("Sales Office"), fieldtype: "Link", options: "LOC Department",
			get_query: () => ({ filters: { department_type: "Sales Office" } }) },
		{ fieldname: "show_all", label: __("Include Approved Stations"), fieldtype: "Check" },
	],
	onload(report) {
		const d = new Date();
		d.setMonth(d.getMonth() - 1);
		const name = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
		frappe.db.exists("Reporting Period", name).then((exists) => {
			if (exists && !report.get_filter_value("reporting_period")) report.set_filter_value("reporting_period", name);
		});
	},
};
