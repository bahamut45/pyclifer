"""Names of the lifecycle events a group can emit."""


class Event(str):
    """A named lifecycle event.

    An Event is a string, so it compares equal to its name and works as a dict key.
    The framework defines its own events; plugins and applications create theirs with
    Event("myplugin.ready") and share the object, which needs no prior registration.
    """


CONFIG_LOADED = Event("config.loaded")
"""Emitted once the configuration file resolution is over."""

EVENTS: frozenset[str] = frozenset({CONFIG_LOADED})
"""Every framework event name; each spec that adds an event extends this set."""

PENDING_ERROR_META = "pyclifer.events.pending_error"
"""ctx.meta key holding a ClickException raised by a handler, until it is reported.

click-extra swallows that exception on a bare call (no arguments), so it is kept
here and reported by the group when the help screen follows."""
