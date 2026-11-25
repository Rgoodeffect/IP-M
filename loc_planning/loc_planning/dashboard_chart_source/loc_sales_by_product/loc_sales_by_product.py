"""Share of fuel sales (litres) by product for the selected period."""

import frappe

from loc_planning.dashboard.api import _filters, sales_block


# Not cached: Frappe's chart cache is keyed by chart name only, which would share one
# user's (permission-filtered) figures with every other user and ignore the filters.
@frappe.whitelist()
def get(
	chart_name=None,
	chart=None,
	no_cache=None,
	filters=None,
	from_date=None,
	to_date=None,
	timespan=None,
	time_interval=None,
	heatmap_year=None,
):
	block = sales_block(_filters(filters)) or {"products": []}
	fuel = [p for p in block["products"] if p["uom"] == "Litre"]
	return {
		"labels": [p["product"] for p in fuel],
		"datasets": [{"values": [round(p["actual"]) for p in fuel]}],
	}
