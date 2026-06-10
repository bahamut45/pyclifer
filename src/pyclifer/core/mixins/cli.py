"""CLI-related mixins for Click options and groups."""

import copy
from typing import Any

import click_extra

from pyclifer.core.callbacks import get_meta_storing_callback

CONTEXT_OPTIONS_PANEL = "Context Options (anywhere-passable)"


class StoreInMetaMixin:
    """Mixin to automatically store option values in Click's context meta."""

    def __init__(self, *args: Any, store_in_meta: bool = False, **kwargs: Any):
        """Initialize the mixin, chaining callbacks if store_in_meta is True.

        Args:
            *args: Positional arguments for the parent class.
            store_in_meta: If True, store the parsed value in ctx.meta.
            **kwargs: Keyword arguments for the parent class.
        """
        self.store_in_meta = store_in_meta
        if self.store_in_meta:
            kwargs["callback"] = get_meta_storing_callback(kwargs.get("callback"))
            kwargs.setdefault("expose_value", False)

        super().__init__(*args, **kwargs)


class GlobalOptionsMixin:
    """Mixin that propagates global options to subcommands."""

    @staticmethod
    def _get_context_option_display_copy(
        opt: click_extra.Parameter, panel_name: str
    ) -> click_extra.Parameter:
        """Create a display-only copy of a context option for subcommand help panels.

        The copy is configured so it appears in a dedicated help panel but is
        never parsed into callback kwargs and never blocks execution when absent.

        Args:
            opt: The original context option to copy.
            panel_name: The rich_help_panel label to set on the copy.

        Returns:
            A shallow copy with expose_value=False, required=False,
            context=False, and rich_help_panel set to panel_name.
        """
        display = copy.copy(opt)
        display.expose_value = False
        display.required = False
        if hasattr(display, "context"):
            display.context = False
        display.rich_help_panel = panel_name
        return display

    def _propagate_global_options(
        self, cmd: click_extra.Command, global_options: list[click_extra.Parameter]
    ) -> None:
        """Recursively propagate global options to a command and its subcommands.

        Args:
            cmd: The command to receive the options.
            global_options: The global options to inject.
        """
        if hasattr(cmd, "params"):
            existing_param_names = {param.name for param in cmd.params}
            for opt in global_options:
                if opt.name not in existing_param_names:
                    cmd.params.append(opt)

        # If the command is a group, recursively apply to its currently registered subcommands
        if hasattr(cmd, "commands"):
            for subcommand in cmd.commands.values():
                self._propagate_global_options(subcommand, global_options)

    # noinspection PyUnresolvedReferences
    def add_command(self, cmd: click_extra.Command, name: str | None = None, **kwargs: Any) -> None:
        """Register a subcommand and inject global options.

        Args:
            cmd: The command to add.
            name: The name to register the command with.
            **kwargs: Additional arguments passed to the parent method.
        """
        # 1. Find global options attached to this group
        global_options = [
            param for param in getattr(self, "params", []) if getattr(param, "is_global", False)
        ]

        # 2. Inject them recursively into the subcommand and all its descendants
        if global_options:
            self._propagate_global_options(cmd, global_options)

        super().add_command(cmd, name, **kwargs)  # type: ignore
