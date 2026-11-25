"""Workspace and Sidebar contents. Each section: (label, icon, [(label, link_type, link_to), ...])."""

WORKSPACE = "LOC Planning"

SECTIONS = [
	(
		"Activity Report",
		"clipboard-list",
		[
			("Department Activity Submission", "DocType", "Department Activity Submission"),
			("Department Activity Status", "Report", "Department Activity Status"),
			("Activity Indicator Template", "DocType", "Activity Indicator Template"),
			("Activity Domain", "DocType", "Activity Domain"),
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
	"Activity Report": "تقرير النشاط",
	"Budget": "الموازنة",
	"Stations and Support Activities": "المحطات والأنشطة المساندة",
	"Investment Section": "قسم الاستثمار",
	"Settings": "الإعدادات",
}
