"""Server-side SVG charts for official PDF / Word outputs (no JavaScript).

Categories run right-to-left so that the first category sits on the right, as in the
Arabic reading order. Text is plain SVG <text>; the browser engine that prints the PDF
shapes the Arabic letters.
"""

import math
from html import escape

PALETTE = ("#1f4e79", "#6fa8dc", "#c9a227", "#7f7f7f", "#2e8b57", "#c0504d")


def _nice_max(value):
	if value <= 0:
		return 1
	exp = 10 ** math.floor(math.log10(value))
	for step in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
		if value <= step * exp:
			return step * exp
	return 10 * exp


def _fmt(value):
	value = float(value or 0)
	if abs(value) >= 1_000_000:
		text = f"{value / 1_000_000:,.1f}".rstrip("0").rstrip(".")
		return f"{text} مليون"
	if abs(value) >= 10_000:
		return f"{value / 1_000:,.0f} ألف"
	return f"{value:,.0f}"


def bar_chart(categories, series, width=680, height=300, font="sans-serif", unit=None):
	"""Grouped vertical bars. `series` = [(name, [values...]), ...]."""
	categories = [str(c) for c in categories]
	if not categories or not series:
		return ""
	left, right, top, bottom = 70, 20, 20, 70
	plot_w, plot_h = width - left - right, height - top - bottom
	top_value = _nice_max(max([max(v or [0]) for _n, v in series] + [0]))
	n_cat, n_ser = len(categories), len(series)
	group_w = plot_w / n_cat
	bar_w = min(38, group_w * 0.7 / n_ser)
	parts = [
		f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
		f'viewBox="0 0 {width} {height}" font-family="{escape(font)}" font-size="11" direction="rtl">'
	]
	# grid and axis labels
	for i in range(5):
		v = top_value * i / 4
		y = top + plot_h - plot_h * i / 4
		parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="#e3e7ec"/>')
		parts.append(
			f'<text x="{left - 6}" y="{y + 4:.1f}" text-anchor="end" fill="#5f6b7a" direction="ltr">{escape(_fmt(v))}</text>'
		)
	for ci, cat in enumerate(categories):
		# right-to-left: category 0 is the rightmost group
		gx = left + plot_w - (ci + 1) * group_w
		start = gx + (group_w - bar_w * n_ser) / 2
		for si, (_name, values) in enumerate(series):
			value = float(values[ci] or 0) if ci < len(values) else 0
			h = plot_h * value / top_value if top_value else 0
			x = start + (n_ser - 1 - si) * bar_w
			y = top + plot_h - h
			parts.append(
				f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w - 2:.1f}" height="{h:.1f}" fill="{PALETTE[si % len(PALETTE)]}" rx="2"/>'
			)
		label = cat if len(cat) <= 22 else cat[:21] + "…"
		parts.append(
			f'<text x="{gx + group_w / 2:.1f}" y="{top + plot_h + 18}" text-anchor="middle" fill="#1d2733">{escape(label)}</text>'
		)
	parts.append(
		f'<line x1="{left}" y1="{top + plot_h}" x2="{width - right}" y2="{top + plot_h}" stroke="#9aa5b1"/>'
	)
	# legend (right aligned)
	lx = width - right
	ly = height - 18
	for si, (name, _values) in enumerate(series):
		text = escape(str(name))
		parts.append(
			f'<rect x="{lx - 12}" y="{ly - 9}" width="10" height="10" fill="{PALETTE[si % len(PALETTE)]}"/>'
		)
		parts.append(f'<text x="{lx - 16}" y="{ly}" text-anchor="end" fill="#1d2733">{text}</text>')
		lx -= 34 + 6.5 * len(str(name))
	if unit:
		parts.append(
			f'<text x="{left - 6}" y="{top - 6}" text-anchor="end" fill="#5f6b7a">{escape(unit)}</text>'
		)
	parts.append("</svg>")
	return "".join(parts)
