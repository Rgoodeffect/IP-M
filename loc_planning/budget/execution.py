"""Budget execution position: approved, revisions, commitments, executed, remaining.

One place computes the figures so that the report, the dashboard and the integrated
activity report always agree.

Definitions (per item and region, for a year, up to a date):
  approved     = amount in the submitted Approved Budget of that year and region
  revised      = approved + revisions submitted up to the date (transfers in/out, increases,
                 decreases)
  commitments  = submitted "Commitment" execution entries up to the date
  executed     = General Ledger (debit - credit of the item's accounts / cost centers for the
                 region) when the item's source is "General Ledger", otherwise submitted
                 "Actual Expense" execution entries
  remaining    = revised - commitments - executed
  execution %  = executed / revised * 100
  status       = slow (< slow threshold) / within plan / limit exceeded (> over threshold),
                 thresholds from LOC Planning Settings
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, getdate

from loc_planning.constants import SETTINGS_DOCTYPE

STATUS_SLOW = "Slow Execution"
STATUS_OK = "Within Plan"
STATUS_OVER = "Limit Exceeded"
STATUS_NONE = "Not Budgeted"


def thresholds():
	s = frappe.get_cached_doc(SETTINGS_DOCTYPE)
	return flt(s.slow_execution_threshold) or 40, flt(s.over_execution_threshold) or 80


def execution_status(pct, revised):
	if not flt(revised):
		return STATUS_NONE
	slow, over = thresholds()
	if flt(pct) > over:
		return STATUS_OVER
	if flt(pct) < slow:
		return STATUS_SLOW
	return STATUS_OK


def pct(part, whole):
	return flt(flt(part) / flt(whole) * 100, 2) if flt(whole) else 0


def year_bounds(year, to_date=None):
	start = getdate(f"{int(year)}-01-01")
	end = getdate(f"{int(year)}-12-31")
	if to_date:
		end = min(end, getdate(to_date))
	return start, end


def get_position(year, to_date=None, region=None, department=None, chapter=None, item=None):
	"""Rows keyed by (budget_item, region) with all figures. Reads are not permission-filtered
	here; callers decide who may see the result (see `check_access`)."""
	start, end = year_bounds(year, to_date)
	items = {
		i.name: i
		for i in frappe.get_all(
			"Budget Item",
			fields=[
				"name",
				"item_name",
				"item_code",
				"chapter",
				"owner_department",
				"execution_source",
				"company",
			],
		)
	}
	rows = {}

	def row(item_name, reg):
		key = (item_name, reg)
		if key not in rows:
			it = items.get(item_name) or frappe._dict(name=item_name)
			rows[key] = frappe._dict(
				budget_item=item_name,
				item_code=it.get("item_code"),
				chapter=it.get("chapter"),
				owner_department=it.get("owner_department"),
				execution_source=it.get("execution_source") or "Manual Entries",
				region=reg,
				approved=0.0,
				revisions=0.0,
				commitments=0.0,
				executed=0.0,
			)
		return rows[key]

	# approved ---------------------------------------------------------------
	budget_filters = {"fiscal_year": int(year), "docstatus": 1}
	if region:
		budget_filters["region"] = region
	budgets = {
		b.name: b.region
		for b in frappe.get_all("Approved Budget", filters=budget_filters, fields=["name", "region"])
	}
	if budgets:
		for line in frappe.get_all(
			"Approved Budget Line",
			filters={"parent": ("in", list(budgets)), "parenttype": "Approved Budget"},
			fields=["parent", "budget_item", "approved_amount"],
		):
			row(line.budget_item, budgets[line.parent]).approved += flt(line.approved_amount)

		# revisions ------------------------------------------------------------
		revisions = frappe.get_all(
			"Budget Revision",
			filters={"approved_budget": ("in", list(budgets)), "docstatus": 1, "revision_date": ("<=", end)},
			fields=["name", "approved_budget"],
		)
		rev_region = {r.name: budgets[r.approved_budget] for r in revisions}
		if rev_region:
			for line in frappe.get_all(
				"Budget Revision Line",
				filters={"parent": ("in", list(rev_region)), "parenttype": "Budget Revision"},
				fields=["parent", "from_item", "to_item", "amount"],
			):
				reg = rev_region[line.parent]
				if line.from_item:
					row(line.from_item, reg).revisions -= flt(line.amount)
				if line.to_item:
					row(line.to_item, reg).revisions += flt(line.amount)

	# manual execution entries ------------------------------------------------
	entry_filters = {"docstatus": 1, "posting_date": ("between", (start, end))}
	if region:
		entry_filters["region"] = region
	for e in frappe.get_all(
		"Budget Execution Entry",
		filters=entry_filters,
		fields=["budget_item", "region", "entry_type", {"SUM": "amount", "as": "amount"}],
		group_by="budget_item, region, entry_type",
	):
		r = row(e.budget_item, e.region)
		if e.entry_type == "Commitment":
			r.commitments += flt(e.amount)
		elif r.execution_source != "General Ledger":
			r.executed += flt(e.amount)

	# general ledger -----------------------------------------------------------
	for (item_name, reg), amount in gl_executed(items, start, end, region).items():
		row(item_name, reg).executed += amount

	# filters on item attributes ---------------------------------------------------
	out = []
	for r in rows.values():
		if department and r.owner_department != department:
			continue
		if chapter and r.chapter != chapter:
			continue
		if item and r.budget_item != item:
			continue
		finish(r)
		out.append(r)
	return out


def finish(r):
	r.revised = flt(r.approved + r.revisions, 2)
	r.remaining = flt(r.revised - r.commitments - r.executed, 2)
	r.execution_pct = pct(r.executed, r.revised)
	r.status = execution_status(r.execution_pct, r.revised)
	return r


def gl_executed(items, start, end, region=None):
	"""{(item, region): debit - credit} from submitted GL entries of the mapped accounts."""
	gl_items = [i for i in items.values() if i.execution_source == "General Ledger"]
	if not gl_items:
		return {}
	mappings = frappe.get_all(
		"Budget Item Account",
		filters={"parent": ("in", [i.name for i in gl_items]), "parenttype": "Budget Item"},
		fields=["parent", "account", "cost_center", "region"],
	)
	result = defaultdict(float)
	for m in mappings:
		if region and m.region != region:
			continue
		company = items[m.parent].company
		filters = {
			"account": m.account,
			"is_cancelled": 0,
			"posting_date": ("between", (start, end)),
		}
		if company:
			filters["company"] = company
		if m.cost_center:
			lft, rgt = frappe.db.get_value("Cost Center", m.cost_center, ["lft", "rgt"])
			centers = frappe.get_all(
				"Cost Center", filters={"lft": (">=", lft), "rgt": ("<=", rgt)}, pluck="name"
			)
			filters["cost_center"] = ("in", centers)
		total = frappe.get_all(
			"GL Entry",
			filters=filters,
			fields=[{"SUM": "debit", "as": "debit"}, {"SUM": "credit", "as": "credit"}],
		)
		if total:
			result[(m.parent, m.region)] += flt(total[0].debit) - flt(total[0].credit)
	return result


def summarize(rows):
	t = frappe._dict(approved=0.0, revisions=0.0, commitments=0.0, executed=0.0)
	for r in rows:
		for k in t:
			t[k] += flt(r.get(k))
	return finish(t)


def check_access():
	"""Budget figures are visible to the roles that can read Approved Budget amounts."""
	if not frappe.has_permission("Approved Budget", "read"):
		frappe.throw(_("You are not allowed to view the budget position"), frappe.PermissionError)
	meta = frappe.get_meta("Approved Budget")
	if 1 not in meta.get_permlevel_access("read"):
		frappe.throw(_("You are not allowed to view budget amounts"), frappe.PermissionError)
