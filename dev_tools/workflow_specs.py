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

SD = "Statistics & Data"
SO = "Sales Office User"

MONTHLY_DATA_STATES = [
	("Draft", 0, SO, "Info"),
	("Pending Review", 0, SD, "Warning"),
	("Returned", 0, SO, "Danger"),
	("Approved", 1, SD, "Success"),
	("Cancelled", 2, SD, "Danger"),
]

MONTHLY_DATA_TRANSITIONS = [
	("Draft", "Submit for Review", "Pending Review", SO),
	("Returned", "Submit for Review", "Pending Review", SO),
	("Pending Review", "Return for Revision", "Returned", SD),
	("Pending Review", "Approve", "Approved", SD),
	("Approved", "Cancel", "Cancelled", SD),
]

DC = "Department Coordinator"
SP = "Strategic Planning"

# Only the department's own head may act at the manager stage (any coordinator of the
# department when no head is set on the department).
IS_HEAD = "not doc.department_head or doc.department_head == frappe.session.user"

ACTIVITY_STATES = [
	("Draft", 0, DC, "Info"),
	("Manager Review", 0, DC, "Primary"),
	("Statistics Review", 0, SD, "Warning"),
	("Planning Approval", 0, SP, "Warning"),
	("Returned", 0, DC, "Danger"),
	("Approved", 1, SP, "Success"),
	("Included in Report", 1, SP, "Success"),
	("Cancelled", 2, SP, "Danger"),
]

ACTIVITY_TRANSITIONS = [
	("Draft", "Submit to Manager", "Manager Review", DC),
	("Returned", "Submit to Manager", "Manager Review", DC),
	("Manager Review", "Approve", "Statistics Review", DC, IS_HEAD),
	("Manager Review", "Return for Revision", "Returned", DC, IS_HEAD),
	("Statistics Review", "Send for Approval", "Planning Approval", SD),
	("Statistics Review", "Return for Revision", "Returned", SD),
	("Planning Approval", "Approve", "Approved", SP),
	("Planning Approval", "Approve", "Approved", DIR),
	("Planning Approval", "Return for Revision", "Returned", SP),
	("Planning Approval", "Return for Revision", "Returned", DIR),
	("Approved", "Include in Report", "Included in Report", SP),
	("Approved", "Cancel", "Cancelled", SP),
	("Approved", "Cancel", "Cancelled", DIR),
]

WORKFLOWS = [
	{
		"name": "Registration Certificate Approval",
		"document_type": "Registration Certificate",
		"states": CERTIFICATE_STATES,
		"transitions": CERTIFICATE_TRANSITIONS,
	},
	{
		"name": "Station Monthly Data Approval",
		"document_type": "Station Monthly Data",
		"states": MONTHLY_DATA_STATES,
		"transitions": MONTHLY_DATA_TRANSITIONS,
	},
	{
		"name": "Department Activity Approval",
		"document_type": "Department Activity Submission",
		"states": ACTIVITY_STATES,
		"transitions": ACTIVITY_TRANSITIONS,
	},
]

STATE_AR = {
	"Requested": "طلب",
	"Under Review": "قيد المراجعة",
	"Pending Approval": "بانتظار الاعتماد",
	"Issued": "صادرة",
	"Rejected": "مرفوضة",
	"Cancelled": "ملغاة",
	"Draft": "مسودة",
	"Pending Review": "بانتظار المراجعة",
	"Returned": "مرجعة للتعديل",
	"Approved": "معتمدة",
	"Manager Review": "مراجعة مدير الإدارة",
	"Statistics Review": "مراجعة قسم الإحصاء والبيانات",
	"Planning Approval": "اعتماد التخطيط الاستراتيجي",
	"Included in Report": "مدرجة في التقرير",
}

ACTION_AR = {
	"Submit for Review": "إرسال للمراجعة",
	"Send for Approval": "إرسال للاعتماد",
	"Return for Revision": "إرجاع للتعديل",
	"Approve": "اعتماد",
	"Reject": "رفض",
	"Reopen": "إعادة فتح",
	"Cancel": "إلغاء",
	"Submit to Manager": "إرسال لمدير الإدارة",
	"Include in Report": "إدراج في التقرير",
}

WORKFLOW_AR = {
	"Registration Certificate Approval": "اعتماد شهادة إثبات القيد",
	"Station Monthly Data Approval": "اعتماد البيانات الشهرية للمحطات",
	"Department Activity Approval": "اعتماد نماذج نشاط الإدارات",
}
