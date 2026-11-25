# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

"""Stations that are not operating now, plus stations that reported stopped days in the
selected months."""

import frappe
from frappe import _
from frappe.utils import cint, date_diff, getdate, today

from loc_planning.stations.report_utils import get_monthly_docs


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, None, get_summary(data)


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
			"width": 180,
		},
		{
			"label": _("Region"),
			"fieldname": "region",
			"fieldtype": "Link",
			"options": "LOC Region",
			"width": 90,
		},
		{"label": _("Status"), "fieldname": "status_label", "fieldtype": "Data", "width": 110},
		{"label": _("Stop Reason"), "fieldname": "stop_reason", "fieldtype": "Data", "width": 220},
		{"label": _("Status Since"), "fieldname": "status_since", "fieldtype": "Date", "width": 100},
		{"label": _("Days in Status"), "fieldname": "days_in_status", "fieldtype": "Int", "width": 90},
		{"label": _("Stopped Days in Period"), "fieldname": "stopped_days", "fieldtype": "Int", "width": 110},
		{
			"label": _("Last Safety Inspection"),
			"fieldname": "last_safety_inspection",
			"fieldtype": "Date",
			"width": 110,
		},
	]


def get_data(filters):
	conditions = {"is_active": 1}
	for key in ("region", "sales_office"):
		if filters.get(key):
			conditions[key] = filters.get(key)
	stations = {
		s.name: s
		for s in frappe.get_list(
			"Fuel Station",
			filters=conditions,
			fields=[
				"name",
				"station_name",
				"sales_office",
				"region",
				"status",
				"stop_reason",
				"status_since",
				"last_safety_inspection",
			],
		)
	}
	stopped = {}
	for d in get_monthly_docs(filters):
		if cint(d.stopped_days) and d.station in stations:
			stopped[d.station] = stopped.get(d.station, 0) + cint(d.stopped_days)

	data = []
	for name, s in sorted(stations.items(), key=lambda x: (x[1].sales_office or "", x[0])):
		if filters.get("status") and s.status != filters.status:
			continue
		if s.status == "Operating" and not stopped.get(name):
			continue
		data.append(
			frappe._dict(
				station=name,
				station_name=s.station_name,
				sales_office=s.sales_office,
				region=s.region,
				status=s.status,
				status_label=_(s.status),
				stop_reason=s.stop_reason,
				status_since=s.status_since,
				days_in_status=date_diff(today(), getdate(s.status_since))
				if s.status_since and s.status != "Operating"
				else None,
				stopped_days=stopped.get(name, 0),
				last_safety_inspection=s.last_safety_inspection,
			)
		)
	return data


def get_summary(data):
	counts = {}
	for d in data:
		counts[d.status] = counts.get(d.status, 0) + 1
	colors = {
		"Stopped": "Red",
		"Under Maintenance": "Orange",
		"Under Construction": "Blue",
		"Operating": "Green",
	}
	return [
		{"label": _(status), "value": n, "datatype": "Int", "indicator": colors.get(status, "Grey")}
		for status, n in counts.items()
	]
