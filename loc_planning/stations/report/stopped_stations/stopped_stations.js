// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.query_reports["Stopped Stations"] = {
	filters: [
		{ fieldname: "region", label: __("Region"), fieldtype: "Link", options: "LOC Region" },
		{ fieldname: "sales_office", label: __("Sales Office"), fieldtype: "Link", options: "LOC Department",
			get_query: () => ({ filters: { department_type: "Sales Office" } }) },
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: [
				"",
				{ value: "Stopped", label: __("Stopped") },
				{ value: "Under Maintenance", label: __("Under Maintenance") },
				{ value: "Under Construction", label: __("Under Construction") },
				{ value: "Operating", label: __("Operating") },
			],
		},
		{ fieldname: "from_period", label: __("From Month"), fieldtype: "Link", options: "Reporting Period",
			get_query: () => ({ filters: { period_type: "Monthly" } }) },
		{ fieldname: "to_period", label: __("To Month"), fieldtype: "Link", options: "Reporting Period",
			get_query: () => ({ filters: { period_type: "Monthly" } }) },
		{ fieldname: "include_unapproved", label: __("Include Unapproved Data"), fieldtype: "Check" },
	],
};
