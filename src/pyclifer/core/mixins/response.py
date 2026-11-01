"""Response-handling mixin for Click groups."""

import logging
from collections.abc import Callable
from typing import Any

import click_extra

from ..events import PENDING_ERROR_META

_log = logging.getLogger(__name__)

_STRUCTURED_FORMATS = ("json", "yaml")
"""Output formats in which a Click error is answered with a Response."""

_PYCLIFER_RESPONSE_DECIDED = "_pyclif_response_decided"
"""Attribute set on a command callback before Click registers it, to signal
that response handling has already been decided (either applied or explicitly
opted out) via the @group.command() factory path.  add_command() checks this
flag to avoid double-wrapping or overriding an explicit handle_response=False.

The flag must be set on the raw function *before* calling decorator(f) because
Click's Group.command() calls self.add_command() internally during that call,
so any flag set afterwards would arrive too late."""


def _apply_handle_response_to_group(group) -> None:
    """Recursively propagate handle_response to an existing group and its commands.

    Sets handle_response_by_default on the group (so future registrations are
    covered) and wraps every already-registered leaf command callback that has
    not yet been decided.  Recurses into nested groups.

    Args:
        group: A Click Group instance to propagate handle_response into.
    """
    from pyclifer.core.decorators import returns_response

    # A group that opted out explicitly keeps its whole sub-tree out of the propagation.
    if getattr(group, "handle_response_opted_out", False) is True:
        return

    # Enable for future registrations if the group supports the mixin.
    if isinstance(group, HandleResponseMixin):
        group.handle_response_by_default = True

    commands = getattr(group, "commands", None) or {}
    for cmd in commands.values():
        # Recurse into nested groups first.
        if getattr(cmd, "commands", None) is not None:
            _apply_handle_response_to_group(cmd)
            continue

        if cmd.callback is None:
            continue
        if getattr(cmd.callback, _PYCLIFER_RESPONSE_DECIDED, False):
            _log.debug(
                "_apply_handle_response_to_group: '%s' already decided — skipping",
                cmd.name,
            )
            continue

        _log.debug(
            "_apply_handle_response_to_group: wrapping '%s' with returns_response",
            cmd.name,
        )
        cmd.callback = returns_response(cmd.callback)


class HandleResponseMixin:
    """Mixin that adds automatic Response dispatch to Click groups.

    When handle_response_by_default is True (set via
    @app_group(handle_response=True)), every command registered through
    @group.command() or group.add_command() automatically wraps its return
    value: if the function returns a Response, it is printed using the output
    format stored in ctx.meta['pyclifer.output_format'].

    The per-command handle_response kwarg always takes precedence over the
    group-level default.
    """

    handle_response_by_default: bool = False
    handle_response_opted_out: bool = False
    output_format_default: str = "table"

    def parse_args(self, ctx: click_extra.Context, args: list[str]) -> list[str]:
        """Parse the arguments, answering a Click error in a structured format.

        Args:
            ctx: The context of this group.
            args: The arguments to parse.

        Returns:
            The remaining arguments, as returned by Click.
        """
        try:
            # noinspection PyUnresolvedReferences
            return super().parse_args(ctx, args)
        except click_extra.ClickException as error:
            # On a bare call click-extra swallows an error raised by an event handler,
            # then Click shows the help. Report the handler error rather than lose it.
            pending = ctx.meta.pop(PENDING_ERROR_META, None)
            if pending is None or pending is error:
                self._answer_click_exception(ctx, error)
                raise
            self._answer_click_exception(ctx, pending)
            pending.show()
            raise

    def invoke(self, ctx: click_extra.Context) -> Any:
        """Invoke the group, answering a Click error in a structured format.

        Args:
            ctx: The context of this group.

        Returns:
            The value returned by the invoked command.
        """
        try:
            # noinspection PyUnresolvedReferences
            return super().invoke(ctx)
        except click_extra.ClickException as error:
            self._answer_click_exception(ctx, error)
            raise

    def _answer_click_exception(
        self, ctx: click_extra.Context, error: click_extra.ClickException
    ) -> None:
        """Answer a Click error with a Response and exit, or return to leave it to Click.

        Only acts when response handling is enabled and the output format is
        structured (json or yaml). The usual message stays on stderr for a person
        at a terminal; the Response goes to stdout for a program.

        Args:
            ctx: The context in which the error was raised.
            error: The Click error (usage error or any other ClickException).
        """
        if not self.handle_response_by_default:
            return
        root = ctx.find_root()
        default_format = getattr(root.command, "output_format_default", self.output_format_default)
        output_format = root.meta.get("pyclifer.output_format", default_format)
        if output_format not in _STRUCTURED_FORMATS:
            return

        # Lazy imports to break circular dependencies: these modules import the mixins.
        from pyclifer.core.context import BaseContext
        from pyclifer.core.output import Response

        error_type = "usage_error" if isinstance(error, click_extra.UsageError) else "click_error"
        # A UsageError carries the context of the command that failed, which is more
        # precise than the context of the group that caught it.
        failing_ctx = getattr(error, "ctx", None) or ctx
        response = Response(
            success=False,
            message=error.format_message(),
            error_code=error.exit_code,
            data={"results": [], "error_type": error_type, "command": failing_ctx.command_path},
        )
        error.show()
        output_ctx = ctx.obj if isinstance(ctx.obj, BaseContext) else BaseContext()
        output_ctx.output_format = output_format
        output_ctx.print_result_based_on_format(response)
        ctx.exit(error.exit_code)

    def command(
        self, *args: Any, handle_response: bool | None = None, **kwargs: Any
    ) -> Callable[..., Any]:
        """Override Click.Group.command to automatically handle Response objects."""
        explicit = handle_response is not None or self.handle_response_opted_out
        if handle_response is None:
            handle_response = self.handle_response_by_default
        # noinspection PyUnresolvedReferences
        decorator = super().command(*args, **kwargs)
        if not handle_response and not explicit:
            # No choice was made: leave the command undecided, so that a parent group
            # that handles responses can still wrap it when this group is attached.
            return decorator
        if not handle_response:
            # Mark the raw function as decided *before* calling decorator(f)
            # so that our add_command() override sees the flag when Click
            # calls self.add_command() internally during decorator(f).
            def wrapped_noop(f):
                """Pass-through decorator that marks the command as opted out."""
                setattr(f, _PYCLIFER_RESPONSE_DECIDED, True)
                return decorator(f)

            return wrapped_noop

        def wrapped(f):
            """Wrapper for commands that automatically handles Response objects."""
            from pyclifer.core.decorators import returns_response

            wrapped_f = returns_response(f)
            setattr(wrapped_f, _PYCLIFER_RESPONSE_DECIDED, True)
            return decorator(wrapped_f)

        return wrapped

    def add_command(self, cmd: Any, name: str | None = None, **kwargs: Any) -> None:
        """Override Click.Group.add_command to propagate response handling.

        Extra keyword arguments, such as a cloup section, are passed on to the
        next class in the chain.

        When handle_response_by_default is True:
        - Sub-groups: handle_response_by_default is propagated recursively so
          that all already-registered leaf commands are wrapped and future
          registrations on those groups are also covered.
        - Leaf commands: the callback is wrapped with returns_response directly.

        Commands whose callback carries the _PYCLIFER_RESPONSE_DECIDED flag
        (set by the @group.command() factory path before Click registers the
        command) are left untouched so that explicit handle_response=False
        overrides and already-wrapped functions are both respected.
        """
        if self.handle_response_by_default:
            is_group = getattr(cmd, "commands", None) is not None
            if is_group:
                _log.debug(
                    "HandleResponseMixin.add_command: propagating handle_response "
                    "into sub-group '%s'",
                    cmd.name,
                )
                _apply_handle_response_to_group(cmd)
            else:
                already_decided = cmd.callback is not None and getattr(
                    cmd.callback, _PYCLIFER_RESPONSE_DECIDED, False
                )
                if cmd.callback is not None and not already_decided:
                    from pyclifer.core.decorators import returns_response

                    _log.debug(
                        "HandleResponseMixin.add_command: wrapping '%s' with returns_response",
                        cmd.name,
                    )
                    cmd.callback = returns_response(cmd.callback)
                else:
                    _log.debug(
                        "HandleResponseMixin.add_command: skipping leaf '%s' (already_decided=%s)",
                        cmd.name,
                        already_decided,
                    )
        else:
            _log.debug(
                "HandleResponseMixin.add_command: handle_response_by_default=False, skipping '%s'",
                cmd.name,
            )
        # noinspection PyUnresolvedReferences
        super().add_command(cmd, name=name, **kwargs)
