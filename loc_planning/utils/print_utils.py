"""Helpers shared by all official print formats (fonts, logo, numbers, dates)."""

import frappe
from frappe.utils import cint, flt, getdate

from loc_planning.constants import SETTINGS_DOCTYPE
from loc_planning.utils.arabic import strip_diacritics
from loc_planning.utils.periods import MONTHS_AR


def get_print_settings():
	"""Values a print format needs: font CSS, logo, official names. All configurable from
	LOC Planning Settings; nothing is hard-coded in the templates."""
	s = frappe.get_cached_doc(SETTINGS_DOCTYPE)
	family = (s.report_font_family or "Fanan").strip()
	fallback = (s.fallback_font_family or "Noto Naskh Arabic").strip()
	font_face = ""
	if s.report_font_file:
		url = frappe.utils.get_url(s.report_font_file)
		font_face = f"@font-face {{ font-family: '{family}'; src: url('{url}'); }}"
	return frappe._dict(
		font_face=font_face,
		font_stack=f"'{family}', '{fallback}', 'Noto Naskh Arabic', 'Amiri', 'Arial', sans-serif",
		base_font_size=cint(s.base_font_size) or 12,
		logo=frappe.utils.get_url(s.company_logo) if s.company_logo else "",
		company_name=strip_diacritics(s.official_company_name or ""),
		header_text=strip_diacritics(s.report_header_text or ""),
		footer_text=strip_diacritics(s.report_footer_text or ""),
		signatory_title=strip_diacritics(s.certificate_signatory_title or ""),
		issuer_name=strip_diacritics(s.certificate_issuer_name or ""),
	)


class arabic_output:
	"""Official outputs are always Arabic, whatever the language of the user producing them."""

	def __enter__(self):
		self.previous = getattr(frappe.local, "lang", None)
		frappe.local.lang = "ar"
		return self

	def __exit__(self, *exc):
		frappe.local.lang = self.previous


def format_arabic_date(value):
	"""25 نوفمبر 2026 — month name in Arabic, Western digits."""
	if not value:
		return ""
	d = getdate(value)
	return f"{d.day} {MONTHS_AR[d.month - 1]} {d.year}"


def format_number(value, precision=0):
	"""Consistent thousands separator for official outputs: 1,234,567.89"""
	return f"{flt(value, precision):,.{precision}f}"
