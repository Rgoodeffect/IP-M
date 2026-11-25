"""Shared constants for the LOC Planning app."""

ROLE_DIRECTOR = "LOC Planning Director"
ROLE_STRATEGIC_PLANNING = "Strategic Planning"
ROLE_STATISTICS = "Statistics & Data"
ROLE_INVESTMENT = "Investment Section"
ROLE_DEPT_COORDINATOR = "Department Coordinator"
ROLE_SALES_OFFICE = "Sales Office User"
ROLE_FINANCE_BUDGET = "Finance Budget"
ROLE_EXECUTIVE = "Executive Viewer"

LOC_ROLES = (
	ROLE_DIRECTOR,
	ROLE_STRATEGIC_PLANNING,
	ROLE_STATISTICS,
	ROLE_INVESTMENT,
	ROLE_DEPT_COORDINATOR,
	ROLE_SALES_OFFICE,
	ROLE_FINANCE_BUDGET,
	ROLE_EXECUTIVE,
)

# Roles allowed to open/close reporting periods
PERIOD_ADMIN_ROLES = ("System Manager", ROLE_DIRECTOR, ROLE_STRATEGIC_PLANNING)

LOC_MODULES = ("LOC Planning", "Budget", "Stations", "Activity Report", "Investment Registry")

# Field that ties a transaction to a Reporting Period (used by the period lock)
PERIOD_FIELD = "reporting_period"
# Field that holds the mandatory reason when cancelling an approved document
CANCEL_REASON_FIELD = "cancel_reason"

SETTINGS_DOCTYPE = "LOC Planning Settings"
