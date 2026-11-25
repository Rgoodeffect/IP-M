"""DocType specifications for Phase 1 (foundation).

Each field is declared as (fieldname, fieldtype, (English label, Arabic label), extra-props).
`dev_tools/gen_doctypes.py` turns these specs into DocType JSON files inside the app and
collects every label into `loc_planning/translations/ar.csv`.
"""

from roles import ALL_LOC_ROLES, DIR, EV, FB, INV, SD, SM, SP, perm, read_perms

REGION = {
	"name": "LOC Region",
	"module": "LOC Planning",
	"autoname": "field:region_name",
	"naming_rule": "By fieldname",
	"title_ar": "المنطقة",
	"search_fields": "region_code",
	"fields": [
		("region_name", "Data", ("Region Name", "اسم المنطقة"), {"reqd": 1, "unique": 1, "in_list_view": 1}),
		("region_code", "Data", ("Region Code", "رمز المنطقة"), {"unique": 1, "in_list_view": 1}),
		("column_break_1", "Column Break", None, {}),
		("is_active", "Check", ("Active", "نشط"), {"default": "1", "in_list_view": 1}),
		("description", "Small Text", ("Description", "الوصف"), {}),
	],
	"permissions": [perm(SM, full=True), perm(DIR, write=True), perm(SP, write=True)]
	+ read_perms([SD, INV, FB, EV, "Department Coordinator", "Sales Office User"]),
}

DEPARTMENT_TYPES = [
	("Company", "الشركة"),
	("Department", "إدارة"),
	("Office", "مكتب"),
	("Sales Office", "مكتب مبيعات"),
	("Section", "قسم"),
	("Unit", "وحدة"),
]

DEPARTMENT = {
	"name": "LOC Department",
	"module": "LOC Planning",
	"autoname": "",
	"naming_rule": "By script",
	"is_tree": 1,
	"nsm_parent_field": "parent_loc_department",
	"title_field": "department_name",
	"show_title_field_in_link": 0,
	"search_fields": "department_type,region",
	"allow_rename": 1,
	"title_ar": "الجهة",
	"fields": [
		("department_name", "Data", ("Department Name", "اسم الجهة"), {"reqd": 1, "in_list_view": 1}),
		(
			"department_type",
			"Select",
			("Department Type", "نوع الجهة"),
			{
				"reqd": 1,
				"options": DEPARTMENT_TYPES,
				"default": "Department",
				"in_list_view": 1,
				"in_standard_filter": 1,
			},
		),
		(
			"parent_loc_department",
			"Link",
			("Parent Department", "الجهة الأم"),
			{"options": "LOC Department", "in_standard_filter": 1, "ignore_user_permissions": 1},
		),
		("is_group", "Check", ("Is Group", "تتبعها جهات"), {}),
		("column_break_1", "Column Break", None, {}),
		(
			"region",
			"Link",
			("Region", "المنطقة"),
			{
				"options": "LOC Region",
				"in_list_view": 1,
				"in_standard_filter": 1,
				"mandatory_depends_on": "eval:doc.department_type=='Sales Office'",
			},
		),
		("head_user", "Link", ("Head", "المسؤول"), {"options": "User"}),
		("department_code", "Data", ("Code", "الرمز"), {}),
		("is_active", "Check", ("Active", "نشط"), {"default": "1"}),
		("section_reporting", "Section Break", ("Activity Reporting", "تقرير النشاط"), {}),
		(
			"requires_activity_report",
			"Check",
			("Requires Activity Report", "مطلوب منه تقرير نشاط"),
			{"in_standard_filter": 1},
		),
		("column_break_2", "Column Break", None, {}),
		(
			"report_deadline_days",
			"Int",
			(
				"Deadline Override (days after period end)",
				"الموعد النهائي الخاص (أيام بعد نهاية الفترة)",
			),
			{
				"depends_on": "requires_activity_report",
				"description": (
					"Leave empty to use the default in LOC Planning Settings",
					"اتركه فارغاً لاستخدام القيمة العامة في إعدادات المنظومة",
				),
			},
		),
		("section_erpnext", "Section Break", ("ERPNext Link", "الربط مع ERPNext"), {"collapsible": 1}),
		("company", "Link", ("Company", "الشركة"), {"options": "Company"}),
		("erpnext_department", "Link", ("ERPNext Department", "القسم في ERPNext"), {"options": "Department"}),
		("column_break_3", "Column Break", None, {}),
		("cost_center", "Link", ("Cost Center", "مركز التكلفة"), {"options": "Cost Center"}),
		("lft", "Int", ("Left", "Left"), {"hidden": 1, "read_only": 1, "no_copy": 1}),
		("rgt", "Int", ("Right", "Right"), {"hidden": 1, "read_only": 1, "no_copy": 1}),
		(
			"old_parent",
			"Link",
			("Old Parent", "Old Parent"),
			{"options": "LOC Department", "hidden": 1, "read_only": 1, "ignore_user_permissions": 1},
		),
	],
	"permissions": [perm(SM, full=True), perm(DIR, write=True), perm(SP, write=True)]
	+ read_perms([SD, INV, FB, EV, "Department Coordinator", "Sales Office User"]),
}

PERIOD_TYPES = [
	("Monthly", "شهري"),
	("Quarterly", "ربع سنوي"),
	("Half-Yearly", "نصف سنوي"),
	("Annual", "سنوي"),
]

REPORTING_PERIOD = {
	"name": "Reporting Period",
	"module": "LOC Planning",
	"autoname": "",
	"naming_rule": "By script",
	"title_field": "title",
	"show_title_field_in_link": 1,
	"sort_field": "from_date",
	"sort_order": "DESC",
	"search_fields": "title,period_type,year,status",
	"title_ar": "الفترة",
	"fields": [
		(
			"period_type",
			"Select",
			("Period Type", "نوع الفترة"),
			{
				"reqd": 1,
				"options": PERIOD_TYPES,
				"default": "Quarterly",
				"set_only_once": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
			},
		),
		("year", "Int", ("Year", "السنة"), {"reqd": 1, "set_only_once": 1, "in_standard_filter": 1}),
		(
			"period_number",
			"Int",
			("Period No.", "رقم الفترة"),
			{
				"set_only_once": 1,
				"depends_on": "eval:doc.period_type!='Annual'",
				"mandatory_depends_on": "eval:doc.period_type!='Annual'",
				"description": (
					"Month 1-12, quarter 1-4 or half 1-2",
					"الشهر 1-12 أو الربع 1-4 أو النصف 1-2",
				),
			},
		),
		("column_break_1", "Column Break", None, {}),
		("title", "Data", ("Title", "العنوان"), {"read_only": 1, "in_list_view": 1}),
		("from_date", "Date", ("From Date", "من تاريخ"), {"read_only": 1, "in_list_view": 1}),
		("to_date", "Date", ("To Date", "إلى تاريخ"), {"read_only": 1}),
		("section_status", "Section Break", ("Status", "الحالة"), {}),
		(
			"status",
			"Select",
			("Status", "الحالة"),
			{
				"options": [("Open", "مفتوحة"), ("Closed", "مغلقة")],
				"default": "Open",
				"read_only": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
				"no_copy": 1,
			},
		),
		(
			"closed_by",
			"Link",
			("Closed By", "أُغلقت بواسطة"),
			{"options": "User", "read_only": 1, "no_copy": 1},
		),
		("column_break_2", "Column Break", None, {}),
		("closed_on", "Datetime", ("Closed On", "تاريخ الإغلاق"), {"read_only": 1, "no_copy": 1}),
		("status_remarks", "Small Text", ("Remarks", "ملاحظات"), {"no_copy": 1}),
	],
	"permissions": [perm(SM, full=True), perm(SP, write=True, delete=True), perm(DIR, write=True)]
	+ read_perms([SD, INV, FB, EV, "Department Coordinator", "Sales Office User"]),
}

PRODUCT_GROUPS = [("Fuel", "وقود"), ("Gas", "غاز"), ("Lubricant", "زيوت"), ("Other", "أخرى")]

FUEL_PRODUCT = {
	"name": "Fuel Product",
	"module": "LOC Planning",
	"autoname": "field:product_name",
	"naming_rule": "By fieldname",
	"sort_field": "display_order",
	"sort_order": "ASC",
	"title_ar": "المنتج",
	"fields": [
		("product_name", "Data", ("Product Name", "اسم المنتج"), {"reqd": 1, "unique": 1, "in_list_view": 1}),
		("product_code", "Data", ("Product Code", "رمز المنتج"), {"unique": 1}),
		(
			"product_group",
			"Select",
			("Product Group", "مجموعة المنتج"),
			{"options": PRODUCT_GROUPS, "default": "Fuel", "in_list_view": 1, "in_standard_filter": 1},
		),
		("column_break_1", "Column Break", None, {}),
		("uom", "Link", ("Unit of Measure", "وحدة القياس"), {"options": "UOM", "reqd": 1, "in_list_view": 1}),
		("display_order", "Int", ("Display Order", "ترتيب العرض"), {}),
		("is_active", "Check", ("Active", "نشط"), {"default": "1"}),
	],
	"permissions": [perm(SM, full=True), perm(DIR, write=True), perm(SP, write=True), perm(SD, write=True)]
	+ read_perms([INV, FB, EV, "Department Coordinator", "Sales Office User"]),
}

SETTINGS = {
	"name": "LOC Planning Settings",
	"module": "LOC Planning",
	"issingle": 1,
	"title_ar": "إعدادات منظومة التخطيط والاستثمار",
	"fields": [
		("section_general", "Section Break", ("General", "عام"), {}),
		("company", "Link", ("Company", "الشركة"), {"options": "Company"}),
		(
			"official_company_name",
			"Data",
			("Official Company Name", "الاسم الرسمي للشركة"),
			{"default": "شركة ليبيا للنفط"},
		),
		(
			"reporting_currency",
			"Link",
			("Reporting Currency", "عملة التقارير"),
			{"options": "Currency", "default": "LYD"},
		),
		("column_break_1", "Column Break", None, {}),
		("company_logo", "Attach Image", ("Company Logo", "شعار الشركة"), {}),
		("section_print", "Section Break", ("Fonts and Printing", "الخطوط والطباعة"), {}),
		("report_font_family", "Data", ("Report Font Family", "خط التقارير"), {"default": "Fanan"}),
		(
			"report_font_file",
			"Attach",
			("Report Font File (TTF/OTF)", "ملف خط التقارير (TTF/OTF)"),
			{},
		),
		("column_break_2", "Column Break", None, {}),
		(
			"fallback_font_family",
			"Data",
			("Fallback Font Family", "الخط البديل"),
			{"default": "Noto Naskh Arabic"},
		),
		("base_font_size", "Int", ("Base Font Size (pt)", "حجم الخط الأساسي (نقطة)"), {"default": "12"}),
		("report_header_text", "Small Text", ("Report Header Text", "نص ترويسة التقارير"), {}),
		("report_footer_text", "Small Text", ("Report Footer Text", "نص تذييل التقارير"), {}),
		("section_budget", "Section Break", ("Budget Thresholds", "عتبات تنفيذ الموازنة"), {}),
		(
			"slow_execution_threshold",
			"Percent",
			("Slow Execution Below (%)", "بطء التنفيذ أقل من (%)"),
			{"default": "40"},
		),
		("column_break_3", "Column Break", None, {}),
		(
			"over_execution_threshold",
			"Percent",
			("Limit Exceeded Above (%)", "تجاوز الحد أعلى من (%)"),
			{"default": "80"},
		),
		("section_activity", "Section Break", ("Activity Reports", "تقارير النشاط"), {}),
		(
			"activity_report_period_type",
			"Select",
			("Activity Report Period Type", "دورية تقرير النشاط"),
			{"options": PERIOD_TYPES, "default": "Quarterly"},
		),
		(
			"activity_report_deadline_days",
			"Int",
			("Deadline (days after period end)", "الموعد النهائي (أيام بعد نهاية الفترة)"),
			{"default": "15"},
		),
		("column_break_4", "Column Break", None, {}),
		(
			"reminder_days_before",
			"Int",
			("Remind Days Before Deadline", "التذكير قبل الموعد بـ (أيام)"),
			{"default": "3"},
		),
		(
			"reminder_repeat_days_after",
			"Int",
			("Repeat Reminder Every (days) After Deadline", "تكرار التذكير بعد الموعد كل (أيام)"),
			{"default": "2"},
		),
		(
			"max_overdue_reminders",
			"Int",
			("Maximum Overdue Reminders", "أقصى عدد لتذكيرات التأخير"),
			{"default": "5"},
		),
		("section_stations", "Section Break", ("Stations", "المحطات"), {}),
		(
			"station_data_due_day",
			"Int",
			(
				"Monthly Station Data Due Day (of following month)",
				"يوم استحقاق بيانات المحطات الشهرية (من الشهر التالي)",
			),
			{"default": "10"},
		),
		("section_investment", "Section Break", ("Investment Registry", "سجل الشركات"), {}),
		(
			"certificate_validity_months",
			"Int",
			("Certificate Validity (months)", "مدة صلاحية الشهادة (أشهر)"),
			{"default": "12"},
		),
		(
			"certificate_expiry_alert_days",
			"Int",
			("Expiry Alert (days before)", "التنبيه قبل انتهاء الشهادة بـ (أيام)"),
			{"default": "30"},
		),
		("column_break_5", "Column Break", None, {}),
		(
			"auto_create_supplier",
			"Check",
			("Create Supplier on Certificate Approval", "إنشاء مورد عند اعتماد الشهادة"),
			{},
		),
		(
			"supplier_group",
			"Link",
			("Supplier Group", "مجموعة الموردين"),
			{"options": "Supplier Group", "depends_on": "auto_create_supplier"},
		),
		("section_periods", "Section Break", ("Reporting Periods", "الفترات"), {}),
		(
			"enforce_period_lock",
			"Check",
			("Lock Data of Closed Periods", "منع تعديل بيانات الفترات المغلقة"),
			{"default": "1"},
		),
		("column_break_6", "Column Break", None, {}),
		("periods_year", "Int", ("Year", "السنة"), {}),
		(
			"create_periods",
			"Button",
			("Create Periods for Year", "إنشاء فترات السنة"),
			{"depends_on": "periods_year"},
		),
	],
	"permissions": [
		perm(SM, write=True, create=True, single=True),
		perm(DIR, write=True, create=True, single=True),
		perm(SP, write=True, create=True, single=True),
	]
	+ [perm(r, single=True) for r in (SD, INV, FB, EV, "Department Coordinator", "Sales Office User")],
}

USER_ASSIGNMENT = {
	"name": "LOC User Assignment",
	"module": "LOC Planning",
	"istable": 1,
	"title_ar": "ربط مستخدم",
	"fields": [
		("user", "Link", ("User", "المستخدم"), {"options": "User", "reqd": 1, "in_list_view": 1}),
		("role", "Link", ("Role", "الدور"), {"options": "Role", "reqd": 1, "in_list_view": 1}),
		(
			"loc_department",
			"Link",
			("Department / Office", "الجهة"),
			{"options": "LOC Department", "in_list_view": 1},
		),
		("region", "Link", ("Region", "المنطقة"), {"options": "LOC Region", "in_list_view": 1}),
		(
			"apply_to_descendants",
			"Check",
			("Include Sub-Departments", "تشمل الجهات التابعة"),
			{"default": "1"},
		),
		(
			"status",
			"Select",
			("Status", "الحالة"),
			{
				"options": [("Pending", "بانتظار التطبيق"), ("Applied", "مطبّق")],
				"default": "Pending",
				"read_only": 1,
				"in_list_view": 1,
			},
		),
		("applied_on", "Datetime", ("Applied On", "تاريخ التطبيق"), {"read_only": 1}),
	],
	"permissions": [],
}

USER_SETUP = {
	"name": "LOC User Setup",
	"module": "LOC Planning",
	"issingle": 1,
	"title_ar": "ربط المستخدمين بالأدوار والجهات",
	"fields": [
		(
			"help_html",
			"HTML",
			("Help", "مساعدة"),
			{
				"options": (
					"<p>Add one row per user, role and department, then press <b>Apply</b>. "
					"Roles are granted and record access is restricted to the selected department "
					"(and region) through User Permissions.</p>",
					"<p>أضف صفاً لكل مستخدم ودوره وجهته ثم اضغط <b>تطبيق</b>. "
					"تُمنح الأدوار ويُقيَّد الوصول إلى سجلات الجهة (والمنطقة) المحددة فقط عبر صلاحيات المستخدم.</p>",
				)
			},
		),
		(
			"assignments",
			"Table",
			("Assignments", "الربط"),
			{"options": "LOC User Assignment"},
		),
	],
	"permissions": [
		perm(SM, write=True, create=True, single=True),
		perm(DIR, write=True, create=True, single=True),
	],
}

SPECS = [REGION, DEPARTMENT, REPORTING_PERIOD, FUEL_PRODUCT, SETTINGS, USER_ASSIGNMENT, USER_SETUP]
ALL_ROLES = ALL_LOC_ROLES
