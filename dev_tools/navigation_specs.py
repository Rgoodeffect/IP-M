"""Workspace and Sidebar contents. Each section: (label, icon, [(label, link_type, link_to), ...])."""

WORKSPACE = "LOC Planning"

SECTIONS = [
	(
		"Activity Report",
		"clipboard-list",
		[
			("Company Activity Report", "DocType", "Company Activity Report"),
			("Department Activity Submission", "DocType", "Department Activity Submission"),
			("Department Activity Status", "Report", "Department Activity Status"),
			("Activity Indicator Template", "DocType", "Activity Indicator Template"),
			("Activity Domain", "DocType", "Activity Domain"),
			("Activity Report Template", "DocType", "Activity Report Template"),
		],
	),
	(
		"Budget",
		"wallet",
		[
			("Budget Execution Position", "Report", "Budget Execution Position"),
			("Approved Budget", "DocType", "Approved Budget"),
			("Budget Revision", "DocType", "Budget Revision"),
			("Budget Execution Entry", "DocType", "Budget Execution Entry"),
			("Budget Item", "DocType", "Budget Item"),
			("Budget Chapter", "DocType", "Budget Chapter"),
		],
	),
	(
		"Stations and Support Activities",
		"fuel",
		[
			("Fuel Station", "DocType", "Fuel Station"),
			("Station Monthly Data", "DocType", "Station Monthly Data"),
			("Station Data Import", "DocType", "Station Data Import"),
			("Station Sales Analysis", "Report", "Station Sales Analysis"),
			("Station Target vs Actual", "Report", "Station Target vs Actual"),
			("Stopped Stations", "Report", "Stopped Stations"),
			("Missing Station Data", "Report", "Missing Station Data"),
			("Station Operation Type", "DocType", "Station Operation Type"),
			("Support Activity Type", "DocType", "Support Activity Type"),
		],
	),
	(
		"Investment Section",
		"building-2",
		[
			("Registered Company", "DocType", "Registered Company"),
			("Registration Certificate", "DocType", "Registration Certificate"),
			("Company Registry", "Report", "Company Registry"),
			("Company Classification", "DocType", "Company Classification"),
			("Company Document Type", "DocType", "Company Document Type"),
		],
	),
	(
		"Settings",
		"settings",
		[
			("LOC Planning Settings", "DocType", "LOC Planning Settings"),
			("LOC Department", "DocType", "LOC Department"),
			("LOC Region", "DocType", "LOC Region"),
			("Reporting Period", "DocType", "Reporting Period"),
			("Fuel Product", "DocType", "Fuel Product"),
			("LOC User Setup", "DocType", "LOC User Setup"),
		],
	),
]

SHORTCUTS = [
	("Company Activity Report", "DocType", "Company Activity Report", "List"),
	("Department Activity Submission", "DocType", "Department Activity Submission", "List"),
	("Department Activity Status", "Report", "Department Activity Status", ""),
	("Budget Execution Position", "Report", "Budget Execution Position", ""),
	("Budget Execution Entry", "DocType", "Budget Execution Entry", "List"),
	("Station Monthly Data", "DocType", "Station Monthly Data", "List"),
	("Station Data Import", "DocType", "Station Data Import", "List"),
	("Registered Company", "DocType", "Registered Company", "List"),
	("Registration Certificate", "DocType", "Registration Certificate", "List"),
	("Company Registry", "Report", "Company Registry", ""),
	("Reporting Period", "DocType", "Reporting Period", "List"),
	("LOC Department", "DocType", "LOC Department", "Tree"),
	("LOC Planning Settings", "DocType", "LOC Planning Settings", ""),
]

SECTION_AR = {
	"LOC Dashboard": "لوحة المؤشرات",
	"Sales Office Portal": "بوابة مكتب المبيعات",
	"Department Coordinator Portal": "بوابة منسق الإدارة",
	"Activity Report": "تقرير النشاط",
	"Budget": "الموازنة",
	"Stations and Support Activities": "المحطات والأنشطة المساندة",
	"Investment Section": "قسم الاستثمار",
	"Settings": "الإعدادات",
}


# Management roles see the main workspace (dashboard, cards, charts); operational roles get
# their own short portal. Frappe filters every sidebar link by the user's permissions.
WORKSPACE_ROLES = [
	"System Manager",
	"LOC Planning Director",
	"Strategic Planning",
	"Statistics & Data",
	"Investment Section",
	"Finance Budget",
	"Executive Viewer",
	"LOC General Manager",
]

TOP_LINKS = [
	("LOC Dashboard", "Page", "loc-dashboard", "chart-column"),
	("Sales Office Portal", "Workspace", "Sales Office Portal", "fuel"),
	("Department Coordinator Portal", "Workspace", "Department Coordinator Portal", "clipboard-list"),
]

NUMBER_CARDS = [
	"LOC Fuel Sales",
	"LOC Budget Execution",
	"LOC Operating Stations",
	"LOC Reports Received",
	"LOC Certificates Issued",
]

CHARTS = ["LOC Monthly Sales Trend", "LOC Sales by Product", "LOC Budget by Chapter"]

PORTALS = [
	{
		"name": "Sales Office Portal",
		"title_ar": "بوابة مكتب المبيعات",
		"intro_ar": "محطات مكتبك وبياناتها الشهرية: الإدخال، والاستيراد من Excel، ومتابعة ما لم يرفع بعد.",
		"icon": "fuel",
		"roles": ["Sales Office User"],
		"shortcuts": [
			("Station Monthly Data", "DocType", "Station Monthly Data", "List"),
			("Station Data Import", "DocType", "Station Data Import", "List"),
			("Fuel Station", "DocType", "Fuel Station", "List"),
			("Missing Station Data", "Report", "Missing Station Data", ""),
			("Station Sales Analysis", "Report", "Station Sales Analysis", ""),
		],
	},
	{
		"name": "Department Coordinator Portal",
		"title_ar": "بوابة منسق الإدارة",
		"intro_ar": "نموذج نشاط إدارتك للفترة الحالية وحالته والموعد النهائي. تصلك التذكيرات والملاحظات في الإشعارات.",
		"icon": "clipboard-list",
		"roles": ["Department Coordinator"],
		"shortcuts": [
			("Department Activity Submission", "DocType", "Department Activity Submission", "List"),
			("Department Activity Status", "Report", "Department Activity Status", ""),
		],
	},
]
