"""Phase 4 upgrade: seed budget chapters and the agreed item ownership."""

from loc_planning.install import seed_simple


def execute():
	seed_simple("Budget Chapter", "chapter_name", "budget_chapters.json")
	seed_simple("Budget Item", "item_name", "budget_items.json")
