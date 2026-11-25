# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

"""Stations whose monthly data for the selected month is missing or not yet approved."""

import frappe
from frappe import _
from frappe.utils import cint, date_diff, getdate, today

from loc_planning.stations.data_status import data_due_date, get_station_data_status


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("reporting_period"):
		frappe.throw(_("Please select a month"))
	data = get_data(filters)
	return get_columns(), data, None, get_chart(data), get_summary(data)


def get_columns():
	return [
		{
			"label": _("Station"),
			"fieldname": "station",
			"fieldtype": "Link",
			"options": "Fuel Station",
			"width": 110,
		},
		{"label": _("Station Name"), "fieldname": "station_name", "fieldtype": "Data", "width": 180},
		{
			"label": _("Sales Office"),
			"fieldname": "sales_office",
			"fieldtype": "Link",
			"options": "LOC Department",
			"width": 190,
		},
		{
			"label": _("Region"),
			"fieldname": "region",
			"fieldtype": "Link",
			"options": "LOC Region",
			"width": 90,
		},
		{"label": _("Data Status"), "fieldname": "state_label", "fieldtype": "Data", "width": 130},
		{
			"label": _("Document"),
			"fieldname": "document",
			"fieldtype": "Link",
			"options": "Station Monthly Data",
			"width": 170,
		},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Days Overdue"), "fieldname": "days_overdue", "fieldtype": "Int", "width": 90},
	]


def get_data(filters):
	due = data_due_date(filters.reporting_period)
	overdue = max(date_diff(today(), due), 0) if due else 0
	rows = get_station_data_status(
		filters.reporting_period, filters.get("region"), filters.get("sales_office")
	)
	data = []
	for r in rows:
		if r.state == "Approved" and not cint(filters.get("show_all")):
			continue
		r.state_label = _(r.state)
		r.due_date = due
		r.days_overdue = overdue if r.state != "Approved" and getdate(today()) > getdate(due) else 0
		data.append(r)
	return data


def get_chart(data):
	counts = {}
	for d in data:
		counts[d.state_label] = counts.get(d.state_label, 0) + 1
	if not counts:
		return None
	return {
		"data": {
			"labels": list(counts),
			"datasets": [{"name": _("Stations"), "values": list(counts.values())}],
		},
		"type": "bar",
	}


def get_summary(data):
	missing = sum(1 for d in data if d.state == "Not Submitted")
	pending = sum(1 for d in data if d.state in ("Draft", "Returned", "Pending Review"))
	return [
		{"label": _("Not Submitted"), "value": missing, "datatype": "Int", "indicator": "Red"},
		{"label": _("Not Yet Approved"), "value": pending, "datatype": "Int", "indicator": "Orange"},
	]
