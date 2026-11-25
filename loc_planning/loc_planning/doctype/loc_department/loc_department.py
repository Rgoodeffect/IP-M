# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet, get_root_of


class LOCDepartment(NestedSet):
	nsm_parent_field = "parent_loc_department"

	def autoname(self):
		"""Name = department name. If the same name already exists (e.g. the same
		department in another region) the region code is appended."""
		name = (self.department_name or "").strip()
		if frappe.db.exists("LOC Department", name) and self.region:
			code = frappe.db.get_value("LOC Region", self.region, "region_code") or self.region
			name = f"{name} - {code}"
		if frappe.db.exists("LOC Department", name):
			frappe.throw(
				_("Department {0} already exists").format(frappe.bold(name)), frappe.DuplicateEntryError
			)
		self.name = name

	def validate(self):
		self.department_name = (self.department_name or "").strip()
		if self.department_type == "Company":
			self.is_group = 1
		if not self.parent_loc_department and self.department_type != "Company":
			root = get_root_of("LOC Department")
			if root and root != self.name:
				self.parent_loc_department = root
		if self.parent_loc_department:
			if self.parent_loc_department == self.name:
				frappe.throw(_("A department cannot be its own parent"))
			if not frappe.db.get_value("LOC Department", self.parent_loc_department, "is_group"):
				frappe.throw(
					_("Parent department {0} must be marked as Is Group").format(
						frappe.bold(self.parent_loc_department)
					)
				)
		if self.report_deadline_days and self.report_deadline_days < 0:
			frappe.throw(_("Deadline days cannot be negative"))

	def on_update(self):
		if not frappe.local.flags.ignore_update_nsm:
			super().on_update()

	def on_trash(self):
		super().on_trash(allow_root_deletion=True)


def on_doctype_update():
	frappe.db.add_index("LOC Department", ["lft", "rgt"])


def get_departments_requiring_report(region=None):
	filters = {"requires_activity_report": 1, "is_active": 1}
	if region:
		filters["region"] = region
	return frappe.get_all("LOC Department", filters=filters, pluck="name", order_by="lft")


def get_descendants(department, include_self=True):
	"""Names of `department` and every department below it."""
	lft, rgt = frappe.db.get_value("LOC Department", department, ["lft", "rgt"]) or (None, None)
	if lft is None:
		return []
	op = ">=" if include_self else ">"
	return frappe.get_all(
		"LOC Department",
		filters={"lft": (op, lft), "rgt": ("<=" if include_self else "<", rgt)},
		pluck="name",
	)


@frappe.whitelist()
def get_children(doctype: str, parent: str | None = None, is_root: bool = False, **kwargs):
	if is_root or not parent or parent == doctype:
		filters = {"parent_loc_department": ("is", "not set")}
	else:
		filters = {"parent_loc_department": parent}
	return frappe.get_list(
		"LOC Department",
		fields=["name as value", "department_name as title", "is_group as expandable", "department_type"],
		filters=filters,
		order_by="lft",
	)


@frappe.whitelist(methods=["POST"])
def add_node():
	from frappe.desk.treeview import make_tree_args

	args = make_tree_args(**frappe.form_dict)
	args.doctype = "LOC Department"
	if not args.department_name:
		args.department_name = args.get("loc_department_name") or args.get("name_field")
	frappe.get_doc(args).insert()
