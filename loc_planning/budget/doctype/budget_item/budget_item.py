# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class BudgetItem(Document):
	def validate(self):
		self.item_name = " ".join((self.item_name or "").split())
		if self.execution_source == "General Ledger":
			if not self.accounts:
				frappe.throw(_("Add at least one GL account when the source is the General Ledger"))
			seen = set()
			for row in self.accounts:
				account = frappe.db.get_value(
					"Account", row.account, ["company", "is_group", "root_type"], as_dict=True
				)
				if account.company != self.company:
					frappe.throw(
						_("Row {0}: account {1} belongs to another company").format(row.idx, row.account)
					)
				if account.root_type not in ("Expense", "Asset"):
					frappe.throw(
						_("Row {0}: account {1} must be an expense or asset account").format(
							row.idx, row.account
						)
					)
				if (
					row.cost_center
					and frappe.db.get_value("Cost Center", row.cost_center, "company") != self.company
				):
					frappe.throw(
						_("Row {0}: cost center {1} belongs to another company").format(
							row.idx, row.cost_center
						)
					)
				key = (row.account, row.cost_center, row.region)
				if key in seen:
					frappe.throw(_("Row {0}: duplicate account mapping").format(row.idx))
				seen.add(key)
			self.validate_no_overlap()
		else:
			self.set("accounts", [])

	def validate_no_overlap(self):
		"""The same account / cost center / region may feed only one item, otherwise the
		amount would be counted twice."""
		for row in self.accounts:
			other = frappe.db.get_value(
				"Budget Item Account",
				{
					"parenttype": "Budget Item",
					"parent": ("!=", self.name or ""),
					"account": row.account,
					"cost_center": row.cost_center or ("is", "not set"),
					"region": row.region,
				},
				"parent",
			)
			if other:
				frappe.throw(
					_("Row {0}: account {1} is already mapped to item {2}").format(
						row.idx, row.account, frappe.bold(other)
					)
				)
