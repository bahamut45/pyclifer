"""Tests for the lifecycle event names."""

from pyclifer.core.events import CONFIG_LOADED, EVENTS


class TestEventNames:
    """The set of lifecycle event names a group can emit."""

    def test_config_loaded_has_the_documented_name(self):
        assert CONFIG_LOADED == "config.loaded"

    def test_config_loaded_is_a_known_event(self):
        assert CONFIG_LOADED in EVENTS

    def test_events_is_immutable(self):
        assert isinstance(EVENTS, frozenset)
