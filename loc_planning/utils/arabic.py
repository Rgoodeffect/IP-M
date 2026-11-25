"""Arabic text helpers: normalisation for duplicate detection and diacritics removal."""

import re

HARAKAT = re.compile("[\u064b-\u0652\u0670]")
TATWEEL = "\u0640"
_ALEF = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_NOISE_WORDS = {
	"شركه",
	"الشركه",
	"مؤسسه",
	"وكاله",
	"للخدمات",
	"ذ.م.م",
	"ذمم",
	"المحدوده",
	"محدوده",
	"المساهمه",
	"co",
	"company",
	"ltd",
	"llc",
	"inc",
}


def strip_diacritics(text):
	"""Remove harakat and tatweel. Official outputs must not carry tashkeel."""
	if not text:
		return text
	return HARAKAT.sub("", str(text)).replace(TATWEEL, "")


def normalize_digits(text):
	return str(text or "").translate(_DIGITS)


def normalize_name(text):
	"""Canonical form of a company name for duplicate detection."""
	if not text:
		return ""
	text = strip_diacritics(normalize_digits(text)).lower().translate(_ALEF)
	text = re.sub(r"[^\w\s.]", " ", text)
	words = [w for w in text.split() if w not in _NOISE_WORDS]
	return " ".join(words)


def normalize_identifier(value):
	"""Canonical form of an identifier (tax no, register no): digits/letters only."""
	return re.sub(r"[^0-9A-Za-z]", "", normalize_digits(value)).upper()
