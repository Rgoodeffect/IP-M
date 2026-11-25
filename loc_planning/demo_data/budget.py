"""Demo approved budgets and execution entries for the seeded budget items.
All documents carry "بيانات تجريبية" in their notes / description."""

import random

import frappe
from frappe.utils import getdate

DEMO_NOTE = "بيانات تجريبية"


def load(year=None, seed=11):
	frappe.only_for("System Manager")
	rng = random.Random(seed)
	year = int(year or getdate().year)
	items = frappe.get_all(
		"Budget Item", filters={"is_active": 1, "execution_source": "Manual Entries"}, pluck="name"
	)
	for region, scale in (("الغربية", 1.0), ("الشرقية", 0.6)):
		if frappe.db.exists("Approved Budget", {"fiscal_year": year, "region": region, "docstatus": 1}):
			continue
		budget = frappe.get_doc(
			{
				"doctype": "Approved Budget",
				"fiscal_year": year,
				"region": region,
				"notes": DEMO_NOTE,
				"items": [
					{"budget_item": i, "approved_amount": round(rng.uniform(0.5, 8) * 1_000_000 * scale, -3)}
					for i in items
				],
			}
		).insert()
		budget.submit()
		for line in budget.items:
			ratio = rng.choice([0.25, 0.55, 0.7, 0.9])
			for month, share in ((2, 0.3), (5, 0.4), (9, 0.3)):
				doc = frappe.get_doc(
					{
						"doctype": "Budget Execution Entry",
						"budget_item": line.budget_item,
						"entry_type": "Actual Expense",
						"amount": round(line.approved_amount * ratio * share, -2),
						"region": region,
						"posting_date": f"{year}-{month:02d}-15",
						"description": DEMO_NOTE,
					}
				).insert()
				doc.submit()
			commitment = frappe.get_doc(
				{
					"doctype": "Budget Execution Entry",
					"budget_item": line.budget_item,
					"entry_type": "Commitment",
					"amount": round(line.approved_amount * rng.uniform(0.02, 0.1), -2),
					"region": region,
					"posting_date": f"{year}-10-01",
					"description": DEMO_NOTE,
				}
			).insert()
			commitment.submit()
	frappe.db.commit()
