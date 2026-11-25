"""DocType specifications for Phase 6 (Integrated company activity report)."""

from roles import DIR, EV, GM, SD, SM, SP, perm, read_perms

MODULE = "Activity Report"

DATA_SOURCES = [
	("Editorial Text", "تحرير يدوي"),
	("Sales Data", "المبيعات حسب المنتج والمنطقة"),
	("Stations Data", "المحطات والأنشطة المساندة"),
	("Budget Position", "الموقف التنفيذي للموازنة"),
	("Department Activities", "نشاط الإدارات"),
	("Department Indicators", "مؤشرات إدارة محددة"),
	("Registry Data", "الاستثمار وتسجيل الشركات"),
	("Difficulties", "الصعوبات والتوصيات"),
]

TEMPLATE_SECTION = {
	"name": "Activity Report Template Section",
	"module": MODULE,
	"istable": 1,
	"title_ar": "قسم قالب التقرير",
	"fields": [
		("section_order", "Int", ("Order", "الترتيب"), {"reqd": 1, "in_list_view": 1, "columns": 1}),
		("title", "Data", ("Title", "العنوان"), {"reqd": 1, "in_list_view": 1, "columns": 3}),
		(
			"data_source",
			"Select",
			("Data Source", "مصدر البيانات"),
			{"options": DATA_SOURCES, "reqd": 1, "in_list_view": 1, "columns": 3},
		),
		(
			"source_department",
			"Link",
			("Source Department", "الإدارة المصدر"),
			{
				"options": "LOC Department",
				"in_list_view": 1,
				"columns": 2,
				"mandatory_depends_on": "eval:doc.data_source=='Department Indicators'",
			},
		),
		("include", "Check", ("Include", "مضمن"), {"default": "1", "in_list_view": 1, "columns": 1}),
	],
}

REPORT_TEMPLATE = {
	"name": "Activity Report Template",
	"module": MODULE,
	"autoname": "field:template_name",
	"naming_rule": "By fieldname",
	"title_ar": "قالب تقرير النشاط",
	"fields": [
		(
			"template_name",
			"Data",
			("Template Name", "اسم القالب"),
			{"reqd": 1, "unique": 1, "in_list_view": 1},
		),
		("report_title", "Data", ("Report Title", "عنوان التقرير"), {"reqd": 1}),
		("is_default", "Check", ("Default", "افتراضي"), {"in_list_view": 1}),
		(
			"sections",
			"Table",
			("Sections", "الأقسام"),
			{"options": "Activity Report Template Section", "reqd": 1},
		),
	],
	"permissions": [perm(SM, full=True), perm(SP, full=True), perm(DIR, full=True)]
	+ read_perms([GM, EV, SD]),
}

READINESS = [("Ready", "جاهز"), ("Incomplete", "غير مكتمل"), ("Not Refreshed", "لم يحدث")]

REPORT_SECTION = {
	"name": "Activity Report Section",
	"module": MODULE,
	"istable": 1,
	"title_ar": "قسم التقرير",
	"fields": [
		("section_order", "Int", ("Order", "الترتيب"), {"reqd": 1, "in_list_view": 1, "columns": 1}),
		("title", "Data", ("Title", "العنوان"), {"reqd": 1, "in_list_view": 1, "columns": 3}),
		(
			"data_source",
			"Select",
			("Data Source", "مصدر البيانات"),
			{"options": DATA_SOURCES, "reqd": 1, "in_list_view": 1, "columns": 2},
		),
		(
			"source_department",
			"Link",
			("Source Department", "الإدارة المصدر"),
			{
				"options": "LOC Department",
				"mandatory_depends_on": "eval:doc.data_source=='Department Indicators'",
			},
		),
		("include", "Check", ("Include", "مضمن"), {"default": "1", "in_list_view": 1, "columns": 1}),
		(
			"readiness",
			"Select",
			("Readiness", "الجاهزية"),
			{
				"options": READINESS,
				"default": "Not Refreshed",
				"read_only": 1,
				"in_list_view": 1,
				"columns": 2,
			},
		),
		("readiness_note", "Small Text", ("Readiness Note", "ملاحظة الجاهزية"), {"read_only": 1}),
		("editorial_text", "Text Editor", ("Editorial Text", "النص التحريري"), {"allow_on_submit": 0}),
		("snapshot_json", "Long Text", ("Snapshot", "اللقطة"), {"read_only": 1, "hidden": 1, "no_copy": 1}),
		("snapshot_at", "Datetime", ("Snapshot Time", "وقت اللقطة"), {"read_only": 1, "no_copy": 1}),
	],
}

SCOPES = [("Company", "الشركة ككل"), ("Region", "منطقة")]
REPORT_STATUS = [
	("Draft", "مسودة"),
	("Director Review", "مراجعة مدير الإدارة"),
	("General Manager Approval", "اعتماد المدير العام"),
	("Approved", "معتمد"),
	("Cancelled", "ملغى"),
]

COMPANY_REPORT = {
	"name": "Company Activity Report",
	"module": MODULE,
	"autoname": "format:CAR-{reporting_period}-{###}",
	"naming_rule": "Expression",
	"is_submittable": 1,
	"title_field": "report_title",
	"default_print_format": "Company Activity Report",
	"title_ar": "تقرير نشاط الشركة",
	"fields": [
		("report_title", "Data", ("Report Title", "عنوان التقرير"), {"reqd": 1, "in_list_view": 1}),
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
			"report_type",
			"Data",
			("Report Type", "نوع التقرير"),
			{"read_only": 1, "in_list_view": 1},
		),
		("column_break_1", "Column Break", None, {}),
		(
			"scope",
			"Select",
			("Scope", "النطاق"),
			{"options": SCOPES, "default": "Company", "reqd": 1, "set_only_once": 1},
		),
		(
			"region",
			"Link",
			("Region", "المنطقة"),
			{
				"options": "LOC Region",
				"depends_on": "eval:doc.scope=='Region'",
				"mandatory_depends_on": "eval:doc.scope=='Region'",
				"set_only_once": 1,
			},
		),
		("template", "Link", ("Template", "القالب"), {"options": "Activity Report Template", "reqd": 1}),
		(
			"status",
			"Select",
			("Status", "الحالة"),
			{
				"options": REPORT_STATUS,
				"default": "Draft",
				"read_only": 1,
				"allow_on_submit": 1,
				"no_copy": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
			},
		),
		("section_readiness", "Section Break", ("Readiness", "الجاهزية"), {}),
		(
			"readiness_pct",
			"Percent",
			("Readiness", "نسبة الجاهزية"),
			{"read_only": 1, "no_copy": 1, "in_list_view": 1},
		),
		(
			"data_refreshed_on",
			"Datetime",
			("Data Refreshed On", "آخر تحديث للبيانات"),
			{"read_only": 1, "no_copy": 1},
		),
		("column_break_2", "Column Break", None, {}),
		(
			"incomplete_sections",
			"Small Text",
			("Incomplete Sections", "الأقسام غير المكتملة"),
			{"read_only": 1, "no_copy": 1},
		),
		("section_sections", "Section Break", ("Report Sections", "أقسام التقرير"), {}),
		("sections", "Table", ("Sections", "الأقسام"), {"options": "Activity Report Section", "reqd": 1}),
		("section_comparison", "Section Break", ("Comparisons", "المقارنات"), {"collapsible": 1}),
		(
			"compare_previous",
			"Check",
			("Compare with Previous Period", "مقارنة مع الفترة السابقة"),
			{"default": "1"},
		),
		("column_break_3", "Column Break", None, {}),
		(
			"compare_last_year",
			"Check",
			("Compare with Same Period Last Year", "مقارنة مع نفس الفترة من العام الماضي"),
			{"default": "1"},
		),
		("section_review", "Section Break", ("Review", "المراجعة"), {}),
		(
			"review_comment",
			"Small Text",
			("Review Comment", "ملاحظات المراجعة"),
			{"allow_on_submit": 1},
		),
		("column_break_4", "Column Break", None, {}),
		(
			"approved_by",
			"Link",
			("Approved By", "اعتمد بواسطة"),
			{"options": "User", "read_only": 1, "no_copy": 1},
		),
		("approved_on", "Datetime", ("Approved On", "تاريخ الاعتماد"), {"read_only": 1, "no_copy": 1}),
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
			("Amended From", "معدل من"),
			{"options": "Company Activity Report", "read_only": 1, "no_copy": 1, "print_hide": 1},
		),
	],
	"permissions": [
		perm(SM, full=True, submit=True, cancel=True, amend=True),
		perm(SP, write=True, delete=True, amend=True),
		perm(DIR, write=True, delete=True, amend=True),
		perm(GM, write=True, submit=True, cancel=True),
	]
	+ read_perms([EV, SD]),
}

SPECS = [TEMPLATE_SECTION, REPORT_TEMPLATE, REPORT_SECTION, COMPANY_REPORT]
