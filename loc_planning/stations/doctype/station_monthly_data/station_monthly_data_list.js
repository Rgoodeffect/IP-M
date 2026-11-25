frappe.listview_settings["Station Monthly Data"] = {
	add_fields: ["status", "docstatus"],
	has_indicator_for_draft: true,
	get_indicator(doc) {
		const map = { Draft: "gray", "Pending Review": "orange", Returned: "red", Approved: "green", Cancelled: "red" };
		return [__(doc.status), map[doc.status] || "gray", "status,=," + doc.status];
	},
};
