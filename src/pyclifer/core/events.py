"""Names of the lifecycle events a group can emit."""

CONFIG_LOADED = "config.loaded"
"""Emitted once the configuration file resolution is over."""

EVENTS: frozenset[str] = frozenset({CONFIG_LOADED})
"""Every valid event name; each spec that adds an event extends this set."""
