// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Company Activity Report", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.template) {
			frappe
				.call("loc_planning.activity_report.doctype.company_activity_report.company_activity_report.get_default_template")
				.then((r) => r.message && frm.set_value("template", r.message));
		}
	},
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Refresh Data"), () => {
				frm.call({ method: "refresh_data", doc: frm.doc, freeze: true, freeze_message: __("Collecting data...") }).then(() =>
					frm.reload_doc()
				);
			}).addClass("btn-primary");
		}
		frm.add_custom_button(__("Download Word"), () => {
			window.open(
				"/api/method/loc_planning.activity_report.docx_export.download_docx?name=" + encodeURIComponent(frm.doc.name)
			);
		});
		const pct = flt(frm.doc.readiness_pct);
		const color = pct >= 100 ? "green" : pct >= 50 ? "orange" : "red";
		frm.dashboard.add_indicator(__("Readiness") + `: ${pct}%`, color);
		if (frm.doc.docstatus === 0 && frm.doc.incomplete_sections) {
			frm.set_intro(
				__("Incomplete sections:") + "<br>" + frappe.utils.escape_html(frm.doc.incomplete_sections).replace(/\n/g, "<br>"),
				"orange"
			);
		}
		if (frm.doc.docstatus === 0 && frm.doc.review_comment && frm.doc.workflow_state === "Draft") {
			frm.set_intro(__("Returned for revision: {0}", [frm.doc.review_comment]), "red");
		}
	},
	before_workflow_action(frm) {
		if (frm.selected_workflow_action !== "Return for Revision") return;
		return new Promise((resolve, reject) => {
			const d = new frappe.ui.Dialog({
				title: __("Return for Revision"),
				fields: [{ fieldname: "comment", fieldtype: "Small Text", label: __("Review Comment"), reqd: 1 }],
				primary_action_label: __("Return for Revision"),
				primary_action(values) {
					frappe
						.call({
							method: "loc_planning.utils.workflow.set_review_comment",
							args: { doctype: frm.doctype, name: frm.doc.name, comment: values.comment },
						})
						.then(() => {
							d.hide();
							resolve();
						}, reject);
				},
			});
			d.onhide = () => reject();
			d.show();
		});
	},
});
