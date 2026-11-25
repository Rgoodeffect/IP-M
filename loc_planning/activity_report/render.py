"""Turns the stored section snapshots of a Company Activity Report into neutral "blocks"
that both the PDF print format (Jinja) and the Word export render the same way.

Block types:
  {"type": "kpis", "items": [(label, value), ...]}
  {"type": "table", "headers": [...], "rows": [[...]], "numeric": [bool...], "total": bool}
  {"type": "chart", "svg": "<svg ...>", "title": str}
  {"type": "html", "html": str}        editorial text (already sanitised by the editor)
  {"type": "note", "text": str}
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from loc_planning.utils.arabic import strip_diacritics
from loc_planning.utils.print_utils import (
	arabic_output,
	format_arabic_date,
	format_number,
	get_print_settings,
)
from loc_planning.utils.svg_charts import bar_chart

N = format_number


def pct(v, digits=1):
	return "" if v is None else f"{flt(v, digits):,.{digits}f}%"


def change(v):
	if v is None:
		return "-"
	sign = "+" if v > 0 else ""
	return f"{sign}{flt(v, 1):,.1f}%"


def get_report_context(doc):
	"""Jinja helper: everything the print format needs (always in Arabic)."""
	with arabic_output():
		return _report_context(doc)


def _report_context(doc):
	if isinstance(doc, str):
		doc = frappe.get_doc("Company Activity Report", doc)
	ps = get_print_settings()
	sections = []
	for i, s in enumerate(doc.get_sections(), start=1):
		blocks = [escape_block(b) for b in build_blocks(s, ps)]
		sections.append(frappe._dict(number=i, title=esc(strip_diacritics(s.title)), blocks=blocks))
	period_title = frappe.db.get_value("Reporting Period", doc.reporting_period, "title")
	scope = _("Company-wide") if doc.scope != "Region" else _("Region: {0}").format(doc.region)
	return frappe._dict(
		ps=ps,
		title=esc(strip_diacritics(doc.report_title)),
		period_title=esc(period_title),
		scope=esc(scope),
		date=format_arabic_date(doc.approved_on or today()),
		is_draft=doc.docstatus != 1,
		sections=sections,
	)


def esc(value):
	return frappe.utils.escape_html(strip_diacritics("" if value is None else str(value)))


def escape_block(block):
	"""Print formats are rendered without auto-escaping: escape every text value. Only the
	generated SVG and the editor's (already sanitised) HTML are inserted as markup."""
	b = dict(block)
	if b.get("title"):
		b["title"] = esc(b["title"])
	if b["type"] == "table":
		b["compact"] = len(b["headers"]) > 6
		b["headers"] = [esc(h) for h in b["headers"]]
		b["rows"] = [[esc(c) for c in row] for row in b["rows"]]
	elif b["type"] == "kpis":
		b["items"] = [(esc(label), esc(value)) for label, value in b["items"]]
	elif b["type"] == "note":
		b["text"] = esc(b["text"])
	return b


def build_blocks(s, ps):
	data = s.data or frappe._dict()
	builder = BUILDERS.get(s.source)
	blocks = []
	if s.text and s.source not in ("Difficulties",):
		blocks.append({"type": "html", "html": strip_diacritics(s.text)})
	if builder and data:
		blocks += builder(data, ps)
	if s.source == "Difficulties" and s.text:
		blocks.append({"type": "html", "html": strip_diacritics(s.text)})
	if not blocks:
		blocks.append({"type": "note", "text": _("No data")})
	return blocks


def comparison_headers(data):
	headers = []
	if "previous" in data:
		headers.append(data.previous)
	if "last_year" in data:
		headers.append(data.last_year)
	return headers


# --------------------------------------------------------------------------------------
# Builders per data source
# --------------------------------------------------------------------------------------


def sales_blocks(data, ps):
	products = data.get("products") or []
	if not products:
		return [{"type": "note", "text": _("No approved station data for this period")}]
	has_prev = "previous" in products[0]
	has_ly = "last_year" in products[0]
	headers = [_("Product"), _("Unit of Measure"), _("Target"), _("Actual Sales"), _("Achievement %")]
	if has_prev:
		headers += [data.previous, _("Change")]
	if has_ly:
		headers += [data.last_year, _("Change")]
	rows = []
	for p in products:
		row = [p["product"], p["uom"], N(p["target"]), N(p["actual"]), pct(p["achievement"])]
		if has_prev:
			row += [N(p["previous"]), change(p["change_previous"])]
		if has_ly:
			row += [N(p["last_year"]), change(p["change_last_year"])]
		rows.append(row)
	blocks = [
		{
			"type": "table",
			"headers": headers,
			"rows": rows,
			"numeric": [False, False] + [True] * (len(headers) - 2),
		}
	]

	names, units = data.get("product_names") or [], data.get("product_units") or []
	if data.get("by_region"):
		blocks.append(
			{
				"type": "table",
				"title": _("Sales by Region"),
				"headers": [_("Region")] + [f"{n} ({u})" for n, u in zip(names, units, strict=False)],
				"rows": [[r["region"]] + [N(v) for v in r["values"]] for r in data["by_region"]],
				"numeric": [False] + [True] * len(names),
			}
		)
	if data.get("by_office"):
		blocks.append(
			{
				"type": "table",
				"title": _("Sales by Sales Office"),
				"headers": [_("Sales Office")] + [f"{n} ({u})" for n, u in zip(names, units, strict=False)],
				"rows": [[r["office"]] + [N(v) for v in r["values"]] for r in data["by_office"]],
				"numeric": [False] + [True] * len(names),
			}
		)
	# chart: only products sharing the first product's unit
	unit = products[0]["uom"]
	same = [p for p in products if p["uom"] == unit]
	series = [(_("Target"), [p["target"] for p in same]), (_("Actual Sales"), [p["actual"] for p in same])]
	if has_ly:
		series.append((data.last_year, [p["last_year"] for p in same]))
	blocks.append(
		{
			"type": "chart",
			"title": _("Target and actual sales") + f" ({unit})",
			"svg": bar_chart([p["product"] for p in same], series, font=ps.font_stack),
		}
	)
	return blocks


def stations_blocks(data, ps):
	blocks = [
		{
			"type": "kpis",
			"items": [
				(_("Stations"), N(data.get("total"))),
				(_("Operating"), N(data.get("operating"))),
				(_("Support Activities Revenue") + " (" + _("LYD") + ")", N(data.get("total_revenue"))),
				(_("Stopped Days"), N(data.get("stopped_days"))),
			],
		},
		{
			"type": "table",
			"title": _("Stations by Status"),
			"headers": [_("Status"), _("Stations")],
			"rows": [[r["status"], N(r["count"])] for r in data.get("by_status") or []],
			"numeric": [False, True],
		},
		{
			"type": "table",
			"title": _("Stations by Operation Type"),
			"headers": [_("Operation Type"), _("Stations")],
			"rows": [[r["type"], N(r["count"])] for r in data.get("by_type") or []],
			"numeric": [False, True],
		},
	]
	if data.get("activities"):
		blocks.append(
			{
				"type": "table",
				"title": _("Support Activities"),
				"headers": [_("Activity Type"), _("Stations"), _("Revenue") + " (" + _("LYD") + ")"],
				"rows": [[a["activity"], N(a["stations"]), N(a["revenue"])] for a in data["activities"]],
				"numeric": [False, True, True],
			}
		)
	if data.get("stopped"):
		blocks.append(
			{
				"type": "table",
				"title": _("Stopped Stations"),
				"headers": [_("Station"), _("Sales Office"), _("Status"), _("Stop Reason")],
				"rows": [
					[s["station"], s["office"], s["status"], s.get("reason") or ""] for s in data["stopped"]
				],
				"numeric": [False] * 4,
			}
		)
	return blocks


def budget_blocks(data, ps):
	total = data.get("total") or {}
	unit = " (" + _("LYD") + ")"
	items = [
		(_("Approved Amount") + unit, N(total.get("approved"))),
		(_("Commitments") + unit, N(total.get("commitments"))),
		(_("Executed") + unit, N(total.get("executed"))),
		(_("Execution %"), pct(total.get("execution_pct"))),
	]
	if "last_year_execution_pct" in data:
		items.append((_("Execution %") + " - " + data.last_year, pct(data.get("last_year_execution_pct"))))
	headers = [
		_("Chapter / Item"),
		_("Owner Department"),
		_("Approved Amount") + unit,
		_("Commitments") + unit,
		_("Executed") + unit,
		_("Remaining") + unit,
		_("Execution %"),
		_("Status"),
	]
	rows, bold = [], []
	for c in data.get("chapters") or []:
		rows.append(
			[
				c["chapter"],
				"",
				N(c["approved"]),
				N(c["commitments"]),
				N(c["executed"]),
				N(c["remaining"]),
				pct(c["execution_pct"]),
				c["status"],
			]
		)
		bold.append(len(rows) - 1)
		for i in c["items"]:
			rows.append(
				[
					"  " + i["item"],
					i["department"] or "",
					N(i["approved"]),
					N(i["commitments"]),
					N(i["executed"]),
					N(i["remaining"]),
					pct(i["execution_pct"]),
					i["status"],
				]
			)
	rows.append(
		[
			_("Grand Total"),
			"",
			N(total.get("approved")),
			N(total.get("commitments")),
			N(total.get("executed")),
			N(total.get("remaining")),
			pct(total.get("execution_pct")),
			total.get("status", ""),
		]
	)
	bold.append(len(rows) - 1)
	chapters = data.get("chapters") or []
	return [
		{"type": "kpis", "items": items},
		{
			"type": "table",
			"headers": headers,
			"rows": rows,
			"numeric": [False, False] + [True] * 5 + [False],
			"bold_rows": bold,
		},
		{
			"type": "chart",
			"title": _("Approved and executed by chapter") + unit,
			"svg": bar_chart(
				[c["chapter"] for c in chapters],
				[
					(_("Approved Amount"), [c["approved"] for c in chapters]),
					(_("Executed"), [c["executed"] for c in chapters]),
				],
				font=ps.font_stack,
			),
		},
	]


def activities_blocks(data, ps):
	blocks = [
		{
			"type": "kpis",
			"items": [
				(_("Required Reports"), N(data.get("required"))),
				(_("Approved"), N(data.get("approved"))),
				(_("Average Achievement"), pct(data.get("average_achievement"))),
			],
		},
		{
			"type": "table",
			"title": _("Department Reports"),
			"headers": [_("Department"), _("Status"), _("Overall Achievement"), _("Days Late")],
			"rows": [
				[d["department"], d["state"], pct(d.get("achievement")), N(d.get("days_late") or 0)]
				for d in data.get("departments") or []
			],
			"numeric": [False, False, True, True],
		},
	]
	for d in data.get("departments") or []:
		if d.get("activities"):
			blocks.append(
				{
					"type": "table",
					"title": d["department"],
					"headers": [_("Activity"), _("Domain"), _("Target"), _("Executed"), _("Achievement %")],
					"rows": [
						[
							a["activity"],
							a.get("domain") or "",
							N(a.get("target")),
							N(a.get("executed")),
							pct(a.get("achievement")),
						]
						for a in d["activities"]
					],
					"numeric": [False, False, True, True, True],
				}
			)
	return blocks


def indicators_blocks(data, ps):
	blocks = []
	if data.get("indicators"):
		blocks.append(
			{
				"type": "table",
				"headers": [_("Indicator"), _("Value"), _("Unit")],
				"rows": [
					[
						i["indicator"],
						N(i.get("value"), 2 if flt(i.get("value")) % 1 else 0),
						i.get("unit") or "",
					]
					for i in data["indicators"]
				],
				"numeric": [False, True, False],
			}
		)
	if data.get("activities"):
		blocks.append(
			{
				"type": "table",
				"title": _("Activities Carried Out"),
				"headers": [_("Activity"), _("Target"), _("Executed"), _("Achievement %")],
				"rows": [
					[a["activity"], N(a.get("target")), N(a.get("executed")), pct(a.get("achievement"))]
					for a in data["activities"]
				],
				"numeric": [False, True, True, True],
			}
		)
	return blocks


def registry_blocks(data, ps):
	items = [
		(_("Companies registered in the period"), N(data.get("registered"))),
		(_("Certificates issued in the period"), N(data.get("issued"))),
		(_("Renewals"), N(data.get("renewals"))),
		(_("Active companies"), N(data.get("total_companies"))),
		(_("Valid Certificates"), N(data.get("valid_certificates"))),
	]
	blocks = [{"type": "kpis", "items": items}]
	comp = []
	if "issued_previous" in data:
		comp.append([data.previous, N(data.get("issued_previous"))])
	if "issued_last_year" in data:
		comp.append([data.last_year, N(data.get("issued_last_year"))])
	if comp:
		blocks.append(
			{
				"type": "table",
				"title": _("Certificates issued - comparison"),
				"headers": [_("Period"), _("Certificates")],
				"rows": [[data.period, N(data.get("issued"))], *comp],
				"numeric": [False, True],
			}
		)
	if data.get("by_classification"):
		blocks.append(
			{
				"type": "table",
				"title": _("New companies by classification"),
				"headers": [_("Classification"), _("Companies")],
				"rows": [[r["classification"], N(r["count"])] for r in data["by_classification"]],
				"numeric": [False, True],
			}
		)
	return blocks


def difficulties_blocks(data, ps):
	plans = [d for d in data.get("departments") or [] if d.get("plan")]
	if not plans:
		return []
	return [
		{
			"type": "table",
			"title": _("Plans for the next period"),
			"headers": [_("Department"), _("Plan for the Next Period")],
			"rows": [[d["department"], d["plan"]] for d in plans],
			"numeric": [False, False],
		}
	]


BUILDERS = {
	"Sales Data": sales_blocks,
	"Stations Data": stations_blocks,
	"Budget Position": budget_blocks,
	"Department Activities": activities_blocks,
	"Department Indicators": indicators_blocks,
	"Registry Data": registry_blocks,
	"Difficulties": difficulties_blocks,
}


def date_label(value):
	return format_arabic_date(getdate(value)) if value else ""
