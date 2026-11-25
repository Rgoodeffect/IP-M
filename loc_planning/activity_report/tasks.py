"""Daily reminders for department activity reports (before and after the deadline)."""

import frappe
from frappe import _
from frappe.utils import add_months, getdate, today

from loc_planning.activity_report.deadlines import get_status, report_period_type
from loc_planning.constants import ROLE_DEPT_COORDINATOR
from loc_planning.utils.notify import department_users, notify, should_remind

PENDING_STATES = ("Not Submitted", "Draft", "Returned")


def daily():
	remind_departments()


def remind_departments(on_date=None):
	"""Returns {department: [users]} reminded today."""
	on_date = getdate(on_date or today())
	periods = frappe.get_all(
		"Reporting Period",
		filters={
			"period_type": report_period_type(),
			"to_date": ("between", (add_months(on_date, -12), on_date)),
		},
		fields=["name", "title"],
	)
	sent = {}
	for period in periods:
		for row in get_status(period.name):
			if (
				row.state not in PENDING_STATES
				or not row.due_date
				or not should_remind(row.due_date, on_date)
			):
				continue
			users = department_users(row.department, ROLE_DEPT_COORDINATOR)
			head = frappe.db.get_value("LOC Department", row.department, "head_user")
			if head:
				users.append(head)
			if getdate(row.due_date) >= on_date:
				subject = _("Reminder: the activity report of {0} for {1} is due on {2}")
			else:
				subject = _("Overdue: the activity report of {0} for {1} was due on {2}")
			subject = subject.format(
				row.department, period.title, frappe.format(row.due_date, {"fieldtype": "Date"})
			)
			reached = notify(
				users, subject, document_type="Department Activity Submission", document_name=row.submission
			)
			if reached:
				sent.setdefault(row.department, []).extend(reached)
	return sent
