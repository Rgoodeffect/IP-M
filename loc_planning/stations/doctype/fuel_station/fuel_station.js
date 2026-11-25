// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fuel Station", {
	setup(frm) {
		frm.set_query("sales_office", () => ({ filters: { department_type: "Sales Office" } }));
	},
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Monthly Data"), () =>
			frappe.set_route("List", "Station Monthly Data", { station: frm.doc.name })
		);
	},
});
