import frappe
from frappe.model.workflow import WorkflowPermissionError, WorkflowTransitionError, apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from loc_planning.activity_report import tasks as activity_tasks
from loc_planning.activity_report.deadlines import due_date
from loc_planning.activity_report.doctype.department_activity_submission.department_activity_submission import (
	set_review_comment,
)
from loc_planning.activity_report.report.department_activity_status.department_activity_status import (
	execute as status_report,
)
from loc_planning.loc_planning.doctype.loc_user_setup.loc_user_setup import apply_assignment
from loc_planning.loc_planning.doctype.reporting_period.reporting_period import set_period_status
from loc_planning.tests.utils import as_user, ensure_period, ensure_test_user
from loc_planning.utils.document_guard import PeriodClosedError

HR = "إدارة الموارد البشرية"
FIN = "إدارة العمليات المالية"
IT = "إدارة تقنية المعلومات"
COORD = "loc_hr_coordinator@example.com"
HEAD = "loc_hr_head@example.com"
FIN_COORD = "loc_fin_coordinator@example.com"
SD_USER = "loc_statistics@example.com"
SP_USER = "loc_planner@example.com"
YEAR = 2040
TRANSITION_ERRORS = (WorkflowPermissionError, WorkflowTransitionError)


def quarter(n):
	return ensure_period("Quarterly", YEAR, n)


def new_submission(department=HR, period=None, **kw):
	return frappe.get_doc(
		{
			"doctype": "Department Activity Submission",
			"department": department,
			"reporting_period": period or quarter(1),
			"activities": [
				{"activity": "نشاط تجريبي 1", "target": 10, "executed": 8},
				{"activity": "نشاط تجريبي 2", "target": 4, "executed": 4},
				{"activity": "نشاط بدون مستهدف"},
			],
			**kw,
		}
	).insert()


def notifications(user):
	return frappe.db.count("Notification Log", {"for_user": user})


class IntegrationTestActivitySubmissions(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for user in (COORD, HEAD):
			ensure_test_user(user, [])
			apply_assignment(user, "Department Coordinator", HR)
		ensure_test_user(FIN_COORD, [])
		apply_assignment(FIN_COORD, "Department Coordinator", FIN)
		ensure_test_user(SD_USER, ["Statistics & Data"])
		ensure_test_user(SP_USER, ["Strategic Planning"])
		frappe.db.set_value("LOC Department", HR, "head_user", HEAD)
		if not frappe.db.exists("Activity Indicator Template", HR):
			frappe.get_doc(
				{
					"doctype": "Activity Indicator Template",
					"department": HR,
					"indicators": [
						{"indicator": "عدد العاملين", "unit": "موظف"},
						{"indicator": "ساعات التدريب", "unit": "ساعة"},
					],
				}
			).insert(ignore_permissions=True)
		for n in range(1, 5):
			quarter(n)
		# remove leftovers of interrupted runs
		for name in frappe.get_all(
			"Department Activity Submission",
			filters={"reporting_period": ("like", f"{YEAR}-%")},
			pluck="name",
		):
			for child in ("Activity Submission Item", "Activity Submission Indicator"):
				frappe.db.delete(child, {"parent": name})
			frappe.db.delete("Department Activity Submission", {"name": name})
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()  # discard the test documents, keep only the reset below
		frappe.db.set_value("LOC Department", HR, "head_user", None)
		frappe.db.commit()
		super().tearDownClass()

	def test_rules_uniqueness_and_template(self):
		with as_user(COORD):
			doc = new_submission(period=quarter(2))
		self.assertEqual(doc.name, f"{HR} - {quarter(2)}")
		self.assertEqual([r.indicator for r in doc.indicators], ["عدد العاملين", "ساعات التدريب"])
		self.assertEqual(doc.activities[0].achievement_pct, 80)
		self.assertEqual(
			doc.overall_achievement, 90
		)  # average of 80 and 100; the row without target is ignored
		self.assertEqual(doc.department_head, HEAD)
		self.assertEqual(getdate(doc.due_date), getdate(due_date(HR, quarter(2))))
		with self.assertRaises(frappe.DuplicateEntryError):
			new_submission(period=quarter(2))
		with self.assertRaises(frappe.ValidationError):
			new_submission(period=ensure_period("Monthly", YEAR, 1))
		with self.assertRaises(frappe.ValidationError):
			new_submission(department="مكتب مبيعات طرابلس الكبرى", period=quarter(2))

	def test_full_workflow_with_mandatory_return_comment(self):
		with as_user(COORD):
			doc = new_submission(period=quarter(3))
			doc = apply_workflow(doc, "Submit to Manager")
			self.assertTrue(doc.submitted_on)
			# a coordinator who is not the department head cannot approve
			with self.assertRaises(TRANSITION_ERRORS):
				apply_workflow(doc, "Approve")
		with as_user(HEAD):
			doc = apply_workflow(doc, "Approve")
		self.assertEqual(doc.workflow_state, "Statistics Review")

		before = notifications(COORD)
		with as_user(SD_USER):
			with self.assertRaises(frappe.ValidationError):
				apply_workflow(doc, "Return for Revision")
			set_review_comment(doc.name, "يرجى استكمال المؤشرات")
			doc = apply_workflow(doc, "Return for Revision")
		self.assertEqual(doc.status, "Returned")
		self.assertGreater(notifications(COORD), before)
		self.assertTrue(
			frappe.db.exists(
				"Comment", {"reference_name": doc.name, "content": ("like", "%يرجى استكمال المؤشرات%")}
			)
		)

		with as_user(COORD):
			with self.assertRaises(frappe.PermissionError):
				set_review_comment(doc.name, "x")  # coordinators cannot return
			doc = apply_workflow(doc, "Submit to Manager")
		self.assertFalse(doc.review_comment)
		with as_user(HEAD):
			doc = apply_workflow(doc, "Approve")
		with as_user(SD_USER):
			doc = apply_workflow(doc, "Send for Approval")
			with self.assertRaises(TRANSITION_ERRORS):
				apply_workflow(doc, "Approve")
		before = notifications(COORD)
		with as_user(SP_USER):
			doc = apply_workflow(doc, "Approve")
		self.assertEqual((doc.docstatus, doc.status), (1, "Approved"))
		self.assertTrue(doc.approved_on)
		self.assertGreater(notifications(COORD), before)
		with as_user(SP_USER):
			doc = apply_workflow(doc, "Include in Report")
		self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "status"), "Included in Report")

	def test_departments_see_only_their_own_reports(self):
		with as_user(COORD):
			hr = new_submission(period=quarter(4))
		with as_user(FIN_COORD):
			fin = new_submission(department=FIN, period=quarter(4))
			visible = frappe.get_list(
				"Department Activity Submission", filters={"reporting_period": quarter(4)}, pluck="name"
			)
			self.assertEqual(visible, [fin.name])
			self.assertFalse(frappe.has_permission("Department Activity Submission", "read", hr.name))
			with self.assertRaises(frappe.PermissionError):
				new_submission(department=IT, period=quarter(4))
			_c, rows, *_ = status_report({"reporting_period": quarter(4)})
			self.assertEqual([r.department for r in rows], [FIN])
		_c, rows, _m, _chart, summary = status_report({"reporting_period": quarter(4)})
		by_dept = {r.department: r for r in rows}
		self.assertEqual(by_dept[HR].state, "Draft")
		self.assertEqual(by_dept[IT].state, "Not Submitted")
		self.assertEqual(summary[0]["value"], len(rows))

	def test_deadline_override_and_lateness(self):
		period = ensure_period("Quarterly", 2025, 4)  # a past quarter, so the report is already late
		frappe.db.set_value("LOC Department", IT, "report_deadline_days", 5)
		try:
			self.assertEqual(getdate(due_date(IT, period)), getdate("2026-01-05"))
			_c, rows, *_ = status_report({"reporting_period": period})
			it = next(r for r in rows if r.department == IT)
			self.assertGreater(it.days_late, 0)
		finally:
			frappe.db.set_value("LOC Department", IT, "report_deadline_days", 0)

	def test_reminders_before_and_after_due_date(self):
		period = quarter(1)
		due = due_date(HR, period)
		with self.change_settings(
			"LOC Planning Settings",
			{"reminder_days_before": 3, "reminder_repeat_days_after": 2, "max_overdue_reminders": 5},
		):
			before = notifications(COORD)
			sent = activity_tasks.remind_departments(add_days(due, -3))
			self.assertIn(COORD, sent.get(HR, []))
			self.assertIn(HEAD, sent.get(HR, []))
			self.assertGreater(notifications(COORD), before)
			self.assertNotIn(HR, activity_tasks.remind_departments(add_days(due, -2)))
			self.assertIn(HR, activity_tasks.remind_departments(add_days(due, 4)))

	def test_closed_period_locks_submissions(self):
		with as_user(COORD):
			doc = new_submission(period=quarter(1), difficulties="<p>نص تجريبي</p>")
		set_period_status(quarter(1), "Closed")
		try:
			doc.reload()
			doc.next_period_plan = "<p>تعديل</p>"
			with self.assertRaises(PeriodClosedError):
				doc.save()
		finally:
			set_period_status(quarter(1), "Open")
