# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today


class FuelStation(Document):
	def validate(self):
		self.station_code = (self.station_code or "").strip()
		self.station_name = " ".join((self.station_name or "").split())
		self.validate_sales_office()
		self.validate_status()
		self.set_capacity_totals()
		self.sync_location()
		self.validate_unique_activities()

	def validate_sales_office(self):
		office = frappe.db.get_value(
			"LOC Department", self.sales_office, ["department_type", "region"], as_dict=True
		)
		if not office or office.department_type != "Sales Office":
			frappe.throw(_("{0} is not a sales office").format(frappe.bold(self.sales_office)))
		if not self.region:
			self.region = office.region

	def validate_status(self):
		if self.status == "Operating":
			self.stop_reason = None
			self.status_since = None
		else:
			if not (self.stop_reason or "").strip():
				frappe.throw(_("Please enter the reason for the status {0}").format(_(self.status)))
			if self.has_value_changed("status") and not self.status_since:
				self.status_since = today()

	def set_capacity_totals(self):
		self.tanks_count = len(self.tanks)
		self.total_capacity = sum(flt(t.capacity) for t in self.tanks)

	def sync_location(self):
		"""Keep latitude/longitude and the map field consistent."""
		if (
			self.latitude
			and self.longitude
			and (
				self.has_value_changed("latitude") or self.has_value_changed("longitude") or not self.location
			)
		):
			self.location = json.dumps(
				{
					"type": "FeatureCollection",
					"features": [
						{
							"type": "Feature",
							"properties": {},
							"geometry": {
								"type": "Point",
								"coordinates": [flt(self.longitude), flt(self.latitude)],
							},
						}
					],
				}
			)
		for name, value in (("latitude", self.latitude), ("longitude", self.longitude)):
			limit = 90 if name == "latitude" else 180
			if value and abs(flt(value)) > limit:
				frappe.throw(_("Invalid {0}").format(_(self.meta.get_label(name))))

	def validate_unique_activities(self):
		seen = set()
		for row in self.support_activities:
			if row.activity_type in seen:
				frappe.throw(
					_("Activity {0} is listed more than once").format(frappe.bold(row.activity_type))
				)
			seen.add(row.activity_type)

	def get_products(self):
		"""Products sold at this station: from its tanks, else every active product."""
		products = []
		for tank in self.tanks:
			if tank.product not in products:
				products.append(tank.product)
		return products or get_active_products()


def get_active_products():
	return frappe.get_all(
		"Fuel Product", filters={"is_active": 1}, order_by="display_order asc, name asc", pluck="name"
	)
