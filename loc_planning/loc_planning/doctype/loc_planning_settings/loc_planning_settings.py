# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

DEFAULTS = {
	"official_company_name": "شركة ليبيا للنفط",
	"reporting_currency": "LYD",
	"report_font_family": "Fanan",
	"fallback_font_family": "Noto Naskh Arabic",
	"base_font_size": 12,
	"slow_execution_threshold": 40,
	"over_execution_threshold": 80,
	"activity_report_period_type": "Quarterly",
	"activity_report_deadline_days": 15,
	"reminder_days_before": 3,
	"reminder_repeat_days_after": 2,
	"max_overdue_reminders": 5,
	"station_data_due_day": 10,
	"certificate_validity_months": 12,
	"certificate_expiry_alert_days": 30,
	"enforce_period_lock": 1,
	"company_registration_series": "REG-.#####",
	"certificate_series": "CERT-.YYYY.-.#####",
	"certificate_signatory_title": "مدير إدارة الاستثمار والتخطيط الاستراتيجي",
	"certificate_issuer_name": "إدارة الاستثمار والتخطيط الاستراتيجي",
}


class LOCPlanningSettings(Document):
	def validate(self):
		slow, over = flt(self.slow_execution_threshold), flt(self.over_execution_threshold)
		if not (0 <= slow < over <= 100):
			frappe.throw(
				_("Budget thresholds must satisfy 0 ≤ slow execution < limit exceeded ≤ 100"),
				title=_("Invalid Thresholds"),
			)
		for field in (
			"activity_report_deadline_days",
			"reminder_days_before",
			"reminder_repeat_days_after",
			"max_overdue_reminders",
			"certificate_validity_months",
			"certificate_expiry_alert_days",
		):
			if cint(self.get(field)) < 0:
				frappe.throw(_("{0} cannot be negative").format(_(self.meta.get_label(field))))
		if self.station_data_due_day and not 1 <= cint(self.station_data_due_day) <= 28:
			frappe.throw(_("Station data due day must be between 1 and 28"))
		if self.base_font_size and not 8 <= cint(self.base_font_size) <= 20:
			frappe.throw(_("Base font size must be between 8 and 20"))


def get_settings():
	"""Cached settings document (invalidated automatically on save)."""
	return frappe.get_cached_doc("LOC Planning Settings")


def apply_defaults():
	"""Fill empty settings with defaults (used at install; never overwrites values)."""
	doc = frappe.get_single("LOC Planning Settings")
	changed = False
	for field, value in DEFAULTS.items():
		empty = (None, "") if field == "enforce_period_lock" else (None, "", 0)
		if doc.get(field) in empty:
			doc.set(field, value)
			changed = True
	if not doc.company:
		doc.company = frappe.defaults.get_global_default("company")
	if changed or doc.is_new():
		doc.flags.ignore_permissions = True
		doc.save()
