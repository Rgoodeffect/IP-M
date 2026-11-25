# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import frappe
import frappe.model.workflow
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_url_to_form, now_datetime

from loc_planning.activity_report.deadlines import days_late, due_date, report_period_type
from loc_planning.constants import ROLE_DEPT_COORDINATOR, ROLE_STATISTICS, ROLE_STRATEGIC_PLANNING
from loc_planning.utils.notify import department_users, notify, role_users

# workflow state -> status while the document is a draft
DRAFT_STATES = ("Draft", "Manager Review", "Statistics Review", "Planning Approval", "Returned")
# who has to act next, per state (used for notifications)
NEXT_ACTOR = {
	"Statistics Review": ROLE_STATISTICS,
	"Planning Approval": ROLE_STRATEGIC_PLANNING,
}


class DepartmentActivitySubmission(Document):
	def autoname(self):
		self.name = f"{self.department} - {self.reporting_period}"

	def before_insert(self):
		existing = frappe.db.get_value(
			"Department Activity Submission",
			{"department": self.department, "reporting_period": self.reporting_period, "docstatus": ("<", 2)},
		)
		if existing:
			frappe.throw(
				_("The activity report of {0} for {1} already exists: {2}").format(
					frappe.bold(self.department), frappe.bold(self.reporting_period), existing
				),
				frappe.DuplicateEntryError,
			)
		if not self.indicators:
			self.load_indicator_template()

	def validate(self):
		self.validate_department_and_period()
		self.due_date = due_date(self.department, self.reporting_period)
		self.set_achievements()
		self.sync_status()
		self.validate_review_comment()

	def validate_department_and_period(self):
		if not frappe.db.get_value("LOC Department", self.department, "requires_activity_report"):
			frappe.throw(
				_("{0} is not required to submit an activity report").format(frappe.bold(self.department))
			)
		period_type = frappe.db.get_value("Reporting Period", self.reporting_period, "period_type")
		expected = report_period_type()
		if period_type != expected:
			frappe.throw(_("Please select a period of type {0}").format(_(expected)))

	def set_achievements(self):
		pcts = []
		for row in self.activities:
			row.achievement_pct = flt(flt(row.executed) / flt(row.target) * 100, 2) if flt(row.target) else 0
			if flt(row.target):
				pcts.append(row.achievement_pct)
		self.overall_achievement = flt(sum(pcts) / len(pcts), 2) if pcts else 0

	def sync_status(self):
		state = self.get("workflow_state") or "Draft"
		if self.docstatus == 0 or state in ("Approved", "Included in Report"):
			self.status = state
		before = self.get_doc_before_save()
		previous = before.get("workflow_state") if before else None
		if state == "Manager Review" and previous != state:
			if not self.submitted_on:
				self.submitted_on = now_datetime()
				self.days_late = days_late(self.due_date, self.submitted_on)
			if previous == "Returned":
				# the comment was answered; it stays in the timeline, the next return needs a new one
				self.review_comment = None
		if state == "Approved" and previous != state:
			self.approved_on = now_datetime()

	def validate_review_comment(self):
		before = self.get_doc_before_save()
		if self.get("workflow_state") == "Returned" and before and before.get("workflow_state") != "Returned":
			if not (self.review_comment or "").strip():
				frappe.throw(
					_(
						"Please write the review comment explaining what must be corrected before returning the report."
					),
					title=_("Review Comment Required"),
				)

	def on_update(self):
		self.notify_transition()

	def on_submit(self):
		self.db_set("status", self.workflow_state or "Approved")

	def before_update_after_submit(self):
		self.sync_status()

	def on_update_after_submit(self):
		self.notify_transition()

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	def notify_transition(self):
		before = self.get_doc_before_save()
		state = self.get("workflow_state")
		if not before or before.get("workflow_state") == state:
			return
		link = f"<a href='{get_url_to_form(self.doctype, self.name)}'>{self.name}</a>"
		coordinators = [*department_users(self.department, ROLE_DEPT_COORDINATOR), self.owner]
		if state == "Returned":
			self.add_comment(
				"Comment",
				_("Returned for revision: {0}").format(frappe.utils.escape_html(self.review_comment or "")),
			)
			notify(
				coordinators,
				_("Activity report {0} was returned for revision").format(self.name),
				f"{link}<br>{frappe.utils.escape_html(self.review_comment or '')}",
				self.doctype,
				self.name,
			)
		elif state == "Manager Review" and self.department_head:
			notify(
				[self.department_head],
				_("Activity report {0} awaits your review").format(self.name),
				link,
				self.doctype,
				self.name,
			)
		elif state in NEXT_ACTOR:
			notify(
				role_users(NEXT_ACTOR[state]),
				_("Activity report {0} awaits your review").format(self.name),
				link,
				self.doctype,
				self.name,
			)
		elif state == "Approved":
			notify(
				[*coordinators, *([self.department_head] if self.department_head else [])],
				_("Activity report {0} was approved").format(self.name),
				link,
				self.doctype,
				self.name,
			)

	def load_indicator_template(self):
		if not frappe.db.exists("Activity Indicator Template", self.department):
			return
		for row in frappe.get_doc("Activity Indicator Template", self.department).indicators:
			self.append("indicators", {"indicator": row.indicator, "unit": row.unit})


@frappe.whitelist(methods=["POST"])
def set_review_comment(name: str, comment: str):
	"""Store the review comment before a "Return for Revision" action (the workflow action
	reloads the document from the database)."""
	doc = frappe.get_doc("Department Activity Submission", name)
	doc.check_permission("read")
	if not (comment or "").strip():
		frappe.throw(_("Please write the review comment"))
	transitions = frappe.model.workflow.get_transitions(doc)
	if not any(t.action == "Return for Revision" for t in transitions):
		frappe.throw(_("You cannot return this report at its current stage"), frappe.PermissionError)
	doc.db_set("review_comment", comment.strip())
	return True


@frappe.whitelist()
def get_template_indicators(department: str):
	frappe.has_permission("LOC Department", "read", department, throw=True)
	if not frappe.db.exists("Activity Indicator Template", department):
		return []
	return [
		{"indicator": r.indicator, "unit": r.unit}
		for r in frappe.get_doc("Activity Indicator Template", department).indicators
	]
