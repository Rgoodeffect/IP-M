// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

const STATUS_COLORS = {
	"Slow Execution": "orange",
	"Within Plan": "green",
	"Limit Exceeded": "red",
	"Not Budgeted": "gray",
};

frappe.query_reports["Budget Execution Position"] = {
	filters: [
		{ fieldname: "fiscal_year", label: __("Year"), fieldtype: "Int", default: new Date().getFullYear(), reqd: 1 },
		{ fieldname: "to_date", label: __("Up to Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "region", label: __("Region"), fieldtype: "Link", options: "LOC Region" },
		{ fieldname: "department", label: __("Owner Department"), fieldtype: "Link", options: "LOC Department" },
		{ fieldname: "chapter", label: __("Chapter"), fieldtype: "Link", options: "Budget Chapter" },
		{ fieldname: "split_regions", label: __("Show East / West Separately"), fieldtype: "Check" },
	],
	tree: true,
	name_field: "name",
	parent_field: "parent_label",
	initial_depth: 1,
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldname === "execution_pct" && data && data.status && !data.is_total) {
			const pct = Math.max(0, Math.min(100, flt(data.execution_pct)));
			const color = STATUS_COLORS[data.status] || "gray";
			return `<div style="display:flex;align-items:center;gap:6px">
				<div style="flex:1;height:8px;background:var(--gray-100);border-radius:4px;overflow:hidden">
					<div style="width:${pct}%;height:100%;background:var(--${color}-500)"></div>
				</div>
				<span style="min-width:48px;text-align:left">${format_number(data.execution_pct, null, 1)}%</span>
			</div>`;
		}
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status_label" && data && data.status) {
			value = `<span class="indicator-pill ${STATUS_COLORS[data.status] || "gray"}">${value}</span>`;
		}
		if (data && (data.indent === 0 || data.is_total)) {
			value = `<b>${value}</b>`;
		}
		return value;
	},
};
