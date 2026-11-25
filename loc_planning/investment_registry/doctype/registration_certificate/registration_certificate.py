# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import getdate, today

from loc_planning.investment_registry.utils import (
	compute_expiry,
	expiry_state,
	new_verification_code,
	refresh_company_certificate,
	settings,
	throw_if_not_allowed_to_issue,
)

REQUEST_SERIES = "CREQ-.YYYY.-.#####"

# Workflow state → certificate status while the document is a draft
DRAFT_STATUS = {"Rejected": "Rejected"}


class RegistrationCertificate(Document):
	def autoname(self):
		# Migrated certificates keep their original number as the document name.
		if self.certificate_no and self.certificate_no.strip():
			self.name = self.certificate_no.strip()
		else:
			self.name = make_autoname(REQUEST_SERIES, doc=self)

	def before_insert(self):
		if not self.verification_code:
			self.verification_code = new_verification_code()

	def validate(self):
		if self.docstatus == 0:
			self.status = DRAFT_STATUS.get(self.get("workflow_state"), "Draft")
		self.validate_renewal()
		self.validate_dates()
		if self.docstatus == 0 and self.request_type == "New" and not self.flags.is_migration:
			self.validate_no_active_certificate()

	def validate_renewal(self):
		if self.request_type != "Renewal":
			self.renewal_of = None
			return
		if not self.renewal_of:
			frappe.throw(_("Please select the certificate being renewed"))
		old = frappe.db.get_value(
			"Registration Certificate", self.renewal_of, ["registered_company", "docstatus"], as_dict=True
		)
		if not old or old.docstatus != 1:
			frappe.throw(_("Only an issued certificate can be renewed"))
		if old.registered_company != self.registered_company:
			frappe.throw(_("The renewed certificate belongs to another company"))

	def validate_dates(self):
		if self.issue_date and self.expiry_date and getdate(self.expiry_date) < getdate(self.issue_date):
			frappe.throw(_("Expiry date cannot be before the issue date"))

	def validate_no_active_certificate(self):
		active = frappe.get_all(
			"Registration Certificate",
			filters={
				"registered_company": self.registered_company,
				"docstatus": 1,
				"status": "Issued",
				"expiry_date": (">=", today()),
				"name": ("!=", self.name or ""),
			},
			pluck="name",
			limit=1,
		)
		if active:
			frappe.throw(
				_("Company already has a valid certificate {0}. Use a renewal request instead.").format(
					frappe.bold(active[0])
				)
			)

	def before_submit(self):
		company = frappe.get_doc("Registered Company", self.registered_company)
		throw_if_not_allowed_to_issue(company)
		missing = company.get_missing_documents()
		if missing:
			frappe.throw(
				_("The following required documents are missing or expired: {0}").format(
					", ".join(frappe.bold(m) for m in missing)
				),
				title=_("Missing Documents"),
			)
		if not self.issue_date:
			self.issue_date = today()
		if not self.expiry_date:
			self.expiry_date = compute_expiry(self.issue_date)
		self.validate_dates()
		if not self.certificate_no:
			self.certificate_no = make_autoname(
				settings().certificate_series or "CERT-.YYYY.-.#####", doc=self
			)
		self.status = "Issued"

	def on_submit(self):
		if self.renewal_of:
			frappe.db.set_value("Registration Certificate", self.renewal_of, "status", "Superseded")
		refresh_company_certificate(self.registered_company)
		if settings().auto_create_supplier:
			link_supplier(self.registered_company)

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		if self.renewal_of:
			old_expiry = frappe.db.get_value("Registration Certificate", self.renewal_of, "expiry_date")
			restored = "Expired" if expiry_state(old_expiry) == "Expired" else "Issued"
			frappe.db.set_value("Registration Certificate", self.renewal_of, "status", restored)
		refresh_company_certificate(self.registered_company)

	def before_update_after_submit(self):
		if self.status == "Draft":
			self.status = "Issued"


def link_supplier(company_name):
	"""Create (or link) an ERPNext Supplier for the registered company."""
	company = frappe.get_doc("Registered Company", company_name)
	if company.supplier and frappe.db.exists("Supplier", company.supplier):
		return company.supplier
	supplier = frappe.db.get_value("Supplier", {"supplier_name": company.company_name}, "name")
	if not supplier and company.tax_id:
		supplier = frappe.db.get_value("Supplier", {"tax_id": company.tax_id}, "name")
	if not supplier:
		group = settings().supplier_group or frappe.db.get_single_value("Buying Settings", "supplier_group")
		doc = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": company.company_name,
				"supplier_group": group or frappe.db.get_value("Supplier Group", {"is_group": 0}, "name"),
				"tax_id": company.tax_id,
				"country": "Libya" if frappe.db.exists("Country", "Libya") else None,
			}
		)
		doc.insert(ignore_permissions=True)
		supplier = doc.name
	frappe.db.set_value("Registered Company", company.name, "supplier", supplier, update_modified=False)
	return supplier
