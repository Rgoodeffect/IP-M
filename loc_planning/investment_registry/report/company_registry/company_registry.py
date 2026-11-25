# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, getdate, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, None, get_summary(data)


def get_columns():
	return [
		{
			"label": _("Registration No."),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Registered Company",
			"width": 120,
		},
		{"label": _("Company Name"), "fieldname": "company_name", "fieldtype": "Data", "width": 230},
		{
			"label": _("Classification"),
			"fieldname": "classification",
			"fieldtype": "Link",
			"options": "Company Classification",
			"width": 140,
		},
		{
			"label": _("Commercial Register No."),
			"fieldname": "commercial_register_no",
			"fieldtype": "Data",
			"width": 130,
		},
		{"label": _("Tax No."), "fieldname": "tax_id", "fieldtype": "Data", "width": 120},
		{"label": _("City"), "fieldname": "city", "fieldtype": "Data", "width": 100},
		{"label": _("Phone"), "fieldname": "phone", "fieldtype": "Data", "width": 110},
		{"label": _("Status"), "fieldname": "status_label", "fieldtype": "Data", "width": 90},
		{
			"label": _("Current Certificate"),
			"fieldname": "current_certificate",
			"fieldtype": "Link",
			"options": "Registration Certificate",
			"width": 140,
		},
		{
			"label": _("Certificate Expiry"),
			"fieldname": "certificate_expiry_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{"label": _("Days to Expiry"), "fieldname": "days_to_expiry", "fieldtype": "Int", "width": 90},
		{
			"label": _("Certificate Status"),
			"fieldname": "certificate_status_label",
			"fieldtype": "Data",
			"width": 120,
		},
	]


def get_data(filters):
	conditions = {}
	if filters.classification:
		conditions["classification"] = filters.classification
	if filters.status:
		conditions["status"] = filters.status
	if filters.certificate_status:
		conditions["certificate_status"] = filters.certificate_status
	if filters.from_date and filters.to_date:
		conditions["registration_date"] = ("between", (filters.from_date, filters.to_date))
	if cint(filters.expiring_within_days):
		conditions["certificate_expiry_date"] = (
			"between",
			(today(), add_days(today(), cint(filters.expiring_within_days))),
		)

	rows = frappe.get_list(
		"Registered Company",
		filters=conditions,
		fields=[
			"name",
			"company_name",
			"classification",
			"commercial_register_no",
			"tax_id",
			"city",
			"phone",
			"status",
			"current_certificate",
			"certificate_expiry_date",
			"certificate_status",
		],
		order_by="name asc",
	)
	for row in rows:
		row.status_label = _(row.status)
		row.certificate_status_label = _(row.certificate_status or "None")
		row.days_to_expiry = (
			date_diff(getdate(row.certificate_expiry_date), getdate(today()))
			if row.certificate_expiry_date
			else None
		)
	return rows


def get_summary(data):
	def count(fn):
		return sum(1 for r in data if fn(r))

	return [
		{"label": _("Registered Companies"), "value": len(data), "indicator": "Blue", "datatype": "Int"},
		{
			"label": _("Valid Certificates"),
			"value": count(lambda r: r.certificate_status == "Valid"),
			"indicator": "Green",
			"datatype": "Int",
		},
		{
			"label": _("Expiring Soon"),
			"value": count(lambda r: r.certificate_status == "Expiring Soon"),
			"indicator": "Orange",
			"datatype": "Int",
		},
		{
			"label": _("Expired"),
			"value": count(lambda r: r.certificate_status == "Expired"),
			"indicator": "Red",
			"datatype": "Int",
		},
		{
			"label": _("Without Certificate"),
			"value": count(lambda r: (r.certificate_status or "None") == "None"),
			"indicator": "Grey",
			"datatype": "Int",
		},
	]
