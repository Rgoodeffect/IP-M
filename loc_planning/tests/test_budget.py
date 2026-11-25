import frappe
from frappe.tests import IntegrationTestCase

from loc_planning.budget.execution import get_position
from loc_planning.budget.report.budget_execution_position.budget_execution_position import execute as report
from loc_planning.loc_planning.doctype.reporting_period.reporting_period import set_period_status
from loc_planning.tests.utils import as_user, ensure_period, ensure_test_user
from loc_planning.utils.document_guard import PeriodClosedError

YEAR = 2039
WEST, EAST = "الغربية", "الشرقية"
HR = "إدارة الموارد البشرية"
CH2 = "الباب الثاني - التسيير"
ITEM_A, ITEM_B, ITEM_GL = "بند اختبار أ", "بند اختبار ب", "بند اختبار دفتر الأستاذ"
COMPANY, ABBR = "LOC Test Company", "LTC"
FIN_USER = "loc_finance@example.com"
SD_USER = "loc_statistics@example.com"
SO_USER = "loc_so_budget@example.com"


def ensure_company():
	# records ERPNext's setup wizard normally creates (absent on a fresh test site)
	if not frappe.db.exists("Warehouse Type", "Transit"):
		frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)
	if not frappe.db.exists("Company", COMPANY):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": COMPANY,
				"abbr": ABBR,
				"default_currency": "LYD",
				"country": "Libya",
				"chart_of_accounts": "Standard",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Fiscal Year", str(YEAR)):
		frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": str(YEAR),
				"year_start_date": f"{YEAR}-01-01",
				"year_end_date": f"{YEAR}-12-31",
			}
		).insert(ignore_permissions=True)
	expense = f"LOC Test Expense - {ABBR}"
	if not frappe.db.exists("Account", expense):
		parent = frappe.db.get_value(
			"Account",
			{"company": COMPANY, "root_type": "Expense", "is_group": 1, "parent_account": ("is", "set")},
			"name",
		)
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "LOC Test Expense",
				"parent_account": parent,
				"company": COMPANY,
				"account_type": "Expense Account",
			}
		).insert(ignore_permissions=True)
	root_cc = frappe.db.get_value("Cost Center", {"company": COMPANY, "is_group": 1}, "name")
	for name in ("LOC West", "LOC East"):
		if not frappe.db.exists("Cost Center", f"{name} - {ABBR}"):
			frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": name,
					"parent_cost_center": root_cc,
					"company": COMPANY,
				}
			).insert(ignore_permissions=True)
	return expense


def post_journal(amount, cost_center, date=f"{YEAR}-03-15"):
	cash = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Cash", "is_group": 0}, "name")
	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": COMPANY,
			"posting_date": date,
			"accounts": [
				{
					"account": f"LOC Test Expense - {ABBR}",
					"debit_in_account_currency": amount,
					"cost_center": cost_center,
				},
				{"account": cash, "credit_in_account_currency": amount, "cost_center": cost_center},
			],
		}
	)
	je.insert(ignore_permissions=True)
	je.submit()
	return je


def ensure_item(name, **kw):
	if not frappe.db.exists("Budget Item", name):
		frappe.get_doc(
			{"doctype": "Budget Item", "item_name": name, "chapter": CH2, "owner_department": HR, **kw}
		).insert(ignore_permissions=True)
	return name


def make_budget(region, lines, submit=True):
	doc = frappe.get_doc(
		{
			"doctype": "Approved Budget",
			"fiscal_year": YEAR,
			"region": region,
			"items": [{"budget_item": i, "approved_amount": a} for i, a in lines],
		}
	).insert()
	if submit:
		doc.submit()
	return doc


def entry(item, amount, entry_type="Actual Expense", region=WEST, date=f"{YEAR}-02-10"):
	doc = frappe.get_doc(
		{
			"doctype": "Budget Execution Entry",
			"budget_item": item,
			"entry_type": entry_type,
			"amount": amount,
			"region": region,
			"posting_date": date,
		}
	).insert()
	doc.submit()
	return doc


def position(item, region=WEST, **kw):
	rows = [r for r in get_position(YEAR, region=region, item=item, **kw)]
	return rows[0] if rows else None


class IntegrationTestBudget(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		expense = ensure_company()
		ensure_item(ITEM_A)
		ensure_item(ITEM_B)
		ensure_item(
			ITEM_GL,
			execution_source="General Ledger",
			company=COMPANY,
			accounts=[
				{"account": expense, "cost_center": f"LOC West - {ABBR}", "region": WEST},
				{"account": expense, "cost_center": f"LOC East - {ABBR}", "region": EAST},
			],
		)
		ensure_test_user(FIN_USER, ["Finance Budget"])
		ensure_test_user(SD_USER, ["Statistics & Data"])
		ensure_test_user(SO_USER, ["Sales Office User"])
		frappe.db.commit()

	def setUp(self):
		# every test starts from an empty year
		for dt in ("Budget Execution Entry", "Budget Revision", "Approved Budget"):
			for name in frappe.get_all(dt, filters={"fiscal_year": YEAR}, pluck="name"):
				frappe.db.set_value(dt, name, "docstatus", 2)

	def test_figures_and_status_thresholds(self):
		make_budget(WEST, [(ITEM_A, 1_000_000)])
		entry(ITEM_A, 100_000, "Commitment")
		entry(ITEM_A, 300_000)
		r = position(ITEM_A)
		self.assertEqual((r.approved, r.commitments, r.executed), (1_000_000, 100_000, 300_000))
		self.assertEqual(r.remaining, 600_000)
		self.assertEqual(r.execution_pct, 30)
		self.assertEqual(r.status, "Slow Execution")

		entry(ITEM_A, 200_000)
		self.assertEqual(position(ITEM_A).status, "Within Plan")
		entry(ITEM_A, 350_000)
		r = position(ITEM_A)
		self.assertEqual((r.execution_pct, r.status), (85, "Limit Exceeded"))
		self.assertEqual(r.remaining, 1_000_000 - 100_000 - 850_000)

		with self.change_settings(
			"LOC Planning Settings", {"slow_execution_threshold": 20, "over_execution_threshold": 90}
		):
			self.assertEqual(position(ITEM_A).status, "Within Plan")

	def test_position_up_to_date(self):
		make_budget(WEST, [(ITEM_A, 500_000)])
		entry(ITEM_A, 100_000, date=f"{YEAR}-01-20")
		entry(ITEM_A, 50_000, date=f"{YEAR}-06-20")
		self.assertEqual(position(ITEM_A, to_date=f"{YEAR}-03-31").executed, 100_000)
		self.assertEqual(position(ITEM_A).executed, 150_000)

	def test_one_approved_budget_per_year_and_region(self):
		make_budget(WEST, [(ITEM_A, 1)])
		with self.assertRaises(frappe.ValidationError):
			make_budget(WEST, [(ITEM_A, 2)])
		make_budget(EAST, [(ITEM_A, 3)])

	def test_transfer_revision_and_history(self):
		budget = make_budget(WEST, [(ITEM_A, 1_000_000), (ITEM_B, 200_000)])
		entry(ITEM_A, 850_000)
		rev = frappe.get_doc(
			{
				"doctype": "Budget Revision",
				"approved_budget": budget.name,
				"revision_type": "Transfer",
				"revision_date": f"{YEAR}-04-01",
				"reason": "سبب تجريبي",
				"lines": [{"from_item": ITEM_A, "to_item": ITEM_B, "amount": 100_000}],
			}
		).insert()
		rev.submit()
		self.assertEqual((position(ITEM_A).revised, position(ITEM_B).revised), (900_000, 300_000))
		self.assertEqual(position(ITEM_A).revisions, -100_000)
		budget.reload()
		self.assertEqual(
			{r.budget_item: r.revised_amount for r in budget.items}, {ITEM_A: 900_000, ITEM_B: 300_000}
		)

		# only 50,000 is left on A (900,000 - 850,000)
		too_much = frappe.copy_doc(rev)
		too_much.docstatus = 0
		too_much.lines[0].amount = 60_000
		too_much.insert()
		with self.assertRaises(frappe.ValidationError):
			too_much.submit()

		rev.cancel_reason = "سبب تجريبي"
		rev.cancel()
		self.assertEqual(position(ITEM_A).revised, 1_000_000)

		# an increase cannot take money from an item
		bad = frappe.copy_doc(rev)
		bad.docstatus = 0
		bad.revision_type = "Increase"
		with self.assertRaises(frappe.ValidationError):
			bad.insert()

	def test_gl_source_by_region_and_cancellation(self):
		make_budget(WEST, [(ITEM_GL, 400_000)])
		make_budget(EAST, [(ITEM_GL, 100_000)])
		post_journal(250_000, f"LOC West - {ABBR}")
		post_journal(70_000, f"LOC East - {ABBR}")
		cancelled = post_journal(9_999, f"LOC West - {ABBR}")
		cancelled.cancel()
		self.assertEqual(position(ITEM_GL, WEST).executed, 250_000)
		self.assertEqual(position(ITEM_GL, EAST).executed, 70_000)
		self.assertEqual(position(ITEM_GL, WEST).execution_pct, 62.5)
		# commitments are still entered manually; actual spending is not
		entry(ITEM_GL, 10_000, "Commitment")
		self.assertEqual(position(ITEM_GL, WEST).commitments, 10_000)
		with self.assertRaises(frappe.ValidationError):
			entry(ITEM_GL, 1, "Actual Expense")

	def test_report_tree_split_and_totals(self):
		make_budget(WEST, [(ITEM_A, 600_000), (ITEM_B, 400_000)])
		make_budget(EAST, [(ITEM_A, 300_000)])
		entry(ITEM_A, 300_000, region=WEST)
		entry(ITEM_A, 30_000, region=EAST)
		columns, data, _m, chart, summary = report({"fiscal_year": YEAR, "chapter": CH2, "split_regions": 1})
		fieldnames = [c["fieldname"] for c in columns]
		self.assertIn(f"revised__{WEST}", fieldnames)
		self.assertIn(f"revised__{EAST}", fieldnames)
		chapter = next(d for d in data if d.get("indent") == 0 and d.get("name") == CH2)
		item_a = next(d for d in data if d.get("name") == ITEM_A)
		self.assertEqual(item_a.revised, 900_000)
		self.assertEqual(item_a[f"executed__{EAST}"], 30_000)
		self.assertEqual(item_a[f"execution_pct__{WEST}"], 50)
		self.assertGreaterEqual(chapter.revised, 1_300_000)
		self.assertTrue(data[-1].get("is_total"))
		self.assertTrue(chart)
		self.assertEqual(summary[0]["value"], data[-1].revised)

	def test_amounts_hidden_from_operational_roles(self):
		make_budget(WEST, [(ITEM_A, 1_000)])
		with as_user(SO_USER):
			with self.assertRaises(frappe.PermissionError):
				report({"fiscal_year": YEAR})
		with as_user(SD_USER):
			report({"fiscal_year": YEAR})
			meta = frappe.get_meta("Approved Budget")
			self.assertIn(1, meta.get_permlevel_access("read"))
			self.assertNotIn(1, meta.get_permlevel_access("write"))
		with as_user(FIN_USER):
			self.assertIn(1, frappe.get_meta("Approved Budget").get_permlevel_access("write"))

	def test_entry_in_closed_month_is_locked(self):
		month = ensure_period("Monthly", YEAR, 5)
		make_budget(WEST, [(ITEM_A, 1_000)])
		set_period_status(month, "Closed")
		try:
			with self.assertRaises(PeriodClosedError):
				entry(ITEM_A, 10, date=f"{YEAR}-05-10")
		finally:
			set_period_status(month, "Open")
		doc = entry(ITEM_A, 10, date=f"{YEAR}-05-10")
		self.assertEqual(doc.reporting_period, month)
