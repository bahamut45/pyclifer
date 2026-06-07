"""Core callback functions for pyclifer applications."""

from collections.abc import Callable
from typing import Any

import click_extra
from click_extra import ParameterSource


def get_meta_storing_callback(original_callback: Callable | None) -> Callable:
    """Create a callback that executes the original callback and stores the result in ctx.meta.

    Because ctx.meta is shared across the whole context chain, explicit values
    (COMMANDLINE, ENVIRONMENT) always overwrite the stored entry, while
    default values use setdefault so that a parent's explicit value is never
    overwritten by a child command's default.

    Args:
        original_callback: The original callback to execute first, or None.

    Returns:
        The wrapped callback function.
    """

    def _meta_storing_callback(
        ctx: click_extra.Context, param: click_extra.Parameter, value: Any
    ) -> Any:
        """Execute the original callback and store a result in ctx.meta."""
        result = value
        if original_callback is not None:
            result = original_callback(ctx, param, result)

        if param.name and result is not None:
            key = f"pyclifer.{param.name}"
            source = ctx.get_parameter_source(param.name)
            if source in (ParameterSource.COMMANDLINE, ParameterSource.ENVIRONMENT):
                ctx.meta[key] = result
            else:
                ctx.meta.setdefault(key, result)
        return result

    return _meta_storing_callback
