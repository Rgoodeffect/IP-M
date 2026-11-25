"""DocType specifications for Phase 5 (Department activity submissions)."""

from roles import DC, DIR, EV, FB, INV, SD, SM, SO, SP, perm, read_perms

MODULE = "Activity Report"

DOMAIN = {
	"name": "Activity Domain",
	"module": MODULE,
	"autoname": "field:domain_name",
	"naming_rule": "By fieldname",
	"title_ar": "مجال النشاط",
	"fields": [
		("domain_name", "Data", ("Domain", "المجال"), {"reqd": 1, "unique": 1, "in_list_view": 1}),
		("is_active", "Check", ("Active", "نشط"), {"default": "1", "in_list_view": 1}),
	],
	"permissions": [perm(SM, full=True), perm(SP, full=True), perm(DIR, full=True)]
	+ read_perms([SD, DC, EV]),
}

TEMPLATE_LINE = {
	"name": "Activity Indicator Template Line",
	"module": MODULE,
	"istable": 1,
	"title_ar": "مؤشر",
	"fields": [
		("indicator", "Data", ("Indicator", "المؤشر"), {"reqd": 1, "in_list_view": 1, "columns": 4}),
		("unit", "Data", ("Unit", "الوحدة"), {"in_list_view": 1, "columns": 2}),
		("description", "Small Text", ("Description", "الوصف"), {"in_list_view": 1, "columns": 4}),
	],
}

TEMPLATE = {
	"name": "Activity Indicator Template",
	"module": MODULE,
	"autoname": "field:department",
	"naming_rule": "By fieldname",
	"title_ar": "قالب مؤشرات الإدارة",
	"fields": [
		(
			"department",
			"Link",
			("Department", "الإدارة"),
			{"options": "LOC Department", "reqd": 1, "unique": 1, "in_list_view": 1},
		),
		("indicators", "Table", ("Indicators", "المؤشرات"), {"options": "Activity Indicator Template Line"}),
	],
	"permissions": [perm(SM, full=True), perm(SP, full=True), perm(DIR, full=True)]
	+ read_perms([SD, DC, EV]),
}

SUBMISSION_ITEM = {
	"name": "Activity Submission Item",
	"module": MODULE,
	"istable": 1,
	"title_ar": "نشاط",
	"fields": [
		("activity", "Small Text", ("Activity", "النشاط"), {"reqd": 1, "in_list_view": 1, "columns": 4}),
		(
			"domain",
			"Link",
			("Domain", "المجال"),
			{"options": "Activity Domain", "in_list_view": 1, "columns": 2},
		),
		("target", "Float", ("Target", "المستهدف"), {"in_list_view": 1, "columns": 1, "non_negative": 1}),
		("executed", "Float", ("Executed", "المنفذ"), {"in_list_view": 1, "columns": 1, "non_negative": 1}),
		(
			"achievement_pct",
			"Percent",
			("Achievement %", "نسبة الإنجاز"),
			{"read_only": 1, "in_list_view": 1, "columns": 1},
		),
		("unit", "Data", ("Unit", "الوحدة"), {}),
		("notes", "Small Text", ("Notes", "ملاحظات"), {}),
	],
}

SUBMISSION_INDICATOR = {
	"name": "Activity Submission Indicator",
	"module": MODULE,
	"istable": 1,
	"title_ar": "مؤشر رقمي",
	"fields": [
		("indicator", "Data", ("Indicator", "المؤشر"), {"reqd": 1, "in_list_view": 1, "columns": 4}),
		("value", "Float", ("Value", "القيمة"), {"in_list_view": 1, "columns": 2}),
		("unit", "Data", ("Unit", "الوحدة"), {"in_list_view": 1, "columns": 2}),
		("notes", "Data", ("Notes", "ملاحظات"), {"in_list_view": 1, "columns": 2}),
	],
}

SUBMISSION_STATUS = [
	("Draft", "مسودة"),
	("Manager Review", "مراجعة مدير الإدارة"),
	("Statistics Review", "مراجعة قسم الإحصاء والبيانات"),
	("Planning Approval", "اعتماد التخطيط الاستراتيجي"),
	("Returned", "مرجعة للتعديل"),
	("Approved", "معتمدة"),
	("Included in Report", "مدرجة في التقرير"),
	("Cancelled", "ملغاة"),
]

SUBMISSION = {
	"name": "Department Activity Submission",
	"module": MODULE,
	"autoname": "",
	"naming_rule": "By script",
	"is_submittable": 1,
	"title_field": "department",
	"search_fields": "department,reporting_period,status",
	"title_ar": "نموذج نشاط الإدارة",
	"fields": [
		(
			"department",
			"Link",
			("Department", "الإدارة"),
			{
				"options": "LOC Department",
				"reqd": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
				"set_only_once": 1,
			},
		),
		(
			"reporting_period",
			"Link",
			("Period", "الفترة"),
			{
				"options": "Reporting Period",
				"reqd": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
				"set_only_once": 1,
			},
		),
		(
			"region",
			"Link",
			("Region", "المنطقة"),
			{
				"options": "LOC Region",
				"fetch_from": "department.region",
				"read_only": 1,
				"in_standard_filter": 1,
			},
		),
		("column_break_1", "Column Break", None, {}),
		(
			"prepared_by",
			"Link",
			("Prepared By", "المعد"),
			{"options": "User", "default": "__user", "read_only": 1},
		),
		(
			"department_head",
			"Link",
			("Department Head", "مدير الإدارة"),
			{"options": "User", "fetch_from": "department.head_user", "read_only": 1},
		),
		("due_date", "Date", ("Due Date", "الموعد النهائي"), {"read_only": 1, "in_list_view": 1}),
		(
			"status",
			"Select",
			("Status", "الحالة"),
			{
				"options": SUBMISSION_STATUS,
				"default": "Draft",
				"read_only": 1,
				"allow_on_submit": 1,
				"no_copy": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
			},
		),
		("section_activities", "Section Break", ("Activities Carried Out", "الأنشطة المنفذة"), {}),
		("activities", "Table", ("Activities", "الأنشطة"), {"options": "Activity Submission Item"}),
		(
			"overall_achievement",
			"Percent",
			("Overall Achievement", "نسبة الإنجاز العامة"),
			{
				"read_only": 1,
				"description": ("Average of the activities with a target", "متوسط الأنشطة ذات المستهدف"),
			},
		),
		("section_indicators", "Section Break", ("Department Indicators", "المؤشرات الرقمية للإدارة"), {}),
		("indicators", "Table", ("Indicators", "المؤشرات"), {"options": "Activity Submission Indicator"}),
		("section_text", "Section Break", ("Difficulties and Plan", "الصعوبات والخطة"), {}),
		("difficulties", "Text Editor", ("Difficulties and Obstacles", "الصعوبات والمعوقات"), {}),
		("next_period_plan", "Text Editor", ("Plan for the Next Period", "خطة الفترة القادمة"), {}),
		("section_review", "Section Break", ("Review", "المراجعة"), {}),
		(
			"review_comment",
			"Small Text",
			("Review Comment", "ملاحظات المراجعة"),
			{
				"allow_on_submit": 1,
				"description": (
					"Required when returning the submission for revision",
					"إلزامية عند إرجاع النموذج للتعديل",
				),
			},
		),
		("column_break_2", "Column Break", None, {}),
		("submitted_on", "Datetime", ("Submitted On", "تاريخ الإرسال"), {"read_only": 1, "no_copy": 1}),
		("approved_on", "Datetime", ("Approved On", "تاريخ الاعتماد"), {"read_only": 1, "no_copy": 1}),
		("days_late", "Int", ("Days Late", "أيام التأخير"), {"read_only": 1, "no_copy": 1}),
		(
			"company_activity_report",
			"Data",
			("Included in Report", "مدرج في التقرير"),
			{"read_only": 1, "no_copy": 1, "allow_on_submit": 1},
		),
		(
			"cancel_reason",
			"Small Text",
			("Cancellation Reason", "سبب الإلغاء"),
			{"allow_on_submit": 1, "no_copy": 1, "depends_on": "eval:doc.docstatus>0"},
		),
		(
			"workflow_state",
			"Link",
			("Workflow State", "مرحلة الاعتماد"),
			{"options": "Workflow State", "read_only": 1, "hidden": 1, "allow_on_submit": 1, "no_copy": 1},
		),
		(
			"amended_from",
			"Link",
			("Amended From", "معدلة من"),
			{"options": "Department Activity Submission", "read_only": 1, "no_copy": 1, "print_hide": 1},
		),
	],
	"permissions": [
		perm(SM, full=True, submit=True, cancel=True, amend=True),
		perm(DIR, write=True, delete=True, submit=True, cancel=True, amend=True),
		perm(SP, write=True, submit=True, cancel=True, amend=True),
		perm(SD, write=True),
		perm(DC, write=True),
	]
	+ read_perms([EV]),
}

SPECS = [DOMAIN, TEMPLATE_LINE, TEMPLATE, SUBMISSION_ITEM, SUBMISSION_INDICATOR, SUBMISSION]
