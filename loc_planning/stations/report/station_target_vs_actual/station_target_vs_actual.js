// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.query_reports["Station Target vs Actual"] = {
	filters: [
		{ fieldname: "from_period", label: __("From Month"), fieldtype: "Link", options: "Reporting Period",
			get_query: () => ({ filters: { period_type: "Monthly" } }) },
		{ fieldname: "to_period", label: __("To Month"), fieldtype: "Link", options: "Reporting Period",
			get_query: () => ({ filters: { period_type: "Monthly" } }) },
		{ fieldname: "region", label: __("Region"), fieldtype: "Link", options: "LOC Region" },
		{ fieldname: "sales_office", label: __("Sales Office"), fieldtype: "Link", options: "LOC Department",
			get_query: () => ({ filters: { department_type: "Sales Office" } }) },
		{ fieldname: "product", label: __("Product"), fieldtype: "Link", options: "Fuel Product" },
		{ fieldname: "include_unapproved", label: __("Include Unapproved Data"), fieldtype: "Check" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "achievement_pct" && data && data.achievement_pct != null) {
			const color = data.achievement_pct >= 100 ? "green" : "orange";
			value = `<span style="color: var(--${color}-600)">${value}</span>`;
		}
		return value;
	},
};
