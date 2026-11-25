"""Workspace and Sidebar contents. Each section: (label, icon, [(label, link_type, link_to), ...])."""

WORKSPACE = "LOC Planning"

SECTIONS = [
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
	("Registered Company", "DocType", "Registered Company", "List"),
	("Registration Certificate", "DocType", "Registration Certificate", "List"),
	("Company Registry", "Report", "Company Registry", ""),
	("Reporting Period", "DocType", "Reporting Period", "List"),
	("LOC Department", "DocType", "LOC Department", "Tree"),
	("LOC Planning Settings", "DocType", "LOC Planning Settings", ""),
]

SECTION_AR = {"Investment Section": "قسم الاستثمار", "Settings": "الإعدادات"}
