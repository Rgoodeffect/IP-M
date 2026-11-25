// Copyright (c) 2026, Oilibya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Station Data Import", {
	setup(frm) {
		frm.set_query("reporting_period", () => ({ filters: { period_type: "Monthly", status: "Open" } }));
		frm.set_query("sales_office", () => ({ filters: { department_type: "Sales Office" } }));
	},
	refresh(frm) {
		if (frm.is_new()) {
			frm.set_intro(__("Save first, then download the template, fill it and attach it here."), "blue");
			return;
		}
		frm.add_custom_button(__("Download Template"), () => {
			window.open(
				"/api/method/loc_planning.stations.doctype.station_data_import.station_data_import.download_template?name=" +
					encodeURIComponent(frm.doc.name)
			);
		});
		if (frm.doc.import_file) {
			frm.add_custom_button(__("Validate"), () => run(frm, "validate_file"));
			frm.add_custom_button(__("Import"), () => run(frm, "start_import")).addClass("btn-primary");
		}
	},
});

function run(frm, method) {
	const go = () =>
		frm.call({ method, doc: frm.doc, freeze: true, freeze_message: __("Processing...") }).then(() => frm.reload_doc());
	if (frm.is_dirty()) {
		frm.save().then(go);
	} else {
		go();
	}
}
