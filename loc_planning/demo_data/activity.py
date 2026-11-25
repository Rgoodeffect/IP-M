"""Demo department activity submissions (texts start with "نشاط تجريبي")."""

import frappe
from frappe.model.workflow import apply_workflow

from loc_planning.activity_report.deadlines import report_period_type, required_departments
from loc_planning.loc_planning.doctype.reporting_period.reporting_period import create_periods_for_year
from loc_planning.utils.periods import period_name

FLOW = ["Submit to Manager", "Approve", "Send for Approval", "Approve"]


def load(year=2026, number=3):
	frappe.only_for("System Manager")
	create_periods_for_year(year, [report_period_type()])
	period = period_name(report_period_type(), year, number)
	for i, dept in enumerate(required_departments()):
		if i % 4 == 3 or frappe.db.exists(
			"Department Activity Submission", {"department": dept.name, "reporting_period": period}
		):
			continue  # leave some departments without a report
		doc = frappe.get_doc(
			{
				"doctype": "Department Activity Submission",
				"department": dept.name,
				"reporting_period": period,
				"activities": [
					{"activity": f"نشاط تجريبي {n}", "target": 10, "executed": (i + n) % 11}
					for n in range(1, 4)
				],
				"difficulties": "<p>صعوبات تجريبية</p>",
				"next_period_plan": "<p>خطة تجريبية</p>",
			}
		).insert()
		for action in FLOW[: i % 5]:
			doc = apply_workflow(doc, action)
	frappe.db.commit()
	return period
