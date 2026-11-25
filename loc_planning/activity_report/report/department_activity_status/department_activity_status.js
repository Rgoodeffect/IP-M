// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.query_reports["Department Activity Status"] = {
	filters: [
		{ fieldname: "reporting_period", label: __("Period"), fieldtype: "Link", options: "Reporting Period", reqd: 1 },
		{ fieldname: "region", label: __("Region"), fieldtype: "Link", options: "LOC Region" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "state_label" && data && data.color) {
			value = `<span class="indicator-pill ${data.color}">${value}</span>`;
		}
		if (column.fieldname === "days_late" && data && data.days_late) {
			value = `<span style="color: var(--red-600)">${value}</span>`;
		}
		return value;
	},
};
