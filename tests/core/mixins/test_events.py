"""Tests for the EventsMixin."""

from unittest.mock import MagicMock

import click_extra
import pytest

from pyclifer.core.events import CONFIG_LOADED
from pyclifer.core.mixins.events import EventsMixin


class _Group(EventsMixin, click_extra.Group):
    """Minimal group under test."""


class TestEventsMixin:
    """EventsMixin lets a group attach handlers to named lifecycle events."""

    def test_emit_calls_a_handler_registered_directly_with_the_context(self):
        group = _Group(name="cli")
        ctx = click_extra.Context(group)
        handler = MagicMock()

        group.on(CONFIG_LOADED, handler)
        group.emit(CONFIG_LOADED, ctx)

        handler.assert_called_with(ctx)

    def test_on_without_handler_works_as_a_decorator_and_returns_the_function(self):
        group = _Group(name="cli")
        ctx = click_extra.Context(group)
        seen = []

        @group.on(CONFIG_LOADED)
        def handler(received_ctx):
            seen.append(received_ctx)

        group.emit(CONFIG_LOADED, ctx)

        assert seen == [ctx]
        assert handler.__name__ == "handler"

    def test_emit_runs_handlers_in_registration_order_and_returns_their_results(self):
        group = _Group(name="cli")
        ctx = click_extra.Context(group)
        group.on(CONFIG_LOADED, lambda _ctx: "first")
        group.on(CONFIG_LOADED, lambda _ctx: "second")

        assert group.emit(CONFIG_LOADED, ctx) == ["first", "second"]

    def test_emit_without_registered_handler_returns_an_empty_list(self):
        group = _Group(name="cli")
        ctx = click_extra.Context(group)

        assert group.emit(CONFIG_LOADED, ctx) == []

    def test_on_rejects_an_unknown_event_and_lists_the_valid_names(self):
        group = _Group(name="cli")

        with pytest.raises(ValueError, match=r"Unknown event 'typo'.*config\.loaded"):
            group.on("typo", lambda _ctx: None)

    def test_on_used_as_a_decorator_also_rejects_an_unknown_event(self):
        group = _Group(name="cli")

        with pytest.raises(ValueError, match="Unknown event 'typo'"):
            group.on("typo")

    def test_a_handler_exception_propagates_out_of_emit(self):
        group = _Group(name="cli")
        ctx = click_extra.Context(group)

        def failing(_ctx):
            raise RuntimeError("handler failed")

        group.on(CONFIG_LOADED, failing)

        with pytest.raises(RuntimeError, match="handler failed"):
            group.emit(CONFIG_LOADED, ctx)

    def test_handlers_are_not_shared_between_groups(self):
        first = _Group(name="first")
        second = _Group(name="second")
        first.on(CONFIG_LOADED, lambda _ctx: "only-first")

        assert second.emit(CONFIG_LOADED, click_extra.Context(second)) == []
