"""Lifecycle events mixin for Click groups."""

from collections.abc import Callable
from typing import Any

import click_extra

from pyclifer.core.events import EVENTS, Event

EventHandler = Callable[[click_extra.Context], Any]
"""A function called with the Click context when its event is emitted."""


class EventsMixin:
    """Mixin that lets a group attach handlers to named lifecycle events.

    Handlers run in registration order. An exception raised by a handler
    propagates to the caller of emit(); nothing is swallowed.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the handler registry then chain to the next class.

        Args:
            *args: Positional arguments for the parent class.
            **kwargs: Keyword arguments for the parent class.
        """
        self._event_handlers: dict[str, list[EventHandler]] = {}
        super().__init__(*args, **kwargs)

    @staticmethod
    def _check_event(event: str) -> None:
        """Accept an Event object or a framework event name, reject any other string."""
        if not isinstance(event, Event) and event not in EVENTS:
            valid = ", ".join(sorted(EVENTS))
            raise ValueError(
                f"Unknown event '{event}'. Valid events: {valid}. "
                f"To define your own, use Event('{event}')."
            )

    def on(self, event: str, handler: EventHandler | None = None) -> Any:
        """Attach a handler to an event, or return a decorator when handler is omitted.

        Args:
            event: An Event object, or the plain name of a framework event.
            handler: The function to call when the event is emitted.

        Returns:
            The handler when given, otherwise a decorator that registers the
            decorated function and returns it unchanged.

        Raises:
            ValueError: When event is a plain string that is not a framework event.
        """
        self._check_event(event)

        def register(function: EventHandler) -> EventHandler:
            """Add the function to the handlers of the event."""
            self._event_handlers.setdefault(event, []).append(function)
            return function

        if handler is None:
            return register
        return register(handler)

    def emit(self, event: str, ctx: click_extra.Context) -> list[Any]:
        """Call every handler attached to an event, in registration order.

        Args:
            event: An Event object, or the plain name of a framework event.
            ctx: The Click context passed to each handler.

        Returns:
            The values returned by the handlers, in the order they ran.

        Raises:
            ValueError: When event is a plain string that is not a framework event.
        """
        self._check_event(event)
        return [handler(ctx) for handler in self._event_handlers.get(event, [])]
