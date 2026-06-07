"""Rich handlers for pyclifer logging."""

import logging
import sys
from io import TextIOBase
from typing import Any

from click_extra.logging import ExtraStreamHandler
from rich.console import Console
from rich.logging import RichHandler

from .filters import SecretsMasker


class RichExtraStreamHandler(ExtraStreamHandler):
    """Enhanced ExtraStreamHandler with Rich support and built-in security filtering.

    Extends click-extra's ExtraStreamHandler to use Rich for beautiful logging
    while maintaining compatibility with click.echo() and color support.
    Automatically includes SecretsMasker for sensitive data protection.
    """

    def __init__(
        self,
        stream: TextIOBase | None = None,
        rich_tracebacks: bool = True,
        enable_secrets_filter: bool = True,
        sensitive_fields: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Rich Extra Stream Handler.

        Args:
            stream: Output stream (defaults to sys.stderr).
            rich_tracebacks: Enable Rich tracebacks.
            enable_secrets_filter: Enable automatic secrets filtering.
            sensitive_fields: Additional field names to mask on top of the defaults.
                              Merged into SecretsMasker.DEFAULT_FIELDS — does not replace them.
            **kwargs: Additional keyword arguments passed to RichHandler.
        """
        super().__init__(stream or sys.stderr)

        self.rich_console = Console(
            file=self.stream,
            stderr=(self.stream == sys.stderr),
        )

        self._rich_handler = RichHandler(
            console=self.rich_console,
            rich_tracebacks=rich_tracebacks,
            **kwargs,
        )

        if enable_secrets_filter:
            self.addFilter(SecretsMasker(sensitive_fields=sensitive_fields))

    def emit(self, record: logging.LogRecord) -> None:
        """Use Rich handler for enhanced output while maintaining click-extra compatibility.

        Args:
            record: LogRecord to emit.
        """
        # noinspection PyBroadException
        try:
            # Use Rich handlers emit method for better formatting
            self._rich_handler.emit(record)
        except RecursionError:
            raise
        except Exception:
            # Fallback to parent's behavior
            super().emit(record)
