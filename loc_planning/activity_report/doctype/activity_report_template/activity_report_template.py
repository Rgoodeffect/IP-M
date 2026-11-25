# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ActivityReportTemplate(Document):
	def validate(self):
		orders = [s.section_order for s in self.sections]
		if len(orders) != len(set(orders)):
			frappe.throw(_("Section order numbers must be unique"))
		for s in self.sections:
			if s.data_source == "Department Indicators" and not s.source_department:
				frappe.throw(_("Row {0}: select the source department").format(s.idx))

	def on_update(self):
		if self.is_default:
			frappe.db.set_value(
				"Activity Report Template", {"name": ("!=", self.name), "is_default": 1}, "is_default", 0
			)
