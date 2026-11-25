"""Demo stations and monthly data (all codes start with DEMO- and names with "محطة تجريبية")."""

import calendar
import random

import frappe
from frappe.utils import getdate

from loc_planning.loc_planning.doctype.reporting_period.reporting_period import create_periods_for_year
from loc_planning.utils.periods import period_name

PREFIX = "DEMO-ST-"


def load(year=None, months=6, stations_per_office=3, seed=7):
	frappe.only_for("System Manager")
	rng = random.Random(seed)
	year = int(year or getdate().year)
	create_periods_for_year(year, ["Monthly"])
	offices = frappe.get_all(
		"LOC Department", filters={"department_type": "Sales Office"}, pluck="name", order_by="lft"
	)
	products = frappe.get_all(
		"Fuel Product", filters={"is_active": 1}, fields=["name", "uom"], order_by="display_order"
	)
	activities = frappe.get_all(
		"Support Activity Type", filters={"is_active": 1, "has_revenue": 1}, pluck="name"
	)
	op_types = frappe.get_all("Station Operation Type", pluck="name")
	n = 0
	for office in offices:
		for _i in range(stations_per_office):
			n += 1
			code = f"{PREFIX}{n:03d}"
			if frappe.db.exists("Fuel Station", code):
				continue
			status = "Operating" if n % 7 else "Stopped"
			frappe.get_doc(
				{
					"doctype": "Fuel Station",
					"station_code": code,
					"station_name": f"محطة تجريبية {n}",
					"operation_type": op_types[n % len(op_types)],
					"sales_office": office,
					"status": status,
					"stop_reason": "بيانات تجريبية" if status != "Operating" else None,
					"pumps_count": 4,
					"nozzles_count": 8,
					"employees_count": 10,
					"tanks": [
						{
							"tank_no": str(i + 1),
							"product": p.name,
							"capacity": 30000 if p.uom == "Litre" else 500,
						}
						for i, p in enumerate(products)
					],
					"support_activities": [
						{"activity_type": a} for a in activities[: 1 + n % len(activities)]
					],
				}
			).insert()
	stations = frappe.get_all(
		"Fuel Station", filters={"name": ("like", f"{PREFIX}%")}, fields=["name", "status"]
	)
	for month in range(1, months + 1):
		period = period_name("Monthly", year, month)
		for s in stations:
			if frappe.db.exists("Station Monthly Data", {"station": s.name, "reporting_period": period}):
				continue
			if month == months and rng.random() < 0.3:
				continue  # leave some missing for the "missing data" report
			rows = []
			for p in products:
				base = 120000 if p.uom == "Litre" else 900
				target = base * rng.uniform(0.8, 1.2)
				actual = 0 if s.status != "Operating" else target * rng.uniform(0.6, 1.15)
				opening = base * 0.2
				received = actual + base * rng.uniform(-0.02, 0.05)
				rows.append(
					{
						"product": p.name,
						"target_qty": round(target),
						"actual_qty": round(actual),
						"opening_stock": round(opening),
						"received_qty": round(max(received, 0)),
						"closing_stock": round(max(opening + received - actual, 0)),
					}
				)
			doc = frappe.get_doc(
				{
					"doctype": "Station Monthly Data",
					"station": s.name,
					"reporting_period": period,
					"products": rows,
					"stopped_days": calendar.monthrange(year, month)[1]
					if s.status != "Operating"
					else rng.choice([0, 0, 0, 2]),
					"support_revenues": [
						{"activity_type": a, "revenue": round(rng.uniform(2000, 15000))} for a in activities
					],
					"notes": "بيانات تجريبية",
				}
			)
			doc.flags.mute_warnings = True
			doc.insert()
			if month < months:
				doc.db_set({"workflow_state": "Approved", "docstatus": 1, "status": "Approved"})
	frappe.db.commit()
	return len(stations)


def remove():
	frappe.only_for("System Manager")
	for name in frappe.get_all(
		"Station Monthly Data", filters={"station": ("like", f"{PREFIX}%")}, pluck="name"
	):
		frappe.db.delete("Station Monthly Product", {"parent": name})
		frappe.db.delete("Station Support Revenue", {"parent": name})
		frappe.db.delete("Station Monthly Data", {"name": name})
	for name in frappe.get_all("Fuel Station", filters={"name": ("like", f"{PREFIX}%")}, pluck="name"):
		frappe.delete_doc("Fuel Station", name, force=True)
	frappe.db.commit()
