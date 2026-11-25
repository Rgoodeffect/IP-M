"""Data source keys were renamed to avoid clashing translations (e.g. "Budget")."""

import frappe

RENAMED = {
	"Manual": "Editorial Text",
	"Sales": "Sales Data",
	"Stations": "Stations Data",
	"Budget": "Budget Position",
	"Investment Registry": "Registry Data",
}


def execute():
	for table in ("Activity Report Section", "Activity Report Template Section"):
		for old, new in RENAMED.items():
			frappe.db.sql(f"update `tab{table}` set data_source=%s where data_source=%s", (new, old))
