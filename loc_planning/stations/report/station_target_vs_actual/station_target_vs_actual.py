# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import flt

from loc_planning.stations.report_utils import get_product_rows, pct, product_order


def execute(filters=None):
	filters = frappe._dict(filters or {})
	rows = get_product_rows(filters)
	return get_columns(), get_data(rows), None, get_chart(rows, filters), get_summary(rows)


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
			"label": _("Product"),
			"fieldname": "product",
			"fieldtype": "Link",
			"options": "Fuel Product",
			"width": 110,
		},
		{"label": _("Unit of Measure"), "fieldname": "uom", "fieldtype": "Data", "width": 90},
		{
			"label": _("Target"),
			"fieldname": "target_qty",
			"fieldtype": "Float",
			"precision": "0",
			"width": 120,
		},
		{
			"label": _("Actual Sales"),
			"fieldname": "actual_qty",
			"fieldtype": "Float",
			"precision": "0",
			"width": 120,
		},
		{
			"label": _("Variance"),
			"fieldname": "variance",
			"fieldtype": "Float",
			"precision": "0",
			"width": 120,
		},
		{"label": _("Achievement %"), "fieldname": "achievement_pct", "fieldtype": "Percent", "width": 110},
	]


def get_data(rows):
	grouped = OrderedDict()
	for r in sorted(rows, key=lambda r: (r.sales_office or "", r.station, r.product)):
		key = (r.station, r.product)
		g = grouped.setdefault(
			key,
			frappe._dict(
				station=r.station,
				station_name=r.station_name,
				sales_office=r.sales_office,
				product=r.product,
				uom=_(r.uom or ""),
				target_qty=0,
				actual_qty=0,
			),
		)
		g.target_qty += flt(r.target_qty)
		g.actual_qty += flt(r.actual_qty)
	data = []
	for g in grouped.values():
		g.achievement_pct = pct(g.actual_qty, g.target_qty)
		g.target_qty, g.actual_qty = round(g.target_qty), round(g.actual_qty)
		g.variance = g.actual_qty - g.target_qty
		data.append(g)
	return data


def get_chart(rows, filters):
	"""Monthly target vs actual for one product (the filtered one, else the first)."""
	if not rows:
		return None
	present = {r.product for r in rows}
	product = filters.get("product") or next(p.name for p in product_order() if p.name in present)
	months = OrderedDict()
	for r in sorted(rows, key=lambda r: r.reporting_period):
		if r.product != product:
			continue
		m = months.setdefault(r.reporting_period, [0, 0])
		m[0] += flt(r.target_qty)
		m[1] += flt(r.actual_qty)
	labels = list(months)
	return {
		"title": product,
		"data": {
			"labels": [frappe.db.get_value("Reporting Period", m, "title") or m for m in labels],
			"datasets": [
				{"name": _("Target"), "values": [round(months[m][0]) for m in labels]},
				{"name": _("Actual Sales"), "values": [round(months[m][1]) for m in labels]},
			],
		},
		"type": "line",
	}


def get_summary(rows):
	totals = OrderedDict()
	for r in rows:
		t = totals.setdefault(r.product, [0, 0])
		t[0] += flt(r.target_qty)
		t[1] += flt(r.actual_qty)
	return [
		{
			"label": _("Achievement %") + f" - {product}",
			"value": pct(actual, target) or 0,
			"datatype": "Percent",
			"indicator": "Green" if (pct(actual, target) or 0) >= 100 else "Orange",
		}
		for product, (target, actual) in totals.items()
	]
