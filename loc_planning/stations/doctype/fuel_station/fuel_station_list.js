frappe.listview_settings["Fuel Station"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const map = { Operating: "green", Stopped: "red", "Under Maintenance": "orange", "Under Construction": "blue" };
		return [__(doc.status), map[doc.status] || "gray", "status,=," + doc.status];
	},
};
