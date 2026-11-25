"""Shared helpers for LOC Planning tests."""

import frappe

TEST_DOCTYPE = "LOC Guard Test Record"


def ensure_test_user(email, roles):
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		)
		user.flags.ignore_permissions = True
		user.insert()
	user = frappe.get_doc("User", email)
	user.flags.ignore_permissions = True
	user.add_roles(*roles)
	return email


def ensure_guard_test_doctype():
	"""A throw-away submittable DocType with the fields the generic guards react to
	(reporting_period, cancel_reason, loc_department). Lives in the LOC Planning module."""
	if frappe.db.exists("DocType", TEST_DOCTYPE):
		return TEST_DOCTYPE
	frappe.get_doc(
		{
			"doctype": "DocType",
			"name": TEST_DOCTYPE,
			"module": "LOC Planning",
			"custom": 1,
			"is_submittable": 1,
			"autoname": "hash",
			"fields": [
				{
					"fieldname": "reporting_period",
					"fieldtype": "Link",
					"options": "Reporting Period",
					"label": "Period",
				},
				{
					"fieldname": "loc_department",
					"fieldtype": "Link",
					"options": "LOC Department",
					"label": "Dept",
				},
				{"fieldname": "amount", "fieldtype": "Float", "label": "Amount", "allow_on_submit": 1},
				{
					"fieldname": "cancel_reason",
					"fieldtype": "Small Text",
					"label": "Reason",
					"allow_on_submit": 1,
				},
			],
			"permissions": [
				{
					"role": "System Manager",
					"read": 1,
					"write": 1,
					"create": 1,
					"delete": 1,
					"submit": 1,
					"cancel": 1,
				},
				{"role": "Department Coordinator", "read": 1, "write": 1, "create": 1},
				{"role": "Sales Office User", "read": 1, "write": 1, "create": 1},
			],
		}
	).insert(ignore_permissions=True)
	return TEST_DOCTYPE


def ensure_period(period_type, year, number):
	from loc_planning.utils.periods import period_name

	name = period_name(period_type, year, number)
	if not frappe.db.exists("Reporting Period", name):
		frappe.get_doc(
			{"doctype": "Reporting Period", "period_type": period_type, "year": year, "period_number": number}
		).insert(ignore_permissions=True)
	return name


def drop_guard_test_doctype():
	if frappe.db.exists("DocType", TEST_DOCTYPE):
		frappe.flags.in_test_cleanup = True
		try:
			frappe.delete_doc("DocType", TEST_DOCTYPE, force=True, ignore_permissions=True)
		finally:
			frappe.flags.in_test_cleanup = False
		frappe.db.commit()


class as_user:
	"""Context manager that runs code as another user and restores the session user."""

	def __init__(self, user):
		self.user = user

	def __enter__(self):
		self.previous = frappe.session.user
		frappe.set_user(self.user)

	def __exit__(self, *exc):
		frappe.set_user(self.previous)
