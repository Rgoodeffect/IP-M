"""Public, read-only certificate verification page: /verify-certificate?code=<token>

Shows only the certificate number, company name, classification, dates and validity.
The code is an unguessable random token, so certificates cannot be enumerated.
"""

import frappe

from loc_planning.investment_registry.utils import VERIFICATION_LABELS, get_verification_result
from loc_planning.utils.print_utils import format_arabic_date, get_print_settings

no_cache = 1
sitemap = 0


def get_context(context):
	code = frappe.form_dict.get("code")
	result = get_verification_result(code) if code else None
	settings = get_print_settings()

	context.no_cache = 1
	context.show_sidebar = False
	context.title = "التحقق من شهادة إثبات القيد"
	context.company_name = settings.company_name
	context.issuer_name = settings.issuer_name
	context.logo = settings.logo
	context.code_given = bool(code)
	context.result = result
	if result:
		label, color = VERIFICATION_LABELS.get(result.state, (result.state, "gray"))
		context.state_label = label
		context.state_color = color
		context.issue_date = format_arabic_date(result.issue_date)
		context.expiry_date = format_arabic_date(result.expiry_date)
	return context
