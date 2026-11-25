// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

const ACT_METHOD = "loc_planning.activity_report.doctype.department_activity_submission.department_activity_submission";

frappe.ui.form.on("Department Activity Submission", {
	setup(frm) {
		frm.set_query("department", () => ({ filters: { requires_activity_report: 1, is_active: 1 } }));
		frappe.db.get_single_value("LOC Planning Settings", "activity_report_period_type").then((type) => {
			frm.set_query("reporting_period", () => ({ filters: { period_type: type || "Quarterly" } }));
		});
	},
	refresh(frm) {
		if (frm.doc.workflow_state === "Returned" && frm.doc.review_comment) {
			frm.set_intro(__("Returned for revision: {0}", [frm.doc.review_comment]), "orange");
		} else if (frm.doc.due_date && frm.doc.docstatus === 0 && ["Draft", "Returned"].includes(frm.doc.workflow_state || "Draft")) {
			const late = frappe.datetime.get_day_diff(frappe.datetime.get_today(), frm.doc.due_date);
			if (late > 0) frm.set_intro(__("This report is {0} days late", [late]), "red");
			else frm.set_intro(__("Due date: {0}", [frappe.datetime.str_to_user(frm.doc.due_date)]), "blue");
		}
	},
	department(frm) {
		if (!frm.doc.department || (frm.doc.indicators || []).length) return;
		frappe.call({ method: `${ACT_METHOD}.get_template_indicators`, args: { department: frm.doc.department } }).then((r) => {
			(r.message || []).forEach((row) => frm.add_child("indicators", row));
			frm.refresh_field("indicators");
		});
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
						.call({ method: `${ACT_METHOD}.set_review_comment`, args: { name: frm.doc.name, comment: values.comment } })
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

frappe.ui.form.on("Activity Submission Item", {
	target: compute,
	executed: compute,
});

function compute(frm, cdt, cdn) {
	const r = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "achievement_pct", r.target ? flt((flt(r.executed) / flt(r.target)) * 100, 2) : 0);
}
