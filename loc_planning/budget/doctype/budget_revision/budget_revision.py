# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from loc_planning.budget.execution import get_position


class BudgetRevision(Document):
	def validate(self):
		budget = frappe.db.get_value(
			"Approved Budget", self.approved_budget, ["docstatus", "fiscal_year", "region"], as_dict=True
		)
		if not budget or budget.docstatus != 1:
			frappe.throw(_("Please select a submitted approved budget"))
		self.fiscal_year, self.region = budget.fiscal_year, budget.region
		if getdate(self.revision_date).year != int(self.fiscal_year):
			frappe.throw(_("The revision date must be in {0}").format(self.fiscal_year))
		for row in self.lines:
			if flt(row.amount) <= 0:
				frappe.throw(_("Row {0}: amount must be greater than zero").format(row.idx))
			if self.revision_type == "Transfer":
				if not (row.from_item and row.to_item):
					frappe.throw(
						_("Row {0}: a transfer needs both a source and a destination item").format(row.idx)
					)
				if row.from_item == row.to_item:
					frappe.throw(_("Row {0}: source and destination items are the same").format(row.idx))
			elif self.revision_type == "Increase":
				if not row.to_item or row.from_item:
					frappe.throw(_("Row {0}: an increase needs a destination item only").format(row.idx))
			elif not row.from_item or row.to_item:
				frappe.throw(_("Row {0}: a decrease needs a source item only").format(row.idx))

	def before_submit(self):
		"""A source item may not be reduced below what is already committed or spent."""
		taken = {}
		for row in self.lines:
			if row.from_item:
				taken[row.from_item] = taken.get(row.from_item, 0) + flt(row.amount)
		if not taken:
			return
		position = {r.budget_item: r for r in get_position(self.fiscal_year, region=self.region)}
		for item, amount in taken.items():
			r = position.get(item)
			available = flt(r.revised - r.commitments - r.executed) if r else 0
			if flt(amount) > flt(available, 2) + 0.005:
				frappe.throw(
					_("Item {0}: only {1} is available for reduction").format(
						frappe.bold(item),
						frappe.format(available, {"fieldtype": "Currency", "options": "LYD"}),
					),
					title=_("Insufficient Balance"),
				)

	def on_submit(self):
		frappe.get_doc("Approved Budget", self.approved_budget).refresh_revised_amounts()

	def on_cancel(self):
		frappe.get_doc("Approved Budget", self.approved_budget).refresh_revised_amounts()
