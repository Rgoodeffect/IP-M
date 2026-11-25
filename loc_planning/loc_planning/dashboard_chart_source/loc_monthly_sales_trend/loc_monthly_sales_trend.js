frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["LOC Monthly Sales Trend"] = {
	method: "loc_planning.loc_planning.dashboard_chart_source.loc_monthly_sales_trend.loc_monthly_sales_trend.get",
	filters: [
		{ fieldname: "reporting_period", label: __("Period"), fieldtype: "Link", options: "Reporting Period" },
		{ fieldname: "region", label: __("Region"), fieldtype: "Link", options: "LOC Region" },
	],
};
