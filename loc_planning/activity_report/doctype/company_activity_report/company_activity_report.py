# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, strip_html

from loc_planning.activity_report import sources
from loc_planning.utils.print_utils import arabic_output

TEXT_SOURCES = ("Editorial Text", "Difficulties")


class CompanyActivityReport(Document):
	def before_insert(self):
		if not self.sections:
			self.load_template()

	def validate(self):
		period = frappe.db.get_value(
			"Reporting Period", self.reporting_period, ["period_type", "title"], as_dict=True
		)
		with arabic_output():
			self.report_type = _(period.period_type)
		if self.scope != "Region":
			self.region = None
		if not self.report_title:
			title = frappe.db.get_value("Activity Report Template", self.template, "report_title") or _(
				"Activity Report"
			)
			self.report_title = f"{title} - {period.title}"
		if self.docstatus == 0:
			self.update_text_readiness()
			self.update_readiness()
		self.sync_status()
		self.validate_return_comment()

	# ------------------------------------------------------------------ template
	def load_template(self):
		template = frappe.get_doc("Activity Report Template", self.template)
		for s in sorted(template.sections, key=lambda s: s.section_order):
			self.append(
				"sections",
				{
					"section_order": s.section_order,
					"title": s.title,
					"data_source": s.data_source,
					"source_department": s.source_department,
					"include": s.include,
					"readiness": "Not Refreshed",
				},
			)

	# ------------------------------------------------------------------ data
	@frappe.whitelist()
	def refresh_data(self):
		"""Re-read every included section and store a snapshot of its figures."""
		self.check_permission("write")
		if self.docstatus != 0:
			frappe.throw(_("The report is approved; its data can no longer be refreshed"))
		ctx = sources.build_context(self)
		now = now_datetime()
		for section in self.sections:
			if not section.include:
				continue
			# labels stored in the snapshot are Arabic whatever the user's language
			with arabic_output():
				snapshot, readiness, note = sources.compute(section.data_source, ctx, section)
			section.snapshot_json = json.dumps(
				{
					"period": ctx.period_title,
					"previous": ctx.prev.title,
					"last_year": ctx.last_year.title,
					**snapshot,
				},
				ensure_ascii=False,
				default=str,
			)
			section.snapshot_at = now
			section.readiness = readiness
			section.readiness_note = note
		self.data_refreshed_on = now
		self.save()
		return self.readiness_pct

	def update_text_readiness(self):
		"""Editorial sections become ready as soon as their text is written."""
		for section in self.sections:
			if section.include and section.data_source in TEXT_SOURCES and section.snapshot_json:
				has_text = bool(strip_html(section.editorial_text or "").strip())
				section.readiness = "Ready" if has_text else "Incomplete"
				section.readiness_note = None if has_text else _("Write the text of this section")

	def update_readiness(self):
		included = [s for s in self.sections if s.include]
		ready = [s for s in included if s.readiness == "Ready"]
		self.readiness_pct = flt(len(ready) / len(included) * 100, 1) if included else 0
		self.incomplete_sections = "\n".join(
			f"{s.section_order}. {s.title}" + (f": {s.readiness_note}" if s.readiness_note else "")
			for s in included
			if s.readiness != "Ready"
		)

	# ------------------------------------------------------------------ workflow
	def sync_status(self):
		state = self.get("workflow_state") or "Draft"
		before = self.get_doc_before_save()
		previous = before.get("workflow_state") if before else None
		self.status = state
		if state == "Director Review" and previous != state:
			if not self.data_refreshed_on:
				frappe.throw(_("Refresh the report data before sending it for review"))
			if flt(self.readiness_pct) < 100:
				frappe.throw(
					_("The following sections are not ready:")
					+ "<br>"
					+ (self.incomplete_sections or "").replace("\n", "<br>"),
					title=_("Report Not Ready"),
				)
		if state == "Draft" and previous in ("Director Review", "General Manager Approval"):
			self.flags.returned = True

	def validate_return_comment(self):
		if self.flags.returned and not (self.review_comment or "").strip():
			frappe.throw(
				_(
					"Please write the review comment explaining what must be corrected before returning the report."
				),
				title=_("Review Comment Required"),
			)

	def on_update(self):
		if self.flags.returned:
			self.add_comment(
				"Comment",
				_("Returned for revision: {0}").format(frappe.utils.escape_html(self.review_comment or "")),
			)

	def before_submit(self):
		self.approved_by = frappe.session.user
		self.approved_on = now_datetime()
		self.status = "Approved"

	def on_submit(self):
		for name in self.included_submissions():
			frappe.db.set_value(
				"Department Activity Submission",
				name,
				{
					"workflow_state": "Included in Report",
					"status": "Included in Report",
					"company_activity_report": self.name,
				},
				update_modified=False,
			)

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		for name in frappe.get_all(
			"Department Activity Submission", filters={"company_activity_report": self.name}, pluck="name"
		):
			frappe.db.set_value(
				"Department Activity Submission",
				name,
				{"workflow_state": "Approved", "status": "Approved", "company_activity_report": None},
				update_modified=False,
			)

	def included_submissions(self):
		if not any(
			s.include and s.data_source in ("Department Activities", "Department Indicators", "Difficulties")
			for s in self.sections
		):
			return []
		filters = {"reporting_period": self.reporting_period, "docstatus": 1, "workflow_state": "Approved"}
		names = frappe.get_all("Department Activity Submission", filters=filters, fields=["name", "region"])
		return [n.name for n in names if not self.region or n.region == self.region]

	# ------------------------------------------------------------------ output
	def get_sections(self):
		"""Included sections with their parsed snapshots, in order (used by print and Word)."""
		out = []
		for s in sorted(self.sections, key=lambda s: s.section_order):
			if not s.include:
				continue
			data = json.loads(s.snapshot_json) if s.snapshot_json else {}
			out.append(
				frappe._dict(
					section=s,
					title=s.title,
					source=s.data_source,
					data=frappe._dict(data),
					text=s.editorial_text,
				)
			)
		return out


@frappe.whitelist()
def get_default_template():
	return frappe.db.get_value("Activity Report Template", {"is_default": 1}, "name")
