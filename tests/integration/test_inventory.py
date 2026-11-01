"""Exhaustiveness guard: every pyclifer feature needs a scenario or a justified exclusion.

The inventory is discovered from the code, never listed by hand. A new GroupConfig field,
option factory, public symbol or event that is not declared in scenarios.py fails this suite.
"""

from pathlib import Path

import pytest

from tests.integration.inventory import discover_inventory
from tests.integration.scenarios import COVERED, EXCLUDED, PENDING

_REPOSITORY = Path(__file__).resolve().parents[2]


def _pending_names() -> list[str]:
    """Flatten the PENDING mapping (item -> names) into a list of names."""
    return [name for names in PENDING.values() for name in names]


def _declared_names() -> list[str]:
    """Every name declared as covered, excluded or pending, with repetitions kept."""
    return [*COVERED, *EXCLUDED, *_pending_names()]


class TestDiscovery:
    """The inventory is read from the code."""

    def test_group_config_fields_are_discovered(self):
        assert "GroupConfig.use_rich_help" in discover_inventory()

    def test_option_factories_are_discovered(self):
        inventory = discover_inventory()

        assert "option_factory.config_option" in inventory
        assert "option_factory.pagination_options" in inventory

    def test_public_symbols_are_discovered_without_dunder_names(self):
        inventory = discover_inventory()

        assert "public.app_group" in inventory
        assert "public.EventsMixin" in inventory
        assert "public.__version__" not in inventory

    def test_framework_events_are_discovered(self):
        assert "event.config.loaded" in discover_inventory()


class TestExhaustiveness:
    """Nothing escapes the inventory, and nothing in it is stale."""

    def test_every_feature_has_a_scenario_or_a_justified_exclusion(self):
        missing = sorted(discover_inventory() - set(_declared_names()))

        assert not missing, f"Features with no scenario, exclusion or pending entry: {missing}"

    def test_no_declared_entry_is_stale(self):
        stale = sorted(set(_declared_names()) - discover_inventory())

        assert not stale, f"Declared entries that no longer exist in the code: {stale}"

    def test_a_feature_is_declared_only_once(self):
        names = _declared_names()
        duplicated = sorted({name for name in names if names.count(name) > 1})

        assert not duplicated, f"Features declared more than once: {duplicated}"

    def test_every_exclusion_states_its_reason(self):
        unexplained = sorted(name for name, reason in EXCLUDED.items() if not reason.strip())

        assert not unexplained, f"Exclusions without a reason: {unexplained}"

    def test_covered_entries_point_to_existing_tests(self):
        broken = []
        for name, reference in COVERED.items():
            path, _, class_name = reference.partition("::")
            file = _REPOSITORY / path
            if not file.is_file() or f"class {class_name}" not in file.read_text():
                broken.append(f"{name} -> {reference}")

        assert not broken, f"Covered entries pointing nowhere: {broken}"

    @pytest.mark.xfail(
        strict=True,
        reason="Pending scenarios are written by items 3 to 6 of the integration-test-matrix spec.",
    )
    def test_no_pending_scenario_is_left(self):
        assert _pending_names() == []
