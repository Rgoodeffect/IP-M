frappe.listview_settings["Company Activity Report"] = {
	add_fields: ["status", "docstatus", "readiness_pct"],
	has_indicator_for_draft: true,
	get_indicator(doc) {
		const map = { Draft: "gray", "Director Review": "blue", "General Manager Approval": "orange", Approved: "green", Cancelled: "red" };
		return [__(doc.status), map[doc.status] || "gray", "status,=," + doc.status];
	},
};
