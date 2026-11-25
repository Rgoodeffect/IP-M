"""Reporting period arithmetic: names, titles, date ranges and comparisons."""

import datetime

from frappe import _
from frappe.utils import get_last_day

MONTHS_AR = (
	"يناير",
	"فبراير",
	"مارس",
	"أبريل",
	"مايو",
	"يونيو",
	"يوليو",
	"أغسطس",
	"سبتمبر",
	"أكتوبر",
	"نوفمبر",
	"ديسمبر",
)
ORDINALS_AR = ("الأول", "الثاني", "الثالث", "الرابع")

# period_type -> (number of periods in a year, months per period, name prefix)
PERIOD_SPEC = {
	"Monthly": (12, 1, ""),
	"Quarterly": (4, 3, "Q"),
	"Half-Yearly": (2, 6, "H"),
	"Annual": (1, 12, ""),
}


def validate_period_args(period_type, year, number):
	if period_type not in PERIOD_SPEC:
		raise ValueError(_("Invalid period type {0}").format(period_type))
	count = PERIOD_SPEC[period_type][0]
	if period_type == "Annual":
		number = 1
	if not year or int(year) < 2000 or int(year) > 2100:
		raise ValueError(_("Invalid year {0}").format(year))
	if not number or not 1 <= int(number) <= count:
		raise ValueError(_("Period number must be between 1 and {0}").format(count))
	return int(year), int(number)


def period_name(period_type, year, number):
	year, number = validate_period_args(period_type, year, number)
	if period_type == "Monthly":
		return f"{year}-{number:02d}"
	if period_type == "Annual":
		return str(year)
	return f"{year}-{PERIOD_SPEC[period_type][2]}{number}"


def period_dates(period_type, year, number):
	year, number = validate_period_args(period_type, year, number)
	months = PERIOD_SPEC[period_type][1]
	start_month = (number - 1) * months + 1
	from_date = datetime.date(year, start_month, 1)
	to_date = get_last_day(datetime.date(year, start_month + months - 1, 1))
	return from_date, to_date


def period_title(period_type, year, number):
	year, number = validate_period_args(period_type, year, number)
	if period_type == "Monthly":
		return f"{MONTHS_AR[number - 1]} {year}"
	if period_type == "Quarterly":
		return f"الربع {ORDINALS_AR[number - 1]} {year}"
	if period_type == "Half-Yearly":
		return f"النصف {ORDINALS_AR[number - 1]} {year}"
	return f"سنة {year}"


def previous_period(period_type, year, number):
	"""Return (year, number) of the period immediately before."""
	year, number = validate_period_args(period_type, year, number)
	if number > 1:
		return year, number - 1
	return year - 1, PERIOD_SPEC[period_type][0]


def same_period_last_year(period_type, year, number):
	year, number = validate_period_args(period_type, year, number)
	return year - 1, number
