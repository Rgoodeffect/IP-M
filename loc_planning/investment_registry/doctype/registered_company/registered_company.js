// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Registered Company", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("New Certificate Request"), () => {
			const renewal = !!frm.doc.current_certificate;
			frappe.new_doc("Registration Certificate", {
				registered_company: frm.doc.name,
				request_type: renewal ? "Renewal" : "New",
				renewal_of: renewal ? frm.doc.current_certificate : null,
			});
		});
		const colors = { Valid: "green", "Expiring Soon": "orange", Expired: "red", None: "gray" };
		if (frm.doc.certificate_status) {
			frm.dashboard.add_indicator(
				__("Certificate") + ": " + __(frm.doc.certificate_status),
				colors[frm.doc.certificate_status] || "gray"
			);
		}
	},
});
