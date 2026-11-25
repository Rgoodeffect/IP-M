# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

from loc_planning.constants import PERIOD_ADMIN_ROLES
from loc_planning.utils import periods


class ReportingPeriod(Document):
	def autoname(self):
		try:
			self.name = periods.period_name(self.period_type, self.year, self._number())
		except ValueError as e:
			frappe.throw(str(e))

	def validate(self):
		self.period_number = self._number()
		try:
			self.from_date, self.to_date = periods.period_dates(
				self.period_type, self.year, self.period_number
			)
			self.title = periods.period_title(self.period_type, self.year, self.period_number)
		except ValueError as e:
			frappe.throw(str(e))
		self.validate_status_change()

	def _number(self):
		return 1 if self.period_type == "Annual" else cint(self.period_number)

	def validate_status_change(self):
		if self.is_new():
			self.status = "Open"
			return
		if not self.has_value_changed("status"):
			return
		if not can_manage_periods():
			frappe.throw(_("You are not allowed to open or close reporting periods."), frappe.PermissionError)
		if self.status == "Closed":
			self.closed_by = frappe.session.user
			self.closed_on = now_datetime()
		else:
			self.closed_by = None
			self.closed_on = None

	@property
	def is_closed(self):
		return self.status == "Closed"

	def get_previous(self):
		year, number = periods.previous_period(self.period_type, self.year, self.period_number)
		return periods.period_name(self.period_type, year, number)

	def get_same_period_last_year(self):
		year, number = periods.same_period_last_year(self.period_type, self.year, self.period_number)
		return periods.period_name(self.period_type, year, number)


def can_manage_periods(user=None):
	return bool(set(frappe.get_roles(user)).intersection(PERIOD_ADMIN_ROLES))


@frappe.whitelist(methods=["POST"])
def set_period_status(name: str, status: str, remarks: str | None = None):
	if status not in ("Open", "Closed"):
		frappe.throw(_("Invalid status"))
	if not can_manage_periods():
		frappe.throw(_("You are not allowed to open or close reporting periods."), frappe.PermissionError)
	doc = frappe.get_doc("Reporting Period", name)
	doc.check_permission("write")
	doc.status = status
	if remarks:
		doc.status_remarks = remarks
	doc.save()
	return doc.status


@frappe.whitelist(methods=["POST"])
def create_periods_for_year(year: int, period_types: str | list | None = None):
	"""Create every missing period of `year`. Returns the names created."""
	if not can_manage_periods():
		frappe.throw(_("You are not allowed to create reporting periods."), frappe.PermissionError)
	frappe.has_permission("Reporting Period", "create", throw=True)
	if isinstance(period_types, str):
		period_types = frappe.parse_json(period_types)
	period_types = period_types or list(periods.PERIOD_SPEC)

	created = []
	for period_type in period_types:
		if period_type not in periods.PERIOD_SPEC:
			frappe.throw(_("Invalid period type {0}").format(period_type))
		for number in range(1, periods.PERIOD_SPEC[period_type][0] + 1):
			name = periods.period_name(period_type, year, number)
			if frappe.db.exists("Reporting Period", name):
				continue
			frappe.get_doc(
				{
					"doctype": "Reporting Period",
					"period_type": period_type,
					"year": cint(year),
					"period_number": number,
				}
			).insert()
			created.append(name)
	return created


def get_period_for_date(period_type, date):
	"""Return the Reporting Period of `period_type` that contains `date`, or None."""
	return frappe.db.get_value(
		"Reporting Period",
		{"period_type": period_type, "from_date": ("<=", date), "to_date": (">=", date)},
		"name",
	)
