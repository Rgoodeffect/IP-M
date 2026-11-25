# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import calendar

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from loc_planning.utils.periods import period_name

# Stock variance above this share of (opening + received) is flagged to the user
STOCK_VARIANCE_WARNING = 0.005

DRAFT_STATUS = {"Pending Review": "Pending Review", "Returned": "Returned"}


class StationMonthlyData(Document):
	def autoname(self):
		self.name = f"{self.station}-{self.reporting_period}"

	def before_insert(self):
		if frappe.db.exists(
			"Station Monthly Data",
			{"station": self.station, "reporting_period": self.reporting_period, "docstatus": ("<", 2)},
		):
			frappe.throw(
				_("Monthly data of station {0} for {1} already exists").format(
					frappe.bold(self.station), frappe.bold(self.reporting_period)
				),
				frappe.DuplicateEntryError,
			)

	def validate(self):
		self.validate_period()
		self.validate_station()
		self.validate_products()
		self.validate_stopped_days()
		self.set_totals()
		self.validate_review_comment()
		if self.docstatus == 0:
			self.status = DRAFT_STATUS.get(self.get("workflow_state"), "Draft")

	def validate_period(self):
		period_type = frappe.db.get_value("Reporting Period", self.reporting_period, "period_type")
		if period_type != "Monthly":
			frappe.throw(_("Please select a monthly period"))

	def validate_station(self):
		station = frappe.db.get_value(
			"Fuel Station",
			self.station,
			["sales_office", "region", "is_active", "station_name"],
			as_dict=True,
		)
		if not station:
			frappe.throw(_("Station {0} not found").format(self.station))
		# Record access follows the station's sales office. The office is copied from the
		# station below, after Frappe's own permission check, so check the station itself.
		if not self.flags.ignore_permissions and not frappe.has_permission(
			"Fuel Station", "read", self.station
		):
			frappe.throw(
				_("You are not allowed to enter data for station {0}").format(frappe.bold(self.station)),
				frappe.PermissionError,
			)
		if not station.is_active and self.is_new():
			frappe.throw(_("Station {0} is not active").format(frappe.bold(self.station)))
		# always follow the station (the fields drive record-level permissions)
		self.sales_office = station.sales_office
		self.region = station.region
		self.station_name = station.station_name

	def validate_products(self):
		seen = set()
		warnings = []
		for row in self.products:
			if row.product in seen:
				frappe.throw(
					_("Row {0}: product {1} is entered twice").format(row.idx, frappe.bold(row.product))
				)
			seen.add(row.product)
			for field in ("target_qty", "actual_qty", "opening_stock", "received_qty", "closing_stock"):
				if flt(row.get(field)) < 0:
					frappe.throw(_("Row {0}: quantities cannot be negative").format(row.idx))
			row.achievement_pct = achievement(row.actual_qty, row.target_qty)
			row.stock_variance = flt(
				flt(row.opening_stock) + flt(row.received_qty) - flt(row.actual_qty) - flt(row.closing_stock),
				3,
			)
			base = flt(row.opening_stock) + flt(row.received_qty)
			if base and abs(row.stock_variance) > base * STOCK_VARIANCE_WARNING:
				warnings.append(row.product)
		if warnings and not self.flags.mute_warnings:
			frappe.msgprint(
				_(
					"Stock does not balance for: {0}. Please check opening, received, sales and closing."
				).format(", ".join(warnings)),
				indicator="orange",
				alert=True,
			)

	def validate_stopped_days(self):
		year, month = frappe.db.get_value(
			"Reporting Period", self.reporting_period, ["year", "period_number"]
		)
		days = calendar.monthrange(cint(year), cint(month))[1]
		if cint(self.stopped_days) > days:
			frappe.throw(_("Stopped days cannot exceed {0}").format(days))

	def set_totals(self):
		seen = set()
		for row in self.support_revenues:
			if row.activity_type in seen:
				frappe.throw(
					_("Activity {0} is listed more than once").format(frappe.bold(row.activity_type))
				)
			seen.add(row.activity_type)
		self.total_support_revenue = sum(flt(r.revenue) for r in self.support_revenues)

	def validate_review_comment(self):
		before = self.get_doc_before_save()
		moved_to_returned = (
			self.get("workflow_state") == "Returned" and before and before.get("workflow_state") != "Returned"
		)
		if moved_to_returned and not (self.review_comment or "").strip():
			frappe.throw(
				_(
					"Please write the review comment explaining what must be corrected before returning the data."
				),
				title=_("Review Comment Required"),
			)

	def on_submit(self):
		self.db_set("status", "Approved")

	def on_cancel(self):
		self.db_set("status", "Cancelled")


def achievement(actual, target):
	return flt(flt(actual) / flt(target) * 100, 2) if flt(target) else 0


@frappe.whitelist()
def get_defaults(station: str, reporting_period: str):
	"""Product rows for a new form: the station's products with the opening stock taken from
	the previous month's closing stock, and its active support activities."""
	frappe.has_permission("Fuel Station", "read", station, throw=True)
	station_doc = frappe.get_doc("Fuel Station", station)
	previous = previous_month_doc(station, reporting_period)
	closing = {}
	if previous:
		closing = {
			r.product: r.closing_stock for r in frappe.get_doc("Station Monthly Data", previous).products
		}
	return {
		"products": [{"product": p, "opening_stock": closing.get(p, 0)} for p in station_doc.get_products()],
		"support_revenues": [
			{"activity_type": a.activity_type}
			for a in station_doc.support_activities
			if a.is_active and frappe.db.get_value("Support Activity Type", a.activity_type, "has_revenue")
		],
	}


def previous_month_doc(station, reporting_period):
	year, month = frappe.db.get_value("Reporting Period", reporting_period, ["year", "period_number"]) or (
		None,
		None,
	)
	if not year:
		return None
	prev = period_name("Monthly", year - 1, 12) if month == 1 else period_name("Monthly", year, month - 1)
	return frappe.db.get_value(
		"Station Monthly Data", {"station": station, "reporting_period": prev, "docstatus": ("<", 2)}, "name"
	)
