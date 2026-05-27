"""Context class"""

import sys

import click_extra
from rich.console import Console

from pyclif.core.mixins import OutputFormatMixin, RichHelpersMixin


class ContextException(Exception):
    """Base exception for context-specific errors in the application."""


class BaseContext(RichHelpersMixin, OutputFormatMixin):
    """BaseContext class initializes state and combines output and rich helpers for CLI commands."""

    def __init__(self) -> None:
        """Initialize the context with a console and detect TTY mode."""
        self.console = Console()
        self.is_atty = sys.stdout.isatty()
        self.output_format = None

    @property
    def click(self) -> click_extra.Context:
        """Return the current Click context.

        Provides access to the full Click context (meta, params, info_name, etc.)
        from any BaseContext subclass without importing Click in command files.

        Returns:
            The active Click context for the running command.
        """
        return click_extra.get_current_context()
