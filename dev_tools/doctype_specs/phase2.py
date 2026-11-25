"""DocType specifications for Phase 2 (Investment Registry)."""

from roles import DIR, EV, INV, SM, SP, perm, read_perms

MODULE = "Investment Registry"

CLASSIFICATION = {
	"name": "Company Classification",
	"module": MODULE,
	"autoname": "field:classification_name",
	"naming_rule": "By fieldname",
	"title_ar": "تصنيف الشركة",
	"fields": [
		(
			"classification_name",
			"Data",
			("Classification", "التصنيف"),
			{"reqd": 1, "unique": 1, "in_list_view": 1},
		),
		("is_active", "Check", ("Active", "نشط"), {"default": "1", "in_list_view": 1}),
		("description", "Small Text", ("Description", "الوصف"), {}),
	],
	"permissions": [perm(SM, full=True), perm(INV, full=True)] + read_perms([DIR, SP, EV]),
}

DOCUMENT_TYPE = {
	"name": "Company Document Type",
	"module": MODULE,
	"autoname": "field:document_type_name",
	"naming_rule": "By fieldname",
	"title_ar": "نوع مستند الشركة",
	"fields": [
		(
			"document_type_name",
			"Data",
			("Document Type", "نوع المستند"),
			{"reqd": 1, "unique": 1, "in_list_view": 1},
		),
		("has_expiry", "Check", ("Has Expiry Date", "له تاريخ انتهاء"), {"default": "1", "in_list_view": 1}),
		(
			"is_mandatory",
			"Check",
			("Required for Certificate", "مطلوب لإصدار الشهادة"),
			{"in_list_view": 1},
		),
		("is_active", "Check", ("Active", "نشط"), {"default": "1"}),
	],
	"permissions": [perm(SM, full=True), perm(INV, full=True)] + read_perms([DIR, SP, EV]),
}

DOC_STATUS = [
	("Valid", "ساري"),
	("Expiring Soon", "قارب على الانتهاء"),
	("Expired", "منتهي"),
	("No Expiry", "بدون انتهاء"),
]

COMPANY_DOCUMENT = {
	"name": "Registered Company Document",
	"module": MODULE,
	"istable": 1,
	"title_ar": "مستند الشركة",
	"fields": [
		(
			"document_type",
			"Link",
			("Document Type", "نوع المستند"),
			{"options": "Company Document Type", "reqd": 1, "in_list_view": 1},
		),
		("document_no", "Data", ("Document No.", "رقم المستند"), {"in_list_view": 1}),
		("issue_date", "Date", ("Issue Date", "تاريخ الإصدار"), {}),
		("expiry_date", "Date", ("Expiry Date", "تاريخ الانتهاء"), {"in_list_view": 1}),
		("attachment", "Attach", ("Attachment", "المرفق"), {"in_list_view": 1}),
		(
			"document_status",
			"Select",
			("Status", "الحالة"),
			{"options": DOC_STATUS, "read_only": 1, "in_list_view": 1},
		),
	],
}

COMPANY_STATUS = [
	("Active", "نشطة"),
	("Suspended", "موقوفة"),
	("Blacklisted", "محظورة"),
	("Inactive", "غير نشطة"),
]

CERTIFICATE_STATUS = [
	("None", "لا توجد"),
	("Valid", "سارية"),
	("Expiring Soon", "قاربت على الانتهاء"),
	("Expired", "منتهية"),
]

REGISTERED_COMPANY = {
	"name": "Registered Company",
	"module": MODULE,
	"autoname": "",
	"naming_rule": "By script",
	"title_field": "company_name",
	"show_title_field_in_link": 1,
	"search_fields": "company_name,classification,tax_id,commercial_register_no",
	"sort_field": "creation",
	"title_ar": "شركة مسجلة",
	"fields": [
		(
			"registration_no",
			"Data",
			("Registration No.", "رقم القيد"),
			{
				"unique": 1,
				"no_copy": 1,
				"set_only_once": 1,
				"in_list_view": 1,
				"description": (
					"Leave empty to number automatically",
					"اتركه فارغا ليرقم تلقائيا",
				),
			},
		),
		("company_name", "Data", ("Company Name", "اسم الشركة"), {"reqd": 1, "in_list_view": 1}),
		("company_name_en", "Data", ("Company Name (English)", "اسم الشركة بالإنجليزية"), {}),
		(
			"classification",
			"Link",
			("Classification", "التصنيف"),
			{"options": "Company Classification", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
		),
		("column_break_1", "Column Break", None, {}),
		(
			"status",
			"Select",
			("Status", "الحالة"),
			{"options": COMPANY_STATUS, "default": "Active", "in_list_view": 1, "in_standard_filter": 1},
		),
		(
			"status_reason",
			"Small Text",
			("Status Reason", "سبب الحالة"),
			{
				"depends_on": "eval:doc.status!='Active'",
				"mandatory_depends_on": "eval:['Suspended','Blacklisted'].includes(doc.status)",
			},
		),
		("registration_date", "Date", ("Registration Date", "تاريخ القيد"), {"default": "Today"}),
		("activity_description", "Small Text", ("Activity", "النشاط"), {}),
		("section_legal", "Section Break", ("Legal Information", "البيانات القانونية"), {}),
		(
			"commercial_register_no",
			"Data",
			("Commercial Register No.", "رقم السجل التجاري"),
			{"in_standard_filter": 1},
		),
		("tax_id", "Data", ("Tax No.", "الرقم الضريبي"), {"in_standard_filter": 1}),
		(
			"chamber_of_commerce_no",
			"Data",
			("Chamber of Commerce No.", "رقم القيد بالغرفة التجارية"),
			{},
		),
		("column_break_2", "Column Break", None, {}),
		("legal_representative", "Data", ("Legal Representative", "الممثل القانوني"), {}),
		("legal_representative_id", "Data", ("Representative ID No.", "رقم إثبات هوية الممثل"), {}),
		("legal_representative_phone", "Data", ("Representative Phone", "هاتف الممثل"), {"options": "Phone"}),
		("section_contact", "Section Break", ("Address and Contact", "العنوان والتواصل"), {}),
		("address", "Small Text", ("Address", "العنوان"), {}),
		("city", "Data", ("City", "المدينة"), {"in_standard_filter": 1}),
		("column_break_3", "Column Break", None, {}),
		("phone", "Data", ("Phone", "الهاتف"), {"options": "Phone"}),
		("email", "Data", ("Email", "البريد الإلكتروني"), {"options": "Email"}),
		("website", "Data", ("Website", "الموقع الإلكتروني"), {"options": "URL"}),
		("section_documents", "Section Break", ("Documents", "المستندات"), {}),
		(
			"documents",
			"Table",
			("Documents", "المستندات"),
			{"options": "Registered Company Document"},
		),
		("section_certificate", "Section Break", ("Certificate", "الشهادة"), {}),
		(
			"current_certificate",
			"Link",
			("Current Certificate", "الشهادة الحالية"),
			{"options": "Registration Certificate", "read_only": 1, "no_copy": 1},
		),
		(
			"certificate_expiry_date",
			"Date",
			("Certificate Expiry", "تاريخ انتهاء الشهادة"),
			{"read_only": 1, "no_copy": 1, "in_list_view": 1},
		),
		("column_break_4", "Column Break", None, {}),
		(
			"certificate_status",
			"Select",
			("Certificate Status", "حالة الشهادة"),
			{
				"options": CERTIFICATE_STATUS,
				"default": "None",
				"read_only": 1,
				"no_copy": 1,
				"in_standard_filter": 1,
			},
		),
		(
			"supplier",
			"Link",
			("ERPNext Supplier", "المورد في ERPNext"),
			{"options": "Supplier", "no_copy": 1},
		),
		("section_migration", "Section Break", ("Migration", "الترحيل"), {"collapsible": 1}),
		("is_migrated", "Check", ("Migrated", "مرحلة"), {"read_only": 1, "no_copy": 1}),
		("legacy_id", "Data", ("Legacy ID", "المعرف في النظام السابق"), {"read_only": 1, "no_copy": 1}),
	],
	"permissions": [perm(SM, full=True), perm(INV, write=True)] + read_perms([DIR, SP, EV]),
}

REQUEST_TYPES = [("New", "جديد"), ("Renewal", "تجديد")]

CERT_STATUS = [
	("Draft", "مسودة"),
	("Issued", "صادرة"),
	("Expired", "منتهية"),
	("Superseded", "مجددة"),
	("Cancelled", "ملغاة"),
	("Rejected", "مرفوضة"),
]

CERTIFICATE = {
	"name": "Registration Certificate",
	"module": MODULE,
	"autoname": "",
	"naming_rule": "By script",
	"is_submittable": 1,
	"default_print_format": "Registration Certificate",
	"title_field": "company_name",
	"show_title_field_in_link": 0,
	"search_fields": "company_name,registered_company,status",
	"title_ar": "شهادة إثبات القيد",
	"fields": [
		(
			"registered_company",
			"Link",
			("Company", "الشركة"),
			{"options": "Registered Company", "reqd": 1, "in_standard_filter": 1},
		),
		(
			"company_name",
			"Data",
			("Company Name", "اسم الشركة"),
			{"fetch_from": "registered_company.company_name", "read_only": 1, "in_list_view": 1},
		),
		(
			"classification",
			"Link",
			("Classification", "التصنيف"),
			{
				"options": "Company Classification",
				"fetch_from": "registered_company.classification",
				"read_only": 1,
			},
		),
		(
			"request_type",
			"Select",
			("Request Type", "نوع الطلب"),
			{"options": REQUEST_TYPES, "default": "New", "reqd": 1, "in_list_view": 1},
		),
		(
			"renewal_of",
			"Link",
			("Renewal Of", "تجديد للشهادة"),
			{
				"options": "Registration Certificate",
				"depends_on": "eval:doc.request_type=='Renewal'",
				"mandatory_depends_on": "eval:doc.request_type=='Renewal'",
			},
		),
		("column_break_1", "Column Break", None, {}),
		(
			"certificate_no",
			"Data",
			("Certificate No.", "رقم الشهادة"),
			{
				"unique": 1,
				"no_copy": 1,
				"read_only": 1,
				"in_list_view": 1,
			},
		),
		("request_date", "Date", ("Request Date", "تاريخ الطلب"), {"default": "Today", "reqd": 1}),
		("issue_date", "Date", ("Issue Date", "تاريخ الإصدار"), {"no_copy": 1}),
		("expiry_date", "Date", ("Expiry Date", "تاريخ الانتهاء"), {"no_copy": 1, "in_list_view": 1}),
		(
			"status",
			"Select",
			("Certificate Status", "حالة الشهادة"),
			{
				"options": CERT_STATUS,
				"default": "Draft",
				"read_only": 1,
				"no_copy": 1,
				"allow_on_submit": 1,
				"in_standard_filter": 1,
			},
		),
		("section_review", "Section Break", ("Review", "المراجعة"), {}),
		("review_notes", "Small Text", ("Review Notes", "ملاحظات المراجعة"), {}),
		("column_break_2", "Column Break", None, {}),
		(
			"cancel_reason",
			"Small Text",
			("Cancellation Reason", "سبب الإلغاء"),
			{"allow_on_submit": 1, "no_copy": 1, "depends_on": "eval:doc.docstatus>0"},
		),
		("section_verification", "Section Break", ("Verification", "التحقق"), {"collapsible": 1}),
		(
			"verification_code",
			"Data",
			("Verification Code", "رمز التحقق"),
			{"read_only": 1, "unique": 1, "no_copy": 1},
		),
		("column_break_3", "Column Break", None, {}),
		("is_migrated", "Check", ("Migrated", "مرحلة"), {"read_only": 1, "no_copy": 1}),
		(
			"workflow_state",
			"Link",
			("Workflow State", "مرحلة الاعتماد"),
			{
				"options": "Workflow State",
				"read_only": 1,
				"hidden": 1,
				"allow_on_submit": 1,
				"no_copy": 1,
				"print_hide": 1,
			},
		),
		(
			"amended_from",
			"Link",
			("Amended From", "معدلة من"),
			{"options": "Registration Certificate", "read_only": 1, "no_copy": 1, "print_hide": 1},
		),
	],
	"permissions": [
		perm(SM, full=True, submit=True, cancel=True, amend=True),
		perm(INV, write=True, amend=True),
		perm(DIR, write=True, submit=True, cancel=True),
	]
	+ read_perms([SP, EV]),
}

SPECS = [CLASSIFICATION, DOCUMENT_TYPE, COMPANY_DOCUMENT, REGISTERED_COMPANY, CERTIFICATE]
