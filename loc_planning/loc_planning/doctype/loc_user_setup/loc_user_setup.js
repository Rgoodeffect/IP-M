// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

const LOC_ROLES = [
	"LOC Planning Director",
	"Strategic Planning",
	"Statistics & Data",
	"Investment Section",
	"Department Coordinator",
	"Sales Office User",
	"Finance Budget",
	"Executive Viewer",
];

frappe.ui.form.on("LOC User Setup", {
	setup(frm) {
		frm.set_query("role", "assignments", () => ({ filters: { name: ["in", LOC_ROLES] } }));
		frm.set_query("user", "assignments", () => ({ filters: { user_type: "System User", enabled: 1 } }));
		frm.set_query("loc_department", "assignments", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			return row.role === "Sales Office User" ? { filters: { department_type: "Sales Office" } } : {};
		});
	},
	refresh(frm) {
		frm.add_custom_button(__("Apply"), () => {
			frm.call({ method: "apply_assignments", doc: frm.doc, freeze: true }).then((r) => {
				frappe.show_alert({ message: __("{0} assignments applied", [r.message || 0]), indicator: "green" });
				frm.reload_doc();
			});
		}).addClass("btn-primary");
	},
});
