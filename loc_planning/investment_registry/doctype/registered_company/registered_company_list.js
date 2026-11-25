frappe.listview_settings["Registered Company"] = {
	add_fields: ["status", "certificate_status"],
	get_indicator(doc) {
		const map = { Active: "green", Suspended: "orange", Blacklisted: "red", Inactive: "gray" };
		return [__(doc.status), map[doc.status] || "gray", "status,=," + doc.status];
	},
};
