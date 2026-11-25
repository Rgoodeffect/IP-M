import frappe
from frappe.tests import IntegrationTestCase

from loc_planning.dashboard import api
from loc_planning.loc_planning.dashboard_chart_source.loc_budget_by_chapter import loc_budget_by_chapter
from loc_planning.loc_planning.dashboard_chart_source.loc_monthly_sales_trend import loc_monthly_sales_trend
from loc_planning.loc_planning.doctype.loc_user_setup.loc_user_setup import apply_assignment
from loc_planning.tests.test_company_activity_report import DEPT, REGION, setup_test_region
from loc_planning.tests.utils import as_user, ensure_test_user

SO_USER = "loc_so_dashboard@example.com"
DC_USER = "loc_dc_dashboard@example.com"
EV_USER = "loc_executive@example.com"


class IntegrationTestDashboard(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.quarter = setup_test_region()
		ensure_test_user(SO_USER, [])
		apply_assignment(SO_USER, "Sales Office User", "مكتب مبيعات طرابلس الكبرى")
		ensure_test_user(DC_USER, [])
		apply_assignment(DC_USER, "Department Coordinator", DEPT)
		ensure_test_user(EV_USER, ["Executive Viewer"])
		frappe.db.commit()

	def data(self):
		return api.get_dashboard_data(self.quarter, REGION)

	def test_management_sees_every_block(self):
		with as_user(EV_USER):
			d = self.data()
		self.assertEqual(d["sales"]["fuel_litres"], 270)
		self.assertEqual(d["sales"]["fuel_achievement"], 90)
		self.assertEqual(d["budget"]["approved"], 1000)
		self.assertEqual(d["stations"], {"total": 1, "operating": 1})
		self.assertEqual(d["reports"]["required"], 1)
		self.assertIsNotNone(d["certificates"])
		self.assertEqual([m["label"] for m in d["trend"]][:3], ["يناير 2041", "فبراير 2041", "مارس 2041"])

	def test_sales_office_sees_only_its_own_data(self):
		with as_user(SO_USER):
			d = self.data()
		self.assertEqual(d["sales"]["fuel_litres"], 0)  # the test station belongs to another office
		self.assertIsNone(d["budget"])  # no access to budget amounts
		self.assertIsNone(d["certificates"])
		self.assertIsNone(d["reports"])
		self.assertEqual(d["stations"]["total"], 0)

	def test_department_coordinator_sees_only_its_department(self):
		with as_user(DC_USER):
			d = self.data()
		self.assertIsNone(d["sales"])
		self.assertIsNone(d["budget"])
		self.assertEqual([r["department"] for r in d["reports"]["rows"]], [DEPT])

	def test_number_cards(self):
		filters = {"reporting_period": self.quarter, "region": REGION}
		with as_user(EV_USER):
			self.assertEqual(api.card_fuel_sales(filters)["value"], 270)
			self.assertEqual(api.card_budget_execution(frappe.as_json(filters))["value"], 40)
			self.assertEqual(api.card_operating_stations(filters)["value"], 1)
			self.assertEqual(api.card_reports_received(filters)["value"], 1)
			self.assertEqual(api.card_certificates_issued(filters)["fieldtype"], "Int")
		with as_user(SO_USER):
			self.assertEqual(api.card_budget_execution(filters)["value"], 0)

	def test_chart_sources_are_computed_per_user(self):
		filters = frappe.as_json({"reporting_period": self.quarter, "region": REGION})
		with as_user(EV_USER):
			trend = loc_monthly_sales_trend.get(chart_name="LOC Monthly Sales Trend", filters=filters)
			budget = loc_budget_by_chapter.get(chart_name="LOC Budget by Chapter", filters=filters)
		self.assertEqual(trend["datasets"][1]["values"][:3], [90, 90, 90])
		self.assertEqual(budget["datasets"][0]["values"], [1000])
		with as_user(SO_USER):
			trend = loc_monthly_sales_trend.get(chart_name="LOC Monthly Sales Trend", filters=filters)
		self.assertEqual(trend["datasets"][1]["values"][:3], [0, 0, 0])  # not another user's cached figures

	def test_workspaces_are_restricted_by_role(self):
		main = [r.role for r in frappe.get_doc("Workspace", "LOC Planning").roles]
		self.assertIn("Executive Viewer", main)
		self.assertNotIn("Sales Office User", main)
		self.assertEqual(
			[r.role for r in frappe.get_doc("Workspace", "Sales Office Portal").roles], ["Sales Office User"]
		)
		self.assertEqual(
			[r.role for r in frappe.get_doc("Workspace", "Department Coordinator Portal").roles],
			["Department Coordinator"],
		)
		self.assertTrue(frappe.db.exists("Page", "loc-dashboard"))
		for card in (
			"LOC Fuel Sales",
			"LOC Budget Execution",
			"LOC Operating Stations",
			"LOC Reports Received",
			"LOC Certificates Issued",
		):
			self.assertEqual(frappe.db.get_value("Number Card", card, "type"), "Custom")
