"""Reminder schedule and in-app / email notifications shared by all modules."""

import frappe
from frappe.utils import cint, date_diff, getdate, today

from loc_planning.constants import SETTINGS_DOCTYPE


def should_remind(due_date, on_date=None):
	"""True on the configured days: `reminder_days_before` days before the due date, on it,
	and every `reminder_repeat_days_after` days after it (at most `max_overdue_reminders`)."""
	s = frappe.get_cached_doc(SETTINGS_DOCTYPE)
	delta = date_diff(getdate(due_date), getdate(on_date or today()))  # > 0 before the due date
	if delta > 0:
		return delta == cint(s.reminder_days_before)
	if delta == 0:
		return True
	every = cint(s.reminder_repeat_days_after) or 1
	late = -delta
	return late % every == 0 and late // every <= cint(s.max_overdue_reminders)


def notify(users, subject, message=None, document_type=None, document_name=None):
	"""System notification for each user, plus one email when an outgoing account exists."""
	users = sorted({u for u in users or [] if u and u not in ("Administrator", "Guest")})
	if not users:
		return []
	enabled = set(frappe.get_all("User", filters={"name": ("in", users), "enabled": 1}, pluck="name"))
	users = [u for u in users if u in enabled]
	for user in users:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"subject": subject,
				"email_content": message or subject,
				"document_type": document_type,
				"document_name": document_name,
			}
		).insert(ignore_permissions=True)
	if users and frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}):
		frappe.sendmail(
			recipients=users,
			subject=subject,
			message=f"<div dir='rtl'>{message or subject}</div>",
			reference_doctype=document_type,
			reference_name=document_name,
			delayed=True,
		)
	return users


def department_users(department, role):
	"""Enabled users holding `role` and restricted (User Permission) to `department`."""
	users = frappe.get_all(
		"User Permission",
		filters={"allow": "LOC Department", "for_value": department},
		pluck="user",
		distinct=True,
	)
	if not users:
		return []
	with_role = frappe.get_all(
		"Has Role", filters={"role": role, "parent": ("in", users), "parenttype": "User"}, pluck="parent"
	)
	return frappe.get_all("User", filters={"name": ("in", with_role or [""]), "enabled": 1}, pluck="name")


def role_users(role):
	users = frappe.get_all(
		"Has Role",
		filters={"role": role, "parenttype": "User", "parent": ("not in", ("Administrator", "Guest"))},
		pluck="parent",
		distinct=True,
	)
	return frappe.get_all("User", filters={"name": ("in", users or [""]), "enabled": 1}, pluck="name")
