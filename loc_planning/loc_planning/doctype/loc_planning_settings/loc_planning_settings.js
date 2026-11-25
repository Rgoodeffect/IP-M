// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.ui.form.on("LOC Planning Settings", {
	onload(frm) {
		if (!frm.doc.periods_year) {
			// helper field only: set without marking the form dirty
			frm.doc.periods_year = new Date().getFullYear();
			frm.refresh_field("periods_year");
		}
	},
	create_periods(frm) {
		if (!frm.doc.periods_year) return;
		frappe
			.call({
				method: "loc_planning.loc_planning.doctype.reporting_period.reporting_period.create_periods_for_year",
				args: { year: frm.doc.periods_year },
				freeze: true,
			})
			.then((r) => {
				const created = r.message || [];
				frappe.msgprint(
					created.length
						? __("{0} periods created for {1}", [created.length, frm.doc.periods_year])
						: __("All periods of {0} already exist", [frm.doc.periods_year])
				);
			});
	},
});
