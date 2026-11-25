"""Monthly data submission status per station (used by the report and the reminders)."""

import frappe
from frappe.utils import add_days, cint, getdate

from loc_planning.constants import SETTINGS_DOCTYPE


def data_due_date(reporting_period):
	"""Due date = the configured day of the month after the period."""
	to_date = frappe.db.get_value("Reporting Period", reporting_period, "to_date")
	if not to_date:
		return None
	day = cint(frappe.get_cached_doc(SETTINGS_DOCTYPE).station_data_due_day) or 10
	return add_days(getdate(to_date), day)


def get_station_data_status(reporting_period, region=None, sales_office=None, ignore_permissions=False):
	"""One row per active station with the state of its data for the month.
	States: Not Submitted / Draft / Returned / Pending Review / Approved."""
	filters = {"is_active": 1}
	if region:
		filters["region"] = region
	if sales_office:
		filters["sales_office"] = sales_office
	getter = frappe.get_all if ignore_permissions else frappe.get_list
	stations = getter(
		"Fuel Station",
		filters=filters,
		fields=["name", "station_name", "sales_office", "region"],
		order_by="sales_office asc, name asc",
	)
	docs = {
		d.station: d
		for d in frappe.get_all(
			"Station Monthly Data",
			filters={"reporting_period": reporting_period, "docstatus": ("<", 2)},
			fields=["name", "station", "docstatus", "workflow_state"],
		)
	}
	out = []
	for s in stations:
		d = docs.get(s.name)
		if not d:
			state = "Not Submitted"
		elif d.docstatus == 1:
			state = "Approved"
		else:
			state = d.workflow_state or "Draft"
		out.append(
			frappe._dict(
				station=s.name,
				station_name=s.station_name,
				sales_office=s.sales_office,
				region=s.region,
				state=state,
				document=d.name if d else None,
			)
		)
	return out
