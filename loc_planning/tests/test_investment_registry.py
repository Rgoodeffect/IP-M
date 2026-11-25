import os
import re

import frappe
from frappe.model.workflow import WorkflowPermissionError, WorkflowTransitionError, apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_months, getdate, today

from loc_planning.investment_registry import tasks
from loc_planning.investment_registry.migration import access_import
from loc_planning.investment_registry.utils import get_verification_result
from loc_planning.tests.utils import as_user, ensure_test_user

INV_USER = "loc_investment@example.com"
DIR_USER = "loc_director@example.com"
DATA = os.path.join(os.path.dirname(__file__), "data", "legacy_registry")
HARAKAT = re.compile("[ً-ْ]")


def make_company(name="شركة تجريبية للاختبار", **kw):
	return frappe.get_doc(
		{"doctype": "Registered Company", "company_name": name, "classification": "مقاول خدمات", **kw}
	).insert()


def issue_certificate(company, **kw):
	"""Run the full approval workflow and return the issued certificate."""
	cert = frappe.get_doc({"doctype": "Registration Certificate", "registered_company": company, **kw})
	with as_user(INV_USER):
		cert.insert()
		cert = apply_workflow(cert, "Submit for Review")
		cert = apply_workflow(cert, "Send for Approval")
	with as_user(DIR_USER):
		cert = apply_workflow(cert, "Approve")
	return frappe.get_doc("Registration Certificate", cert.name)


class IntegrationTestInvestmentRegistry(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_test_user(INV_USER, ["Investment Section"])
		ensure_test_user(DIR_USER, ["LOC Planning Director"])
		frappe.db.commit()

	# ---------------------------------------------------------------- companies
	def test_registration_number_from_series_and_preserved(self):
		auto = make_company("شركة تجريبية أولى")
		self.assertTrue(auto.name.startswith("REG-"))
		self.assertEqual(auto.registration_no, auto.name)
		kept = make_company("شركة تجريبية ثانية", registration_no="LEGACY-777")
		self.assertEqual(kept.name, "LEGACY-777")

	def test_duplicate_identifiers_are_rejected_after_normalisation(self):
		make_company("شركة تجريبية ثالثة", tax_id="١٢٣-٤٥٦")
		with self.assertRaises(frappe.DuplicateEntryError):
			make_company("شركة تجريبية رابعة", tax_id="123456")

	def test_suspension_needs_reason(self):
		with self.assertRaises(frappe.ValidationError):
			make_company("شركة تجريبية موقوفة", status="Suspended")

	# ------------------------------------------------------------- certificates
	def test_workflow_issues_certificate(self):
		company = make_company("شركة تجريبية للشهادة")
		cert = issue_certificate(company.name)
		self.assertEqual(cert.docstatus, 1)
		self.assertEqual(cert.workflow_state, "Issued")
		self.assertEqual(cert.status, "Issued")
		self.assertTrue(cert.certificate_no.startswith("CERT-"))
		self.assertEqual(getdate(cert.issue_date), getdate(today()))
		self.assertEqual(getdate(cert.expiry_date), getdate(add_days(add_months(today(), 12), -1)))
		self.assertTrue(cert.verification_code)
		company.reload()
		self.assertEqual(company.current_certificate, cert.name)
		self.assertEqual(company.certificate_status, "Valid")

	def test_investment_section_cannot_approve(self):
		company = make_company("شركة تجريبية بدون اعتماد")
		cert = frappe.get_doc({"doctype": "Registration Certificate", "registered_company": company.name})
		with self.set_user(INV_USER):
			cert.insert()
			cert = apply_workflow(cert, "Submit for Review")
			cert = apply_workflow(cert, "Send for Approval")
			with self.assertRaises((WorkflowPermissionError, WorkflowTransitionError)):
				apply_workflow(cert, "Approve")

	def test_reject_and_return(self):
		company = make_company("شركة تجريبية مرفوضة")
		cert = frappe.get_doc({"doctype": "Registration Certificate", "registered_company": company.name})
		with self.set_user(INV_USER):
			cert.insert()
			cert = apply_workflow(cert, "Submit for Review")
			cert = apply_workflow(cert, "Send for Approval")
		with self.set_user(DIR_USER):
			cert = apply_workflow(cert, "Return for Revision")
			self.assertEqual(cert.workflow_state, "Under Review")
		with self.set_user(INV_USER):
			cert = apply_workflow(cert, "Send for Approval")
		with self.set_user(DIR_USER):
			cert = apply_workflow(cert, "Reject")
		self.assertEqual(cert.status, "Rejected")
		self.assertEqual(cert.docstatus, 0)

	def test_second_new_certificate_requires_renewal(self):
		company = make_company("شركة تجريبية للتجديد")
		first = issue_certificate(company.name)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{"doctype": "Registration Certificate", "registered_company": company.name}
			).insert()
		renewal = issue_certificate(company.name, request_type="Renewal", renewal_of=first.name)
		self.assertEqual(frappe.db.get_value("Registration Certificate", first.name, "status"), "Superseded")
		company.reload()
		self.assertEqual(company.current_certificate, renewal.name)
		# the superseded certificate is reported as such on the public page
		self.assertEqual(get_verification_result(first.verification_code).state, "Superseded")

	def test_cancel_requires_reason_and_updates_company(self):
		company = make_company("شركة تجريبية للإلغاء")
		cert = issue_certificate(company.name)
		with self.set_user(DIR_USER):
			with self.assertRaises(frappe.ValidationError):
				apply_workflow(cert, "Cancel")
			cert.reload()
			cert.cancel_reason = "سبب تجريبي"
			cert.save()
			cert = apply_workflow(cert, "Cancel")
		self.assertEqual(cert.docstatus, 2)
		self.assertEqual(frappe.db.get_value("Registration Certificate", cert.name, "status"), "Cancelled")
		company.reload()
		self.assertFalse(company.current_certificate)
		self.assertEqual(company.certificate_status, "None")
		self.assertEqual(get_verification_result(cert.verification_code).state, "Cancelled")

	def test_blacklisted_company_cannot_get_certificate(self):
		company = make_company("شركة تجريبية محظورة")
		cert = frappe.get_doc(
			{"doctype": "Registration Certificate", "registered_company": company.name}
		).insert()
		company.status = "Blacklisted"
		company.status_reason = "سبب تجريبي"
		company.save()
		cert.reload()
		with self.assertRaises(frappe.ValidationError):
			cert.submit()

	def test_mandatory_documents_enforced(self):
		frappe.db.set_value("Company Document Type", "السجل التجاري", "is_mandatory", 1)
		try:
			company = make_company("شركة تجريبية بلا مستندات")
			cert = frappe.get_doc(
				{"doctype": "Registration Certificate", "registered_company": company.name}
			).insert()
			with self.assertRaises(frappe.ValidationError):
				cert.submit()
			company.append(
				"documents",
				{
					"document_type": "السجل التجاري",
					"document_no": "1",
					"expiry_date": add_days(today(), 400),
					"attachment": "/files/test.pdf",
				},
			)
			company.save()
			cert.reload()
			cert.submit()
			self.assertEqual(cert.status, "Issued")
		finally:
			frappe.db.set_value("Company Document Type", "السجل التجاري", "is_mandatory", 0)

	# ------------------------------------------------------------- verification
	def test_verification_page(self):
		company = make_company("شركة تجريبية للتحقق")
		cert = issue_certificate(company.name)
		result = get_verification_result(cert.verification_code)
		self.assertEqual(result.state, "Valid")
		self.assertEqual(result.company_name, company.company_name)
		self.assertNotIn("tax_id", result)
		self.assertIsNone(get_verification_result("does-not-exist"))
		self.assertIsNone(get_verification_result("x" * 200))

		from loc_planning.www import verify_certificate

		with self.set_user("Guest"):
			frappe.local.form_dict = frappe._dict(code=cert.verification_code)
			context = verify_certificate.get_context(frappe._dict())
		self.assertEqual(context.state_label, "شهادة سارية")
		self.assertEqual(context.result.company_name, company.company_name)

		# the page itself is public and renders for a guest
		from frappe.website.serve import get_response_content

		frappe.local.form_dict = frappe._dict()
		with self.set_user("Guest"):
			html = get_response_content("verify-certificate")
		self.assertIn("التحقق من شهادة إثبات القيد", html)

	def test_draft_is_not_verifiable(self):
		company = make_company("شركة تجريبية مسودة")
		cert = frappe.get_doc(
			{"doctype": "Registration Certificate", "registered_company": company.name}
		).insert()
		self.assertIsNone(get_verification_result(cert.verification_code))

	def test_print_format_renders_arabic_with_qr(self):
		company = make_company("شركة تجريبية للطباعة", commercial_register_no="CR-PRINT-1")
		cert = issue_certificate(company.name)
		html = frappe.get_print(
			"Registration Certificate", cert.name, print_format="Registration Certificate"
		)
		self.assertIn(company.company_name, html)
		self.assertIn("شهادة إثبات قيد", html)
		self.assertIn("data:image/png;base64,", html)
		self.assertNotIn("مسودة", html)
		self.assertIsNone(HARAKAT.search(frappe.utils.strip_html(html)))
		pdf = frappe.get_print(
			"Registration Certificate", cert.name, print_format="Registration Certificate", as_pdf=True
		)
		self.assertTrue(pdf.startswith(b"%PDF"))

	# -------------------------------------------------------------- daily task
	def test_daily_task_expires_and_alerts(self):
		company = make_company("شركة تجريبية منتهية")
		cert = issue_certificate(company.name)
		frappe.db.set_value("Registration Certificate", cert.name, "expiry_date", add_days(today(), -1))
		soon_company = make_company("شركة تجريبية قاربت")
		soon = issue_certificate(soon_company.name)
		frappe.db.set_value("Registration Certificate", soon.name, "expiry_date", add_days(today(), 10))

		before = frappe.db.count("Notification Log", {"for_user": INV_USER})
		tasks.daily()
		self.assertEqual(frappe.db.get_value("Registration Certificate", cert.name, "status"), "Expired")
		self.assertEqual(
			frappe.db.get_value("Registered Company", company.name, "certificate_status"), "Expired"
		)
		self.assertEqual(
			frappe.db.get_value("Registered Company", soon_company.name, "certificate_status"),
			"Expiring Soon",
		)
		self.assertIn(soon.name, [c.name for c in tasks.get_expiring_certificates()])
		self.assertGreater(frappe.db.count("Notification Log", {"for_user": INV_USER}), before)

	def test_supplier_created_when_enabled(self):
		with self.change_settings("LOC Planning Settings", {"auto_create_supplier": 1}):
			company = make_company("شركة تجريبية مورد", tax_id="TAX-SUP-1")
			issue_certificate(company.name)
		supplier = frappe.db.get_value("Registered Company", company.name, "supplier")
		self.assertTrue(supplier)
		self.assertEqual(frappe.db.get_value("Supplier", supplier, "supplier_name"), company.company_name)

	def test_company_registry_report(self):
		from loc_planning.investment_registry.report.company_registry.company_registry import execute

		company = make_company("شركة تجريبية للتقرير")
		issue_certificate(company.name)
		_columns, data, _msg, _chart, summary = execute({"certificate_status": "Valid"})
		self.assertIn(company.name, [r.name for r in data])
		self.assertTrue(all(r.certificate_status == "Valid" for r in data))
		self.assertEqual(summary[0]["value"], len(data))


class IntegrationTestRegistryMigration(IntegrationTestCase):
	def test_dry_run_saves_nothing(self):
		report = os.path.join(frappe.get_site_path("private", "files"), "test_mig_dry.csv")
		summary = access_import.run(DATA, dry_run=1, report_path=report)
		self.assertTrue(summary["dry_run"])
		self.assertEqual(summary["companies_created"], 4)
		self.assertFalse(frappe.db.exists("Registered Company", "REG-90001"))
		self.assertTrue(os.path.exists(report))

	def test_import_keeps_numbers_and_reports_errors(self):
		report = os.path.join(frappe.get_site_path("private", "files"), "test_mig_run.csv")
		summary = access_import.run(DATA, dry_run=0, report_path=report, commit=False)
		self.assertEqual(summary["company_rows"], 7)
		self.assertEqual(summary["companies_created"], 4)
		self.assertEqual(summary["certificates_created"], 3)
		# duplicate registration no, duplicate tax no, empty name; 3 bad certificates
		self.assertEqual(summary["errors"], 6)

		self.assertEqual(frappe.db.get_value("Registered Company", "REG-90001", "legacy_id"), "1")
		self.assertEqual(frappe.db.get_value("Registered Company", "REG-90003", "status"), "Suspended")
		self.assertTrue(frappe.db.exists("Company Classification", "تصنيف تجريبي جديد"))
		self.assertEqual(
			getdate(frappe.db.get_value("Registered Company", "REG-90002", "registration_date")),
			getdate("2020-07-14"),
		)

		valid = frappe.get_doc("Registration Certificate", "OLD-T-0001")
		self.assertEqual((valid.docstatus, valid.status, valid.certificate_no), (1, "Issued", "OLD-T-0001"))
		self.assertEqual(get_verification_result(valid.verification_code).state, "Valid")
		self.assertEqual(frappe.db.get_value("Registration Certificate", "OLD-T-0002", "status"), "Expired")
		self.assertEqual(frappe.db.get_value("Registration Certificate", "OLD-T-0003", "docstatus"), 2)
		self.assertEqual(
			frappe.db.get_value("Registered Company", "REG-90001", "current_certificate"), "OLD-T-0001"
		)

		# new companies continue after the highest migrated number
		self.assertGreaterEqual(access_import.get_series_current("REG-"), 90007)
		new = make_company("شركة تجريبية بعد الترحيل")
		self.assertGreater(int(new.name.split("-")[1]), 90007)

		# re-running skips what is already there
		again = access_import.run(DATA, dry_run=0, report_path=report, commit=False)
		self.assertEqual(again.get("companies_created", 0), 0)
		self.assertEqual(again["companies_skipped"], 4)
		self.assertEqual(again["certificates_skipped"], 3)
