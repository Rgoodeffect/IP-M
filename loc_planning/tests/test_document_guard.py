import frappe
from frappe.tests import IntegrationTestCase

from loc_planning.loc_planning.doctype.reporting_period.reporting_period import set_period_status
from loc_planning.tests.utils import (
	TEST_DOCTYPE,
	drop_guard_test_doctype,
	ensure_guard_test_doctype,
	ensure_period,
)
from loc_planning.utils.document_guard import PeriodClosedError


class IntegrationTestDocumentGuard(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_guard_test_doctype()
		cls.open_period = ensure_period("Monthly", 2035, 1)
		cls.closed_period = ensure_period("Monthly", 2035, 2)
		frappe.db.commit()  # DDL above commits implicitly; keep fixtures consistent

	def setUp(self):
		frappe.db.set_value("Reporting Period", self.closed_period, "status", "Open")

	def _close(self):
		set_period_status(self.closed_period, "Closed")

	def _new(self, period, **kw):
		return frappe.get_doc({"doctype": TEST_DOCTYPE, "reporting_period": period, **kw})

	def test_cannot_create_in_closed_period(self):
		self._close()
		with self.assertRaises(PeriodClosedError):
			self._new(self.closed_period).insert()

	def test_cannot_edit_after_close(self):
		doc = self._new(self.closed_period, amount=1).insert()
		self._close()
		doc.reload()
		doc.amount = 2
		with self.assertRaises(PeriodClosedError):
			doc.save()

	def test_cannot_move_document_out_of_closed_period(self):
		doc = self._new(self.closed_period).insert()
		self._close()
		doc.reload()
		doc.reporting_period = self.open_period
		with self.assertRaises(PeriodClosedError):
			doc.save()

	def test_cannot_update_after_submit_or_cancel_in_closed_period(self):
		doc = self._new(self.closed_period, amount=1).insert()
		doc.submit()
		self._close()
		doc.reload()
		doc.amount = 5
		with self.assertRaises(PeriodClosedError):
			doc.save()
		doc.reload()
		doc.cancel_reason = "test"
		with self.assertRaises(PeriodClosedError):
			doc.cancel()

	def test_open_period_is_editable(self):
		doc = self._new(self.open_period, amount=1).insert()
		doc.amount = 3
		doc.save()
		self.assertEqual(frappe.db.get_value(TEST_DOCTYPE, doc.name, "amount"), 3)

	def test_lock_can_be_disabled_in_settings(self):
		self._close()
		with self.change_settings("LOC Planning Settings", {"enforce_period_lock": 0}):
			self._new(self.closed_period).insert()

	def test_cancel_requires_reason(self):
		doc = self._new(self.open_period).insert()
		doc.submit()
		with self.assertRaises(frappe.ValidationError):
			doc.cancel()
		doc.reload()
		doc.cancel_reason = "duplicate entry"
		doc.cancel()
		self.assertEqual(doc.docstatus, 2)

	def test_cancelled_document_cannot_be_deleted(self):
		doc = self._new(self.open_period).insert()
		doc.submit()
		doc.cancel_reason = "x"
		doc.cancel()
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc(TEST_DOCTYPE, doc.name)

	def test_draft_can_be_deleted(self):
		doc = self._new(self.open_period).insert()
		frappe.delete_doc(TEST_DOCTYPE, doc.name)
		self.assertFalse(frappe.db.exists(TEST_DOCTYPE, doc.name))


def tearDownModule():
	drop_guard_test_doctype()
