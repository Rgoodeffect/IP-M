// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Budget Execution Entry", {
	setup(frm) {
		frm.set_query("budget_item", () => ({ filters: { is_active: 1 } }));
	},
	budget_item(frm) {
		if (!frm.doc.budget_item) return;
		frappe.db.get_value("Budget Item", frm.doc.budget_item, "execution_source").then((r) => {
			const gl = r.message && r.message.execution_source === "General Ledger";
			frm.set_df_property("entry_type", "options", gl ? ["Commitment"] : ["Commitment", "Actual Expense"]);
			if (gl) frm.set_value("entry_type", "Commitment");
		});
	},
});
