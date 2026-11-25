"""Workflow definitions. `gen_doctypes.py` writes them to loc_planning/fixtures/*.json.

State and action names are English (stable identifiers); Arabic comes from ar.csv.
"""

DIR = "LOC Planning Director"
INV = "Investment Section"

# (state, doc_status, allow_edit role, style)
CERTIFICATE_STATES = [
	("Requested", 0, INV, "Info"),
	("Under Review", 0, INV, "Primary"),
	("Pending Approval", 0, DIR, "Warning"),
	("Issued", 1, DIR, "Success"),
	("Rejected", 0, INV, "Danger"),
	("Cancelled", 2, DIR, "Danger"),
]

# (from, action, to, role)
CERTIFICATE_TRANSITIONS = [
	("Requested", "Submit for Review", "Under Review", INV),
	("Under Review", "Send for Approval", "Pending Approval", INV),
	("Under Review", "Return for Revision", "Requested", INV),
	("Pending Approval", "Approve", "Issued", DIR),
	("Pending Approval", "Return for Revision", "Under Review", DIR),
	("Pending Approval", "Reject", "Rejected", DIR),
	("Rejected", "Reopen", "Requested", INV),
	("Issued", "Cancel", "Cancelled", DIR),
]

WORKFLOWS = [
	{
		"name": "Registration Certificate Approval",
		"document_type": "Registration Certificate",
		"states": CERTIFICATE_STATES,
		"transitions": CERTIFICATE_TRANSITIONS,
	},
]

STATE_AR = {
	"Requested": "طلب",
	"Under Review": "قيد المراجعة",
	"Pending Approval": "بانتظار الاعتماد",
	"Issued": "صادرة",
	"Rejected": "مرفوضة",
	"Cancelled": "ملغاة",
}

ACTION_AR = {
	"Submit for Review": "إرسال للمراجعة",
	"Send for Approval": "إرسال للاعتماد",
	"Return for Revision": "إرجاع للتعديل",
	"Approve": "اعتماد",
	"Reject": "رفض",
	"Reopen": "إعادة فتح",
	"Cancel": "إلغاء",
}

WORKFLOW_AR = {"Registration Certificate Approval": "اعتماد شهادة إثبات القيد"}
