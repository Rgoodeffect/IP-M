// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Reporting Period", {
	refresh(frm) {
		if (frm.is_new()) return;

		const closed = frm.doc.status === "Closed";
		frm.page.set_indicator(closed ? __("Closed") : __("Open"), closed ? "red" : "green");

		const can_manage = ["System Manager", "LOC Planning Director", "Strategic Planning"].some((r) =>
			frappe.user.has_role(r)
		);
		if (!can_manage) return;

		if (closed) {
			frm.add_custom_button(__("Reopen Period"), () => set_status(frm, "Open"));
		} else {
			frm.add_custom_button(__("Close Period"), () => set_status(frm, "Closed"));
		}
	},
});

function set_status(frm, status) {
	const title =
		status === "Closed"
			? __("Closing the period locks all data linked to it. Continue?")
			: __("Reopening the period allows its data to be changed again. Continue?");
	frappe.prompt(
		{ fieldname: "remarks", fieldtype: "Small Text", label: __("Remarks") },
		(values) => {
			frappe
				.call({
					method: "loc_planning.loc_planning.doctype.reporting_period.reporting_period.set_period_status",
					args: { name: frm.doc.name, status: status, remarks: values.remarks },
					freeze: true,
				})
				.then(() => frm.reload_doc());
		},
		title
	);
}
