frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["LOC Sales by Product"] = {
	method: "loc_planning.loc_planning.dashboard_chart_source.loc_sales_by_product.loc_sales_by_product.get",
	filters: [
		{ fieldname: "reporting_period", label: __("Period"), fieldtype: "Link", options: "Reporting Period" },
		{ fieldname: "region", label: __("Region"), fieldtype: "Link", options: "LOC Region" },
	],
};
