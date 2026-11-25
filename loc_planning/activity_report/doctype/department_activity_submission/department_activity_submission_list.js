frappe.listview_settings["Department Activity Submission"] = {
	add_fields: ["status", "docstatus", "due_date"],
	has_indicator_for_draft: true,
	get_indicator(doc) {
		const map = {
			Draft: "gray",
			"Manager Review": "blue",
			"Statistics Review": "orange",
			"Planning Approval": "orange",
			Returned: "red",
			Approved: "green",
			"Included in Report": "green",
			Cancelled: "red",
		};
		return [__(doc.status), map[doc.status] || "gray", "status,=," + doc.status];
	},
};
