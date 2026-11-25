import io

import frappe
from frappe.model.workflow import WorkflowPermissionError, WorkflowTransitionError, apply_workflow
from frappe.tests import IntegrationTestCase

from loc_planning.loc_planning.doctype.loc_user_setup.loc_user_setup import apply_assignment
from loc_planning.loc_planning.doctype.reporting_period.reporting_period import set_period_status
from loc_planning.stations import tasks as station_tasks
from loc_planning.stations.doctype.station_data_import import station_data_import as sdi
from loc_planning.stations.doctype.station_monthly_data.station_monthly_data import get_defaults
from loc_planning.tests.utils import as_user, ensure_period, ensure_test_user
from loc_planning.utils.document_guard import PeriodClosedError

TRIPOLI = "مكتب مبيعات طرابلس الكبرى"
MISRATA = "مكتب مبيعات المنطقة الوسطى مصراتة"
SO_USER = "loc_so_tripoli@example.com"
SD_USER = "loc_statistics@example.com"
YEAR = 2037
ST_T1, ST_T2, ST_M1, ST_STOP = "T-ST-T1", "T-ST-T2", "T-ST-M1", "T-ST-STOP"


def make_station(code, office, status="Operating", **kw):
	if frappe.db.exists("Fuel Station", code):
		return frappe.get_doc("Fuel Station", code)
	return frappe.get_doc(
		{
			"doctype": "Fuel Station",
			"station_code": code,
			"station_name": f"محطة اختبار {code}",
			"operation_type": "وكيل",
			"sales_office": office,
			"status": status,
			"stop_reason": "سبب تجريبي" if status != "Operating" else None,
			"tanks": [
				{"tank_no": "1", "product": "بنزين", "capacity": 30000},
				{"tank_no": "2", "product": "ديزل", "capacity": 20000},
			],
			"support_activities": [{"activity_type": "ماركت"}],
			**kw,
		}
	).insert(ignore_permissions=True)


def month(n):
	return ensure_period("Monthly", YEAR, n)


def monthly(station, period, products=None, **kw):
	doc = frappe.get_doc(
		{
			"doctype": "Station Monthly Data",
			"station": station,
			"reporting_period": period,
			"products": products
			or [
				{
					"product": "بنزين",
					"target_qty": 1000,
					"actual_qty": 900,
					"opening_stock": 200,
					"received_qty": 900,
					"closing_stock": 200,
				},
				{"product": "ديزل", "target_qty": 500, "actual_qty": 600},
			],
			**kw,
		}
	)
	doc.flags.mute_warnings = True
	return doc.insert()


def approve(doc):
	with as_user(SO_USER):
		doc = apply_workflow(doc, "Submit for Review")
	with as_user(SD_USER):
		doc = apply_workflow(doc, "Approve")
	return doc


class IntegrationTestStations(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_test_user(SO_USER, [])
		apply_assignment(SO_USER, "Sales Office User", TRIPOLI)
		ensure_test_user(SD_USER, ["Statistics & Data"])
		make_station(ST_T1, TRIPOLI)
		make_station(ST_T2, TRIPOLI)
		make_station(ST_M1, MISRATA)
		make_station(ST_STOP, MISRATA, status="Stopped")
		for n in range(1, 13):
			month(n)
		frappe.db.commit()

	# ------------------------------------------------------------------ station
	def test_station_rules(self):
		station = frappe.get_doc("Fuel Station", ST_T1)
		self.assertEqual(station.region, "الغربية")
		self.assertEqual(station.tanks_count, 2)
		self.assertEqual(station.total_capacity, 50000)
		with self.assertRaises(frappe.ValidationError):
			make_station("T-ST-BAD", "إدارة التفتيش")
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Fuel Station",
					"station_code": "T-ST-NOREASON",
					"station_name": "x",
					"operation_type": "وكيل",
					"sales_office": TRIPOLI,
					"status": "Stopped",
				}
			).insert()

	# ------------------------------------------------------------ monthly data
	def test_calculations_and_uniqueness(self):
		doc = monthly(ST_T1, month(1))
		petrol = doc.products[0]
		self.assertEqual(petrol.achievement_pct, 90)
		self.assertEqual(petrol.stock_variance, 0)
		self.assertEqual(doc.sales_office, TRIPOLI)
		self.assertEqual(doc.name, f"{ST_T1}-{month(1)}")
		with self.assertRaises(frappe.DuplicateEntryError):
			monthly(ST_T1, month(1))

	def test_monthly_period_required_and_stopped_days_limit(self):
		quarter = ensure_period("Quarterly", YEAR, 1)
		with self.assertRaises(frappe.ValidationError):
			monthly(ST_T2, quarter)
		with self.assertRaises(frappe.ValidationError):
			monthly(ST_T2, month(2), stopped_days=29)  # February 2037 has 28 days

	def test_opening_stock_defaults_from_previous_month(self):
		monthly(ST_T2, month(3), products=[{"product": "بنزين", "closing_stock": 777}])
		defaults = get_defaults(ST_T2, month(4))
		petrol = next(r for r in defaults["products"] if r["product"] == "بنزين")
		self.assertEqual(petrol["opening_stock"], 777)
		self.assertEqual([r["activity_type"] for r in defaults["support_revenues"]], ["ماركت"])

	def test_workflow_and_mandatory_return_comment(self):
		with as_user(SO_USER):
			doc = monthly(ST_T1, month(5))
			doc = apply_workflow(doc, "Submit for Review")
			with self.assertRaises((WorkflowPermissionError, WorkflowTransitionError)):
				apply_workflow(doc, "Approve")
		with as_user(SD_USER):
			with self.assertRaises(frappe.ValidationError):
				apply_workflow(doc, "Return for Revision")
			doc.reload()
			doc.review_comment = "يرجى تصحيح مبيعات الديزل"
			doc.save()
			doc = apply_workflow(doc, "Return for Revision")
		self.assertEqual(doc.status, "Returned")
		with as_user(SO_USER):
			doc = apply_workflow(doc, "Submit for Review")
		with as_user(SD_USER):
			doc = apply_workflow(doc, "Approve")
		self.assertEqual((doc.docstatus, doc.status), (1, "Approved"))

	def test_sales_office_isolation(self):
		mine = monthly(ST_T1, month(6))
		other = monthly(ST_M1, month(6))
		with as_user(SO_USER):
			visible = frappe.get_list(
				"Station Monthly Data", filters={"reporting_period": month(6)}, pluck="name"
			)
			self.assertIn(mine.name, visible)
			self.assertNotIn(other.name, visible)
			self.assertFalse(frappe.has_permission("Station Monthly Data", "read", other.name))
			stations = frappe.get_list("Fuel Station", pluck="name")
			self.assertIn(ST_T1, stations)
			self.assertNotIn(ST_M1, stations)
			with self.assertRaises(frappe.PermissionError):
				monthly(ST_M1, month(7))

	def test_closed_month_is_locked(self):
		doc = monthly(ST_T2, month(8))
		set_period_status(month(8), "Closed")
		try:
			doc.reload()
			doc.notes = "x"
			with self.assertRaises(PeriodClosedError):
				doc.save()
		finally:
			set_period_status(month(8), "Open")

	# ------------------------------------------------------------------ import
	def _template_and_fill(self, period, fill):
		from openpyxl import load_workbook

		imp = frappe.get_doc({"doctype": "Station Data Import", "reporting_period": period}).insert()
		sdi.download_template(imp.name)
		wb = load_workbook(io.BytesIO(frappe.response["filecontent"]))
		ws = wb[sdi.DATA_SHEET]
		keys = [c.value for c in ws[1]]
		for row in ws.iter_rows(min_row=3):
			code = row[0].value
			for key, value in fill.get(code, {}).items():
				row[keys.index(key)].value = value
		extra = fill.get("__extra__")
		if extra:
			ws.append([extra.get(k) for k in keys])
		buf = io.BytesIO()
		wb.save(buf)
		f = frappe.get_doc(
			{"doctype": "File", "file_name": f"{imp.name}.xlsx", "content": buf.getvalue(), "is_private": 1}
		).insert()
		imp.import_file = f.file_url
		imp.save()
		return imp, keys

	def test_template_contains_only_own_stations_with_opening_stock(self):
		monthly(ST_T1, month(9), products=[{"product": "بنزين", "closing_stock": 555}])
		with as_user(SO_USER):
			_imp, keys = self._template_and_fill(month(10), {})
			self.assertIn("actual_qty|بنزين", keys)
			self.assertIn("revenue|ماركت", keys)
			rows = sdi.template_rows(month(10))
		codes = [r["station"] for r in rows]
		self.assertIn(ST_T1, codes)
		self.assertNotIn(ST_M1, codes)
		t1 = next(r for r in rows if r["station"] == ST_T1)
		self.assertEqual(t1["opening_stock|بنزين"], 555)

	def test_import_validate_then_import(self):
		fill = {
			ST_T1: {
				"target_qty|بنزين": 1000,
				"actual_qty|بنزين": "\u0661\u066c\u0662\u0660\u0660",  # Arabic-Indic digits: 1,200
				"revenue|ماركت": 4500,
				"stopped_days": 1,
			},
			ST_T2: {"actual_qty|ديزل": "abc"},
			"__extra__": {"station": ST_M1, "actual_qty|بنزين": 10},
		}
		with as_user(SO_USER):
			imp, _keys = self._template_and_fill(month(11), fill)
			counts = imp.validate_file()
			self.assertEqual(counts["Created"], 1)
			self.assertFalse(
				frappe.db.exists("Station Monthly Data", {"station": ST_T1, "reporting_period": month(11)})
			)
			imp.reload()
			self.assertEqual(imp.status, "Failed")

			counts = imp.start_import()
		self.assertEqual(counts["Created"], 1)
		self.assertEqual(counts["Error"], 2)  # invalid number + station of another office
		imp.reload()
		self.assertEqual(imp.status, "Partially Imported")
		doc = frappe.get_doc("Station Monthly Data", f"{ST_T1}-{month(11)}")
		petrol = next(r for r in doc.products if r.product == "بنزين")
		self.assertEqual((petrol.target_qty, petrol.actual_qty), (1000, 1200))
		self.assertEqual(doc.total_support_revenue, 4500)
		self.assertEqual(doc.stopped_days, 1)
		messages = " ".join(r.message or "" for r in imp.log)
		self.assertIn(ST_M1, messages)

		# second import updates the draft; approved data is refused
		with as_user(SO_USER):
			imp2, _ = self._template_and_fill(month(11), {ST_T1: {"actual_qty|بنزين": 1300}})
			self.assertEqual(imp2.start_import()["Updated"], 1)
		doc.reload()
		approve(doc)
		with as_user(SO_USER):
			imp3, _ = self._template_and_fill(month(11), {ST_T1: {"actual_qty|بنزين": 1}})
			self.assertEqual(imp3.start_import()["Error"], 1)

	# ----------------------------------------------------------------- reports
	def test_reports(self):
		from loc_planning.stations.report.missing_station_data.missing_station_data import execute as missing
		from loc_planning.stations.report.station_sales_analysis.station_sales_analysis import (
			execute as sales,
		)
		from loc_planning.stations.report.station_target_vs_actual.station_target_vs_actual import (
			execute as tva,
		)
		from loc_planning.stations.report.stopped_stations.stopped_stations import execute as stopped

		p = month(12)
		approve(monthly(ST_T1, p))
		approve(monthly(ST_T2, p))
		filters = {"from_period": p, "to_period": p}

		_c, data, _m, chart, _summary = sales({**filters, "group_by": "Product"})
		petrol = next(r for r in data if r.product == "بنزين")
		self.assertEqual((petrol.actual_qty, petrol.target_qty, petrol.stations), (1800, 2000, 2))
		self.assertEqual(petrol.achievement_pct, 90)
		self.assertTrue(chart)

		_c, data, *_ = sales({**filters, "group_by": "Sales Office"})
		self.assertEqual([r["group"] for r in data], [TRIPOLI])

		_c, data, *_ = tva({**filters, "product": "ديزل"})
		self.assertEqual({r.station for r in data}, {ST_T1, ST_T2})
		self.assertTrue(all(r.variance == 100 and r.achievement_pct == 120 for r in data))

		_c, data, *_ = missing({"reporting_period": p})
		missing_codes = {r.station for r in data}
		self.assertIn(ST_M1, missing_codes)
		self.assertNotIn(ST_T1, missing_codes)

		with as_user(SO_USER):
			_c, data, *_ = missing({"reporting_period": p})
			self.assertNotIn(ST_M1, {r.station for r in data})

		_c, data, *_ = stopped({})
		self.assertIn(ST_STOP, {r.station for r in data})

	# --------------------------------------------------------------- reminders
	def test_reminder_schedule(self):
		with self.change_settings(
			"LOC Planning Settings",
			{"reminder_days_before": 3, "reminder_repeat_days_after": 2, "max_overdue_reminders": 2},
		):
			self.assertTrue(station_tasks.should_remind("2037-02-10", "2037-02-07"))
			self.assertFalse(station_tasks.should_remind("2037-02-10", "2037-02-08"))
			self.assertTrue(station_tasks.should_remind("2037-02-10", "2037-02-10"))
			self.assertTrue(station_tasks.should_remind("2037-02-10", "2037-02-12"))
			self.assertFalse(station_tasks.should_remind("2037-02-10", "2037-02-13"))
			self.assertFalse(station_tasks.should_remind("2037-02-10", "2037-02-16"))

	def test_missing_data_reminder_reaches_sales_office(self):
		before = frappe.db.count("Notification Log", {"for_user": SO_USER})
		# data for December 2037 is due on 10 January 2038 (default due day 10)
		sent = station_tasks.remind_missing_station_data("2038-01-10")
		self.assertIn(TRIPOLI, sent)
		self.assertIn(SO_USER, sent[TRIPOLI])
		self.assertGreater(frappe.db.count("Notification Log", {"for_user": SO_USER}), before)
