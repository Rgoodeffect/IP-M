frappe.listview_settings["Reporting Period"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		return doc.status === "Closed"
			? [__("Closed"), "red", "status,=,Closed"]
			: [__("Open"), "green", "status,=,Open"];
	},
};
