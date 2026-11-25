# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname

from loc_planning.investment_registry.utils import expiry_state, settings
from loc_planning.utils.arabic import normalize_identifier, normalize_name

IDENTIFIER_FIELDS = ("tax_id", "commercial_register_no")


class RegisteredCompany(Document):
	def autoname(self):
		if self.registration_no and self.registration_no.strip():
			self.name = self.registration_no.strip()
		else:
			self.name = make_autoname(settings().company_registration_series or "REG-.#####", doc=self)
		self.registration_no = self.name

	def validate(self):
		for field in ("company_name", "company_name_en", *IDENTIFIER_FIELDS, "chamber_of_commerce_no"):
			if self.get(field):
				self.set(field, " ".join(str(self.get(field)).split()))
		if self.status in ("Suspended", "Blacklisted") and not (self.status_reason or "").strip():
			frappe.throw(_("Please enter the reason for the status {0}").format(_(self.status)))
		self.validate_unique_identifiers()
		self.warn_similar_names()
		self.update_document_statuses()

	def validate_unique_identifiers(self):
		for field in IDENTIFIER_FIELDS:
			duplicate = find_by_identifier(field, self.get(field), exclude=self.name)
			if duplicate:
				frappe.throw(
					_("{0} {1} is already registered for company {2}").format(
						_(self.meta.get_label(field)), frappe.bold(self.get(field)), frappe.bold(duplicate)
					),
					frappe.DuplicateEntryError,
				)

	def warn_similar_names(self):
		if not self.is_new() and not self.has_value_changed("company_name"):
			return
		similar = find_similar_names(self.company_name, exclude=self.name)
		if similar:
			frappe.msgprint(
				_("A company with a similar name is already registered: {0}").format(
					", ".join(frappe.bold(s) for s in similar[:5])
				),
				indicator="orange",
				alert=True,
			)

	def update_document_statuses(self):
		for row in self.documents:
			has_expiry = frappe.get_cached_value("Company Document Type", row.document_type, "has_expiry")
			row.document_status = expiry_state(row.expiry_date) if row.expiry_date else "No Expiry"
			if has_expiry and not row.expiry_date:
				row.document_status = "No Expiry"

	def get_missing_documents(self):
		"""Mandatory document types that are absent or expired."""
		mandatory = frappe.get_all(
			"Company Document Type", filters={"is_mandatory": 1, "is_active": 1}, pluck="name"
		)
		valid = {
			row.document_type
			for row in self.documents
			if row.attachment and expiry_state(row.expiry_date) != "Expired"
		}
		return [d for d in mandatory if d not in valid]


def find_by_identifier(field, value, exclude=None):
	key = normalize_identifier(value)
	if not key:
		return None
	filters = {field: ("is", "set")}
	if exclude:
		filters["name"] = ("!=", exclude)
	for row in frappe.get_all("Registered Company", filters=filters, fields=["name", field]):
		if normalize_identifier(row.get(field)) == key:
			return row.name
	return None


def find_similar_names(company_name, exclude=None):
	key = normalize_name(company_name)
	if not key:
		return []
	filters = {"name": ("!=", exclude)} if exclude else {}
	return [
		row.name
		for row in frappe.get_all("Registered Company", filters=filters, fields=["name", "company_name"])
		if normalize_name(row.company_name) == key
	]
