"""Investment Registry helpers: certificate status, verification, QR code."""

import base64
import io
import secrets

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, date_diff, get_url, getdate, today

from loc_planning.constants import SETTINGS_DOCTYPE

CERT_DOCTYPE = "Registration Certificate"
COMPANY_DOCTYPE = "Registered Company"


def settings():
	return frappe.get_cached_doc(SETTINGS_DOCTYPE)


def new_verification_code():
	"""Unguessable public token (≈ 96 bits). Not derived from the certificate number."""
	while True:
		code = secrets.token_urlsafe(12).replace("-", "x").replace("_", "y")
		if not frappe.db.exists(CERT_DOCTYPE, {"verification_code": code}):
			return code


def compute_expiry(issue_date):
	months = cint(settings().certificate_validity_months) or 12
	return add_days(add_months(getdate(issue_date), months), -1)


def alert_days():
	return cint(settings().certificate_expiry_alert_days) or 30


def expiry_state(expiry_date, on_date=None):
	"""Valid / Expiring Soon / Expired for a date (None → No Expiry)."""
	if not expiry_date:
		return None
	remaining = date_diff(getdate(expiry_date), getdate(on_date or today()))
	if remaining < 0:
		return "Expired"
	if remaining <= alert_days():
		return "Expiring Soon"
	return "Valid"


def verification_url(code):
	base = (settings().verification_base_url or "").strip().rstrip("/")
	path = f"/verify-certificate?code={code}"
	return f"{base}{path}" if base else get_url(path)


def qr_code_data_uri(text, scale=4):
	"""PNG QR code as a data URI (rendered on the server, works in PDF)."""
	import pyqrcode

	qr = pyqrcode.create(text, error="M")
	buf = io.BytesIO()
	qr.png(buf, scale=scale, quiet_zone=2)
	return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def get_certificate_qr(doc):
	"""Jinja helper for the certificate print format."""
	if isinstance(doc, str):
		doc = frappe.get_doc(CERT_DOCTYPE, doc)
	if not doc.verification_code:
		return ""
	return qr_code_data_uri(verification_url(doc.verification_code))


def refresh_company_certificate(company):
	"""Point the company at its latest issued certificate and cache its status."""
	latest = frappe.get_all(
		CERT_DOCTYPE,
		filters={"registered_company": company, "docstatus": 1, "status": ("in", ("Issued", "Expired"))},
		fields=["name", "expiry_date"],
		order_by="expiry_date desc, creation desc",
		limit=1,
	)
	if latest:
		cert = latest[0]
		values = {
			"current_certificate": cert.name,
			"certificate_expiry_date": cert.expiry_date,
			"certificate_status": expiry_state(cert.expiry_date) or "Valid",
		}
	else:
		values = {"current_certificate": None, "certificate_expiry_date": None, "certificate_status": "None"}
	frappe.db.set_value(COMPANY_DOCTYPE, company, values, update_modified=False)


def get_verification_result(code):
	"""Public, read-only view of a certificate. Returns only non-sensitive fields."""
	code = (code or "").strip()
	if not code or len(code) > 64:
		return None
	cert = frappe.db.get_value(
		CERT_DOCTYPE,
		{"verification_code": code, "docstatus": ("in", (1, 2))},
		[
			"name",
			"certificate_no",
			"company_name",
			"classification",
			"registered_company",
			"issue_date",
			"expiry_date",
			"status",
			"docstatus",
		],
		as_dict=True,
	)
	if not cert:
		return None
	if cert.docstatus == 2 or cert.status == "Cancelled":
		state = "Cancelled"
	elif cert.status == "Superseded":
		state = "Superseded"
	else:
		state = "Expired" if expiry_state(cert.expiry_date) == "Expired" else "Valid"
	company_status = frappe.db.get_value(COMPANY_DOCTYPE, cert.registered_company, "status")
	if state == "Valid" and company_status in ("Suspended", "Blacklisted"):
		state = "Suspended"
	return frappe._dict(
		certificate_no=cert.certificate_no or cert.name,
		company_name=cert.company_name,
		classification=cert.classification,
		issue_date=cert.issue_date,
		expiry_date=cert.expiry_date,
		state=state,
	)


VERIFICATION_LABELS = {
	"Valid": ("شهادة سارية", "green"),
	"Expired": ("شهادة منتهية الصلاحية", "orange"),
	"Cancelled": ("شهادة ملغاة", "red"),
	"Superseded": ("شهادة مجددة بشهادة أحدث", "orange"),
	"Suspended": ("قيد الشركة موقوف", "red"),
}


def throw_if_not_allowed_to_issue(company_doc):
	if company_doc.status != "Active":
		frappe.throw(
			_("Company {0} is {1}. A certificate cannot be issued.").format(
				frappe.bold(company_doc.company_name), _(company_doc.status)
			)
		)
