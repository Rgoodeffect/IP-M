# Copyright (c) 2026, Oilibya and contributors
# For license information, please see license.txt

"""Bulk monthly station data through one Excel sheet: one row per station.

Template layout (sheet "البيانات", right-to-left):
  row 1  hidden machine keys, e.g. `station`, `actual_qty|بنزين`, `revenue|ماركت`
  row 2  Arabic headers
  row 3+ one row per station, pre-filled with the opening stock (previous month's closing)
         and with values already saved for the month, if any.
Import creates or updates draft Station Monthly Data documents with the user's own
permissions, so a sales office can only touch its own stations.
"""

import io

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from loc_planning.stations.doctype.fuel_station.fuel_station import get_active_products
from loc_planning.stations.doctype.station_monthly_data.station_monthly_data import get_defaults
from loc_planning.utils.arabic import normalize_digits

PRODUCT_FIELDS = (
	("target_qty", "المستهدف"),
	("actual_qty", "المبيعات الفعلية"),
	("opening_stock", "مخزون أول المدة"),
	("received_qty", "الوارد"),
	("closing_stock", "مخزون آخر المدة"),
)
DATA_SHEET = "البيانات"
EDITABLE_STATES = (None, "", "Draft", "Returned", "Pending Review")


class StationDataImport(Document):
	def validate(self):
		if frappe.db.get_value("Reporting Period", self.reporting_period, "period_type") != "Monthly":
			frappe.throw(_("Please select a monthly period"))
		if (
			self.sales_office
			and frappe.db.get_value("LOC Department", self.sales_office, "department_type") != "Sales Office"
		):
			frappe.throw(_("{0} is not a sales office").format(frappe.bold(self.sales_office)))

	@frappe.whitelist()
	def validate_file(self):
		return self._run(commit=False)

	@frappe.whitelist()
	def start_import(self):
		return self._run(commit=True)

	def _run(self, commit):
		self.check_permission("write")
		if not self.import_file:
			frappe.throw(_("Please attach the Excel file first"))
		rows = read_rows(self.import_file)
		if not commit:
			frappe.db.savepoint("station_import_validate")
		self.set("log", [])
		counts = {"Created": 0, "Updated": 0, "Skipped": 0, "Error": 0}

		for row_no, values in rows:
			result, document, message = import_row(values, self.reporting_period, self.sales_office)
			counts[result] += 1
			self.append(
				"log",
				{
					"row_no": row_no,
					"station": values.get("station"),
					"result": result,
					"document": document,
					"message": message,
				},
			)

		if not commit:
			frappe.db.rollback(save_point="station_import_validate")
			# the rollback discards the rows written so far; keep only the log on this document
			for row in self.log:
				row.document = None
		ok = counts["Created"] + counts["Updated"]
		if not commit:
			self.status = "Validated" if not counts["Error"] else "Failed"
		elif counts["Error"]:
			self.status = "Partially Imported" if ok else "Failed"
		else:
			self.status = "Imported"
		self.summary = _("Created: {0} | Updated: {1} | Skipped: {2} | Errors: {3}").format(
			counts["Created"], counts["Updated"], counts["Skipped"], counts["Error"]
		)
		if not commit:
			self.summary = _("Validation only, nothing was saved.") + " " + self.summary
		self.save()
		return counts


def import_row(values, reporting_period, sales_office=None):
	"""Returns (result, document name, message)."""
	station = (values.get("station") or "").strip()
	if not station:
		return "Skipped", None, _("No station code")
	if not frappe.db.exists("Fuel Station", station):
		return "Error", None, _("Station {0} not found").format(station)
	if not frappe.has_permission("Fuel Station", "read", station):
		return "Error", None, _("You are not allowed to enter data for station {0}").format(station)
	if sales_office and frappe.db.get_value("Fuel Station", station, "sales_office") != sales_office:
		return "Error", None, _("Station {0} does not belong to {1}").format(station, sales_office)

	numbers = {k: v for k, v in values.items() if k not in ("station", "station_name", "notes")}
	# The template pre-fills the opening stock, so a row only counts when something else is entered.
	entered = [v for k, v in numbers.items() if not k.startswith("opening_stock|") and v not in (None, "")]
	if not entered and not values.get("notes"):
		return "Skipped", None, _("Empty row")
	try:
		parsed = {k: parse_number(v) for k, v in numbers.items()}
	except ValueError as e:
		return "Error", None, str(e)

	existing = frappe.db.get_value(
		"Station Monthly Data",
		{"station": station, "reporting_period": reporting_period, "docstatus": ("<", 2)},
		["name", "docstatus", "workflow_state"],
		as_dict=True,
	)
	if existing and (existing.docstatus == 1 or existing.workflow_state not in EDITABLE_STATES):
		return "Error", existing.name, _("Data for this month is already approved")

	frappe.db.savepoint("station_import_row")
	try:
		if existing:
			doc = frappe.get_doc("Station Monthly Data", existing.name)
		else:
			doc = frappe.new_doc("Station Monthly Data")
			doc.station = station
			doc.reporting_period = reporting_period
			defaults = get_defaults(station, reporting_period)
			for row in defaults["products"]:
				doc.append("products", row)
			for row in defaults["support_revenues"]:
				doc.append("support_revenues", row)
		apply_values(doc, parsed, values.get("notes"))
		doc.flags.mute_warnings = True
		doc.save()
		return ("Updated" if existing else "Created"), doc.name, ""
	except Exception as e:
		frappe.db.rollback(save_point="station_import_row")
		message = frappe.utils.strip_html(str(e)) or e.__class__.__name__
		frappe.clear_messages()
		return "Error", existing.name if existing else None, message


def apply_values(doc, parsed, notes=None):
	product_rows = {r.product: r for r in doc.products}
	revenue_rows = {r.activity_type: r for r in doc.support_revenues}
	for key, value in parsed.items():
		if value is None:
			continue
		if key == "stopped_days":
			doc.stopped_days = cint(value)
			continue
		field, _sep, target = key.partition("|")
		if field == "revenue":
			row = revenue_rows.get(target) or doc.append("support_revenues", {"activity_type": target})
			revenue_rows[target] = row
			row.revenue = value
		elif field in dict(PRODUCT_FIELDS):
			row = product_rows.get(target) or doc.append("products", {"product": target})
			product_rows[target] = row
			row.set(field, value)
	if notes:
		doc.notes = notes


def parse_number(value):
	if value in (None, ""):
		return None
	if isinstance(value, int | float):
		return flt(value)
	text = normalize_digits(str(value)).replace(",", "").replace("\u066c", "").replace("\u066b", ".").strip()
	if not text:
		return None
	try:
		return flt(float(text))
	except ValueError:
		raise ValueError(_("Invalid number: {0}").format(value))


def read_rows(file_url):
	from openpyxl import load_workbook

	content = frappe.get_doc("File", {"file_url": file_url}).get_content()
	wb = load_workbook(io.BytesIO(content), data_only=True, read_only=True)
	ws = wb[DATA_SHEET] if DATA_SHEET in wb.sheetnames else wb.worksheets[0]
	rows = list(ws.iter_rows(values_only=True))
	if len(rows) < 2 or not rows[0] or "station" not in rows[0]:
		frappe.throw(_("This file is not a station data template. Please download the template again."))
	keys = [str(k).strip() if k else None for k in rows[0]]
	out = []
	for index, row in enumerate(rows[2:], start=3):
		values = {k: v for k, v in zip(keys, row, strict=False) if k}
		if any(v not in (None, "") for v in values.values()):
			out.append((index, values))
	return out


# ----------------------------------------------------------------------------------------
# Template
# ----------------------------------------------------------------------------------------


def template_columns():
	products = get_active_products()
	activities = frappe.get_all(
		"Support Activity Type",
		filters={"is_active": 1, "has_revenue": 1},
		order_by="display_order asc, name asc",
		pluck="name",
	)
	columns = [("station", "رمز المحطة"), ("station_name", "اسم المحطة")]
	for product in products:
		for field, label in PRODUCT_FIELDS:
			columns.append((f"{field}|{product}", f"{product} - {label}"))
	columns.append(("stopped_days", "أيام التوقف"))
	for activity in activities:
		columns.append((f"revenue|{activity}", f"إيراد {activity}"))
	columns.append(("notes", "ملاحظات"))
	return columns


def template_rows(reporting_period, sales_office=None):
	filters = {"is_active": 1}
	if sales_office:
		filters["sales_office"] = sales_office
	stations = frappe.get_list(
		"Fuel Station",
		filters=filters,
		fields=["name", "station_name"],
		order_by="sales_office asc, name asc",
	)
	rows = []
	for station in stations:
		values = {"station": station.name, "station_name": station.station_name}
		existing = frappe.db.get_value(
			"Station Monthly Data",
			{"station": station.name, "reporting_period": reporting_period, "docstatus": ("<", 2)},
		)
		if existing:
			doc = frappe.get_doc("Station Monthly Data", existing)
			for r in doc.products:
				for field, _label in PRODUCT_FIELDS:
					values[f"{field}|{r.product}"] = r.get(field)
			for r in doc.support_revenues:
				values[f"revenue|{r.activity_type}"] = r.revenue
			values["stopped_days"] = doc.stopped_days
			values["notes"] = doc.notes
		else:
			for r in get_defaults(station.name, reporting_period)["products"]:
				values[f"opening_stock|{r['product']}"] = r["opening_stock"]
		rows.append(values)
	return rows


@frappe.whitelist()
def download_template(name: str):
	from openpyxl import Workbook
	from openpyxl.styles import Alignment, Font, PatternFill

	doc = frappe.get_doc("Station Data Import", name)
	doc.check_permission("read")
	columns = template_columns()
	wb = Workbook()
	ws = wb.active
	ws.title = DATA_SHEET
	ws.sheet_view.rightToLeft = True
	ws.append([key for key, _label in columns])
	ws.append([label for _key, label in columns])
	ws.row_dimensions[1].hidden = True
	header_fill = PatternFill("solid", fgColor="DCE6F1")
	for cell in ws[2]:
		cell.font = Font(bold=True)
		cell.fill = header_fill
		cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
	ws.row_dimensions[2].height = 45
	for values in template_rows(doc.reporting_period, doc.sales_office):
		ws.append([values.get(key) for key, _label in columns])
	for index, (key, _label) in enumerate(columns, start=1):
		ws.column_dimensions[ws.cell(row=2, column=index).column_letter].width = (
			28 if key == "station_name" else 16
		)
	ws.freeze_panes = "C3"

	info = wb.create_sheet("تعليمات")
	info.sheet_view.rightToLeft = True
	for line in (
		"قالب البيانات الشهرية للمحطات",
		f"الشهر: {doc.reporting_period}",
		"أدخل الكميات بالأرقام فقط دون وحدات. الوقود باللتر والغاز بالأسطوانة.",
		"مخزون أول المدة معبأ من مخزون آخر المدة للشهر السابق، ويمكن تعديله.",
		"لا تغير ترتيب الأعمدة ولا تحذف السطر الأول المخفي.",
		"السطور الفارغة تتخطى، والبيانات المعتمدة لا يمكن تعديلها من هنا.",
	):
		info.append([line])
	info.column_dimensions["A"].width = 90

	buf = io.BytesIO()
	wb.save(buf)
	frappe.response["filename"] = f"station-data-{doc.reporting_period}.xlsx"
	frappe.response["filecontent"] = buf.getvalue()
	frappe.response["type"] = "binary"
