"""Fuel sales (litres): monthly target vs actual for the year of the selected period."""

import frappe
from frappe import _

from loc_planning.dashboard.api import _filters, monthly_trend


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
	months = monthly_trend(_filters(filters)) or []
	return {
		"labels": [m["label"] for m in months],
		"datasets": [
			{"name": _("Target"), "values": [round(m["target"]) for m in months]},
			{"name": _("Actual Sales"), "values": [round(m["actual"]) for m in months]},
		],
	}
