# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

"""Sales by product / region / sales office / station / month.

Quantities of different products are never added together (litres and cylinders),
so every product keeps its own column and its own totals."""

from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import flt

from loc_planning.stations.report_utils import get_product_rows, pct, product_order

GROUP_FIELDS = {
	"Region": ("region", "Link", "LOC Region"),
	"Sales Office": ("sales_office", "Link", "LOC Department"),
	"Station": ("station", "Link", "Fuel Station"),
	"Month": ("reporting_period", "Link", "Reporting Period"),
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	group_by = filters.get("group_by") or "Product"
	rows = get_product_rows(filters)
	if group_by == "Product":
		columns, data = by_product(rows)
	else:
		columns, data = by_dimension(rows, group_by)
	return columns, data, None, get_chart(rows), get_summary(rows)


def by_product(rows):
	columns = [
		{
			"label": _("Product"),
			"fieldname": "product",
			"fieldtype": "Link",
			"options": "Fuel Product",
			"width": 150,
		},
		{"label": _("Unit of Measure"), "fieldname": "uom", "fieldtype": "Data", "width": 100},
		{
			"label": _("Target"),
			"fieldname": "target_qty",
			"fieldtype": "Float",
			"precision": "0",
			"width": 140,
		},
		{
			"label": _("Actual Sales"),
			"fieldname": "actual_qty",
			"fieldtype": "Float",
			"precision": "0",
			"width": 140,
		},
		{"label": _("Achievement %"), "fieldname": "achievement_pct", "fieldtype": "Percent", "width": 120},
		{
			"label": _("Stations"),
			"fieldname": "stations",
			"fieldtype": "Float",
			"precision": "0",
			"width": 90,
		},
	]
	totals = OrderedDict(
		(p.name, frappe._dict(product=p.name, uom=_(p.uom or ""), target_qty=0, actual_qty=0, stations=set()))
		for p in product_order()
	)
	for r in rows:
		t = totals.setdefault(
			r.product,
			frappe._dict(product=r.product, uom=_(r.uom or ""), target_qty=0, actual_qty=0, stations=set()),
		)
		t.target_qty += flt(r.target_qty)
		t.actual_qty += flt(r.actual_qty)
		t.stations.add(r.station)
	data = []
	for t in totals.values():
		if not t.stations:
			continue
		t.achievement_pct = pct(t.actual_qty, t.target_qty)
		t.target_qty, t.actual_qty = round(t.target_qty), round(t.actual_qty)
		t.stations = len(t.stations)
		data.append(t)
	return columns, data


def by_dimension(rows, group_by):
	field, fieldtype, options = GROUP_FIELDS[group_by]
	products = [p for p in product_order() if any(r.product == p.name for r in rows)]
	columns = [
		{"label": _(group_by), "fieldname": "group", "fieldtype": fieldtype, "options": options, "width": 200}
	]
	if group_by == "Station":
		columns.append(
			{"label": _("Station Name"), "fieldname": "station_name", "fieldtype": "Data", "width": 180}
		)
	for i, p in enumerate(products):
		columns.append(
			{
				"label": f"{p.name} ({_(p.uom or '')})",
				"fieldname": f"p{i}",
				"fieldtype": "Float",
				"precision": "0",
				"width": 140,
			}
		)
		columns.append(
			{
				"label": _("Achievement %") + f" - {p.name}",
				"fieldname": f"p{i}_pct",
				"fieldtype": "Percent",
				"width": 110,
			}
		)
	index = {p.name: i for i, p in enumerate(products)}
	groups = OrderedDict()
	for r in sorted(rows, key=lambda r: r.get(field) or ""):
		key = r.get(field)
		g = groups.setdefault(key, {"group": key, "station_name": r.station_name, "_t": {}})
		i = index[r.product]
		g[f"p{i}"] = flt(g.get(f"p{i}")) + flt(r.actual_qty)
		g["_t"][i] = flt(g["_t"].get(i)) + flt(r.target_qty)
	data = []
	for g in groups.values():
		for i, target in g.pop("_t").items():
			g[f"p{i}_pct"] = pct(g.get(f"p{i}"), target)
			g[f"p{i}"] = round(flt(g.get(f"p{i}")))
		data.append(g)
	return columns, data


def get_chart(rows):
	"""Actual sales per product. Only products sharing the first product's unit are drawn,
	so litres and cylinders are never compared on one axis."""
	if not rows:
		return None
	order = [p for p in product_order() if any(r.product == p.name for r in rows)]
	unit = order[0].uom
	totals = OrderedDict((p.name, 0) for p in order if p.uom == unit)
	for r in rows:
		if r.product in totals:
			totals[r.product] += flt(r.actual_qty)
	labels = list(totals)
	return {
		"title": _("Actual Sales") + f" ({_(unit or '')})",
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Actual Sales"), "values": [round(totals[k]) for k in labels]}],
		},
		"type": "bar",
	}


def get_summary(rows):
	summary = []
	totals = OrderedDict()
	for r in rows:
		t = totals.setdefault(r.product, [0, 0, r.uom])
		t[0] += flt(r.actual_qty)
		t[1] += flt(r.target_qty)
	for product, (actual, _target, uom) in totals.items():
		summary.append(
			{
				"label": f"{product} ({_(uom or '')})",
				"value": actual,
				"datatype": "Float",
				"precision": 0,
				"indicator": "Blue",
			}
		)
	return summary
