"""Deadlines and submission status of the periodic department activity reports."""

import frappe
from frappe.utils import add_days, cint, date_diff, getdate, today

from loc_planning.constants import SETTINGS_DOCTYPE

SUBMITTED_STATES = (
	"Manager Review",
	"Statistics Review",
	"Planning Approval",
	"Approved",
	"Included in Report",
)


def report_period_type():
	return frappe.get_cached_doc(SETTINGS_DOCTYPE).activity_report_period_type or "Quarterly"


def due_date(department, reporting_period):
	"""Period end + the department's own deadline (if set) or the general one."""
	to_date = frappe.db.get_value("Reporting Period", reporting_period, "to_date")
	if not to_date:
		return None
	days = frappe.db.get_value("LOC Department", department, "report_deadline_days")
	if not cint(days):
		days = cint(frappe.get_cached_doc(SETTINGS_DOCTYPE).activity_report_deadline_days) or 15
	return add_days(getdate(to_date), cint(days))


def days_late(due, submitted_on=None):
	end = getdate(submitted_on) if submitted_on else getdate(today())
	return max(date_diff(end, getdate(due)), 0) if due else 0


def required_departments(region=None):
	filters = {"requires_activity_report": 1, "is_active": 1}
	if region:
		filters["region"] = region
	return frappe.get_all(
		"LOC Department",
		filters=filters,
		fields=["name", "region", "head_user", "department_type"],
		order_by="lft",
	)


def get_status(reporting_period, region=None, departments=None):
	"""One row per department required to report, with its submission state."""
	subs = {
		s.department: s
		for s in frappe.get_all(
			"Department Activity Submission",
			filters={"reporting_period": reporting_period, "docstatus": ("<", 2)},
			fields=[
				"name",
				"department",
				"workflow_state",
				"submitted_on",
				"approved_on",
				"overall_achievement",
			],
		)
	}
	rows = []
	for d in required_departments(region):
		if departments is not None and d.name not in departments:
			continue
		s = subs.get(d.name)
		due = due_date(d.name, reporting_period)
		state = (s.workflow_state or "Draft") if s else "Not Submitted"
		submitted = s.submitted_on if s and state in SUBMITTED_STATES else None
		rows.append(
			frappe._dict(
				department=d.name,
				department_type=d.department_type,
				region=d.region,
				state=state,
				submission=s.name if s else None,
				due_date=due,
				submitted_on=submitted,
				approved_on=s.approved_on if s else None,
				overall_achievement=s.overall_achievement if s else None,
				# late days count until the first submission to the manager (or until today)
				days_late=days_late(due, submitted),
			)
		)
	return rows
