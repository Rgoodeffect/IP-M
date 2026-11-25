"""Daily jobs for the Investment Registry."""

import frappe
from frappe import _
from frappe.utils import add_days, get_url_to_form, today

from loc_planning.constants import ROLE_INVESTMENT
from loc_planning.investment_registry.utils import alert_days, expiry_state, refresh_company_certificate


def daily():
	expire_certificates()
	refresh_company_statuses()
	send_expiry_alert()


def expire_certificates():
	"""Issued certificates past their expiry date become Expired (document stays submitted)."""
	expired = frappe.get_all(
		"Registration Certificate",
		filters={"docstatus": 1, "status": "Issued", "expiry_date": ("<", today())},
		pluck="name",
	)
	for name in expired:
		frappe.db.set_value("Registration Certificate", name, "status", "Expired", update_modified=False)
	return expired


def refresh_company_statuses():
	"""Recompute cached certificate and document statuses of every company."""
	for name in frappe.get_all("Registered Company", pluck="name"):
		refresh_company_certificate(name)
	rows = frappe.get_all(
		"Registered Company Document",
		filters={"parenttype": "Registered Company"},
		fields=["name", "expiry_date", "document_status"],
	)
	for row in rows:
		status = expiry_state(row.expiry_date) if row.expiry_date else "No Expiry"
		if status != row.document_status:
			frappe.db.set_value(
				"Registered Company Document", row.name, "document_status", status, update_modified=False
			)


def get_expiring_certificates(days=None):
	days = alert_days() if days is None else days
	return frappe.get_all(
		"Registration Certificate",
		filters={
			"docstatus": 1,
			"status": "Issued",
			"expiry_date": ("between", (today(), add_days(today(), days))),
		},
		fields=["name", "certificate_no", "company_name", "expiry_date"],
		order_by="expiry_date asc",
	)


def send_expiry_alert():
	"""One digest per day to the Investment Section: system notification + email."""
	certificates = get_expiring_certificates()
	if not certificates:
		return 0
	recipients = get_role_users(ROLE_INVESTMENT)
	if not recipients:
		return 0

	subject = _("{0} registration certificates expire within {1} days").format(
		len(certificates), alert_days()
	)
	rows = "".join(
		f"<tr><td>{frappe.utils.escape_html(c.certificate_no or c.name)}</td>"
		f"<td>{frappe.utils.escape_html(c.company_name or '')}</td>"
		f"<td>{c.expiry_date}</td>"
		f"<td><a href='{get_url_to_form('Registration Certificate', c.name)}'>{_('Open')}</a></td></tr>"
		for c in certificates
	)
	message = (
		f"<div dir='rtl'><p>{subject}</p><table border='1' cellpadding='4' style='border-collapse:collapse'>"
		f"<tr><th>{_('Certificate No.')}</th><th>{_('Company')}</th><th>{_('Expiry Date')}</th><th></th></tr>"
		f"{rows}</table></div>"
	)
	for user in recipients:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"document_type": "Registration Certificate",
				"document_name": certificates[0].name,
				"subject": subject,
				"email_content": message,
			}
		).insert(ignore_permissions=True)
	if frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}):
		frappe.sendmail(recipients=recipients, subject=subject, message=message, delayed=True)
	return len(certificates)


def get_role_users(role):
	users = frappe.get_all(
		"Has Role",
		filters={"role": role, "parenttype": "User", "parent": ("not in", ("Administrator", "Guest"))},
		pluck="parent",
		distinct=True,
	)
	if not users:
		return []
	return frappe.get_all("User", filters={"name": ("in", users), "enabled": 1}, pluck="name")
