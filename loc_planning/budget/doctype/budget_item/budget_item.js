// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Budget Item", {
	setup(frm) {
		frm.set_query("account", "accounts", () => ({
			filters: { company: frm.doc.company, is_group: 0, root_type: ["in", ["Expense", "Asset"]] },
		}));
		frm.set_query("cost_center", "accounts", () => ({ filters: { company: frm.doc.company } }));
	},
});
