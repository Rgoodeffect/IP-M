"""Phase 3 upgrade: seed station operation types and support activity types."""

from loc_planning.install import seed_simple


def execute():
	seed_simple("Station Operation Type", "operation_type_name", "station_operation_types.json")
	seed_simple("Support Activity Type", "activity_type_name", "support_activity_types.json")
