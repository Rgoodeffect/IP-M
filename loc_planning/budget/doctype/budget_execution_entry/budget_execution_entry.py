# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from loc_planning.budget.execution import get_position
from loc_planning.loc_planning.doctype.reporting_period.reporting_period import get_period_for_date


class BudgetExecutionEntry(Document):
	def validate(self):
		item = frappe.db.get_value(
			"Budget Item",
			self.budget_item,
			["execution_source", "owner_department", "is_active"],
			as_dict=True,
		)
		if not item.is_active and self.is_new():
			frappe.throw(_("Item {0} is not active").format(frappe.bold(self.budget_item)))
		if self.entry_type == "Actual Expense" and item.execution_source == "General Ledger":
			frappe.throw(
				_(
					"The executed amount of item {0} is taken from the General Ledger. Only commitments can be entered here."
				).format(frappe.bold(self.budget_item))
			)
		if flt(self.amount) <= 0:
			frappe.throw(_("Amount must be greater than zero"))
		if not self.department:
			self.department = item.owner_department
		self.fiscal_year = getdate(self.posting_date).year
		# ties the entry to its month so that closing the month locks it
		self.reporting_period = get_period_for_date("Monthly", self.posting_date)

	def on_submit(self):
		self.warn_if_over_budget()

	def warn_if_over_budget(self):
		rows = get_position(self.fiscal_year, region=self.region, item=self.budget_item)
		if rows and rows[0].remaining < 0:
			frappe.msgprint(
				_("Item {0} has exceeded its approved amount for {1} by {2}").format(
					frappe.bold(self.budget_item),
					self.region,
					frappe.format(-rows[0].remaining, {"fieldtype": "Currency", "options": "LYD"}),
				),
				indicator="orange",
				title=_("Budget Exceeded"),
			)
