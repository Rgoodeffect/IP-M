// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.query_reports["Station Sales Analysis"] = {
	filters: [
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: [
				{ value: "Product", label: __("Product") },
				{ value: "Region", label: __("Region") },
				{ value: "Sales Office", label: __("Sales Office") },
				{ value: "Station", label: __("Station") },
				{ value: "Month", label: __("Month") },
			],
			default: "Product",
		},
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
};
