"""Install / migrate hooks: master data seeding (idempotent)."""

import json
import os

import frappe

from loc_planning.constants import LOC_ROLES

SETUP_DATA = os.path.join(os.path.dirname(__file__), "setup_data")

# UOMs needed by the fuel products: (name, must be whole number)
REQUIRED_UOMS = (("Litre", 0), ("Cylinder", 1))


def after_install():
	seed_master_data()
	set_arabic_defaults()


def after_migrate():
	ensure_roles()
	ensure_uoms()


def _load(name):
	with open(os.path.join(SETUP_DATA, name), encoding="utf-8") as fh:
		return json.load(fh)


def seed_master_data():
	"""Create the initial regions, products, organisation tree and settings.
	Safe to run more than once: existing records are never modified."""
	ensure_roles()
	ensure_uoms()
	seed_regions()
	seed_fuel_products()
	seed_departments()
	seed_simple("Company Classification", "classification_name", "company_classifications.json")
	seed_simple("Company Document Type", "document_type_name", "company_document_types.json")
	seed_simple("Station Operation Type", "operation_type_name", "station_operation_types.json")
	seed_simple("Support Activity Type", "activity_type_name", "support_activity_types.json")
	seed_simple("Budget Chapter", "chapter_name", "budget_chapters.json")
	seed_simple("Budget Item", "item_name", "budget_items.json")
	seed_simple("Activity Report Template", "template_name", "activity_report_templates.json")
	from loc_planning.loc_planning.doctype.loc_planning_settings.loc_planning_settings import apply_defaults

	apply_defaults()


def ensure_roles():
	for role in LOC_ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def ensure_uoms():
	for uom, whole in REQUIRED_UOMS:
		if not frappe.db.exists("UOM", uom):
			frappe.get_doc({"doctype": "UOM", "uom_name": uom, "must_be_whole_number": whole}).insert(
				ignore_permissions=True
			)


def seed_regions():
	for row in _load("regions.json"):
		if not frappe.db.exists("LOC Region", row["region_name"]):
			frappe.get_doc({"doctype": "LOC Region", **row}).insert(ignore_permissions=True)


def seed_fuel_products():
	for row in _load("fuel_products.json"):
		if not frappe.db.exists("Fuel Product", row["product_name"]):
			frappe.get_doc({"doctype": "Fuel Product", **row}).insert(ignore_permissions=True)


def seed_simple(doctype, key, filename):
	for row in _load(filename):
		if not frappe.db.exists(doctype, row[key]):
			frappe.get_doc({"doctype": doctype, **row}).insert(ignore_permissions=True)


def seed_departments():
	data = _load("departments.json")
	root = data["root"]
	if not frappe.db.exists("LOC Department", root["department_name"]):
		frappe.get_doc({"doctype": "LOC Department", "is_group": 1, **root}).insert(ignore_permissions=True)

	region = data.get("default_region")
	for row in data["departments"]:
		if frappe.db.exists("LOC Department", row["department_name"]):
			continue
		row = dict(row)
		parent = row.pop("parent", None) or root["department_name"]
		frappe.get_doc(
			{
				"doctype": "LOC Department",
				"parent_loc_department": parent,
				"region": region,
				**row,
			}
		).insert(ignore_permissions=True)


def set_arabic_defaults():
	"""Arabic UI and Libyan Dinar as defaults for a fresh site (does not touch an
	existing company's currency)."""
	if frappe.db.get_single_value("System Settings", "language") in (None, "", "en"):
		frappe.db.set_single_value("System Settings", "language", "ar")
	if frappe.db.exists("Currency", "LYD"):
		frappe.db.set_value("Currency", "LYD", "enabled", 1)
