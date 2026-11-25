// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.query_reports["Company Registry"] = {
	filters: [
		{ fieldname: "classification", label: __("Classification"), fieldtype: "Link", options: "Company Classification" },
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: [
				"",
				{ value: "Active", label: __("Active") },
				{ value: "Suspended", label: __("Suspended") },
				{ value: "Blacklisted", label: __("Blacklisted") },
				{ value: "Inactive", label: __("Inactive") },
			],
		},
		{
			fieldname: "certificate_status",
			label: __("Certificate Status"),
			fieldtype: "Select",
			options: [
				"",
				{ value: "Valid", label: __("Valid") },
				{ value: "Expiring Soon", label: __("Expiring Soon") },
				{ value: "Expired", label: __("Expired") },
				{ value: "None", label: __("None") },
			],
		},
		{ fieldname: "expiring_within_days", label: __("Certificate Expiring Within (days)"), fieldtype: "Int" },
		{ fieldname: "from_date", label: __("Registered From"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("Registered To"), fieldtype: "Date" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "certificate_status_label" && data) {
			const color = { Valid: "green", "Expiring Soon": "orange", Expired: "red" }[data.certificate_status];
			if (color) value = `<span class="indicator-pill ${color}">${value}</span>`;
		}
		return value;
	},
};
