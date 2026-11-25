"""Generic document guards wired through `doc_events["*"]` in hooks.py.

1. Period lock: any document that has a `reporting_period` field cannot be created, edited,
   cancelled or deleted while that period (or the period it is being moved away from) is
   closed. Controlled by `LOC Planning Settings.enforce_period_lock`.
2. Cancel reason: a document with a `cancel_reason` field cannot be cancelled without one.
3. No deletion of approved records: submitted or cancelled documents of the LOC modules
   cannot be deleted; they can only be cancelled (with a reason) to keep the audit trail.
"""

import frappe
from frappe import _

from loc_planning.constants import CANCEL_REASON_FIELD, LOC_MODULES, PERIOD_FIELD, SETTINGS_DOCTYPE


class PeriodClosedError(frappe.ValidationError):
	pass


def _skip(doc):
	return (
		frappe.flags.in_install
		or frappe.flags.in_migrate
		or frappe.flags.ignore_period_lock
		or doc.doctype in ("Reporting Period", SETTINGS_DOCTYPE)
	)


def _lock_enabled():
	try:
		return bool(frappe.get_cached_doc(SETTINGS_DOCTYPE).enforce_period_lock)
	except frappe.DoesNotExistError:
		return True


def assert_period_open(period, doc=None):
	if not period:
		return
	if frappe.db.get_value("Reporting Period", period, "status") == "Closed":
		title = frappe.db.get_value("Reporting Period", period, "title") or period
		frappe.throw(
			_("Reporting period {0} is closed. Changes to its data are not allowed.").format(
				frappe.bold(title)
			),
			exc=PeriodClosedError,
			title=_("Period Closed"),
		)


def _periods_of(doc, include_previous=True):
	periods = {doc.get(PERIOD_FIELD)}
	if include_previous and not doc.is_new():
		before = doc.get_doc_before_save()
		if before:
			periods.add(before.get(PERIOD_FIELD))
	return [p for p in periods if p]


def check_period_lock(doc, method=None):
	"""validate / before_update_after_submit / before_cancel / on_trash"""
	if _skip(doc) or not frappe.get_meta(doc.doctype).has_field(PERIOD_FIELD):
		return
	if not _lock_enabled():
		return
	for period in _periods_of(doc, include_previous=method in ("validate", "before_update_after_submit")):
		assert_period_open(period, doc)


def require_cancel_reason(doc, method=None):
	"""before_cancel"""
	if frappe.flags.in_install or frappe.flags.in_migrate:
		return
	if (
		frappe.get_meta(doc.doctype).has_field(CANCEL_REASON_FIELD)
		and not (doc.get(CANCEL_REASON_FIELD) or "").strip()
	):
		frappe.throw(
			_("Please enter the cancellation reason before cancelling."),
			title=_("Cancellation Reason Required"),
		)


def prevent_delete_of_approved(doc, method=None):
	"""on_trash"""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_test_cleanup:
		return
	if doc.docstatus and frappe.get_meta(doc.doctype).module in LOC_MODULES:
		frappe.throw(
			_("Approved documents cannot be deleted. Cancel the document with a reason instead."),
			title=_("Not Allowed"),
		)


def on_validate(doc, method=None):
	check_period_lock(doc, "validate")


def on_before_update_after_submit(doc, method=None):
	check_period_lock(doc, "before_update_after_submit")


def on_before_cancel(doc, method=None):
	require_cancel_reason(doc, method)
	check_period_lock(doc, "before_cancel")


def on_trash(doc, method=None):
	prevent_delete_of_approved(doc, method)
	check_period_lock(doc, "on_trash")
