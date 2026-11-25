# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from loc_planning.constants import LOC_ROLES

# Roles whose access must be limited to their own department / sales office
RESTRICTED_ROLES = ("Department Coordinator", "Sales Office User")


class LOCUserSetup(Document):
	def validate(self):
		for row in self.assignments:
			if row.role not in LOC_ROLES and row.role != "System Manager":
				frappe.throw(
					_("Row {0}: role {1} is not a role of this system").format(row.idx, frappe.bold(row.role))
				)
			if row.role in RESTRICTED_ROLES and not row.loc_department:
				frappe.throw(
					_("Row {0}: a department or sales office is required for role {1}").format(
						row.idx, frappe.bold(_(row.role))
					)
				)
			if row.role == "Sales Office User" and row.loc_department:
				dept_type = frappe.db.get_value("LOC Department", row.loc_department, "department_type")
				if dept_type != "Sales Office":
					frappe.throw(
						_("Row {0}: {1} is not a sales office").format(
							row.idx, frappe.bold(row.loc_department)
						)
					)

	@frappe.whitelist()
	def apply_assignments(self):
		frappe.only_for(("System Manager", "LOC Planning Director"))
		self.save()
		applied = 0
		for row in self.assignments:
			apply_assignment(row.user, row.role, row.loc_department, row.region, row.apply_to_descendants)
			row.status = "Applied"
			row.applied_on = now_datetime()
			applied += 1
		self.save()
		return applied


def apply_assignment(user, role, loc_department=None, region=None, apply_to_descendants=1):
	"""Grant `role` to `user` and restrict the user to `loc_department` / `region`.
	Idempotent: existing roles and User Permissions are left untouched."""
	user_doc = frappe.get_doc("User", user)
	if role not in [r.role for r in user_doc.roles]:
		user_doc.flags.ignore_permissions = True
		user_doc.add_roles(role)

	if loc_department:
		ensure_user_permission(
			user, "LOC Department", loc_department, hide_descendants=0 if apply_to_descendants else 1
		)
	if region:
		ensure_user_permission(user, "LOC Region", region)


def ensure_user_permission(user, allow, for_value, hide_descendants=0):
	filters = {"user": user, "allow": allow, "for_value": for_value}
	if frappe.db.exists("User Permission", filters):
		return
	frappe.get_doc(
		{
			"doctype": "User Permission",
			"user": user,
			"allow": allow,
			"for_value": for_value,
			"apply_to_all_doctypes": 1,
			"hide_descendants": hide_descendants,
		}
	).insert(ignore_permissions=True)
