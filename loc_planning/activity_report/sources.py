"""Data sources of the integrated company activity report.

Every source returns `(snapshot, readiness, note)`:
  snapshot   plain JSON-serialisable dict stored on the report section, so an approved
             report never changes when the underlying data changes later
  readiness  "Ready" or "Incomplete"
  note       human readable reason when incomplete

All reads here are company-wide (the report is prepared by Strategic Planning for the
whole company or a region); access to the report itself is controlled by its DocType.
"""

from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, strip_html

from loc_planning.activity_report.deadlines import get_status
from loc_planning.budget.execution import get_position, summarize
from loc_planning.stations.report_utils import get_monthly_docs, get_product_rows, pct, product_order
from loc_planning.utils import periods

READY, INCOMPLETE = "Ready", "Incomplete"


# --------------------------------------------------------------------------------------
# Context
# --------------------------------------------------------------------------------------


def build_context(report):
	period = frappe.get_doc("Reporting Period", report.reporting_period)
	ctx = frappe._dict(
		period=period.name,
		period_title=period.title,
		period_type=period.period_type,
		year=period.year,
		number=period.period_number,
		from_date=getdate(period.from_date),
		to_date=getdate(period.to_date),
		region=report.region if report.scope == "Region" else None,
		compare_previous=report.compare_previous,
		compare_last_year=report.compare_last_year,
	)
	y, n = periods.previous_period(period.period_type, period.year, period.period_number)
	ctx.prev = _period_info(period.period_type, y, n)
	y, n = periods.same_period_last_year(period.period_type, period.year, period.period_number)
	ctx.last_year = _period_info(period.period_type, y, n)
	return ctx


def _period_info(period_type, year, number):
	start, end = periods.period_dates(period_type, year, number)
	return frappe._dict(
		name=periods.period_name(period_type, year, number),
		title=periods.period_title(period_type, year, number),
		from_date=start,
		to_date=end,
		year=year,
	)


def change_pct(current, previous):
	return flt((flt(current) - flt(previous)) / flt(previous) * 100, 1) if flt(previous) else None


def compute(source, ctx, section):
	fn = SOURCES.get(source)
	if not fn:
		frappe.throw(_("Unknown data source {0}").format(source))
	return fn(ctx, section)


# --------------------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------------------


def manual(ctx, section):
	ready = bool(strip_html(section.editorial_text or "").strip())
	return {}, READY if ready else INCOMPLETE, None if ready else _("Write the text of this section")


def sales(ctx, section):
	def totals(start, end):
		rows = get_product_rows(
			{"from_date": start, "to_date": end, "region": ctx.region}, ignore_permissions=True
		)
		out = OrderedDict()
		by_region = OrderedDict()
		by_office = OrderedDict()
		for r in rows:
			t = out.setdefault(r.product, {"target": 0.0, "actual": 0.0, "uom": r.uom})
			t["target"] += flt(r.target_qty)
			t["actual"] += flt(r.actual_qty)
			by_region.setdefault(r.region, {}).setdefault(r.product, 0.0)
			by_region[r.region][r.product] += flt(r.actual_qty)
			by_office.setdefault(r.sales_office, {}).setdefault(r.product, 0.0)
			by_office[r.sales_office][r.product] += flt(r.actual_qty)
		return out, by_region, by_office

	current, by_region, by_office = totals(ctx.from_date, ctx.to_date)
	prev = totals(ctx.prev.from_date, ctx.prev.to_date)[0] if ctx.compare_previous else {}
	last = totals(ctx.last_year.from_date, ctx.last_year.to_date)[0] if ctx.compare_last_year else {}
	order = [p for p in product_order() if p.name in current]
	products = []
	for p in order:
		c = current[p.name]
		row = {
			"product": p.name,
			"uom": _(p.uom or ""),
			"target": round(c["target"]),
			"actual": round(c["actual"]),
			"achievement": pct(c["actual"], c["target"]),
		}
		if ctx.compare_previous:
			row["previous"] = round(prev.get(p.name, {}).get("actual", 0))
			row["change_previous"] = change_pct(c["actual"], row["previous"])
		if ctx.compare_last_year:
			row["last_year"] = round(last.get(p.name, {}).get("actual", 0))
			row["change_last_year"] = change_pct(c["actual"], row["last_year"])
		products.append(row)
	names = [p.name for p in order]
	snapshot = {
		"products": products,
		"by_region": [
			{"region": k, "values": [round(v.get(n, 0)) for n in names]} for k, v in by_region.items()
		],
		"by_office": [
			{"office": k, "values": [round(v.get(n, 0)) for n in names]} for k, v in sorted(by_office.items())
		],
		"product_names": names,
		"product_units": [_(p.uom or "") for p in order],
	}
	missing = missing_station_months(ctx)
	snapshot["missing_station_months"] = missing
	if not products:
		return snapshot, INCOMPLETE, _("No approved station data for this period")
	if missing:
		return snapshot, INCOMPLETE, _("{0} station-months without approved data").format(missing)
	return snapshot, READY, None


def missing_station_months(ctx):
	months = frappe.get_all(
		"Reporting Period",
		filters={
			"period_type": "Monthly",
			"from_date": (">=", ctx.from_date),
			"to_date": ("<=", ctx.to_date),
		},
		pluck="name",
	)
	filters = {"is_active": 1, "status": "Operating"}
	if ctx.region:
		filters["region"] = ctx.region
	stations = frappe.get_all("Fuel Station", filters=filters, pluck="name")
	if not months or not stations:
		return 0
	approved = frappe.db.count(
		"Station Monthly Data",
		{"reporting_period": ("in", months), "station": ("in", stations), "docstatus": 1},
	)
	return max(len(months) * len(stations) - approved, 0)


def stations(ctx, section):
	filters = {"is_active": 1}
	if ctx.region:
		filters["region"] = ctx.region
	rows = frappe.get_all(
		"Fuel Station",
		filters=filters,
		fields=["name", "station_name", "status", "operation_type", "sales_office", "stop_reason"],
	)
	by_status = OrderedDict()
	by_type = OrderedDict()
	for r in rows:
		by_status[r.status] = by_status.get(r.status, 0) + 1
		by_type[r.operation_type] = by_type.get(r.operation_type, 0) + 1
	docs = get_monthly_docs(
		{"from_date": ctx.from_date, "to_date": ctx.to_date, "region": ctx.region}, ignore_permissions=True
	)
	revenue = OrderedDict()
	if docs:
		for r in frappe.get_all(
			"Station Support Revenue",
			filters={"parent": ("in", [d.name for d in docs]), "parenttype": "Station Monthly Data"},
			fields=["activity_type", "revenue"],
		):
			revenue[r.activity_type] = revenue.get(r.activity_type, 0) + flt(r.revenue)
	activities = OrderedDict()
	for a in frappe.get_all(
		"Station Support Activity",
		filters={
			"parenttype": "Fuel Station",
			"is_active": 1,
			"parent": ("in", [r.name for r in rows] or [""]),
		},
		fields=["activity_type"],
	):
		activities[a.activity_type] = activities.get(a.activity_type, 0) + 1
	snapshot = {
		"total": len(rows),
		"operating": by_status.get("Operating", 0),
		"by_status": [{"status": _(k), "count": v} for k, v in by_status.items()],
		"by_type": [{"type": k, "count": v} for k, v in by_type.items()],
		"activities": [
			{"activity": k, "stations": v, "revenue": round(revenue.get(k, 0))} for k, v in activities.items()
		],
		"total_revenue": round(sum(revenue.values())),
		"stopped": [
			{
				"station": r.station_name,
				"office": r.sales_office,
				"status": _(r.status),
				"reason": r.stop_reason,
			}
			for r in rows
			if r.status != "Operating"
		],
		"stopped_days": sum(int(d.stopped_days or 0) for d in docs),
	}
	if not rows:
		return snapshot, INCOMPLETE, _("No stations registered")
	return snapshot, READY, None


def budget(ctx, section):
	year = ctx.to_date.year
	rows = get_position(year, to_date=ctx.to_date, region=ctx.region)
	chapters = OrderedDict()
	chapter_no = {
		c.name: c.chapter_no for c in frappe.get_all("Budget Chapter", fields=["name", "chapter_no"])
	}
	for r in sorted(rows, key=lambda r: chapter_no.get(r.chapter) or 99):
		chapters.setdefault(r.chapter, []).append(r)
	total = summarize(rows)
	snapshot = {
		"year": year,
		"chapters": [
			{
				"chapter": c,
				**_money(summarize(items)),
				"items": [
					{"item": i.budget_item, "department": i.owner_department, **_money(i)} for i in items
				],
			}
			for c, items in chapters.items()
		],
		"total": _money(total),
	}
	if ctx.compare_last_year:
		ly = summarize(get_position(year - 1, to_date=add_days(ctx.to_date, -365), region=ctx.region))
		snapshot["last_year_execution_pct"] = ly.execution_pct
	budget_filters = {"fiscal_year": year, "docstatus": 1}
	if ctx.region:
		budget_filters["region"] = ctx.region
	if not frappe.db.exists("Approved Budget", budget_filters):
		return snapshot, INCOMPLETE, _("No approved budget for {0}").format(year)
	return snapshot, READY, None


def _money(r):
	return {
		"approved": round(flt(r.revised)),
		"commitments": round(flt(r.commitments)),
		"executed": round(flt(r.executed)),
		"remaining": round(flt(r.remaining)),
		"execution_pct": flt(r.execution_pct, 1),
		"status": _(r.status),
		"status_key": r.status,
	}


def department_activities(ctx, section):
	status = get_status(ctx.period, ctx.region)
	approved = [s for s in status if s.state in ("Approved", "Included in Report")]
	departments = []
	for s in status:
		entry = {
			"department": s.department,
			"state": _(s.state),
			"state_key": s.state,
			"achievement": s.overall_achievement,
			"days_late": s.days_late,
		}
		if s in approved:
			doc = frappe.get_doc("Department Activity Submission", s.submission)
			entry["activities"] = [
				{
					"activity": strip_html(a.activity or ""),
					"domain": a.domain,
					"target": a.target,
					"executed": a.executed,
					"achievement": a.achievement_pct,
				}
				for a in doc.activities
			]
		departments.append(entry)
	snapshot = {
		"required": len(status),
		"approved": len(approved),
		"average_achievement": flt(sum(flt(s.overall_achievement) for s in approved) / len(approved), 1)
		if approved
		else 0,
		"departments": departments,
	}
	missing = [s.department for s in status if s not in approved]
	if missing:
		return snapshot, INCOMPLETE, _("Not approved yet: {0}").format("، ".join(missing))
	return snapshot, READY, None


def department_indicators(ctx, section):
	dept = section.source_department
	name = frappe.db.get_value(
		"Department Activity Submission",
		{"department": dept, "reporting_period": ctx.period, "docstatus": 1},
	)
	snapshot = {"department": dept, "indicators": [], "activities": []}
	if not name:
		return snapshot, INCOMPLETE, _("The report of {0} for this period is not approved yet").format(dept)
	doc = frappe.get_doc("Department Activity Submission", name)
	snapshot["indicators"] = [
		{"indicator": i.indicator, "value": i.value, "unit": i.unit} for i in doc.indicators
	]
	snapshot["activities"] = [
		{
			"activity": strip_html(a.activity or ""),
			"target": a.target,
			"executed": a.executed,
			"achievement": a.achievement_pct,
		}
		for a in doc.activities
	]
	snapshot["achievement"] = doc.overall_achievement
	return snapshot, READY, None


def investment_registry(ctx, section):
	def issued(start, end):
		return frappe.db.count(
			"Registration Certificate",
			{"docstatus": 1, "issue_date": ("between", (start, end)), "is_migrated": 0},
		)

	registered = frappe.db.count(
		"Registered Company", {"registration_date": ("between", (ctx.from_date, ctx.to_date))}
	)
	by_class = OrderedDict()
	for r in frappe.get_all(
		"Registered Company",
		filters={"registration_date": ("between", (ctx.from_date, ctx.to_date))},
		fields=["classification"],
	):
		by_class[r.classification] = by_class.get(r.classification, 0) + 1
	snapshot = {
		"registered": registered,
		"issued": issued(ctx.from_date, ctx.to_date),
		"renewals": frappe.db.count(
			"Registration Certificate",
			{
				"docstatus": 1,
				"request_type": "Renewal",
				"issue_date": ("between", (ctx.from_date, ctx.to_date)),
			},
		),
		"total_companies": frappe.db.count("Registered Company", {"status": "Active"}),
		"valid_certificates": frappe.db.count(
			"Registration Certificate",
			{"docstatus": 1, "status": "Issued", "expiry_date": (">=", ctx.to_date)},
		),
		"by_classification": [{"classification": k, "count": v} for k, v in by_class.items()],
	}
	if ctx.compare_previous:
		snapshot["issued_previous"] = issued(ctx.prev.from_date, ctx.prev.to_date)
	if ctx.compare_last_year:
		snapshot["issued_last_year"] = issued(ctx.last_year.from_date, ctx.last_year.to_date)
	return snapshot, READY, None


def difficulties(ctx, section):
	rows = []
	for s in get_status(ctx.period, ctx.region):
		if s.state not in ("Approved", "Included in Report"):
			continue
		doc = frappe.get_doc("Department Activity Submission", s.submission)
		text = strip_html(doc.difficulties or "").strip()
		plan = strip_html(doc.next_period_plan or "").strip()
		if text or plan:
			rows.append({"department": s.department, "difficulties": text, "plan": plan})
	snapshot = {"departments": rows}
	if not (section.editorial_text or "").strip() and rows:
		# pre-fill the editable text from the departments; the editor can rewrite it
		section.editorial_text = "".join(
			f"<p><b>{frappe.utils.escape_html(r['department'])}:</b> {frappe.utils.escape_html(r['difficulties'])}</p>"
			for r in rows
			if r["difficulties"]
		)
	ready = bool(strip_html(section.editorial_text or "").strip())
	return snapshot, READY if ready else INCOMPLETE, None if ready else _("No difficulties text yet")


SOURCES = {
	"Editorial Text": manual,
	"Sales Data": sales,
	"Stations Data": stations,
	"Budget Position": budget,
	"Department Activities": department_activities,
	"Department Indicators": department_indicators,
	"Registry Data": investment_registry,
	"Difficulties": difficulties,
}
