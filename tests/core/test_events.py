"""Tests for the lifecycle event names."""

from pyclifer.core.events import CONFIG_LOADED, EVENTS, Event


class TestEventNames:
    """The set of lifecycle event names a group can emit."""

    def test_config_loaded_has_the_documented_name(self):
        assert CONFIG_LOADED == "config.loaded"

    def test_config_loaded_is_a_known_event(self):
        assert CONFIG_LOADED in EVENTS

    def test_events_is_immutable(self):
        assert isinstance(EVENTS, frozenset)


class TestEvent:
    """Event is a string, so code written with plain names keeps working."""

    def test_config_loaded_is_an_event_equal_to_its_name(self):
        assert isinstance(CONFIG_LOADED, Event)
        assert CONFIG_LOADED == "config.loaded"

    def test_a_plain_string_is_not_an_event(self):
        assert not isinstance("config.loaded", Event)

    def test_a_custom_event_is_not_a_framework_event(self):
        assert Event("myplugin.ready") not in EVENTS

    def test_a_plain_name_finds_the_handlers_registered_under_an_event(self):
        handlers = {Event("myplugin.ready"): ["handler"]}

        assert handlers["myplugin.ready"] == ["handler"]
