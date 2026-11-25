"""One-time migration of the legacy company registry (MS Access) into the Investment Registry.

Usage
-----
Dry run (nothing is saved, a report is written):

    bench --site <site> execute loc_planning.investment_registry.migration.access_import.run \\
        --kwargs "{'source': '/path/registry.accdb', 'mapping': '/path/mapping.json'}"

Real run (add 'dry_run': 0). `source` is either an .accdb/.mdb file (read with mdbtools'
`mdb-export`) or a folder holding one CSV per table (`<table>.csv`, UTF-8).

What it does
------------
- Maps legacy columns to fields through `mapping.json` (see mapping.example.json).
- Keeps the legacy registration numbers and certificate numbers as document names.
- Detects duplicates inside the source (registration no., tax no., commercial register no.,
  normalised Arabic name) and against records already in the system. Rows whose
  registration number already exists are skipped, so the script can be re-run safely.
- Imports issued / expired / cancelled certificates as final documents with a fresh
  verification code.
- Moves the registration-number series past the highest migrated number that uses it.
- Writes a CSV report (level, entity, row, key, message) and returns a summary.
"""

import csv
import datetime
import io
import json
import os
import re
import shutil
import subprocess

import frappe
from frappe.utils import cint, getdate, now_datetime

from loc_planning.investment_registry.utils import (
	expiry_state,
	new_verification_code,
	refresh_company_certificate,
)
from loc_planning.utils.arabic import normalize_identifier, normalize_name, strip_diacritics

DEFAULT_MAPPING = os.path.join(os.path.dirname(__file__), "mapping.example.json")
COMPANY_FIELDS = (
	"registration_no",
	"company_name",
	"company_name_en",
	"classification",
	"registration_date",
	"activity_description",
	"commercial_register_no",
	"tax_id",
	"chamber_of_commerce_no",
	"legal_representative",
	"legal_representative_id",
	"legal_representative_phone",
	"address",
	"city",
	"phone",
	"email",
	"website",
	"status",
	"status_reason",
)


class MigrationReport:
	def __init__(self):
		self.rows = []
		self.counts = {}

	def add(self, level, entity, row_no, key, message):
		self.rows.append((level, entity, row_no, key or "", message))

	def count(self, key, n=1):
		self.counts[key] = self.counts.get(key, 0) + n

	@property
	def errors(self):
		return sum(1 for r in self.rows if r[0] == "ERROR")

	@property
	def warnings(self):
		return sum(1 for r in self.rows if r[0] == "WARNING")

	def write(self, path):
		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, "w", encoding="utf-8-sig", newline="") as fh:
			writer = csv.writer(fh)
			writer.writerow(["level", "entity", "source_row", "key", "message"])
			writer.writerows(self.rows)
		return path


# --------------------------------------------------------------------------------------
# Reading the source
# --------------------------------------------------------------------------------------


def read_table(source, table):
	"""Return the rows of `table` as a list of dicts (header → value)."""
	if os.path.isdir(source):
		path = os.path.join(source, f"{table}.csv")
		if not os.path.exists(path):
			raise FileNotFoundError(f"{path} not found")
		with open(path, encoding="utf-8-sig", newline="") as fh:
			return list(csv.DictReader(fh))
	if not shutil.which("mdb-export"):
		raise RuntimeError("mdb-export (mdbtools) is not installed: apt-get install mdbtools")
	out = subprocess.run(
		["mdb-export", "-D", "%Y-%m-%d", "-T", "%Y-%m-%d %H:%M:%S", source, table],
		check=True,
		capture_output=True,
	).stdout.decode("utf-8")
	return list(csv.DictReader(io.StringIO(out)))


def list_access_tables(source):
	"""Helper to discover table names in an Access file (for writing the mapping)."""
	out = subprocess.run(["mdb-tables", "-1", source], check=True, capture_output=True).stdout
	return [t for t in out.decode("utf-8").splitlines() if t.strip()]


def load_mapping(mapping):
	if isinstance(mapping, dict):
		return mapping
	with open(mapping or DEFAULT_MAPPING, encoding="utf-8") as fh:
		return json.load(fh)


# --------------------------------------------------------------------------------------
# Value conversion
# --------------------------------------------------------------------------------------


def clean(value):
	if value is None:
		return None
	value = strip_diacritics(" ".join(str(value).split()))
	return value or None


def parse_date(value, formats):
	value = clean(value)
	if not value:
		return None
	for fmt in formats:
		try:
			return datetime.datetime.strptime(value, fmt).date()
		except ValueError:
			continue
	try:
		return getdate(value)
	except Exception:
		raise ValueError(f"unrecognised date '{value}'")


def map_row(row, columns):
	return {field: clean(row.get(column)) for field, column in columns.items() if column}


# --------------------------------------------------------------------------------------
# Companies
# --------------------------------------------------------------------------------------


def prepare_companies(rows, cfg, mapping, report):
	"""Validate and de-duplicate company rows. Returns list of (row_no, legacy_id, values)."""
	formats = mapping.get("date_formats", [])
	status_values = cfg.get("status_values", {})
	class_values = cfg.get("classification_values", {})
	seen = {"registration_no": {}, "tax_id": {}, "commercial_register_no": {}, "name": {}}
	prepared = []

	for i, raw in enumerate(rows, start=2):  # row 1 is the header
		values = map_row(raw, cfg["columns"])
		legacy_id = values.pop("legacy_id", None)
		key = values.get("registration_no") or legacy_id
		if not values.get("company_name"):
			report.add("ERROR", "company", i, key, "company name is empty")
			continue
		if values.get("registration_date"):
			try:
				values["registration_date"] = parse_date(values["registration_date"], formats)
			except ValueError as e:
				report.add("WARNING", "company", i, key, f"registration date: {e}")
				values["registration_date"] = None

		status = values.get("status")
		values["status"] = status_values.get(status, status) if status else "Active"
		if values["status"] not in ("Active", "Suspended", "Blacklisted", "Inactive"):
			report.add("WARNING", "company", i, key, f"unknown status '{status}', set to Active")
			values["status"] = "Active"
		if values["status"] in ("Suspended", "Blacklisted") and not values.get("status_reason"):
			values["status_reason"] = "مرحل من النظام السابق"

		classification = values.get("classification")
		classification = class_values.get(classification, classification) or mapping.get(
			"default_classification"
		)
		if not classification:
			report.add(
				"ERROR", "company", i, key, "classification is empty and no default_classification set"
			)
			continue
		values["classification"] = classification

		duplicate = False
		for field in ("registration_no", "tax_id", "commercial_register_no"):
			ident = (
				normalize_identifier(values.get(field)) if field != "registration_no" else values.get(field)
			)
			if not ident:
				continue
			if ident in seen[field]:
				report.add(
					"ERROR",
					"company",
					i,
					key,
					f"duplicate {field} '{values.get(field)}' (also in source row {seen[field][ident]})",
				)
				duplicate = True
			else:
				seen[field][ident] = i
		if duplicate:
			continue
		name_key = normalize_name(values["company_name"])
		if name_key in seen["name"]:
			report.add(
				"WARNING",
				"company",
				i,
				key,
				f"similar name to source row {seen['name'][name_key]}; imported anyway",
			)
		seen["name"].setdefault(name_key, i)
		prepared.append((i, legacy_id, values))
	return prepared


def import_companies(prepared, mapping, report):
	"""Insert companies; returns {legacy_ref: company name} for linking certificates."""
	from loc_planning.investment_registry.doctype.registered_company.registered_company import (
		find_by_identifier,
		find_similar_names,
	)

	refs = {}
	create_classes = mapping.get("create_missing_classifications", True)
	for row_no, legacy_id, values in prepared:
		key = values.get("registration_no") or legacy_id
		reg_no = values.get("registration_no")
		if reg_no and frappe.db.exists("Registered Company", reg_no):
			report.add("INFO", "company", row_no, key, "already exists, skipped")
			report.count("companies_skipped")
			_remember(refs, legacy_id, values, reg_no)
			continue
		for field in ("tax_id", "commercial_register_no"):
			existing = find_by_identifier(field, values.get(field))
			if existing:
				report.add("ERROR", "company", row_no, key, f"{field} already registered for {existing}")
				break
		else:
			similar = find_similar_names(values["company_name"])
			if similar:
				report.add("WARNING", "company", row_no, key, f"similar name already in system: {similar[0]}")
			if not frappe.db.exists("Company Classification", values["classification"]):
				if not create_classes:
					report.add(
						"ERROR",
						"company",
						row_no,
						key,
						f"unknown classification '{values['classification']}'",
					)
					continue
				frappe.get_doc(
					{"doctype": "Company Classification", "classification_name": values["classification"]}
				).insert(ignore_permissions=True)
				report.add("INFO", "classification", row_no, values["classification"], "created")
			frappe.db.savepoint("loc_mig_company")
			try:
				doc = frappe.get_doc(
					{
						"doctype": "Registered Company",
						**{f: values.get(f) for f in COMPANY_FIELDS if values.get(f) is not None},
						"is_migrated": 1,
						"legacy_id": legacy_id,
					}
				)
				doc.flags.is_migration = True
				doc.flags.mute_messages = True
				doc.insert(ignore_permissions=True)
				report.count("companies_created")
				_remember(refs, legacy_id, values, doc.name)
			except Exception as e:
				frappe.db.rollback(save_point="loc_mig_company")
				report.add("ERROR", "company", row_no, key, _error_text(e))
	return refs


def _remember(refs, legacy_id, values, name):
	if legacy_id:
		refs[("legacy_id", str(legacy_id))] = name
	if values.get("registration_no"):
		refs[("registration_no", values["registration_no"])] = name


# --------------------------------------------------------------------------------------
# Certificates
# --------------------------------------------------------------------------------------


def import_certificates(rows, cfg, mapping, refs, report):
	formats = mapping.get("date_formats", [])
	status_values = cfg.get("status_values", {})
	ref_field = cfg.get("company_ref_field", "legacy_id")
	seen = set()
	touched = set()

	for i, raw in enumerate(rows, start=2):
		values = map_row(raw, cfg["columns"])
		cert_no = values.get("certificate_no")
		if not cert_no:
			report.add("ERROR", "certificate", i, None, "certificate number is empty")
			continue
		if cert_no in seen:
			report.add("ERROR", "certificate", i, cert_no, "duplicate certificate number in source")
			continue
		seen.add(cert_no)
		if frappe.db.exists("Registration Certificate", cert_no):
			report.add("INFO", "certificate", i, cert_no, "already exists, skipped")
			report.count("certificates_skipped")
			continue

		company_ref = values.get("company_ref")
		company = refs.get((ref_field, str(company_ref))) if company_ref else None
		if (
			not company
			and ref_field == "registration_no"
			and frappe.db.exists("Registered Company", company_ref)
		):
			company = company_ref
		if not company:
			report.add("ERROR", "certificate", i, cert_no, f"company '{company_ref}' not found")
			continue
		try:
			issue_date = parse_date(values.get("issue_date"), formats)
			expiry_date = parse_date(values.get("expiry_date"), formats)
		except ValueError as e:
			report.add("ERROR", "certificate", i, cert_no, str(e))
			continue
		if not issue_date or not expiry_date:
			report.add("ERROR", "certificate", i, cert_no, "issue or expiry date missing")
			continue
		if expiry_date < issue_date:
			report.add("ERROR", "certificate", i, cert_no, "expiry date before issue date")
			continue

		legacy_status = values.get("status")
		status = status_values.get(legacy_status, legacy_status) if legacy_status else "Issued"
		if status not in ("Issued", "Expired", "Cancelled"):
			report.add(
				"WARNING", "certificate", i, cert_no, f"unknown status '{legacy_status}', treated as Issued"
			)
			status = "Issued"
		if status == "Issued" and expiry_state(expiry_date) == "Expired":
			status = "Expired"

		frappe.db.savepoint("loc_mig_cert")
		try:
			doc = frappe.get_doc(
				{
					"doctype": "Registration Certificate",
					"certificate_no": cert_no,
					"registered_company": company,
					"request_type": "New",
					"request_date": issue_date,
					"issue_date": issue_date,
					"expiry_date": expiry_date,
					"is_migrated": 1,
					"verification_code": new_verification_code(),
					"cancel_reason": values.get("cancel_reason")
					or ("مرحل من النظام السابق" if status == "Cancelled" else None),
				}
			)
			doc.flags.is_migration = True
			doc.insert(ignore_permissions=True)
			# Legacy certificates were already approved: store them as final documents
			# without replaying the approval workflow.
			frappe.db.set_value(
				"Registration Certificate",
				doc.name,
				{
					"docstatus": 2 if status == "Cancelled" else 1,
					"status": status,
					"workflow_state": "Cancelled" if status == "Cancelled" else "Issued",
				},
				update_modified=False,
			)
			report.count("certificates_created")
			touched.add(company)
		except Exception as e:
			frappe.db.rollback(save_point="loc_mig_cert")
			report.add("ERROR", "certificate", i, cert_no, _error_text(e))

	for company in touched:
		refresh_company_certificate(company)


# --------------------------------------------------------------------------------------
# Naming series
# --------------------------------------------------------------------------------------


def bump_series(series, report):
	"""Move `series` past the highest migrated number that uses its prefix."""
	from frappe.model.naming import NamingSeries

	if not series or "#" not in series:
		return
	prefix = NamingSeries(series).get_prefix()
	if any(token in prefix for token in (".", "{")):
		report.add("INFO", "series", None, series, "series contains date parts; not adjusted")
		return
	pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
	highest = 0
	for name in frappe.get_all("Registered Company", filters={"is_migrated": 1}, pluck="name"):
		m = pattern.match(name)
		if m:
			highest = max(highest, int(m.group(1)))
	if highest:
		current = get_series_current(prefix)
		if highest > current:
			if frappe.db.sql("select name from `tabSeries` where name=%s", prefix):
				frappe.db.sql("update `tabSeries` set current=%s where name=%s", (highest, prefix))
			else:
				frappe.db.sql("insert into `tabSeries` (name, current) values (%s, %s)", (prefix, highest))
			report.add("INFO", "series", None, prefix, f"series moved to {highest}")


def get_series_current(prefix):
	row = frappe.db.sql("select current from `tabSeries` where name=%s", prefix)
	return cint(row[0][0]) if row else 0


# --------------------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------------------


def run(source, mapping=None, dry_run=1, report_path=None, commit=True):
	"""`commit=False` leaves the transaction open (used by tests)."""
	frappe.only_for(("System Manager", "Investment Section"))
	dry_run = cint(dry_run)
	mapping = load_mapping(mapping)
	report = MigrationReport()

	companies_cfg = mapping["companies"]
	company_rows = read_table(source, companies_cfg["table"])
	report.count("company_rows", len(company_rows))
	prepared = prepare_companies(company_rows, companies_cfg, mapping, report)
	refs = import_companies(prepared, mapping, report)

	certs_cfg = mapping.get("certificates")
	if certs_cfg and certs_cfg.get("table"):
		cert_rows = read_table(source, certs_cfg["table"])
		report.count("certificate_rows", len(cert_rows))
		import_certificates(cert_rows, certs_cfg, mapping, refs, report)

	series = frappe.get_cached_doc("LOC Planning Settings").company_registration_series
	bump_series(series, report)

	if dry_run:
		frappe.db.rollback()
	elif commit:
		frappe.db.commit()

	if not report_path:
		stamp = now_datetime().strftime("%Y%m%d-%H%M%S")
		report_path = frappe.get_site_path(
			"private", "files", f"loc_registry_migration_{'dryrun' if dry_run else 'run'}_{stamp}.csv"
		)
	report.write(report_path)

	summary = {
		"dry_run": bool(dry_run),
		**report.counts,
		"errors": report.errors,
		"warnings": report.warnings,
		"report": report_path,
	}
	print(json.dumps(summary, ensure_ascii=False, indent=1, default=str))
	return summary


def _error_text(e):
	text = frappe.utils.strip_html(str(e)) or e.__class__.__name__
	frappe.clear_messages()
	return text
