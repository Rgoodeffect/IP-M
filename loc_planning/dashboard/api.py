"""Dashboard data (لوحة المؤشرات): one permission-aware source for the dashboard page, the
workspace Number Cards and the Dashboard Chart sources.

Every block respects the user's access:
- sales and station figures go through `frappe.get_list`, so a sales office only sees its
  own stations;
- budget figures are returned only to roles that can read budget amounts;
- certificates only to roles that can read Registration Certificate;
- the department report table only lists departments the user can see.
A block the user may not see is returned as None and simply not drawn.
"""

from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from loc_planning.activity_report.deadlines import get_status, report_period_type
from loc_planning.loc_planning.doctype.reporting_period.reporting_period import get_period_for_date
from loc_planning.stations.report_utils import get_product_rows, pct, product_order

# --------------------------------------------------------------------------------------
# Period
# --------------------------------------------------------------------------------------


def default_period():
	"""The latest finished period of the activity-report type (else the current one)."""
	period_type = report_period_type()
	finished = frappe.get_all(
		"Reporting Period",
		filters={"period_type": period_type, "to_date": ("<", today())},
		order_by="to_date desc",
		limit=1,
		pluck="name",
	)
	return finished[0] if finished else get_period_for_date(period_type, today())


def resolve(period=None, region=None):
	period = period or default_period()
	if not period:
		frappe.throw(_("Create the reporting periods first (LOC Planning Settings)"))
	p = frappe.db.get_value(
		"Reporting Period", period, ["name", "title", "period_type", "from_date", "to_date"], as_dict=True
	)
	if not p:
		frappe.throw(_("Period {0} not found").format(period))
	return frappe._dict(
		period=p.name,
		title=p.title,
		period_type=p.period_type,
		from_date=getdate(p.from_date),
		to_date=getdate(p.to_date),
		region=region or None,
	)


def _filters(filters):
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	return resolve(filters.get("reporting_period"), filters.get("region"))


# --------------------------------------------------------------------------------------
# Blocks
# --------------------------------------------------------------------------------------


def can_read(doctype):
	return frappe.has_permission(doctype, "read")


def sales_block(ctx):
	if not can_read("Station Monthly Data"):
		return None
	rows = get_product_rows({"from_date": ctx.from_date, "to_date": ctx.to_date, "region": ctx.region})
	order = product_order()
	products = OrderedDict(
		(p.name, {"product": p.name, "uom": p.uom, "target": 0.0, "actual": 0.0}) for p in order
	)
	for r in rows:
		p = products.setdefault(r.product, {"product": r.product, "uom": r.uom, "target": 0.0, "actual": 0.0})
		p["target"] += flt(r.target_qty)
		p["actual"] += flt(r.actual_qty)
	items = [
		dict(p, achievement=pct(p["actual"], p["target"]), uom_label=_(p["uom"] or ""))
		for p in products.values()
		if p["actual"] or p["target"]
	]
	fuel = [p for p in items if p["uom"] == "Litre"]
	return {
		"products": items,
		"fuel_litres": round(sum(p["actual"] for p in fuel)),
		"fuel_target": round(sum(p["target"] for p in fuel)),
		"fuel_achievement": pct(sum(p["actual"] for p in fuel), sum(p["target"] for p in fuel)),
		"other": [p for p in items if p["uom"] != "Litre"],
	}


def monthly_trend(ctx):
	"""Fuel litres target vs actual for each month of the period's year up to its end."""
	if not can_read("Station Monthly Data"):
		return None
	start = getdate(f"{ctx.to_date.year}-01-01")
	rows = get_product_rows({"from_date": start, "to_date": ctx.to_date, "region": ctx.region})
	months = OrderedDict(
		(m.name, {"label": m.title, "target": 0.0, "actual": 0.0})
		for m in frappe.get_all(
			"Reporting Period",
			filters={"period_type": "Monthly", "from_date": (">=", start), "to_date": ("<=", ctx.to_date)},
			fields=["name", "title"],
			order_by="from_date asc",
		)
	)
	for r in rows:
		if r.uom == "Litre" and r.reporting_period in months:
			months[r.reporting_period]["target"] += flt(r.target_qty)
			months[r.reporting_period]["actual"] += flt(r.actual_qty)
	return list(months.values())


def budget_block(ctx):
	from loc_planning.budget.execution import get_position, summarize

	meta = frappe.get_meta("Approved Budget")
	if not can_read("Approved Budget") or 1 not in meta.get_permlevel_access("read"):
		return None
	rows = get_position(ctx.to_date.year, to_date=ctx.to_date, region=ctx.region)
	total = summarize(rows)
	chapters = OrderedDict()
	chapter_no = {
		c.name: c.chapter_no for c in frappe.get_all("Budget Chapter", fields=["name", "chapter_no"])
	}
	for r in sorted(rows, key=lambda r: chapter_no.get(r.chapter) or 99):
		c = chapters.setdefault(r.chapter, {"chapter": r.chapter, "approved": 0.0, "executed": 0.0})
		c["approved"] += flt(r.revised)
		c["executed"] += flt(r.executed)
	for c in chapters.values():
		c["execution_pct"] = pct(c["executed"], c["approved"]) or 0
	return {
		"year": ctx.to_date.year,
		"approved": round(total.revised),
		"executed": round(total.executed),
		"execution_pct": total.execution_pct,
		"status": total.status,
		"status_label": _(total.status),
		"chapters": list(chapters.values()),
	}


def stations_block(ctx):
	if not can_read("Fuel Station"):
		return None
	filters = {"is_active": 1}
	if ctx.region:
		filters["region"] = ctx.region
	rows = frappe.get_list("Fuel Station", filters=filters, fields=["status"])
	return {"total": len(rows), "operating": sum(1 for r in rows if r.status == "Operating")}


def reports_block(ctx):
	if not can_read("Department Activity Submission"):
		return None
	# the activity-report period that contains the selected period's end
	period = (
		ctx.period
		if ctx.period_type == report_period_type()
		else get_period_for_date(report_period_type(), ctx.to_date)
	)
	if not period:
		return None
	visible = set(frappe.get_list("LOC Department", pluck="name"))
	rows = get_status(period, ctx.region, departments=visible)
	received = [r for r in rows if r.state not in ("Not Submitted", "Draft", "Returned")]
	return {
		"period": period,
		"period_title": frappe.db.get_value("Reporting Period", period, "title"),
		"required": len(rows),
		"received": len(received),
		"approved": sum(1 for r in rows if r.state in ("Approved", "Included in Report")),
		"rows": [
			{
				"department": r.department,
				"state": r.state,
				"state_label": _(r.state),
				"due_date": str(r.due_date) if r.due_date else None,
				"days_late": r.days_late,
				"submission": r.submission,
				"achievement": r.overall_achievement,
			}
			for r in rows
		],
	}


def certificates_block(ctx):
	if not can_read("Registration Certificate"):
		return None
	issued = frappe.get_list(
		"Registration Certificate",
		filters={"docstatus": 1, "issue_date": ("between", (ctx.from_date, ctx.to_date))},
		pluck="name",
	)
	return {"issued": len(issued)}


# --------------------------------------------------------------------------------------
# Page API
# --------------------------------------------------------------------------------------


@frappe.whitelist()
def get_dashboard_data(period: str | None = None, region: str | None = None):
	ctx = resolve(period, region)
	return {
		"period": ctx.period,
		"period_title": ctx.title,
		"region": ctx.region,
		"sales": sales_block(ctx),
		"trend": monthly_trend(ctx),
		"budget": budget_block(ctx),
		"stations": stations_block(ctx),
		"reports": reports_block(ctx),
		"certificates": certificates_block(ctx),
	}


# --------------------------------------------------------------------------------------
# Number Cards (type "Custom")
# --------------------------------------------------------------------------------------


def _card(value, fieldtype="Int", **kw):
	return {"value": value, "fieldtype": fieldtype, **kw}


@frappe.whitelist()
def card_fuel_sales(filters=None):
	block = sales_block(_filters(filters))
	return _card(block["fuel_litres"] if block else 0)


@frappe.whitelist()
def card_budget_execution(filters=None):
	block = budget_block(_filters(filters))
	return _card(block["execution_pct"] if block else 0, "Percent")


@frappe.whitelist()
def card_operating_stations(filters=None):
	block = stations_block(_filters(filters))
	return _card(block["operating"] if block else 0)


@frappe.whitelist()
def card_reports_received(filters=None):
	block = reports_block(_filters(filters))
	return _card(block["received"] if block else 0)


@frappe.whitelist()
def card_certificates_issued(filters=None):
	block = certificates_block(_filters(filters))
	return _card(block["issued"] if block else 0)
