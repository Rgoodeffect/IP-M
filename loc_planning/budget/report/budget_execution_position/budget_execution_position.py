# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

"""الموقف التنفيذي للموازنة: chapter → item tree with approved, commitments, executed,
remaining, execution % and status. Optional side-by-side columns per region."""

from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import cint, getdate

from loc_planning.budget.execution import check_access, finish, get_position, summarize

MONEY = {"fieldtype": "Float", "precision": "0", "width": 150}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	check_access()
	year = cint(filters.get("fiscal_year")) or getdate().year
	rows = get_position(
		year,
		to_date=filters.get("to_date"),
		region=filters.get("region"),
		department=filters.get("department"),
		chapter=filters.get("chapter"),
	)
	split = cint(filters.get("split_regions")) and not filters.get("region")
	regions = sorted({r.region for r in rows}) if split else []
	columns = get_columns(regions)
	data = build_tree(rows, regions)
	return columns, data, None, get_chart(rows), get_summary(rows)


def get_columns(regions):
	unit = " (" + _("LYD") + ")"
	columns = [
		{"label": _("Chapter / Item"), "fieldname": "label", "fieldtype": "Data", "width": 260},
		{
			"label": _("Owner Department"),
			"fieldname": "owner_department",
			"fieldtype": "Link",
			"options": "LOC Department",
			"width": 190,
		},
		{"label": _("Source"), "fieldname": "source_label", "fieldtype": "Data", "width": 110},
	]
	for reg in regions:
		columns += [
			{"label": _("Approved Amount") + f" - {reg}", "fieldname": f"revised__{reg}", **MONEY},
			{"label": _("Executed") + f" - {reg}", "fieldname": f"executed__{reg}", **MONEY},
			{
				"label": _("Execution %") + f" - {reg}",
				"fieldname": f"execution_pct__{reg}",
				"fieldtype": "Percent",
				"width": 100,
			},
		]
	columns += [
		{
			"label": (_("Approved Amount") if not regions else _("Total Approved")) + unit,
			"fieldname": "revised",
			**MONEY,
		},
		{"label": _("Revisions") + unit, "fieldname": "revisions", **MONEY, "width": 115},
		{"label": _("Commitments") + unit, "fieldname": "commitments", **MONEY},
		{
			"label": (_("Executed") if not regions else _("Total Executed")) + unit,
			"fieldname": "executed",
			**MONEY,
		},
		{"label": _("Remaining") + unit, "fieldname": "remaining", **MONEY},
		{"label": _("Execution %"), "fieldname": "execution_pct", "fieldtype": "Percent", "width": 150},
		{"label": _("Status"), "fieldname": "status_label", "fieldtype": "Data", "width": 120},
		{"label": "", "fieldname": "status", "fieldtype": "Data", "hidden": 1},
	]
	return columns


def build_tree(rows, regions):
	"""Chapter rows (indent 0) followed by their item rows (indent 1); items are merged
	across regions with per-region columns when `regions` is given."""
	chapter_no = {
		c.name: c.chapter_no for c in frappe.get_all("Budget Chapter", fields=["name", "chapter_no"])
	}
	items = OrderedDict()
	for r in sorted(rows, key=lambda r: (chapter_no.get(r.chapter) or 99, r.item_code or "", r.budget_item)):
		items.setdefault(r.budget_item, []).append(r)

	chapters = OrderedDict()
	for item_name, item_rows in items.items():
		merged = summarize(item_rows)
		first = item_rows[0]
		line = frappe._dict(
			merged,
			name=item_name,
			label=item_name,
			chapter=first.chapter,
			owner_department=first.owner_department,
			source_label=_(first.execution_source),
			indent=1,
			parent_label=first.chapter,
		)
		for reg in regions:
			reg_row = next((x for x in item_rows if x.region == reg), None)
			if reg_row:
				line[f"revised__{reg}"] = reg_row.revised
				line[f"executed__{reg}"] = reg_row.executed
				line[f"execution_pct__{reg}"] = reg_row.execution_pct
		line.status_label = _(line.status)
		chapters.setdefault(first.chapter, []).append(line)

	data = []
	for chapter, lines in chapters.items():
		total = summarize(lines)
		head = frappe._dict(total, name=chapter, label=chapter or _("Not Classified"), indent=0, is_group=1)
		for reg in regions:
			reg_lines = [
				frappe._dict(approved=l.get(f"revised__{reg}") or 0, executed=l.get(f"executed__{reg}") or 0)
				for l in lines
			]
			reg_total = finish(summarize(reg_lines))
			head[f"revised__{reg}"] = reg_total.revised
			head[f"executed__{reg}"] = reg_total.executed
			head[f"execution_pct__{reg}"] = reg_total.execution_pct
		head.status_label = _(head.status)
		data.append(head)
		data.extend(lines)
	if data:
		grand = summarize([d for d in data if d.indent == 0])
		data.append(
			frappe._dict(
				grand, label=_("Grand Total"), indent=0, is_total=1, status_label=_(grand.status), bold=1
			)
		)
	return data


def get_chart(rows):
	by_chapter = OrderedDict()
	for r in rows:
		c = by_chapter.setdefault(r.chapter or _("Not Classified"), [0, 0])
		c[0] += r.revised
		c[1] += r.executed
	if not by_chapter:
		return None
	labels = list(by_chapter)
	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Approved Amount"), "values": [round(by_chapter[c][0]) for c in labels]},
				{"name": _("Executed"), "values": [round(by_chapter[c][1]) for c in labels]},
			],
		},
		"type": "bar",
	}


def get_summary(rows):
	t = summarize(rows)
	money = {"datatype": "Float", "precision": 0}
	unit = " (" + _("LYD") + ")"
	return [
		{"label": _("Approved Amount") + unit, "value": t.revised, "indicator": "Blue", **money},
		{"label": _("Commitments") + unit, "value": t.commitments, "indicator": "Orange", **money},
		{"label": _("Executed") + unit, "value": t.executed, "indicator": "Green", **money},
		{"label": _("Remaining") + unit, "value": t.remaining, "indicator": "Grey", **money},
		{"label": _("Execution %"), "value": t.execution_pct, "datatype": "Percent", "indicator": "Purple"},
	]
