app_name = "loc_planning"
app_title = "LOC Planning"
app_publisher = "Oilibya"
app_description = "منظومة التخطيط والاستثمار - شركة ليبيا للنفط"
app_email = "it@oilibya.ly"
app_license = "mit"

# Fixtures
# --------
LOC_ROLES = [
	"LOC Planning Director",
	"Strategic Planning",
	"Statistics & Data",
	"Investment Section",
	"Department Coordinator",
	"Sales Office User",
	"Finance Budget",
	"Executive Viewer",
]


def _fixture_names():
	import json
	import os

	with open(
		os.path.join(os.path.dirname(__file__), "config", "fixture_names.json"), encoding="utf-8"
	) as fh:
		return json.load(fh)


_FIXTURE_NAMES = _fixture_names()

fixtures = [
	{"dt": "Role", "filters": [["name", "in", LOC_ROLES]]},
	{"dt": "Workflow State", "filters": [["name", "in", _FIXTURE_NAMES["states"]]]},
	{"dt": "Workflow Action Master", "filters": [["name", "in", _FIXTURE_NAMES["actions"]]]},
	{"dt": "Workflow", "filters": [["name", "in", _FIXTURE_NAMES["workflows"]]]},
]

# Jinja helpers available in print formats
jinja = {
	"methods": [
		"loc_planning.investment_registry.utils.get_certificate_qr",
		"loc_planning.investment_registry.utils.verification_url",
		"loc_planning.utils.print_utils.get_print_settings",
		"loc_planning.utils.print_utils.format_arabic_date",
	],
}

scheduler_events = {
	"daily": [
		"loc_planning.investment_registry.tasks.daily",
	],
}

required_apps = ["erpnext"]

app_include_css = "/assets/loc_planning/css/loc_planning.css"

after_install = "loc_planning.install.after_install"
after_migrate = "loc_planning.install.after_migrate"

# Generic guards (period lock, cancel reason, no deletion of approved docs).
# Each handler returns immediately for DocTypes that do not have the relevant field / module.
doc_events = {
	"*": {
		"validate": "loc_planning.utils.document_guard.on_validate",
		"before_update_after_submit": "loc_planning.utils.document_guard.on_before_update_after_submit",
		"before_cancel": "loc_planning.utils.document_guard.on_before_cancel",
		"on_trash": "loc_planning.utils.document_guard.on_trash",
	}
}

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "loc_planning",
# 		"logo": "/assets/loc_planning/logo.png",
# 		"title": "LOC Planning",
# 		"route": "/loc_planning",
# 		"has_permission": "loc_planning.api.permission.has_app_permission",
# 	}
# ]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `loc_planning/dock/loc_planning/loc_planning.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/loc_planning/css/loc_planning.css"
# app_include_js = "/assets/loc_planning/js/loc_planning.js"

# include js, css files in header of web template
# web_include_css = "/assets/loc_planning/css/loc_planning.css"
# web_include_js = "/assets/loc_planning/js/loc_planning.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "loc_planning/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_kanban_js = {"doctype" : "public/js/doctype_kanban.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "loc_planning/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "loc_planning.utils.jinja_methods",
# 	"filters": "loc_planning.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "loc_planning.install.before_install"
# after_install = "loc_planning.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "loc_planning.uninstall.before_uninstall"
# after_uninstall = "loc_planning.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "loc_planning.utils.before_app_install"
# after_app_install = "loc_planning.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "loc_planning.utils.before_app_uninstall"
# after_app_uninstall = "loc_planning.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "loc_planning.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "loc_planning.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "loc_planning.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["loc_planning.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"loc_planning.tasks.all"
# 	],
# 	"daily": [
# 		"loc_planning.tasks.daily"
# 	],
# 	"hourly": [
# 		"loc_planning.tasks.hourly"
# 	],
# 	"weekly": [
# 		"loc_planning.tasks.weekly"
# 	],
# 	"monthly": [
# 		"loc_planning.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "loc_planning.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "loc_planning.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "loc_planning.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "loc_planning.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["loc_planning.utils.before_request"]
# after_request = ["loc_planning.utils.after_request"]

# Job Events
# ----------
# before_job = ["loc_planning.utils.before_job"]
# after_job = ["loc_planning.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"loc_planning.auth.validate"
# ]

# on_social_login = "loc_planning.auth.on_social_login"

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
