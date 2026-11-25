// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Budget Revision", {
	setup(frm) {
		frm.set_query("approved_budget", () => ({ filters: { docstatus: 1 } }));
	},
	revision_type(frm) {
		const type = frm.doc.revision_type;
		frm.fields_dict.lines.grid.update_docfield_property("from_item", "read_only", type === "Increase");
		frm.fields_dict.lines.grid.update_docfield_property("to_item", "read_only", type === "Decrease");
	},
	refresh(frm) {
		frm.trigger("revision_type");
	},
});
