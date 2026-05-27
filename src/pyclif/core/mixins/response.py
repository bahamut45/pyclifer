"""Response-handling mixin for Click groups."""

import logging
from collections.abc import Callable
from typing import Any

_log = logging.getLogger(__name__)

_PYCLIF_RESPONSE_DECIDED = "_pyclif_response_decided"
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
    from pyclif.core.decorators import returns_response

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
        if getattr(cmd.callback, _PYCLIF_RESPONSE_DECIDED, False):
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
    format stored in ctx.meta['pyclif.output_format'].

    The per-command handle_response kwarg always takes precedence over the
    group-level default.
    """

    handle_response_by_default: bool = False

    def command(
        self, *args: Any, handle_response: bool | None = None, **kwargs: Any
    ) -> Callable[..., Any]:
        """Override Click.Group.command to automatically handle Response objects."""
        if handle_response is None:
            handle_response = self.handle_response_by_default
        # noinspection PyUnresolvedReferences
        decorator = super().command(*args, **kwargs)
        if not handle_response:
            # Mark the raw function as decided *before* calling decorator(f)
            # so that our add_command() override sees the flag when Click
            # calls self.add_command() internally during decorator(f).
            def wrapped_noop(f):
                """Pass-through decorator that marks the command as opted out."""
                setattr(f, _PYCLIF_RESPONSE_DECIDED, True)
                return decorator(f)

            return wrapped_noop

        def wrapped(f):
            """Wrapper for commands that automatically handles Response objects."""
            from pyclif.core.decorators import returns_response

            wrapped_f = returns_response(f)
            setattr(wrapped_f, _PYCLIF_RESPONSE_DECIDED, True)
            return decorator(wrapped_f)

        return wrapped

    def add_command(self, cmd: Any, name: str | None = None) -> None:
        """Override Click.Group.add_command to propagate response handling.

        When handle_response_by_default is True:
        - Sub-groups: handle_response_by_default is propagated recursively so
          that all already-registered leaf commands are wrapped and future
          registrations on those groups are also covered.
        - Leaf commands: the callback is wrapped with returns_response directly.

        Commands whose callback carries the _PYCLIF_RESPONSE_DECIDED flag
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
                    cmd.callback, _PYCLIF_RESPONSE_DECIDED, False
                )
                if cmd.callback is not None and not already_decided:
                    from pyclif.core.decorators import returns_response

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
        super().add_command(cmd, name=name)
