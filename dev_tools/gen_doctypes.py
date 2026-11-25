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

SPEC_MODULES = ["phase1", "phase2", "phase3"]
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
		"default_print_format",
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


def write_workflow_fixtures(tr):
	sys.path.insert(0, os.path.join(ROOT, "dev_tools"))
	wf = importlib.import_module("workflow_specs")
	fixtures = os.path.join(APP, "fixtures")
	os.makedirs(fixtures, exist_ok=True)
	ts = "2026-11-25 12:00:00.000000"

	workflows, states, actions = [], {}, set()
	for spec in wf.WORKFLOWS:
		tr.add(spec["name"], wf.WORKFLOW_AR.get(spec["name"]))
		doc = {
			"doctype": "Workflow",
			"name": spec["name"],
			"workflow_name": spec["name"],
			"document_type": spec["document_type"],
			"is_active": 1,
			"override_status": 0,
			"send_email_alert": 0,
			"enable_action_confirmation": 1,
			"workflow_state_field": "workflow_state",
			"modified": ts,
			"states": [],
			"transitions": [],
		}
		for state, docstatus, role, style in spec["states"]:
			states[state] = style
			doc["states"].append(
				{"state": state, "doc_status": str(docstatus), "allow_edit": role, "is_optional_state": 0}
			)
		for src, action, dst, role in spec["transitions"]:
			actions.add(action)
			doc["transitions"].append(
				{"state": src, "action": action, "next_state": dst, "allowed": role, "allow_self_approval": 1}
			)
		workflows.append(doc)

	for state, ar in wf.STATE_AR.items():
		tr.add(state, ar)
	for action, ar in wf.ACTION_AR.items():
		tr.add(action, ar)

	def dump(name, data):
		with open(os.path.join(fixtures, name), "w", encoding="utf-8") as fh:
			json.dump(data, fh, indent=1, ensure_ascii=False)
			fh.write("\n")

	dump("workflow.json", workflows)
	dump(
		"workflow_state.json",
		[
			{"doctype": "Workflow State", "name": s, "workflow_state_name": s, "style": style, "modified": ts}
			for s, style in sorted(states.items())
		],
	)
	dump(
		"workflow_action_master.json",
		[
			{"doctype": "Workflow Action Master", "name": a, "workflow_action_name": a, "modified": ts}
			for a in sorted(actions)
		],
	)
	return sorted(states), sorted(actions), [w["name"] for w in workflows]


def write_print_formats():
	sys.path.insert(0, os.path.join(ROOT, "dev_tools"))
	specs = importlib.import_module("print_format_specs")
	for spec in specs.PRINT_FORMATS:
		folder = os.path.join(APP, MODULE_FOLDERS[spec["module"]], "print_format", scrub(spec["name"]))
		os.makedirs(folder, exist_ok=True)
		write_if_missing(os.path.join(os.path.dirname(folder), "__init__.py"), "")
		write_if_missing(os.path.join(folder, "__init__.py"), "")
		with open(os.path.join(folder, scrub(spec["name"]) + ".html"), encoding="utf-8") as fh:
			html = fh.read()
		top, right, bottom, left = spec.get("margins", (15, 15, 15, 15))
		doc = {
			"absolute_value": 0,
			"align_labels_right": 0,
			"creation": "2026-11-25 12:00:00.000000",
			"custom_format": 1,
			"default_print_language": "ar",
			"disabled": 0,
			"doc_type": spec["doc_type"],
			"docstatus": 0,
			"doctype": "Print Format",
			"font_size": 0,
			"html": html,
			"idx": 0,
			"line_breaks": 0,
			"margin_bottom": float(bottom),
			"margin_left": float(left),
			"margin_right": float(right),
			"margin_top": float(top),
			"modified_by": "Administrator",
			"module": spec["module"],
			"name": spec["name"],
			"owner": "Administrator",
			"page_number": spec.get("page_number", "Hide"),
			"pdf_generator": spec.get("pdf_generator", "chrome"),
			"print_format_builder": 0,
			"print_format_builder_beta": 0,
			"print_format_type": "Jinja",
			"raw_printing": 0,
			"show_section_headings": 0,
			"standard": "Yes",
		}
		path = os.path.join(folder, scrub(spec["name"]) + ".json")
		modified = None
		if os.path.exists(path):
			with open(path, encoding="utf-8") as fh:
				old = json.load(fh)
			old_modified = old.pop("modified", None)
			if old == doc:
				modified = old_modified
		doc["modified"] = modified or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
		with open(path, "w", encoding="utf-8") as fh:
			json.dump(dict(sorted(doc.items())), fh, indent=1, ensure_ascii=False)
			fh.write("\n")
		print("wrote", os.path.relpath(path, ROOT))


def write_navigation(tr):
	"""Workspace (module page), Sidebar and Dock from dev_tools/navigation_specs.py."""
	sys.path.insert(0, os.path.join(ROOT, "dev_tools"))
	nav = importlib.import_module("navigation_specs")
	ts = "2026-11-25 12:00:00.000000"
	name = nav.WORKSPACE

	def link(label, link_type, link_to, child=0, icon=""):
		return {
			"added": 0,
			"child": child,
			"collapsible": 1,
			"hidden": 0,
			"icon": icon,
			"indent": 0,
			# claims the DocType/Report for this sidebar, so its forms open inside it
			"is_default_module": 0 if link_type == "Workspace" else 1,
			"keep_closed": 0,
			"label": label,
			"link_to": link_to,
			"link_type": link_type,
			"open_in_new_tab": 0,
			"show_arrow": 0,
			"type": "Link",
		}

	items = [link("Home", "Workspace", name, icon="house")]
	ws_links, content = (
		[],
		[
			{
				"id": "locheader01",
				"type": "header",
				"data": {"text": '<span class="h4"><b>منظومة التخطيط والاستثمار</b></span>', "col": 12},
			}
		],
	)
	for i, (label, _ltype, _target, _view) in enumerate(nav.SHORTCUTS):
		content.append(
			{"id": f"locshort{i:03d}", "type": "shortcut", "data": {"shortcut_name": label, "col": 3}}
		)
	content.append({"id": "locspacer01", "type": "spacer", "data": {"col": 12}})
	for i, (section, icon, links) in enumerate(nav.SECTIONS):
		tr.add(section, nav.SECTION_AR.get(section))
		items.append(
			{
				"added": 0,
				"child": 0,
				"collapsible": 1,
				"hidden": 0,
				"icon": icon,
				"indent": 1,
				"is_default_module": 0,
				"keep_closed": 0,
				"label": section,
				"link_type": "DocType",
				"open_in_new_tab": 0,
				"show_arrow": 0,
				"type": "Section Break",
			}
		)
		ws_links.append(
			{
				"hidden": 0,
				"is_query_report": 0,
				"label": section,
				"link_count": len(links),
				"onboard": 0,
				"type": "Card Break",
			}
		)
		for label, ltype, target in links:
			items.append(link(label, ltype, target, child=1))
			ws_links.append(
				{
					"dependencies": "",
					"hidden": 0,
					"is_query_report": 1 if ltype == "Report" else 0,
					"label": label,
					"link_count": 0,
					"link_to": target,
					"link_type": ltype,
					"onboard": 0,
					"type": "Link",
				}
			)
		content.append({"id": f"loccard{i:04d}", "type": "card", "data": {"card_name": section, "col": 4}})

	shortcuts = [
		{"color": "Grey", "doc_view": view, "label": label, "link_to": target, "type": ltype}
		for label, ltype, target, view in nav.SHORTCUTS
	]
	workspace = {
		"app": "loc_planning",
		"charts": [],
		"content": json.dumps(content, ensure_ascii=False),
		"creation": ts,
		"custom_blocks": [],
		"docstatus": 0,
		"doctype": "Workspace",
		"for_user": "",
		"hide_custom": 1,
		"icon": "briefcase",
		"idx": 0,
		"is_hidden": 0,
		"label": name,
		"links": ws_links,
		"modified_by": "Administrator",
		"module": "LOC Planning",
		"name": name,
		"number_cards": [],
		"owner": "Administrator",
		"parent_page": "",
		"public": 1,
		"quick_lists": [],
		"restrict_to_domain": "",
		"roles": [],
		"sequence_id": 50.0,
		"shortcuts": shortcuts,
		"sidebar_items": items,
		"standard": 1,
		"title": name,
		"type": "Workspace",
	}
	sidebar = {
		"app": "loc_planning",
		"creation": ts,
		"docstatus": 0,
		"doctype": "Sidebar",
		"header_icon": "briefcase",
		"idx": 0,
		"items": items,
		"modified_by": "Administrator",
		"module": "LOC Planning",
		"name": name,
		"owner": "Administrator",
		"standard": 1,
		"title": name,
	}
	for doc, rel in (
		(workspace, ("loc_planning", "workspace", scrub(name), scrub(name) + ".json")),
		(sidebar, ("loc_planning", "sidebar", scrub(name), scrub(name) + ".json")),
	):
		path = os.path.join(APP, *rel)
		os.makedirs(os.path.dirname(path), exist_ok=True)
		modified = None
		if os.path.exists(path):
			with open(path, encoding="utf-8") as fh:
				old = json.load(fh)
			old_modified = old.pop("modified", None)
			if old == doc:
				modified = old_modified
		doc["modified"] = modified or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
		with open(path, "w", encoding="utf-8") as fh:
			json.dump(dict(sorted(doc.items())), fh, indent=1, ensure_ascii=False)
			fh.write("\n")
		print("wrote", os.path.relpath(path, ROOT))


def main():
	tr = Translations()
	for mod in SPEC_MODULES:
		specs = importlib.import_module(mod)
		for role, label in importlib.import_module("roles").ROLE_LABELS_AR.items():
			tr.add(role, label)
		for spec in specs.SPECS:
			print("wrote", os.path.relpath(write_doctype(spec, tr), ROOT))
	write_print_formats()
	write_navigation(tr)
	states, actions, workflows = write_workflow_fixtures(tr)
	with open(os.path.join(APP, "config", "fixture_names.json"), "w", encoding="utf-8") as fh:
		json.dump({"states": states, "actions": actions, "workflows": workflows}, fh, indent=1)
		fh.write("\n")
	write_translations(tr)
	print("translations:", len(tr.rows))


if __name__ == "__main__":
	main()
