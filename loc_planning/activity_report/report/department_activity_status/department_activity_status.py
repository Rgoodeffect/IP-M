# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

"""حالة تقارير الإدارات: one row per department required to report, for a period."""

import frappe
from frappe import _

from loc_planning.activity_report.deadlines import get_status

COLORS = {
	"Not Submitted": "red",
	"Draft": "gray",
	"Returned": "red",
	"Manager Review": "blue",
	"Statistics Review": "orange",
	"Planning Approval": "orange",
	"Approved": "green",
	"Included in Report": "green",
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("reporting_period"):
		frappe.throw(_("Please select a period"))
	visible = set(frappe.get_list("LOC Department", pluck="name"))
	rows = get_status(filters.reporting_period, filters.get("region"), departments=visible)
	for r in rows:
		r.state_label = _(r.state)
		r.color = COLORS.get(r.state, "gray")
	return get_columns(), rows, None, get_chart(rows), get_summary(rows)


def get_columns():
	return [
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "LOC Department",
			"width": 280,
		},
		{
			"label": _("Region"),
			"fieldname": "region",
			"fieldtype": "Link",
			"options": "LOC Region",
			"width": 90,
		},
		{"label": _("Status"), "fieldname": "state_label", "fieldtype": "Data", "width": 170},
		{
			"label": _("Submission"),
			"fieldname": "submission",
			"fieldtype": "Link",
			"options": "Department Activity Submission",
			"width": 230,
		},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Submitted On"), "fieldname": "submitted_on", "fieldtype": "Datetime", "width": 150},
		{"label": _("Days Late"), "fieldname": "days_late", "fieldtype": "Int", "width": 90},
		{
			"label": _("Overall Achievement"),
			"fieldname": "overall_achievement",
			"fieldtype": "Percent",
			"width": 120,
		},
		{"label": "", "fieldname": "color", "fieldtype": "Data", "hidden": 1},
	]


def get_chart(rows):
	counts = {}
	for r in rows:
		counts[r.state_label] = counts.get(r.state_label, 0) + 1
	if not counts:
		return None
	return {
		"data": {
			"labels": list(counts),
			"datasets": [{"name": _("Departments"), "values": list(counts.values())}],
		},
		"type": "bar",
	}


def get_summary(rows):
	received = [r for r in rows if r.state not in ("Not Submitted", "Draft", "Returned")]
	approved = [r for r in rows if r.state in ("Approved", "Included in Report")]
	late = [r for r in rows if r.days_late]
	return [
		{"label": _("Required Reports"), "value": len(rows), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Received"), "value": len(received), "datatype": "Int", "indicator": "Green"},
		{"label": _("Approved"), "value": len(approved), "datatype": "Int", "indicator": "Green"},
		{
			"label": _("Not Submitted"),
			"value": sum(1 for r in rows if r.state == "Not Submitted"),
			"datatype": "Int",
			"indicator": "Red",
		},
		{"label": _("Late"), "value": len(late), "datatype": "Int", "indicator": "Orange"},
	]
