"""Daily reminders for missing monthly station data."""

import frappe
from frappe import _
from frappe.utils import add_months, cint, date_diff, getdate, today

from loc_planning.constants import ROLE_SALES_OFFICE
from loc_planning.stations.data_status import data_due_date, get_station_data_status
from loc_planning.utils.notify import department_users, should_remind
from loc_planning.utils.periods import period_name


def daily():
	remind_missing_station_data()


def remind_missing_station_data(on_date=None):
	"""Notify each sales office about its stations without submitted data for last month."""
	on_date = getdate(on_date or today())
	last_month = add_months(on_date, -1)
	period = period_name("Monthly", last_month.year, last_month.month)
	if not frappe.db.exists("Reporting Period", period):
		return {}
	due = data_due_date(period)
	if not due or not should_remind(due, on_date):
		return {}

	missing = {}
	for row in get_station_data_status(period, ignore_permissions=True):
		if row.state in ("Not Submitted", "Draft", "Returned"):
			missing.setdefault(row.sales_office, []).append(row.station)

	sent = {}
	title = frappe.db.get_value("Reporting Period", period, "title") or period
	for office, stations in missing.items():
		users = office_users(office)
		if not users:
			continue
		subject = _("Monthly data of {0} stations for {1} is not submitted yet (due {2})").format(
			len(stations), title, frappe.format(due, {"fieldtype": "Date"})
		)
		for user in users:
			frappe.get_doc(
				{
					"doctype": "Notification Log",
					"for_user": user,
					"type": "Alert",
					"subject": subject,
					"email_content": ", ".join(stations),
				}
			).insert(ignore_permissions=True)
		sent[office] = users
	return sent


def office_users(office):
	return department_users(office, ROLE_SALES_OFFICE)
