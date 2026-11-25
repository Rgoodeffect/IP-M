// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.ui.form.on("LOC Department", {
	setup(frm) {
		frm.set_query("parent_loc_department", () => ({
			filters: { is_group: 1, name: ["!=", frm.doc.name || ""] },
		}));
		frm.set_query("erpnext_department", () => ({
			filters: frm.doc.company ? { company: frm.doc.company } : {},
		}));
		frm.set_query("cost_center", () => ({
			filters: Object.assign({ is_group: 0 }, frm.doc.company ? { company: frm.doc.company } : {}),
		}));
	},
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("View Tree"), () => frappe.set_route("Tree", "LOC Department"));
		}
	},
});
