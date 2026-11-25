"""DocType specifications for Phase 4 (Budget execution position)."""

from roles import DIR, EV, FB, SD, SM, SP, perm, read_perms

MODULE = "Budget"

# Amounts live on permission level 1: only these roles can read them ...
AMOUNT_READERS = [DIR, SP, EV, SD]
# ... and these can write them (besides System Manager)
AMOUNT_WRITERS = [FB]


def amount_perms(writers=AMOUNT_WRITERS, readers=AMOUNT_READERS):
	return (
		[perm(SM, write=True, permlevel=1)]
		+ [perm(r, write=True, permlevel=1) for r in writers]
		+ [perm(r, permlevel=1) for r in readers]
	)


CHAPTER = {
	"name": "Budget Chapter",
	"module": MODULE,
	"autoname": "field:chapter_name",
	"naming_rule": "By fieldname",
	"sort_field": "chapter_no",
	"sort_order": "ASC",
	"title_ar": "باب الموازنة",
	"fields": [
		("chapter_name", "Data", ("Chapter", "الباب"), {"reqd": 1, "unique": 1, "in_list_view": 1}),
		("chapter_no", "Int", ("Chapter No.", "رقم الباب"), {"reqd": 1, "in_list_view": 1}),
		("description", "Small Text", ("Description", "الوصف"), {}),
	],
	"permissions": [perm(SM, full=True), perm(FB, full=True)] + read_perms([DIR, SP, EV, SD]),
}

ITEM_ACCOUNT = {
	"name": "Budget Item Account",
	"module": MODULE,
	"istable": 1,
	"title_ar": "حساب بند الموازنة",
	"fields": [
		("account", "Link", ("Account", "الحساب"), {"options": "Account", "reqd": 1, "in_list_view": 1}),
		(
			"cost_center",
			"Link",
			("Cost Center", "مركز التكلفة"),
			{"options": "Cost Center", "in_list_view": 1},
		),
		(
			"region",
			"Link",
			("Region", "المنطقة"),
			{"options": "LOC Region", "reqd": 1, "in_list_view": 1},
		),
	],
}

EXECUTION_SOURCES = [("Manual Entries", "قيود التنفيذ اليدوية"), ("General Ledger", "دفتر الأستاذ العام")]

BUDGET_ITEM = {
	"name": "Budget Item",
	"module": MODULE,
	"autoname": "field:item_name",
	"naming_rule": "By fieldname",
	"title_ar": "بند الموازنة",
	"search_fields": "chapter,owner_department",
	"sort_field": "item_code",
	"sort_order": "ASC",
	"fields": [
		("item_name", "Data", ("Item", "البند"), {"reqd": 1, "unique": 1, "in_list_view": 1}),
		("item_code", "Data", ("Item Code", "رمز البند"), {}),
		(
			"chapter",
			"Link",
			("Chapter", "الباب"),
			{"options": "Budget Chapter", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
		),
		("column_break_1", "Column Break", None, {}),
		(
			"owner_department",
			"Link",
			("Owner Department", "الإدارة المالكة"),
			{"options": "LOC Department", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
		),
		(
			"coordinated_by",
			"Data",
			("Coordinated By", "عن طريق"),
			{"description": ("e.g. a coordinating unit", "مثال: منسقية الخدمات")},
		),
		("is_active", "Check", ("Active", "نشط"), {"default": "1"}),
		("section_execution", "Section Break", ("Execution Source", "مصدر المنفذ"), {}),
		(
			"execution_source",
			"Select",
			("Executed Amount Source", "مصدر قيمة المنفذ"),
			{"options": EXECUTION_SOURCES, "default": "Manual Entries", "reqd": 1, "in_list_view": 1},
		),
		(
			"company",
			"Link",
			("Company", "الشركة"),
			{
				"options": "Company",
				"depends_on": "eval:doc.execution_source=='General Ledger'",
				"mandatory_depends_on": "eval:doc.execution_source=='General Ledger'",
			},
		),
		(
			"accounts",
			"Table",
			("GL Accounts", "حسابات دفتر الأستاذ"),
			{
				"options": "Budget Item Account",
				"depends_on": "eval:doc.execution_source=='General Ledger'",
				"description": (
					"Executed = debit minus credit of these accounts (and cost centers) for the region",
					"المنفذ = المدين ناقص الدائن لهذه الحسابات (ومراكز التكلفة) لكل منطقة",
				),
			},
		),
	],
	"permissions": [perm(SM, full=True), perm(FB, full=True)] + read_perms([DIR, SP, EV, SD]),
}

BUDGET_LINE = {
	"name": "Approved Budget Line",
	"module": MODULE,
	"istable": 1,
	"title_ar": "بند معتمد",
	"fields": [
		(
			"budget_item",
			"Link",
			("Item", "البند"),
			{"options": "Budget Item", "reqd": 1, "in_list_view": 1, "columns": 3},
		),
		(
			"chapter",
			"Link",
			("Chapter", "الباب"),
			{
				"options": "Budget Chapter",
				"fetch_from": "budget_item.chapter",
				"read_only": 1,
				"in_list_view": 1,
			},
		),
		(
			"owner_department",
			"Link",
			("Owner Department", "الإدارة المالكة"),
			{"options": "LOC Department", "fetch_from": "budget_item.owner_department", "read_only": 1},
		),
		(
			"approved_amount",
			"Currency",
			("Approved Amount", "القيمة المعتمدة"),
			{"options": "LYD", "reqd": 1, "in_list_view": 1, "permlevel": 1, "non_negative": 1, "columns": 2},
		),
		(
			"revised_amount",
			"Currency",
			("Amount After Revisions", "القيمة بعد التعديلات"),
			{
				"options": "LYD",
				"read_only": 1,
				"allow_on_submit": 1,
				"in_list_view": 1,
				"permlevel": 1,
				"columns": 2,
			},
		),
	],
}

APPROVED_BUDGET = {
	"name": "Approved Budget",
	"module": MODULE,
	"autoname": "format:BUD-{fiscal_year}-{region}-{##}",
	"naming_rule": "Expression",
	"is_submittable": 1,
	"title_ar": "الموازنة المعتمدة",
	"search_fields": "fiscal_year,region",
	"fields": [
		("fiscal_year", "Int", ("Year", "السنة"), {"reqd": 1, "in_list_view": 1, "in_standard_filter": 1}),
		(
			"region",
			"Link",
			("Region", "المنطقة"),
			{"options": "LOC Region", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
		),
		("column_break_1", "Column Break", None, {}),
		("approval_date", "Date", ("Approval Date", "تاريخ الاعتماد"), {}),
		("approval_reference", "Data", ("Approval Reference", "مرجع الاعتماد"), {}),
		("section_items", "Section Break", ("Items", "البنود"), {}),
		("items", "Table", ("Items", "البنود"), {"options": "Approved Budget Line", "reqd": 1}),
		(
			"total_approved",
			"Currency",
			("Total Approved", "إجمالي المعتمد"),
			{"options": "LYD", "read_only": 1, "permlevel": 1, "in_list_view": 1},
		),
		(
			"total_revised",
			"Currency",
			("Total After Revisions", "الإجمالي بعد التعديلات"),
			{"options": "LYD", "read_only": 1, "allow_on_submit": 1, "permlevel": 1},
		),
		("notes", "Small Text", ("Notes", "ملاحظات"), {}),
		(
			"cancel_reason",
			"Small Text",
			("Cancellation Reason", "سبب الإلغاء"),
			{"allow_on_submit": 1, "no_copy": 1, "depends_on": "eval:doc.docstatus>0"},
		),
		(
			"amended_from",
			"Link",
			("Amended From", "معدلة من"),
			{"options": "Approved Budget", "read_only": 1, "no_copy": 1, "print_hide": 1},
		),
	],
	"permissions": [
		perm(SM, full=True, submit=True, cancel=True, amend=True),
		perm(FB, write=True, delete=True, submit=True, cancel=True, amend=True),
	]
	+ read_perms([DIR, SP, EV, SD])
	+ amount_perms(),
}

REVISION_TYPES = [("Transfer", "مناقلة"), ("Increase", "زيادة"), ("Decrease", "تخفيض")]

REVISION_LINE = {
	"name": "Budget Revision Line",
	"module": MODULE,
	"istable": 1,
	"title_ar": "سطر تعديل الموازنة",
	"fields": [
		(
			"from_item",
			"Link",
			("From Item", "من البند"),
			{"options": "Budget Item", "in_list_view": 1, "columns": 3},
		),
		(
			"to_item",
			"Link",
			("To Item", "إلى البند"),
			{"options": "Budget Item", "in_list_view": 1, "columns": 3},
		),
		(
			"amount",
			"Currency",
			("Amount", "القيمة"),
			{"options": "LYD", "reqd": 1, "in_list_view": 1, "permlevel": 1, "non_negative": 1, "columns": 2},
		),
	],
}

BUDGET_REVISION = {
	"name": "Budget Revision",
	"module": MODULE,
	"autoname": "format:BREV-{fiscal_year}-{####}",
	"naming_rule": "Expression",
	"is_submittable": 1,
	"title_ar": "تعديل / مناقلة الموازنة",
	"fields": [
		(
			"approved_budget",
			"Link",
			("Approved Budget", "الموازنة المعتمدة"),
			{"options": "Approved Budget", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
		),
		(
			"fiscal_year",
			"Int",
			("Year", "السنة"),
			{"fetch_from": "approved_budget.fiscal_year", "read_only": 1, "in_standard_filter": 1},
		),
		(
			"region",
			"Link",
			("Region", "المنطقة"),
			{
				"options": "LOC Region",
				"fetch_from": "approved_budget.region",
				"read_only": 1,
				"in_list_view": 1,
			},
		),
		("column_break_1", "Column Break", None, {}),
		(
			"revision_type",
			"Select",
			("Revision Type", "نوع التعديل"),
			{"options": REVISION_TYPES, "default": "Transfer", "reqd": 1, "in_list_view": 1},
		),
		(
			"revision_date",
			"Date",
			("Revision Date", "تاريخ التعديل"),
			{"reqd": 1, "default": "Today", "in_list_view": 1},
		),
		("reference", "Data", ("Approval Reference", "مرجع الاعتماد"), {}),
		("section_lines", "Section Break", ("Lines", "البنود"), {}),
		("lines", "Table", ("Lines", "البنود"), {"options": "Budget Revision Line", "reqd": 1}),
		("reason", "Small Text", ("Reason", "المبررات"), {"reqd": 1}),
		(
			"cancel_reason",
			"Small Text",
			("Cancellation Reason", "سبب الإلغاء"),
			{"allow_on_submit": 1, "no_copy": 1, "depends_on": "eval:doc.docstatus>0"},
		),
		(
			"amended_from",
			"Link",
			("Amended From", "معدلة من"),
			{"options": "Budget Revision", "read_only": 1, "no_copy": 1, "print_hide": 1},
		),
	],
	"permissions": [
		perm(SM, full=True, submit=True, cancel=True, amend=True),
		perm(FB, write=True, delete=True, submit=True, cancel=True, amend=True),
	]
	+ read_perms([DIR, SP, EV, SD])
	+ amount_perms(),
}

ENTRY_TYPES = [("Commitment", "التزام"), ("Actual Expense", "صرف فعلي")]

EXECUTION_ENTRY = {
	"name": "Budget Execution Entry",
	"module": MODULE,
	"autoname": "format:BEX-{fiscal_year}-{#####}",
	"naming_rule": "Expression",
	"is_submittable": 1,
	"title_ar": "قيد تنفيذ الموازنة",
	"search_fields": "budget_item,entry_type,reference_no",
	"fields": [
		(
			"budget_item",
			"Link",
			("Item", "البند"),
			{"options": "Budget Item", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
		),
		(
			"chapter",
			"Link",
			("Chapter", "الباب"),
			{
				"options": "Budget Chapter",
				"fetch_from": "budget_item.chapter",
				"read_only": 1,
				"in_standard_filter": 1,
			},
		),
		(
			"entry_type",
			"Select",
			("Entry Type", "نوع القيد"),
			{"options": ENTRY_TYPES, "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
		),
		(
			"amount",
			"Currency",
			("Amount", "القيمة"),
			{"options": "LYD", "reqd": 1, "in_list_view": 1, "permlevel": 1, "non_negative": 1},
		),
		("column_break_1", "Column Break", None, {}),
		(
			"department",
			"Link",
			("Department", "الإدارة"),
			{
				"options": "LOC Department",
				"reqd": 1,
				"fetch_from": "budget_item.owner_department",
				"fetch_if_empty": 1,
				"in_standard_filter": 1,
			},
		),
		(
			"region",
			"Link",
			("Region", "المنطقة"),
			{"options": "LOC Region", "reqd": 1, "in_standard_filter": 1},
		),
		("posting_date", "Date", ("Date", "التاريخ"), {"reqd": 1, "default": "Today", "in_list_view": 1}),
		("fiscal_year", "Int", ("Year", "السنة"), {"read_only": 1}),
		(
			"reporting_period",
			"Link",
			("Month", "الشهر"),
			{"options": "Reporting Period", "read_only": 1},
		),
		("section_reference", "Section Break", ("Reference", "المستند المرجعي"), {}),
		("reference_no", "Data", ("Reference No.", "رقم المستند المرجعي"), {"in_list_view": 1}),
		("reference_date", "Date", ("Reference Date", "تاريخ المستند المرجعي"), {}),
		("column_break_2", "Column Break", None, {}),
		("attachment", "Attach", ("Attachment", "المرفق"), {}),
		("description", "Small Text", ("Description", "البيان"), {}),
		(
			"cancel_reason",
			"Small Text",
			("Cancellation Reason", "سبب الإلغاء"),
			{"allow_on_submit": 1, "no_copy": 1, "depends_on": "eval:doc.docstatus>0"},
		),
		(
			"amended_from",
			"Link",
			("Amended From", "معدلة من"),
			{"options": "Budget Execution Entry", "read_only": 1, "no_copy": 1, "print_hide": 1},
		),
	],
	"permissions": [
		perm(SM, full=True, submit=True, cancel=True, amend=True),
		perm(FB, write=True, delete=True, submit=True, cancel=True, amend=True),
		perm(SD, write=True, delete=True, submit=True, cancel=True, amend=True),
	]
	+ read_perms([DIR, SP, EV])
	+ amount_perms(writers=[FB, SD], readers=[DIR, SP, EV]),
}

SPECS = [
	CHAPTER,
	ITEM_ACCOUNT,
	BUDGET_ITEM,
	BUDGET_LINE,
	APPROVED_BUDGET,
	REVISION_LINE,
	BUDGET_REVISION,
	EXECUTION_ENTRY,
]
