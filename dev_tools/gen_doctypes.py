#!/usr/bin/env python3
"""Generate DocType JSON files and the Arabic translation catalog from the specs.

Usage (from the repository root):
    python3 dev_tools/gen_doctypes.py

- Writes `loc_planning/<module>/doctype/<name>/<name>.json` for every spec.
- Creates `__init__.py` and a controller `.py` stub only when missing,
  so hand-written controllers are never overwritten.
- Rebuilds `loc_planning/translations/ar.csv` from every label in the specs plus
  `dev_tools/manual_ar.csv` (messages used in code).
- The `modified` timestamp is bumped only when the JSON content actually changed, so
  `bench migrate` reloads exactly the DocTypes that were edited.
"""

import csv
import datetime
import importlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "loc_planning")
SPEC_DIR = os.path.join(ROOT, "dev_tools", "doctype_specs")
sys.path.insert(0, SPEC_DIR)

SPEC_MODULES = ["phase1"]
MODULE_FOLDERS = {
	"LOC Planning": "loc_planning",
	"Budget": "budget",
	"Stations": "stations",
	"Activity Report": "activity_report",
	"Investment Registry": "investment_registry",
}


def scrub(name):
	return name.replace(" ", "_").replace("-", "_").replace("&", "and").lower()


def classname(name):
	return "".join(p for p in name.replace("-", " ").replace("&", " ").split())


class Translations:
	def __init__(self):
		self.rows = {}

	def add(self, en, ar):
		if en and ar and en != ar:
			if en in self.rows and self.rows[en] != ar:
				# first definition wins; keep labels consistent across DocTypes
				return
			self.rows.setdefault(en, ar)


def build_field(spec_field, idx, tr):
	fieldname, fieldtype, labels, extra = spec_field
	f = {"fieldname": fieldname, "fieldtype": fieldtype}
	if labels:
		f["label"] = labels[0]
		tr.add(labels[0], labels[1])
	for key, value in extra.items():
		if key == "options" and isinstance(value, list):
			f["options"] = "\n".join(v[0] if isinstance(v, tuple) else v for v in value)
			for v in value:
				if isinstance(v, tuple):
					tr.add(v[0], v[1])
		elif key == "options" and isinstance(value, tuple):
			# HTML content: Arabic is the display language
			f["options"] = value[1]
		elif key == "description" and isinstance(value, tuple):
			f["description"] = value[0]
			tr.add(value[0], value[1])
		else:
			f[key] = value
	return f


def build_doctype(spec, tr):
	name = spec["name"]
	tr.add(name, spec.get("title_ar"))
	fields = [build_field(sf, i, tr) for i, sf in enumerate(spec["fields"])]
	doc = {
		"actions": [],
		"allow_import": 0 if spec.get("issingle") or spec.get("istable") else 1,
		"allow_rename": spec.get("allow_rename", 0),
		"creation": "2026-11-25 12:00:00.000000",
		"doctype": "DocType",
		"engine": "InnoDB",
		"field_order": [f["fieldname"] for f in fields],
		"fields": fields,
		"index_web_pages_for_search": 0,
		"links": [],
		"modified_by": "Administrator",
		"module": spec["module"],
		"name": name,
		"owner": "Administrator",
		"permissions": spec.get("permissions", []),
		"sort_field": spec.get("sort_field", "creation"),
		"sort_order": spec.get("sort_order", "DESC"),
		"states": [],
		"track_changes": 0 if spec.get("istable") else 1,
	}
	for key in (
		"autoname",
		"naming_rule",
		"is_tree",
		"nsm_parent_field",
		"title_field",
		"show_title_field_in_link",
		"search_fields",
		"issingle",
		"istable",
		"is_submittable",
		"editable_grid",
		"quick_entry",
		"track_seen",
		"image_field",
		"max_attachments",
		"description",
	):
		if key in spec:
			doc[key] = spec[key]
	if spec.get("istable"):
		doc["editable_grid"] = spec.get("editable_grid", 1)
	if spec.get("is_submittable"):
		doc["is_submittable"] = 1
	return dict(sorted(doc.items()))


CONTROLLER = """# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

{imports}


class {cls}({base}):
	pass
"""


def write_if_missing(path, content):
	if not os.path.exists(path):
		with open(path, "w", encoding="utf-8") as fh:
			fh.write(content)


def write_doctype(spec, tr):
	doc = build_doctype(spec, tr)
	folder = os.path.join(APP, MODULE_FOLDERS[spec["module"]], "doctype", scrub(spec["name"]))
	os.makedirs(folder, exist_ok=True)
	write_if_missing(os.path.join(os.path.dirname(folder), "__init__.py"), "")
	write_if_missing(os.path.join(folder, "__init__.py"), "")
	path = os.path.join(folder, scrub(spec["name"]) + ".json")

	modified = None
	if os.path.exists(path):
		with open(path, encoding="utf-8") as fh:
			old = json.load(fh)
		old_modified = old.pop("modified", None)
		if old == doc:
			modified = old_modified
	doc["modified"] = modified or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
	doc = dict(sorted(doc.items()))
	with open(path, "w", encoding="utf-8") as fh:
		json.dump(doc, fh, indent=1, ensure_ascii=False)
		fh.write("\n")

	cls = classname(spec["name"])
	if spec.get("is_tree"):
		imports, base = "from frappe.utils.nestedset import NestedSet", "NestedSet"
	else:
		imports, base = "from frappe.model.document import Document", "Document"
	write_if_missing(
		os.path.join(folder, scrub(spec["name"]) + ".py"),
		CONTROLLER.format(imports=imports, cls=cls, base=base),
	)
	# Client scripts and tests are hand-written (tests live in loc_planning/tests/).
	return path


def write_translations(tr):
	manual = os.path.join(ROOT, "dev_tools", "manual_ar.csv")
	if os.path.exists(manual):
		with open(manual, encoding="utf-8", newline="") as fh:
			for row in csv.reader(fh):
				if len(row) >= 2 and row[0] and not row[0].startswith("#"):
					tr.add(row[0], row[1])
	out_dir = os.path.join(APP, "translations")
	os.makedirs(out_dir, exist_ok=True)
	with open(os.path.join(out_dir, "ar.csv"), "w", encoding="utf-8", newline="") as fh:
		writer = csv.writer(fh, lineterminator="\n")
		for en in sorted(tr.rows):
			writer.writerow([en, tr.rows[en]])


def main():
	tr = Translations()
	for mod in SPEC_MODULES:
		specs = importlib.import_module(mod)
		for role, label in importlib.import_module("roles").ROLE_LABELS_AR.items():
			tr.add(role, label)
		for spec in specs.SPECS:
			print("wrote", os.path.relpath(write_doctype(spec, tr), ROOT))
	write_translations(tr)
	print("translations:", len(tr.rows))


if __name__ == "__main__":
	main()
