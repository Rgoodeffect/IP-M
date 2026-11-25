// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Station Monthly Data", {
	setup(frm) {
		frm.set_query("reporting_period", () => ({ filters: { period_type: "Monthly", status: "Open" } }));
		frm.set_query("station", () => ({ filters: { is_active: 1 } }));
	},
	station(frm) {
		load_defaults(frm);
	},
	reporting_period(frm) {
		load_defaults(frm);
	},
	refresh(frm) {
		if (frm.doc.review_comment && frm.doc.workflow_state === "Returned") {
			frm.set_intro(__("Returned for revision: {0}", [frm.doc.review_comment]), "orange");
		}
	},
});

frappe.ui.form.on("Station Monthly Product", {
	target_qty: compute_row,
	actual_qty: compute_row,
	opening_stock: compute_row,
	received_qty: compute_row,
	closing_stock: compute_row,
});

function compute_row(frm, cdt, cdn) {
	const r = locals[cdt][cdn];
	const pct = r.target_qty ? (flt(r.actual_qty) / flt(r.target_qty)) * 100 : 0;
	frappe.model.set_value(cdt, cdn, "achievement_pct", flt(pct, 2));
	frappe.model.set_value(
		cdt,
		cdn,
		"stock_variance",
		flt(flt(r.opening_stock) + flt(r.received_qty) - flt(r.actual_qty) - flt(r.closing_stock), 3)
	);
}

function load_defaults(frm) {
	if (!frm.is_new() || !frm.doc.station || !frm.doc.reporting_period) return;
	if ((frm.doc.products || []).length) return;
	frappe
		.call({
			method: "loc_planning.stations.doctype.station_monthly_data.station_monthly_data.get_defaults",
			args: { station: frm.doc.station, reporting_period: frm.doc.reporting_period },
		})
		.then((r) => {
			const d = r.message || {};
			frm.clear_table("products");
			(d.products || []).forEach((row) => frm.add_child("products", row));
			frm.clear_table("support_revenues");
			(d.support_revenues || []).forEach((row) => frm.add_child("support_revenues", row));
			frm.refresh_fields(["products", "support_revenues"]);
		});
}
