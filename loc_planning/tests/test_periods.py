import datetime

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from loc_planning.loc_planning.doctype.reporting_period.reporting_period import (
	create_periods_for_year,
	set_period_status,
)
from loc_planning.tests.utils import ensure_test_user
from loc_planning.utils import periods


class UnitTestPeriodArithmetic(UnitTestCase):
	def test_names(self):
		self.assertEqual(periods.period_name("Monthly", 2026, 3), "2026-03")
		self.assertEqual(periods.period_name("Quarterly", 2026, 2), "2026-Q2")
		self.assertEqual(periods.period_name("Half-Yearly", 2026, 2), "2026-H2")
		self.assertEqual(periods.period_name("Annual", 2026, None), "2026")

	def test_dates(self):
		self.assertEqual(
			periods.period_dates("Monthly", 2024, 2), (datetime.date(2024, 2, 1), datetime.date(2024, 2, 29))
		)
		self.assertEqual(
			periods.period_dates("Quarterly", 2026, 4),
			(datetime.date(2026, 10, 1), datetime.date(2026, 12, 31)),
		)
		self.assertEqual(
			periods.period_dates("Half-Yearly", 2026, 1),
			(datetime.date(2026, 1, 1), datetime.date(2026, 6, 30)),
		)
		self.assertEqual(
			periods.period_dates("Annual", 2026, 1), (datetime.date(2026, 1, 1), datetime.date(2026, 12, 31))
		)

	def test_titles_have_no_diacritics(self):
		harakat = set("ًٌٍَُِّْ")
		for ptype, count, _months, _prefix in [(k, *v) for k, v in periods.PERIOD_SPEC.items()]:
			for n in range(1, count + 1):
				title = periods.period_title(ptype, 2026, n)
				self.assertFalse(harakat.intersection(title), title)
		self.assertEqual(periods.period_title("Quarterly", 2026, 1), "الربع الأول 2026")
		self.assertEqual(periods.period_title("Monthly", 2026, 12), "ديسمبر 2026")

	def test_comparisons(self):
		self.assertEqual(periods.previous_period("Quarterly", 2026, 1), (2025, 4))
		self.assertEqual(periods.previous_period("Monthly", 2026, 5), (2026, 4))
		self.assertEqual(periods.same_period_last_year("Half-Yearly", 2026, 2), (2025, 2))

	def test_invalid_numbers(self):
		with self.assertRaises(ValueError):
			periods.period_name("Quarterly", 2026, 5)
		with self.assertRaises(ValueError):
			periods.period_name("Monthly", 2026, 0)


class IntegrationTestReportingPeriod(IntegrationTestCase):
	def test_create_period_sets_dates_and_title(self):
		doc = frappe.get_doc(
			{"doctype": "Reporting Period", "period_type": "Quarterly", "year": 2031, "period_number": 3}
		).insert()
		self.assertEqual(doc.name, "2031-Q3")
		self.assertEqual(str(doc.from_date), "2031-07-01")
		self.assertEqual(str(doc.to_date), "2031-09-30")
		self.assertEqual(doc.title, "الربع الثالث 2031")
		self.assertEqual(doc.status, "Open")

	def test_period_is_unique(self):
		data = {"doctype": "Reporting Period", "period_type": "Monthly", "year": 2031, "period_number": 1}
		frappe.get_doc(data).insert()
		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc(data).insert()

	def test_create_periods_for_year(self):
		created = create_periods_for_year(2032)
		self.assertEqual(len(created), 12 + 4 + 2 + 1)
		self.assertEqual(create_periods_for_year(2032), [])

	def test_close_and_reopen(self):
		name = create_periods_for_year(2033, ["Annual"])[0]
		set_period_status(name, "Closed", "end of year")
		doc = frappe.get_doc("Reporting Period", name)
		self.assertEqual(doc.status, "Closed")
		self.assertEqual(doc.closed_by, "Administrator")
		set_period_status(name, "Open")
		self.assertEqual(frappe.db.get_value("Reporting Period", name, "status"), "Open")

	def test_only_period_admins_can_close(self):
		name = create_periods_for_year(2034, ["Annual"])[0]
		user = ensure_test_user("loc_viewer@example.com", ["Executive Viewer"])
		with self.set_user(user):
			with self.assertRaises(frappe.PermissionError):
				set_period_status(name, "Closed")
