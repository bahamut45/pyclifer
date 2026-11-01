"""Discovery of the pyclifer features that integration tests must exercise."""

import dataclasses
import inspect
import re

import pyclifer
from pyclifer.core import decorators
from pyclifer.core.classes import GroupConfig
from pyclifer.core.events import EVENTS

_OPTION_FACTORY_NAME = re.compile(r"option(s)?$")


def discover_inventory() -> set[str]:
    """Read every feature to exercise from the code, never from a hand-written list.

    Names are prefixed by their kind: GroupConfig.<field>, option_factory.<function>,
    public.<symbol> and event.<name>. Dunder symbols of pyclifer.__all__ are metadata,
    not features, and are left out.

    Returns:
        The set of feature names.
    """
    fields = {f"GroupConfig.{field.name}" for field in dataclasses.fields(GroupConfig)}
    factories = {
        f"option_factory.{name}"
        for name, obj in vars(decorators).items()
        if inspect.isfunction(obj)
        and obj.__module__ == decorators.__name__
        and not name.startswith("_")
        and _OPTION_FACTORY_NAME.search(name)
    }
    public = {f"public.{name}" for name in pyclifer.__all__ if not name.startswith("__")}
    events = {f"event.{name}" for name in EVENTS}
    return fields | factories | public | events
