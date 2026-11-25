frappe.listview_settings["Registration Certificate"] = {
	add_fields: ["status", "docstatus", "expiry_date"],
	has_indicator_for_draft: true,
	get_indicator(doc) {
		const map = {
			Draft: "gray",
			Issued: "green",
			Expired: "orange",
			Superseded: "blue",
			Cancelled: "red",
			Rejected: "red",
		};
		return [__(doc.status), map[doc.status] || "gray", "status,=," + doc.status];
	},
};
