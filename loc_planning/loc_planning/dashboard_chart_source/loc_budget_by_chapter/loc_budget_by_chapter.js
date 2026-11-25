frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["LOC Budget by Chapter"] = {
	method: "loc_planning.loc_planning.dashboard_chart_source.loc_budget_by_chapter.loc_budget_by_chapter.get",
	filters: [
		{ fieldname: "reporting_period", label: __("Period"), fieldtype: "Link", options: "Reporting Period" },
		{ fieldname: "region", label: __("Region"), fieldtype: "Link", options: "LOC Region" },
	],
};
