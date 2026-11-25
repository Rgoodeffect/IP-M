"""DocType specifications for Phase 3 (Stations and support activities)."""

from roles import DIR, EV, FB, SD, SM, SO, SP, perm, read_perms

MODULE = "Stations"

OPERATION_TYPE = {
	"name": "Station Operation Type",
	"module": MODULE,
	"autoname": "field:operation_type_name",
	"naming_rule": "By fieldname",
	"title_ar": "نوع تشغيل المحطة",
	"fields": [
		(
			"operation_type_name",
			"Data",
			("Operation Type", "نوع التشغيل"),
			{"reqd": 1, "unique": 1, "in_list_view": 1},
		),
		("is_company_owned", "Check", ("Company Owned", "مملوكة للشركة"), {"in_list_view": 1}),
		("is_active", "Check", ("Active", "نشط"), {"default": "1"}),
	],
	"permissions": [perm(SM, full=True), perm(SD, full=True)] + read_perms([SO, DIR, SP, EV, FB]),
}

ACTIVITY_TYPE = {
	"name": "Support Activity Type",
	"module": MODULE,
	"autoname": "field:activity_type_name",
	"naming_rule": "By fieldname",
	"title_ar": "نوع النشاط المساند",
	"fields": [
		(
			"activity_type_name",
			"Data",
			("Activity Type", "النشاط المساند"),
			{"reqd": 1, "unique": 1, "in_list_view": 1},
		),
		("has_revenue", "Check", ("Has Revenue", "له إيراد"), {"default": "1", "in_list_view": 1}),
		("display_order", "Int", ("Display Order", "ترتيب العرض"), {}),
		("is_active", "Check", ("Active", "نشط"), {"default": "1"}),
	],
	"permissions": [perm(SM, full=True), perm(SD, full=True)] + read_perms([SO, DIR, SP, EV, FB]),
}

TANK = {
	"name": "Fuel Station Tank",
	"module": MODULE,
	"istable": 1,
	"title_ar": "خزان",
	"fields": [
		("tank_no", "Data", ("Tank No.", "رقم الخزان"), {"in_list_view": 1}),
		("product", "Link", ("Product", "المنتج"), {"options": "Fuel Product", "reqd": 1, "in_list_view": 1}),
		("capacity", "Float", ("Capacity", "السعة"), {"reqd": 1, "in_list_view": 1, "non_negative": 1}),
		(
			"uom",
			"Link",
			("Unit of Measure", "وحدة القياس"),
			{"options": "UOM", "fetch_from": "product.uom", "read_only": 1, "in_list_view": 1},
		),
	],
}

STATION_ACTIVITY = {
	"name": "Station Support Activity",
	"module": MODULE,
	"istable": 1,
	"title_ar": "نشاط مساند بالمحطة",
	"fields": [
		(
			"activity_type",
			"Link",
			("Activity Type", "النشاط المساند"),
			{"options": "Support Activity Type", "reqd": 1, "in_list_view": 1},
		),
		("is_active", "Check", ("Active", "نشط"), {"default": "1", "in_list_view": 1}),
		("operator", "Data", ("Operated By", "الجهة المشغلة"), {"in_list_view": 1}),
		("notes", "Small Text", ("Notes", "ملاحظات"), {}),
	],
}

STATION_STATUS = [
	("Operating", "عاملة"),
	("Stopped", "متوقفة"),
	("Under Maintenance", "تحت الصيانة"),
	("Under Construction", "تحت الإنشاء"),
]

FUEL_STATION = {
	"name": "Fuel Station",
	"module": MODULE,
	"autoname": "field:station_code",
	"naming_rule": "By fieldname",
	"title_field": "station_name",
	"show_title_field_in_link": 1,
	"search_fields": "station_name,sales_office,municipality,status",
	"sort_field": "station_code",
	"sort_order": "ASC",
	"title_ar": "محطة وقود",
	"fields": [
		("station_code", "Data", ("Station Code", "رمز المحطة"), {"reqd": 1, "unique": 1, "in_list_view": 1}),
		("station_name", "Data", ("Station Name", "اسم المحطة"), {"reqd": 1, "in_list_view": 1}),
		(
			"operation_type",
			"Link",
			("Operation Type", "نوع التشغيل"),
			{"options": "Station Operation Type", "reqd": 1, "in_standard_filter": 1},
		),
		("operation_date", "Date", ("Operation Start Date", "تاريخ التشغيل"), {}),
		("column_break_1", "Column Break", None, {}),
		(
			"sales_office",
			"Link",
			("Sales Office", "مكتب المبيعات"),
			{"options": "LOC Department", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
		),
		(
			"region",
			"Link",
			("Region", "المنطقة"),
			{
				"options": "LOC Region",
				"reqd": 1,
				"fetch_from": "sales_office.region",
				"fetch_if_empty": 1,
				"in_standard_filter": 1,
			},
		),
		("municipality", "Data", ("Municipality", "البلدية"), {"in_standard_filter": 1}),
		(
			"status",
			"Select",
			("Status", "الحالة"),
			{
				"options": STATION_STATUS,
				"default": "Operating",
				"reqd": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
			},
		),
		(
			"stop_reason",
			"Small Text",
			("Stop Reason", "سبب التوقف"),
			{
				"depends_on": "eval:doc.status!='Operating'",
				"mandatory_depends_on": "eval:doc.status!='Operating'",
			},
		),
		(
			"status_since",
			"Date",
			("Status Since", "تاريخ الحالة"),
			{"depends_on": "eval:doc.status!='Operating'"},
		),
		("section_location", "Section Break", ("Location", "الموقع"), {"collapsible": 1}),
		("address", "Small Text", ("Address", "العنوان"), {}),
		("column_break_2", "Column Break", None, {}),
		("latitude", "Float", ("Latitude", "خط العرض"), {"precision": "6"}),
		("longitude", "Float", ("Longitude", "خط الطول"), {"precision": "6"}),
		("location", "Geolocation", ("Map", "الخريطة"), {}),
		("section_capacity", "Section Break", ("Tanks and Equipment", "الخزانات والمعدات"), {}),
		("tanks", "Table", ("Tanks", "الخزانات"), {"options": "Fuel Station Tank"}),
		("tanks_count", "Int", ("Number of Tanks", "عدد الخزانات"), {"read_only": 1}),
		("total_capacity", "Float", ("Total Capacity", "إجمالي السعة"), {"read_only": 1}),
		("column_break_3", "Column Break", None, {}),
		("pumps_count", "Int", ("Pumps", "عدد المضخات"), {"non_negative": 1}),
		("nozzles_count", "Int", ("Nozzles", "عدد المسدسات"), {"non_negative": 1}),
		("employees_count", "Int", ("Employees", "عدد العاملين"), {"non_negative": 1}),
		("last_safety_inspection", "Date", ("Last Safety Inspection", "آخر تفتيش سلامة"), {}),
		("section_activities", "Section Break", ("Support Activities", "الأنشطة المساندة"), {}),
		(
			"support_activities",
			"Table",
			("Support Activities", "الأنشطة المساندة"),
			{"options": "Station Support Activity"},
		),
		("is_active", "Check", ("Active", "نشط"), {"default": "1"}),
	],
	"permissions": [perm(SM, full=True), perm(SD, full=True)] + read_perms([SO, DIR, SP, EV, FB]),
}

MONTHLY_PRODUCT = {
	"name": "Station Monthly Product",
	"module": MODULE,
	"istable": 1,
	"title_ar": "بيانات منتج شهرية",
	"fields": [
		(
			"product",
			"Link",
			("Product", "المنتج"),
			{"options": "Fuel Product", "reqd": 1, "in_list_view": 1, "columns": 2},
		),
		("target_qty", "Float", ("Target", "المستهدف"), {"in_list_view": 1, "non_negative": 1}),
		("actual_qty", "Float", ("Actual Sales", "المبيعات الفعلية"), {"in_list_view": 1, "non_negative": 1}),
		(
			"achievement_pct",
			"Percent",
			("Achievement %", "نسبة التحقيق"),
			{"read_only": 1, "in_list_view": 1},
		),
		(
			"opening_stock",
			"Float",
			("Opening Stock", "مخزون أول المدة"),
			{"in_list_view": 1, "non_negative": 1},
		),
		("received_qty", "Float", ("Received", "الوارد"), {"in_list_view": 1, "non_negative": 1}),
		(
			"closing_stock",
			"Float",
			("Closing Stock", "مخزون آخر المدة"),
			{"in_list_view": 1, "non_negative": 1},
		),
		(
			"stock_variance",
			"Float",
			("Stock Variance", "فرق المخزون"),
			{
				"read_only": 1,
				"description": (
					"Opening + Received - Sales - Closing",
					"أول المدة + الوارد - المبيعات - آخر المدة",
				),
			},
		),
		(
			"uom",
			"Link",
			("Unit of Measure", "وحدة القياس"),
			{"options": "UOM", "fetch_from": "product.uom", "read_only": 1},
		),
	],
}

SUPPORT_REVENUE = {
	"name": "Station Support Revenue",
	"module": MODULE,
	"istable": 1,
	"title_ar": "إيراد نشاط مساند",
	"fields": [
		(
			"activity_type",
			"Link",
			("Activity Type", "النشاط المساند"),
			{"options": "Support Activity Type", "reqd": 1, "in_list_view": 1},
		),
		(
			"revenue",
			"Currency",
			("Revenue", "الإيراد"),
			{"in_list_view": 1, "non_negative": 1, "options": "LYD"},
		),
		("notes", "Data", ("Notes", "ملاحظات"), {"in_list_view": 1}),
	],
}

MONTHLY_STATUS = [
	("Draft", "مسودة"),
	("Pending Review", "بانتظار المراجعة"),
	("Returned", "مرجعة للتعديل"),
	("Approved", "معتمدة"),
	("Cancelled", "ملغاة"),
]

MONTHLY_DATA = {
	"name": "Station Monthly Data",
	"module": MODULE,
	"autoname": "format:{station}-{reporting_period}",
	"naming_rule": "Expression",
	"is_submittable": 1,
	"title_field": "station_name",
	"search_fields": "station_name,reporting_period,sales_office",
	"title_ar": "البيانات الشهرية للمحطة",
	"fields": [
		(
			"station",
			"Link",
			("Station", "المحطة"),
			{"options": "Fuel Station", "reqd": 1, "in_standard_filter": 1, "set_only_once": 1},
		),
		(
			"station_name",
			"Data",
			("Station Name", "اسم المحطة"),
			{"fetch_from": "station.station_name", "read_only": 1, "in_list_view": 1},
		),
		(
			"reporting_period",
			"Link",
			("Month", "الشهر"),
			{
				"options": "Reporting Period",
				"reqd": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
				"set_only_once": 1,
			},
		),
		("column_break_1", "Column Break", None, {}),
		(
			"sales_office",
			"Link",
			("Sales Office", "مكتب المبيعات"),
			{
				"options": "LOC Department",
				"fetch_from": "station.sales_office",
				"read_only": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
			},
		),
		(
			"region",
			"Link",
			("Region", "المنطقة"),
			{
				"options": "LOC Region",
				"fetch_from": "station.region",
				"read_only": 1,
				"in_standard_filter": 1,
			},
		),
		(
			"status",
			"Select",
			("Status", "الحالة"),
			{
				"options": MONTHLY_STATUS,
				"default": "Draft",
				"read_only": 1,
				"allow_on_submit": 1,
				"no_copy": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
			},
		),
		("section_products", "Section Break", ("Sales and Stock", "المبيعات والمخزون"), {}),
		("products", "Table", ("Products", "المنتجات"), {"options": "Station Monthly Product"}),
		("section_operation", "Section Break", ("Operation", "التشغيل"), {}),
		("stopped_days", "Int", ("Stopped Days", "أيام التوقف"), {"non_negative": 1}),
		("column_break_2", "Column Break", None, {}),
		("stop_notes", "Small Text", ("Stop Notes", "ملاحظات التوقف"), {"depends_on": "stopped_days"}),
		("section_revenue", "Section Break", ("Support Activities Revenue", "إيرادات الأنشطة المساندة"), {}),
		("support_revenues", "Table", ("Revenues", "الإيرادات"), {"options": "Station Support Revenue"}),
		(
			"total_support_revenue",
			"Currency",
			("Total Support Revenue", "إجمالي إيرادات الأنشطة المساندة"),
			{"read_only": 1, "options": "LYD"},
		),
		("section_review", "Section Break", ("Review", "المراجعة"), {}),
		("notes", "Small Text", ("Notes", "ملاحظات"), {}),
		("column_break_3", "Column Break", None, {}),
		(
			"review_comment",
			"Small Text",
			("Review Comment", "ملاحظات المراجعة"),
			{
				"description": (
					"Required when returning the data for revision",
					"إلزامية عند إرجاع البيانات للتعديل",
				),
			},
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
			{"options": "Station Monthly Data", "read_only": 1, "no_copy": 1, "print_hide": 1},
		),
	],
	"permissions": [
		perm(SM, full=True, submit=True, cancel=True, amend=True),
		perm(SO, write=True),
		perm(SD, write=True, submit=True, cancel=True, amend=True),
	]
	+ read_perms([DIR, SP, EV, FB]),
}

IMPORT_STATUS = [
	("Draft", "مسودة"),
	("Validated", "تم التحقق"),
	("Imported", "تم الاستيراد"),
	("Partially Imported", "استيراد جزئي"),
	("Failed", "فشل"),
]

IMPORT_LOG = {
	"name": "Station Data Import Log",
	"module": MODULE,
	"istable": 1,
	"title_ar": "سجل الاستيراد",
	"fields": [
		("row_no", "Int", ("Row", "السطر"), {"in_list_view": 1, "columns": 1}),
		("station", "Data", ("Station", "المحطة"), {"in_list_view": 1, "columns": 2}),
		(
			"result",
			"Select",
			("Result", "النتيجة"),
			{
				"options": [("Created", "أنشئت"), ("Updated", "حدثت"), ("Skipped", "تخطي"), ("Error", "خطأ")],
				"in_list_view": 1,
				"columns": 2,
			},
		),
		(
			"document",
			"Link",
			("Document", "المستند"),
			{"options": "Station Monthly Data", "in_list_view": 1, "columns": 2},
		),
		("message", "Small Text", ("Message", "الرسالة"), {"in_list_view": 1, "columns": 3}),
	],
}

DATA_IMPORT = {
	"name": "Station Data Import",
	"module": MODULE,
	"autoname": "format:SDI-{reporting_period}-{####}",
	"naming_rule": "Expression",
	"title_ar": "استيراد بيانات المحطات",
	"fields": [
		(
			"reporting_period",
			"Link",
			("Month", "الشهر"),
			{"options": "Reporting Period", "reqd": 1, "in_list_view": 1},
		),
		(
			"sales_office",
			"Link",
			("Sales Office", "مكتب المبيعات"),
			{
				"options": "LOC Department",
				"in_list_view": 1,
				"description": (
					"Leave empty to include all stations you can access",
					"اتركه فارغا لتشمل كل المحطات المتاحة لك",
				),
			},
		),
		("column_break_1", "Column Break", None, {}),
		(
			"import_file",
			"Attach",
			("Excel File", "ملف Excel"),
			{"description": ("Use the downloaded template", "استخدم القالب المحمل من هذه الصفحة")},
		),
		(
			"status",
			"Select",
			("Status", "الحالة"),
			{"options": IMPORT_STATUS, "default": "Draft", "read_only": 1, "in_list_view": 1, "no_copy": 1},
		),
		("section_log", "Section Break", ("Result", "النتيجة"), {}),
		("summary", "Small Text", ("Summary", "الملخص"), {"read_only": 1, "no_copy": 1}),
		(
			"log",
			"Table",
			("Log", "السجل"),
			{"options": "Station Data Import Log", "read_only": 1, "no_copy": 1},
		),
	],
	"permissions": [
		perm(SM, full=True),
		perm(SD, write=True, delete=True),
		perm(SO, write=True, delete=True),
	],
}

SPECS = [
	OPERATION_TYPE,
	ACTIVITY_TYPE,
	TANK,
	STATION_ACTIVITY,
	FUEL_STATION,
	MONTHLY_PRODUCT,
	SUPPORT_REVENUE,
	MONTHLY_DATA,
	IMPORT_LOG,
	DATA_IMPORT,
]
