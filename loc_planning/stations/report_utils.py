"""Shared data access for the station reports. All reads go through `frappe.get_list`
on the parent document, so a sales office user only ever sees its own stations."""

import frappe
from frappe import _
from frappe.utils import flt, getdate


def period_bounds(filters):
	"""(from_date, to_date) from the from/to monthly periods (defaults: the current year)."""

	def bound(name, field):
		return frappe.db.get_value("Reporting Period", name, field) if name else None

	start = filters.get("from_date") or bound(filters.get("from_period"), "from_date")
	end = filters.get("to_date") or bound(filters.get("to_period"), "to_date")
	if not start:
		start = getdate(f"{getdate().year}-01-01")
	if not end:
		end = getdate(f"{getdate().year}-12-31")
	if getdate(start) > getdate(end):
		frappe.throw(_("The start month is after the end month"))
	return start, end


def get_monthly_docs(filters, fields=None, ignore_permissions=False):
	start, end = period_bounds(filters)
	periods = frappe.get_all(
		"Reporting Period",
		filters={"period_type": "Monthly", "from_date": (">=", start), "to_date": ("<=", end)},
		pluck="name",
	)
	if not periods:
		return []
	conditions = {"reporting_period": ("in", periods)}
	conditions["docstatus"] = ("<", 2) if filters.get("include_unapproved") else 1
	for key in ("region", "sales_office", "station"):
		if filters.get(key):
			conditions[key] = filters.get(key)
	# a Python argument, never a filter: report filters come from the browser
	getter = frappe.get_all if ignore_permissions else frappe.get_list
	return getter(
		"Station Monthly Data",
		filters=conditions,
		fields=fields
		or [
			"name",
			"station",
			"station_name",
			"sales_office",
			"region",
			"reporting_period",
			"stopped_days",
			"total_support_revenue",
		],
		order_by="reporting_period asc, station asc",
	)


def get_product_rows(filters, ignore_permissions=False):
	"""One dict per (monthly document, product) with the parent's dimensions attached."""
	docs = get_monthly_docs(filters, ignore_permissions=ignore_permissions)
	if not docs:
		return []
	by_name = {d.name: d for d in docs}
	product_filter = {"parent": ("in", list(by_name)), "parenttype": "Station Monthly Data"}
	if filters.get("product"):
		product_filter["product"] = filters.get("product")
	rows = frappe.get_all(
		"Station Monthly Product",
		filters=product_filter,
		fields=[
			"parent",
			"product",
			"target_qty",
			"actual_qty",
			"opening_stock",
			"received_qty",
			"closing_stock",
			"uom",
		],
	)
	out = []
	for r in rows:
		doc = by_name[r.parent]
		out.append(frappe._dict({**doc, **r}))
	return out


def pct(actual, target):
	return flt(flt(actual) / flt(target) * 100, 2) if flt(target) else None


def product_order():
	return frappe.get_all("Fuel Product", order_by="display_order asc, name asc", fields=["name", "uom"])
