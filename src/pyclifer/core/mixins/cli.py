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
            panel_name: The panel label to set on the copy.

        Returns:
            A shallow copy with expose_value=False, required=False,
            context=False, and panel set to panel_name.
        """
        display = copy.copy(opt)
        display.expose_value = False
        display.required = False
        if hasattr(display, "context"):
            display.context = False
        display.panel = panel_name
        return display

    @staticmethod
    def _rebuild_help_cache(cmd: click_extra.Command) -> None:
        """Make the help of a command list the options added to it after its construction.

        click-extra commands (cloup.OptionGroupMixin) keep the arguments, option groups and
        ungrouped options in lists built once. An option appended to params later is parsed
        but never listed in the help unless those lists are rebuilt. A command without them,
        such as a plain Click command, is left alone.

        Args:
            cmd: The command whose parameters changed.
        """
        if hasattr(cmd, "_group_params") and hasattr(cmd, "ungrouped_options"):
            arguments, option_groups, ungrouped_options = cmd._group_params(cmd.params)
            cmd.arguments = arguments
            cmd.option_groups = option_groups
            cmd.ungrouped_options = ungrouped_options

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
            added = False
            for opt in global_options:
                if opt.name not in existing_param_names:
                    cmd.params.append(opt)
                    added = True
            if added:
                self._rebuild_help_cache(cmd)

        # If the command is a group, recursively apply to its currently registered subcommands
        if hasattr(cmd, "commands"):
            for subcommand in cmd.commands.values():
                self._propagate_global_options(subcommand, global_options)

    def _propagate_context_options(
        self,
        cmd: click_extra.Command,
        context_options: list[click_extra.Parameter],
        panel_name: str,
    ) -> None:
        """Recursively inject display-only copies of context options into a command tree.

        Each copy is configured so it renders in the dedicated help panel but
        never interferes with argument parsing or callback signatures.

        Args:
            cmd: Root of the command tree to receive the display copies.
            context_options: Original context options from the root group.
            panel_name: Label for the rich_help_panel on each display copy.
        """
        if hasattr(cmd, "params"):
            existing_names = {p.name for p in cmd.params}
            for opt in context_options:
                if opt.name not in existing_names:
                    cmd.params.append(self._get_context_option_display_copy(opt, panel_name))

            self._rebuild_help_cache(cmd)

        if hasattr(cmd, "commands") and cmd.commands:
            for subcommand in cmd.commands.values():
                self._propagate_context_options(subcommand, context_options, panel_name)

    # noinspection PyUnresolvedReferences
    def add_command(self, cmd: click_extra.Command, name: str | None = None, **kwargs: Any) -> None:
        """Register a subcommand and inject global and context options.

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

        # 3. Find context=True (non-global) options marked for subcommand help
        context_options = [
            param
            for param in getattr(self, "params", [])
            if getattr(param, "context", False)
            and not getattr(param, "is_global", False)
            and getattr(param, "show_in_subcommand_help", True)
        ]
        if context_options:
            panel_name = getattr(self, "_context_options_panel", CONTEXT_OPTIONS_PANEL)
            self._propagate_context_options(cmd, context_options, panel_name)

        super().add_command(cmd, name, **kwargs)  # type: ignore
