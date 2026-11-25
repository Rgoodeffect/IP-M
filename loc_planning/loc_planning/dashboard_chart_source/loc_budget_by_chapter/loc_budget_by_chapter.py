"""Budget execution by chapter (approved vs executed) up to the end of the selected period."""

import frappe
from frappe import _

from loc_planning.dashboard.api import _filters, budget_block


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
	block = budget_block(_filters(filters)) or {"chapters": []}
	return {
		"labels": [c["chapter"] for c in block["chapters"]],
		"datasets": [
			{"name": _("Approved Amount"), "values": [round(c["approved"]) for c in block["chapters"]]},
			{"name": _("Executed"), "values": [round(c["executed"]) for c in block["chapters"]]},
		],
	}
