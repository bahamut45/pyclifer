"""Plain Click help for the rich-click commands of an application that asked for it.

group() and command() build rich-click commands, because they are written before they are
attached to an application and cannot know whether it wants Rich help. `use_rich_help=False` is
a choice of the application, so the commands it receives are switched to Click's help when they
are attached to it.
"""

import functools
from typing import Any

import click  # the plain Click implementations, which click_extra's own commands replace
import click_extra
from rich_click import RichCommand

_PLAIN_HELP = "_pyclifer_plain_help"
"""Marks a class that prints plain Click help."""


class PlainCommandHelpMixin:
    """Overrides that make a rich-click command print the help Click prints.

    rich-click draws its help through a Rich formatter that its own methods expect, so every
    method that writes the help is given back its Click implementation, with Click's context.
    """

    context_class = click_extra.Context
    format_help = click.Command.format_help
    format_help_text = click.Command.format_help_text
    format_options = click.Command.format_options
    format_epilog = click.Command.format_epilog
    get_help_option = click.Command.get_help_option


class PlainGroupHelpMixin(PlainCommandHelpMixin):
    """The same for a group, which also lists its commands."""

    format_options = click.Group.format_options
    format_commands = click.Group.format_commands


def has_plain_help(cmd: click.Command) -> bool:
    """Tell whether a command prints plain Click help.

    Args:
        cmd: The command to look at.

    Returns:
        False for a rich-click command that has not been switched, True for anything else.
    """
    return not isinstance(cmd, RichCommand) or getattr(type(cmd), _PLAIN_HELP, False)


@functools.cache
def _plain_twin(command_class: type) -> type:
    """The subclass of a rich-click class that prints plain help, built once per class."""
    mixin = PlainGroupHelpMixin if issubclass(command_class, click.Group) else PlainCommandHelpMixin
    return type(
        f"Plain{command_class.__name__}",
        (mixin, command_class),
        {
            "__module__": command_class.__module__,
            "__qualname__": f"Plain{command_class.__qualname__}",
            _PLAIN_HELP: True,
        },
    )


def make_help_plain(cmd: click.Command) -> None:
    """Switch a rich-click command, and every command it holds, to Click's help.

    The class of the command is replaced by a subclass of itself, which adds no attribute to the
    instance, so its options, callback, handlers and commands are all kept. A command that does
    not use rich-click is left as it is, but the commands it holds are still visited.

    Args:
        cmd: The command to switch.
    """
    if not has_plain_help(cmd):
        cmd.__class__ = _plain_twin(type(cmd))
        # The plain context does not know this setting, which rich-click's decorators add.
        cmd.context_settings = {
            key: value for key, value in cmd.context_settings.items() if key != "rich_help_config"
        }
    children: dict[str, Any] = getattr(cmd, "commands", {})
    for child in children.values():
        make_help_plain(child)
