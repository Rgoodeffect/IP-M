"""Phase 2 upgrade: seed classifications / document types and new settings defaults."""

from loc_planning.install import seed_simple
from loc_planning.loc_planning.doctype.loc_planning_settings.loc_planning_settings import apply_defaults


def execute():
	seed_simple("Company Classification", "classification_name", "company_classifications.json")
	seed_simple("Company Document Type", "document_type_name", "company_document_types.json")
	apply_defaults()
