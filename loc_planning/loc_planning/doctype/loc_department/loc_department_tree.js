frappe.treeview_settings["LOC Department"] = {
	ignore_fields: ["parent_loc_department"],
	get_tree_nodes: "loc_planning.loc_planning.doctype.loc_department.loc_department.get_children",
	add_tree_node: "loc_planning.loc_planning.doctype.loc_department.loc_department.add_node",
	fields: [
		{ fieldtype: "Data", fieldname: "department_name", label: __("Department Name"), reqd: true },
		{
			fieldtype: "Select",
			fieldname: "department_type",
			label: __("Department Type"),
			options: [
				{ value: "Department", label: __("Department") },
				{ value: "Office", label: __("Office") },
				{ value: "Sales Office", label: __("Sales Office") },
				{ value: "Section", label: __("Section") },
				{ value: "Unit", label: __("Unit") },
			],
			default: "Department",
			reqd: true,
		},
		{ fieldtype: "Link", fieldname: "region", label: __("Region"), options: "LOC Region" },
		{ fieldtype: "Check", fieldname: "is_group", label: __("Is Group") },
		{ fieldtype: "Check", fieldname: "requires_activity_report", label: __("Requires Activity Report") },
	],
	breadcrumb: "LOC Planning",
	root_label: __("LOC Department"),
	get_tree_root: false,
	title: __("LOC Department"),
	onload(treeview) {
		treeview.make_tree();
	},
};
