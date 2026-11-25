"""Phase 6 upgrade: General Manager role and the default activity report template."""

from loc_planning.install import ensure_roles, seed_simple


def execute():
	ensure_roles()
	seed_simple("Activity Report Template", "template_name", "activity_report_templates.json")
