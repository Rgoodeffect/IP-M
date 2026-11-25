// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Registration Certificate", {
	setup(frm) {
		frm.set_query("registered_company", () => ({ filters: { status: "Active" } }));
		frm.set_query("renewal_of", () => ({
			filters: { registered_company: frm.doc.registered_company || "", docstatus: 1 },
		}));
	},
	refresh(frm) {
		if (frm.doc.docstatus === 1 && ["Issued", "Expired"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Renew"), () => {
				frappe.new_doc("Registration Certificate", {
					registered_company: frm.doc.registered_company,
					request_type: "Renewal",
					renewal_of: frm.doc.name,
				});
			});
		}
		if (frm.doc.docstatus === 1 && frm.doc.verification_code) {
			frm.add_custom_button(__("Verification Page"), () => {
				window.open(`/verify-certificate?code=${encodeURIComponent(frm.doc.verification_code)}`);
			});
		}
		if (frm.doc.docstatus === 1 && !frm.doc.cancel_reason) {
			frm.set_intro(__("To cancel this certificate, enter the cancellation reason and save first."), "blue");
		}
	},
	registered_company(frm) {
		if (!frm.doc.registered_company || frm.doc.request_type === "Renewal") return;
		frappe.db
			.get_value("Registered Company", frm.doc.registered_company, "current_certificate")
			.then((r) => {
				const current = r.message && r.message.current_certificate;
				if (current) {
					frm.set_value("request_type", "Renewal");
					frm.set_value("renewal_of", current);
				}
			});
	},
});
