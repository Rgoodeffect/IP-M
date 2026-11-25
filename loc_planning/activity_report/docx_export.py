"""Word (.docx) export of the Company Activity Report (second output besides the PDF).

Uses the same blocks as the print format (`render.build_blocks`). Paragraphs, runs and
tables are marked right-to-left; charts are the same SVGs rasterised to PNG with the
headless Chromium that Frappe already uses for PDFs.
"""

import io
import os
import re
import shutil
import subprocess
import tempfile

import frappe
from frappe import _
from frappe.utils import strip_html

from loc_planning.activity_report.render import build_blocks
from loc_planning.utils.arabic import strip_diacritics
from loc_planning.utils.print_utils import arabic_output, format_arabic_date, get_print_settings

PRIMARY = "1F4E79"


@frappe.whitelist()
def download_docx(name: str):
	doc = frappe.get_doc("Company Activity Report", name)
	doc.check_permission("read")
	with arabic_output():
		content = build_docx(doc)
	frappe.response["filename"] = f"{doc.name}.docx"
	frappe.response["filecontent"] = content
	frappe.response["type"] = "binary"


def build_docx(doc):
	from docx import Document
	from docx.enum.section import WD_ORIENT
	from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
	from docx.shared import Pt, RGBColor

	ps = get_print_settings()
	font = (frappe.get_cached_doc("LOC Planning Settings").report_font_family or "Fanan").strip()
	document = Document()
	_set_default_font(document, font, ps.base_font_size)

	if doc.docstatus != 1:
		header = document.sections[0].header.paragraphs[0]
		_rtl(header)
		run = header.add_run("مسودة")
		run.font.color.rgb = RGBColor(0xC0, 0x30, 0x30)
		run.bold = True
		_rtl_run(run)

	# cover ------------------------------------------------------------------
	logo = _local_file(frappe.get_cached_doc("LOC Planning Settings").company_logo)
	if logo:
		p = document.add_paragraph()
		p.alignment = WD_ALIGN_PARAGRAPH.CENTER
		p.add_run().add_picture(logo, height=Pt(80))
	for text, size, bold, color in (
		(ps.company_name, ps.base_font_size + 8, True, None),
		(ps.issuer_name, ps.base_font_size + 3, False, None),
		("", ps.base_font_size, False, None),
		(strip_diacritics(doc.report_title), ps.base_font_size + 14, True, PRIMARY),
		(
			frappe.db.get_value("Reporting Period", doc.reporting_period, "title"),
			ps.base_font_size + 5,
			False,
			None,
		),
		(
			_("Company-wide") if doc.scope != "Region" else _("Region: {0}").format(doc.region),
			ps.base_font_size + 1,
			False,
			None,
		),
		(format_arabic_date(doc.approved_on or frappe.utils.today()), ps.base_font_size, False, None),
	):
		p = document.add_paragraph()
		p.alignment = WD_ALIGN_PARAGRAPH.CENTER
		_rtl(p)
		if text:
			_add_text(p, text, size=size, bold=bold, color=color)
	document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

	# contents ---------------------------------------------------------------
	sections = doc.get_sections()
	_heading(document, "المحتويات", ps.base_font_size + 5)
	for i, s in enumerate(sections, start=1):
		p = document.add_paragraph()
		_rtl(p)
		_add_text(p, f"{i}. {strip_diacritics(s.title)}", size=ps.base_font_size + 1)
	document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

	# sections ---------------------------------------------------------------
	for i, s in enumerate(sections, start=1):
		_heading(document, f"{i}. {strip_diacritics(s.title)}", ps.base_font_size + 4)
		for block in build_blocks(s, ps):
			if block.get("title"):
				_heading(document, block["title"], ps.base_font_size + 1, color="2B3A4A")
			kind = block["type"]
			if kind == "kpis":
				_table(
					document, [label for label, _v in block["items"]], [[v for _l, v in block["items"]]], ps
				)
			elif kind == "table":
				_table(
					document,
					block["headers"],
					block["rows"],
					ps,
					numeric=block.get("numeric"),
					bold_rows=block.get("bold_rows"),
				)
			elif kind == "chart" and block.get("svg"):
				png = svg_to_png(block["svg"])
				if png:
					p = document.add_paragraph()
					p.alignment = WD_ALIGN_PARAGRAPH.CENTER
					p.add_run().add_picture(io.BytesIO(png), width=Pt(430))
			elif kind == "html":
				for para in _html_paragraphs(block["html"]):
					p = document.add_paragraph()
					_rtl(p)
					p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
					_add_text(p, para, size=ps.base_font_size)
			elif kind == "note":
				p = document.add_paragraph()
				_rtl(p)
				_add_text(p, block["text"], size=ps.base_font_size, italic=True)

	buf = io.BytesIO()
	document.save(buf)
	return buf.getvalue()


# --------------------------------------------------------------------------------------
# python-docx helpers (RTL)
# --------------------------------------------------------------------------------------


def _oxml(tag, **attrs):
	from docx.oxml import OxmlElement
	from docx.oxml.ns import qn

	el = OxmlElement(tag)
	for k, v in attrs.items():
		el.set(qn(k), v)
	return el


def _rtl(paragraph):
	ppr = paragraph._p.get_or_add_pPr()
	ppr.append(_oxml("w:bidi"))
	if paragraph.alignment is None:
		from docx.enum.text import WD_ALIGN_PARAGRAPH

		paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def _rtl_run(run):
	rpr = run._r.get_or_add_rPr()
	rpr.append(_oxml("w:rtl"))


def _add_text(paragraph, text, size=None, bold=False, italic=False, color=None):
	from docx.shared import Pt, RGBColor

	run = paragraph.add_run(strip_diacritics(str(text)))
	_rtl_run(run)
	if size:
		run.font.size = Pt(size)
		run._r.get_or_add_rPr().append(_oxml("w:szCs", **{"w:val": str(int(size * 2))}))
	if bold:
		run.bold = True
		run._r.get_or_add_rPr().append(_oxml("w:bCs"))
	if italic:
		run.italic = True
	if color:
		run.font.color.rgb = RGBColor.from_string(color)
	return run


def _heading(document, text, size, color=PRIMARY):
	p = document.add_paragraph()
	_rtl(p)
	p.paragraph_format.space_before = None
	p.paragraph_format.keep_with_next = True
	_add_text(p, text, size=size, bold=True, color=color)
	return p


def _set_default_font(document, font, size):
	from docx.shared import Pt

	style = document.styles["Normal"]
	style.font.name = font
	style.font.size = Pt(size)
	rpr = style.element.get_or_add_rPr()
	fonts = rpr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rFonts")
	if fonts is None:
		fonts = _oxml("w:rFonts")
		rpr.append(fonts)
	from docx.oxml.ns import qn

	for attr in ("w:ascii", "w:hAnsi", "w:cs"):
		fonts.set(qn(attr), font)
	rpr.append(_oxml("w:rtl"))


def _shade(cell, fill):
	tcpr = cell._tc.get_or_add_tcPr()
	tcpr.append(_oxml("w:shd", **{"w:val": "clear", "w:color": "auto", "w:fill": fill}))


def _table(document, headers, rows, ps, numeric=None, bold_rows=None):
	from docx.enum.text import WD_ALIGN_PARAGRAPH
	from docx.shared import Pt, RGBColor

	table = document.add_table(rows=1, cols=len(headers))
	table.style = "Table Grid"
	tblpr = table._tbl.tblPr
	tblpr.append(_oxml("w:bidiVisual"))
	table.autofit = False
	for i, h in enumerate(headers):
		cell = table.rows[0].cells[i]
		_shade(cell, PRIMARY)
		p = cell.paragraphs[0]
		_rtl(p)
		run = _add_text(p, h, size=ps.base_font_size - (3 if len(headers) > 6 else 1), bold=True)
		run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
	# repeat the header row on every page
	table.rows[0]._tr.get_or_add_trPr().append(_oxml("w:tblHeader"))
	size = ps.base_font_size - (3 if len(headers) > 6 else 1)
	for r_index, row in enumerate(rows):
		cells = table.add_row().cells
		bold = bool(bold_rows and r_index in bold_rows)
		for i, value in enumerate(row):
			p = cells[i].paragraphs[0]
			_rtl(p)
			if numeric and i < len(numeric) and numeric[i]:
				p.alignment = WD_ALIGN_PARAGRAPH.LEFT
				# keep numbers on one line (no "3,876," / "226" splits)
				cells[i]._tc.get_or_add_tcPr().append(_oxml("w:noWrap"))
			_add_text(p, value, size=size, bold=bold)
			if bold:
				_shade(cells[i], "E6EDF5")
	_fit_columns(table, headers, rows, numeric, font_size=size)
	document.add_paragraph().paragraph_format.space_after = Pt(4)
	return table


def _fit_columns(table, headers, rows, numeric=None, font_size=10, total_twips=9300):
	"""Numeric columns get the absolute width of their longest value at the table's font
	size (numbers never break); text columns share the remaining width and wrap."""
	from docx.shared import Twips

	char_twips = font_size * 0.66 * 20  # average digit width ~0.6em, with a margin
	padding = 260
	widths, text_cols = [], []
	for i, h in enumerate(headers):
		if numeric and i < len(numeric) and numeric[i]:
			longest = max((len(str(r[i])) for r in rows if i < len(r)), default=1)
			header_word = max((len(w) for w in str(h).split()), default=1)
			widths.append(int(max(longest + 1, header_word, 5) * char_twips + padding))
		else:
			widths.append(None)
			text_cols.append(i)
	remaining = max(total_twips - sum(w for w in widths if w), 900 * max(len(text_cols), 1))
	for i in text_cols:
		widths[i] = int(remaining / len(text_cols))
	if sum(widths) > total_twips:  # very wide tables: shrink everything to the page width
		factor = total_twips / sum(widths)
		widths = [int(w * factor) for w in widths]
	for i, col in enumerate(table.columns):
		col.width = Twips(widths[i])
		for cell in col.cells:
			cell.width = Twips(widths[i])


def _html_paragraphs(html):
	parts = re.split(r"(?i)</p>|<br\s*/?>|</li>|</h\d>", html or "")
	return [t for t in (strip_html(p).strip() for p in parts) if t]


def _local_file(file_url):
	if not file_url:
		return None
	try:
		path = frappe.get_doc("File", {"file_url": file_url}).get_full_path()
		return path if os.path.exists(path) else None
	except Exception:
		return None


# --------------------------------------------------------------------------------------
# SVG -> PNG through headless Chromium
# --------------------------------------------------------------------------------------


def chromium_path():
	path = shutil.which(frappe.get_common_site_config().get("chromium_path") or "")
	if path:
		return path
	try:
		from frappe.utils.print_utils import find_or_download_chromium_executable

		return find_or_download_chromium_executable()
	except Exception:
		return None


def svg_to_png(svg, scale=2):
	m = re.search(r'width="(\d+)"[^>]*height="(\d+)"', svg)
	width, height = (int(m.group(1)), int(m.group(2))) if m else (680, 300)
	binary = chromium_path()
	if not binary:
		return None
	with tempfile.TemporaryDirectory() as tmp:
		html = os.path.join(tmp, "chart.html")
		png = os.path.join(tmp, "chart.png")
		with open(html, "w", encoding="utf-8") as fh:
			fh.write(f"<html><body style='margin:0;background:#fff'>{svg}</body></html>")
		try:
			subprocess.run(
				[
					binary,
					"--headless",
					"--no-sandbox",
					"--disable-gpu",
					"--hide-scrollbars",
					f"--force-device-scale-factor={scale}",
					f"--window-size={width},{height}",
					f"--screenshot={png}",
					f"file://{html}",
				],
				check=True,
				capture_output=True,
				timeout=60,
			)
			with open(png, "rb") as fh:
				return fh.read()
		except Exception:
			frappe.log_error(title="LOC Planning: chart rendering for Word failed")
			return None
