import json
import re

import frappe
from frappe.model.workflow import WorkflowPermissionError, WorkflowTransitionError, apply_workflow
from frappe.tests import IntegrationTestCase

from loc_planning.activity_report.docx_export import build_docx
from loc_planning.activity_report.render import get_report_context
from loc_planning.tests.utils import as_user, ensure_period, ensure_test_user
from loc_planning.utils.workflow import set_review_comment

YEAR = 2041
REGION, REGION_CODE = "منطقة اختبار", "TST"
OFFICE = "مكتب مبيعات اختبار"
DEPT = "إدارة اختبار التقرير"
STATION = "T-CAR-1"
ITEM = "بند اختبار التقرير"
TEMPLATE = "تقرير النشاط الربع سنوي"
SP_USER, DIR_USER, GM_USER = "loc_planner@example.com", "loc_director@example.com", "loc_gm@example.com"
HARAKAT = re.compile("[ً-ْ]")


def month(year, n):
	return ensure_period("Monthly", year, n)


def approved_station_month(period, actual, target=100):
	if frappe.db.exists(
		"Station Monthly Data", {"station": STATION, "reporting_period": period, "docstatus": 1}
	):
		return
	doc = frappe.get_doc(
		{
			"doctype": "Station Monthly Data",
			"station": STATION,
			"reporting_period": period,
			"products": [{"product": "بنزين", "target_qty": target, "actual_qty": actual}],
		}
	)
	doc.flags.mute_warnings = True
	doc.insert(ignore_permissions=True)
	doc = apply_workflow(doc, "Submit for Review")
	apply_workflow(doc, "Approve")


def setup_test_region():
	if not frappe.db.exists("LOC Region", REGION):
		frappe.get_doc({"doctype": "LOC Region", "region_name": REGION, "region_code": REGION_CODE}).insert()
	for name, kind, extra in (
		(OFFICE, "Sales Office", {}),
		(DEPT, "Department", {"requires_activity_report": 1}),
	):
		if not frappe.db.exists("LOC Department", name):
			frappe.get_doc(
				{
					"doctype": "LOC Department",
					"department_name": name,
					"department_type": kind,
					"region": REGION,
					**extra,
				}
			).insert()
	if not frappe.db.exists("Fuel Station", STATION):
		frappe.get_doc(
			{
				"doctype": "Fuel Station",
				"station_code": STATION,
				"station_name": "محطة اختبار التقرير",
				"operation_type": "وكيل",
				"sales_office": OFFICE,
				"tanks": [{"tank_no": "1", "product": "بنزين", "capacity": 1000}],
			}
		).insert()
	# current quarter: 3 x 90 = 270; previous quarter (Dec): 60; same quarter last year (Jan): 30
	for m in (1, 2, 3):
		approved_station_month(month(YEAR, m), 90)
	approved_station_month(month(YEAR - 1, 12), 60)
	approved_station_month(month(YEAR - 1, 1), 30)
	for m in (10, 11):
		approved_station_month(month(YEAR - 1, m), 0)
	for m in (2, 3):
		approved_station_month(month(YEAR - 1, m), 0)

	if not frappe.db.exists("Budget Item", ITEM):
		frappe.get_doc(
			{
				"doctype": "Budget Item",
				"item_name": ITEM,
				"chapter": "الباب الثاني - التسيير",
				"owner_department": DEPT,
			}
		).insert()
	if not frappe.db.exists("Approved Budget", {"fiscal_year": YEAR, "region": REGION, "docstatus": 1}):
		budget = frappe.get_doc(
			{
				"doctype": "Approved Budget",
				"fiscal_year": YEAR,
				"region": REGION,
				"items": [{"budget_item": ITEM, "approved_amount": 1000}],
			}
		).insert()
		budget.submit()
		entry = frappe.get_doc(
			{
				"doctype": "Budget Execution Entry",
				"budget_item": ITEM,
				"entry_type": "Actual Expense",
				"amount": 400,
				"region": REGION,
				"posting_date": f"{YEAR}-02-15",
			}
		).insert()
		entry.submit()

	quarter = ensure_period("Quarterly", YEAR, 1)
	if not frappe.db.exists(
		"Department Activity Submission", {"department": DEPT, "reporting_period": quarter}
	):
		sub = frappe.get_doc(
			{
				"doctype": "Department Activity Submission",
				"department": DEPT,
				"reporting_period": quarter,
				"activities": [{"activity": "نشاط اختبار", "target": 4, "executed": 3}],
				"difficulties": "<p>صعوبة اختبار</p>",
				"next_period_plan": "<p>خطة اختبار</p>",
			}
		).insert()
		for action in ("Submit to Manager", "Approve", "Send for Approval", "Approve"):
			sub = apply_workflow(sub, action)
	return quarter


def new_report(quarter):
	doc = frappe.get_doc(
		{
			"doctype": "Company Activity Report",
			"reporting_period": quarter,
			"scope": "Region",
			"region": REGION,
			"template": TEMPLATE,
		}
	)
	doc.insert()
	for s in doc.sections:
		if s.data_source == "Department Indicators":
			s.include = 0  # those departments are not in the test region
		if s.data_source == "Editorial Text":
			s.editorial_text = "<p>ملخص تنفيذي للاختبار</p>"
	doc.save()
	return doc


def section(doc, source):
	s = next(s for s in doc.sections if s.data_source == source)
	return s, json.loads(s.snapshot_json) if s.snapshot_json else {}


class IntegrationTestCompanyActivityReport(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_test_user(SP_USER, ["Strategic Planning"])
		ensure_test_user(DIR_USER, ["LOC Planning Director"])
		ensure_test_user(GM_USER, ["LOC General Manager"])
		cls.quarter = setup_test_region()
		frappe.db.commit()

	def test_template_sections_and_title(self):
		doc = new_report(self.quarter)
		self.assertEqual(len(doc.sections), 9)
		self.assertEqual(doc.sections[0].title, "الملخص التنفيذي")
		self.assertIn("الربع الأول 2041", doc.report_title)
		self.assertTrue(all(s.readiness == "Not Refreshed" for s in doc.sections if s.include))

	def test_refresh_figures_comparisons_and_readiness(self):
		doc = new_report(self.quarter)
		doc.refresh_data()
		doc.reload()

		s, data = section(doc, "Sales Data")
		self.assertEqual(s.readiness, "Ready", s.readiness_note)
		petrol = data["products"][0]
		self.assertEqual((petrol["product"], petrol["actual"], petrol["target"]), ("بنزين", 270, 300))
		self.assertEqual(petrol["achievement"], 90)
		self.assertEqual((petrol["previous"], petrol["change_previous"]), (60, 350))
		self.assertEqual((petrol["last_year"], petrol["change_last_year"]), (30, 800))

		_s, data = section(doc, "Budget Position")
		self.assertEqual(data["total"]["approved"], 1000)
		self.assertEqual(data["total"]["executed"], 400)
		self.assertEqual(data["total"]["execution_pct"], 40)

		s, data = section(doc, "Department Activities")
		self.assertEqual((s.readiness, data["required"], data["approved"]), ("Ready", 1, 1))

		s, _data = section(doc, "Difficulties")
		self.assertIn("صعوبة اختبار", s.editorial_text)  # pre-filled from the departments
		self.assertEqual(s.readiness, "Ready")

		_s, data = section(doc, "Stations Data")
		self.assertEqual(data["total"], 1)
		self.assertEqual(doc.readiness_pct, 100, doc.incomplete_sections)

		# clearing the executive summary makes the report incomplete again
		doc.sections[0].editorial_text = ""
		doc.save()
		self.assertLess(doc.readiness_pct, 100)
		self.assertIn("الملخص التنفيذي", doc.incomplete_sections)

	def test_cannot_send_unready_report(self):
		doc = new_report(self.quarter)
		with as_user(SP_USER):
			with self.assertRaises(frappe.ValidationError):
				apply_workflow(doc, "Submit for Review")  # data never refreshed

	def test_approval_flow_snapshot_and_inclusion(self):
		doc = new_report(self.quarter)
		doc.refresh_data()
		with as_user(SP_USER):
			doc = apply_workflow(doc, "Submit for Review")
		with as_user(DIR_USER):
			with self.assertRaises(frappe.ValidationError):
				apply_workflow(doc, "Return for Revision")  # a comment is mandatory
			set_review_comment(doc.doctype, doc.name, "يرجى مراجعة الملخص")
			doc = apply_workflow(doc, "Return for Revision")
		self.assertEqual(doc.workflow_state, "Draft")
		with as_user(SP_USER):
			doc = apply_workflow(doc, "Submit for Review")
		with as_user(DIR_USER):
			doc = apply_workflow(doc, "Send for Approval")
		with as_user(SP_USER):
			with self.assertRaises((WorkflowPermissionError, WorkflowTransitionError)):
				apply_workflow(doc, "Approve")
		with as_user(GM_USER):
			doc = apply_workflow(doc, "Approve")
		self.assertEqual((doc.docstatus, doc.status, doc.approved_by), (1, "Approved", GM_USER))
		sub = frappe.db.get_value(
			"Department Activity Submission",
			{"department": DEPT, "reporting_period": self.quarter},
			["workflow_state", "company_activity_report"],
			as_dict=True,
		)
		self.assertEqual((sub.workflow_state, sub.company_activity_report), ("Included in Report", doc.name))

		# the approved report keeps its figures when the source data changes later
		before = frappe.as_json(get_report_context(doc).sections)
		extra = frappe.get_doc(
			{
				"doctype": "Budget Execution Entry",
				"budget_item": ITEM,
				"entry_type": "Actual Expense",
				"amount": 100,
				"region": REGION,
				"posting_date": f"{YEAR}-03-01",
			}
		).insert()
		extra.submit()
		self.assertEqual(
			frappe.as_json(get_report_context(frappe.get_doc(doc.doctype, doc.name)).sections), before
		)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(doc.doctype, doc.name).refresh_data()
		extra.cancel_reason = "اختبار"
		extra.cancel()

		# cancelling the report releases the department submissions
		doc.reload()
		doc.cancel_reason = "اختبار"
		doc.save()
		with as_user(GM_USER):
			apply_workflow(doc, "Cancel")
		self.assertEqual(
			frappe.db.get_value(
				"Department Activity Submission",
				{"department": DEPT, "reporting_period": self.quarter},
				"workflow_state",
			),
			"Approved",
		)

	def test_pdf_and_word_outputs(self):
		doc = new_report(self.quarter)
		doc.refresh_data()
		html = frappe.get_print(doc.doctype, doc.name, print_format="Company Activity Report")
		self.assertIn("مسودة", html)  # draft watermark
		self.assertIn("<svg", html)  # server-side chart
		self.assertIn("المحتويات", html)
		self.assertIn("1,000", html)  # thousands separator
		self.assertIsNone(HARAKAT.search(frappe.utils.strip_html(html)))
		body = html[html.index('<div class="car">') : html.index("<script data-frappe-print")]
		self.assertNotIn("<script", body.lower())  # nothing executable inside the report itself
		pdf = frappe.get_print(doc.doctype, doc.name, print_format="Company Activity Report", as_pdf=True)
		self.assertTrue(pdf.startswith(b"%PDF"))
		docx = build_docx(doc)
		self.assertTrue(docx.startswith(b"PK"))
		import io
		import zipfile

		xml = zipfile.ZipFile(io.BytesIO(docx)).read("word/document.xml").decode()
		self.assertIn("الملخص التنفيذي", xml)
		self.assertIn("<w:bidi/>", xml)

	def test_text_values_are_escaped_in_print(self):
		from loc_planning.activity_report.render import escape_block

		block = escape_block(
			{
				"type": "table",
				"title": "<i>t</i>",
				"headers": ["<b>h</b>"],
				"rows": [["<script>x</script>", "1,000"]],
			}
		)
		self.assertEqual(block["headers"], ["&lt;b&gt;h&lt;/b&gt;"])
		self.assertEqual(block["rows"][0][0], "&lt;script&gt;x&lt;/script&gt;")
		self.assertEqual(block["rows"][0][1], "1,000")
		self.assertEqual(block["title"], "&lt;i&gt;t&lt;/i&gt;")
