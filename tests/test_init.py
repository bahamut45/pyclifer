"""Tests for the public API exposed by the pyclifer package."""

import pyclifer
from pyclifer.core.mixins.events import EventsMixin


class TestPublicApi:
    """Symbols users import with from pyclifer import ..."""

    def test_events_mixin_is_exported(self):
        assert pyclifer.EventsMixin is EventsMixin

    def test_events_mixin_is_listed_in_all(self):
        assert "EventsMixin" in pyclifer.__all__
