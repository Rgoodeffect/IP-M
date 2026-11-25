"""Workflow helpers shared by documents that require a comment when returned."""

import frappe
import frappe.model.workflow
from frappe import _

RETURN_ACTION = "Return for Revision"


@frappe.whitelist(methods=["POST"])
def set_review_comment(doctype: str, name: str, comment: str, field: str = "review_comment"):
	"""Store the review comment before a "Return for Revision" action (the workflow action
	reloads the document from the database, so the comment must be saved first)."""
	if doctype not in ("Department Activity Submission", "Company Activity Report", "Station Monthly Data"):
		frappe.throw(_("Not allowed"), frappe.PermissionError)
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	if not (comment or "").strip():
		frappe.throw(_("Please write the review comment"))
	if not any(t.action == RETURN_ACTION for t in frappe.model.workflow.get_transitions(doc)):
		frappe.throw(_("You cannot return this report at its current stage"), frappe.PermissionError)
	doc.db_set(field, comment.strip())
	return True
