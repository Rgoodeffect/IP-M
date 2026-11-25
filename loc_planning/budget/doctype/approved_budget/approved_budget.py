# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class ApprovedBudget(Document):
	def validate(self):
		if not 2000 <= int(self.fiscal_year or 0) <= 2100:
			frappe.throw(_("Invalid year {0}").format(self.fiscal_year))
		seen = set()
		for row in self.items:
			if row.budget_item in seen:
				frappe.throw(
					_("Row {0}: item {1} is entered twice").format(row.idx, frappe.bold(row.budget_item))
				)
			seen.add(row.budget_item)
			if self.docstatus == 0:
				row.revised_amount = row.approved_amount
		self.total_approved = sum(flt(r.approved_amount) for r in self.items)
		if self.docstatus == 0:
			self.total_revised = self.total_approved

	def before_submit(self):
		other = frappe.db.get_value(
			"Approved Budget",
			{
				"fiscal_year": self.fiscal_year,
				"region": self.region,
				"docstatus": 1,
				"name": ("!=", self.name),
			},
		)
		if other:
			frappe.throw(
				_(
					"An approved budget for {0} / {1} already exists: {2}. Use a budget revision instead."
				).format(self.fiscal_year, self.region, frappe.bold(other))
			)

	def before_cancel(self):
		revisions = frappe.get_all(
			"Budget Revision", filters={"approved_budget": self.name, "docstatus": 1}, pluck="name"
		)
		if revisions:
			frappe.throw(_("Cancel the revisions of this budget first: {0}").format(", ".join(revisions)))

	def refresh_revised_amounts(self):
		"""Recompute 'amount after revisions' from the submitted revisions."""
		delta = {}
		for line in frappe.get_all(
			"Budget Revision Line",
			filters={
				"parenttype": "Budget Revision",
				"parent": (
					"in",
					frappe.get_all(
						"Budget Revision", {"approved_budget": self.name, "docstatus": 1}, pluck="name"
					)
					or [""],
				),
			},
			fields=["from_item", "to_item", "amount"],
		):
			if line.from_item:
				delta[line.from_item] = delta.get(line.from_item, 0) - flt(line.amount)
			if line.to_item:
				delta[line.to_item] = delta.get(line.to_item, 0) + flt(line.amount)
		total = 0
		for row in self.items:
			revised = flt(row.approved_amount) + delta.pop(row.budget_item, 0)
			row.db_set("revised_amount", revised, update_modified=False)
			total += revised
		self.db_set("total_revised", total + sum(delta.values()), update_modified=False)
		return delta  # items added by revisions that are not lines of this budget
