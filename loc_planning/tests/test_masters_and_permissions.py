import frappe
from frappe.tests import IntegrationTestCase

from loc_planning.install import seed_master_data
from loc_planning.loc_planning.doctype.loc_department.loc_department import get_descendants
from loc_planning.loc_planning.doctype.loc_user_setup.loc_user_setup import apply_assignment
from loc_planning.tests.utils import (
	TEST_DOCTYPE,
	drop_guard_test_doctype,
	ensure_guard_test_doctype,
	ensure_period,
	ensure_test_user,
)

ROOT = "شركة ليبيا للنفط"
HR = "إدارة الموارد البشرية"
FIN = "إدارة العمليات المالية"
INVEST_DEPT = "إدارة الاستثمار والتخطيط الاستراتيجي"
TRIPOLI = "مكتب مبيعات طرابلس الكبرى"
MISRATA = "مكتب مبيعات المنطقة الوسطى مصراتة"


class IntegrationTestMasterData(IntegrationTestCase):
	def test_seed_is_idempotent(self):
		counts = {dt: frappe.db.count(dt) for dt in ("LOC Department", "LOC Region", "Fuel Product")}
		seed_master_data()
		seed_master_data()
		for dt, count in counts.items():
			self.assertEqual(frappe.db.count(dt), count, dt)

	def test_initial_structure(self):
		west = {"region": "الغربية"}  # other tests add departments in their own test region
		self.assertEqual(frappe.db.count("LOC Department", {**west, "department_type": "Department"}), 10)
		self.assertEqual(frappe.db.count("LOC Department", {**west, "department_type": "Office"}), 4)
		self.assertEqual(frappe.db.count("LOC Department", {**west, "department_type": "Sales Office"}), 5)
		sections = get_descendants(INVEST_DEPT, include_self=False)
		self.assertEqual(len(sections), 3)
		self.assertIn("قسم الإحصاء والبيانات", sections)
		self.assertEqual(
			frappe.db.get_value("LOC Department", "النقل", "parent_loc_department"), "إدارة عمليات التشغيل"
		)
		self.assertEqual(frappe.db.get_value("Fuel Product", "غاز مسال", "uom"), "Cylinder")
		self.assertEqual(frappe.db.get_value("Fuel Product", "بنزين", "uom"), "Litre")

	def test_same_department_name_in_other_region_gets_suffix(self):
		doc = frappe.get_doc(
			{
				"doctype": "LOC Department",
				"department_name": HR,
				"department_type": "Department",
				"region": "الشرقية",
			}
		).insert()
		self.assertEqual(doc.name, f"{HR} - E")
		self.assertEqual(doc.parent_loc_department, ROOT)

	def test_parent_must_be_group(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "LOC Department",
					"department_name": "وحدة تجريبية",
					"department_type": "Unit",
					"parent_loc_department": FIN,
				}
			).insert()

	def test_settings_threshold_validation(self):
		settings = frappe.get_single("LOC Planning Settings")
		self.assertEqual(settings.slow_execution_threshold, 40)
		self.assertEqual(settings.over_execution_threshold, 80)
		settings.slow_execution_threshold = 90
		with self.assertRaises(frappe.ValidationError):
			settings.save()


class IntegrationTestRecordIsolation(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_guard_test_doctype()
		cls.period = ensure_period("Monthly", 2036, 1)
		frappe.db.commit()

	def _record(self, dept):
		return frappe.get_doc(
			{"doctype": TEST_DOCTYPE, "reporting_period": self.period, "loc_department": dept}
		).insert(ignore_permissions=True)

	def test_department_coordinator_sees_only_own_department(self):
		user = ensure_test_user("loc_hr_coord@example.com", [])
		apply_assignment(user, "Department Coordinator", HR)
		own, other = self._record(HR), self._record(FIN)

		with self.set_user(user):
			visible = frappe.get_list(
				TEST_DOCTYPE, pluck="name", filters={"name": ("in", [own.name, other.name])}
			)
			self.assertEqual(visible, [own.name])
			self.assertTrue(frappe.has_permission(TEST_DOCTYPE, "read", own.name))
			self.assertFalse(frappe.has_permission(TEST_DOCTYPE, "read", other.name))
			depts = frappe.get_list("LOC Department", pluck="name")
			self.assertEqual(depts, [HR])

	def test_sales_office_sees_only_own_office(self):
		user = ensure_test_user("loc_tripoli@example.com", [])
		apply_assignment(user, "Sales Office User", TRIPOLI)
		own, other = self._record(TRIPOLI), self._record(MISRATA)

		with self.set_user(user):
			visible = frappe.get_list(
				TEST_DOCTYPE, pluck="name", filters={"name": ("in", [own.name, other.name])}
			)
			self.assertEqual(visible, [own.name])
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc({"doctype": TEST_DOCTYPE, "loc_department": MISRATA}).insert()

	def test_director_restricted_to_parent_sees_sections(self):
		user = ensure_test_user("loc_invest_head@example.com", [])
		apply_assignment(user, "Department Coordinator", INVEST_DEPT, apply_to_descendants=1)
		section = self._record("قسم الاستثمار")
		with self.set_user(user):
			self.assertTrue(frappe.has_permission(TEST_DOCTYPE, "read", section.name))

	def test_apply_assignment_is_idempotent(self):
		user = ensure_test_user("loc_fin_coord@example.com", [])
		apply_assignment(user, "Department Coordinator", FIN)
		apply_assignment(user, "Department Coordinator", FIN)
		self.assertEqual(frappe.db.count("User Permission", {"user": user, "allow": "LOC Department"}), 1)
		self.assertIn("Department Coordinator", frappe.get_roles(user))

	def test_user_setup_requires_department_for_restricted_roles(self):
		setup = frappe.get_single("LOC User Setup")
		setup.set("assignments", [])
		setup.append("assignments", {"user": "Administrator", "role": "Sales Office User"})
		with self.assertRaises(frappe.ValidationError):
			setup.save()
		setup.assignments[0].loc_department = HR  # not a sales office
		with self.assertRaises(frappe.ValidationError):
			setup.save()


def tearDownModule():
	drop_guard_test_doctype()
