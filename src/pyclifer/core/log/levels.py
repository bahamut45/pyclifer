"""Logging levels for pyclifer."""

import logging
import sys
from typing import Any, Protocol

from click_extra.logging import LogLevel

LOG_LEVELS = {level.name: level.value for level in LogLevel}

TRACE = 5
logging.addLevelName(TRACE, "TRACE")

# Extend click-extra levels with TRACE
PYCLIFER_LOG_LEVELS: dict[str, int] = {**LOG_LEVELS, "TRACE": TRACE}


class SupportsTraceLogger(Protocol):
    """Minimal contract for a logger supporting TRACE."""

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a message at the DEBUG level."""

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a message at the INFO level."""

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a message at the WARNING level."""

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a message at the ERROR level."""

    def trace(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a message at the TRACE level."""


# Since Python 3.11 logging counts stacklevel from the first frame outside the logging module,
# which is trace() itself, so trace() must add its own frame. Python 3.10 counted from the caller
# of the method that calls _log, which is already the right frame. Measured on 3.10 to 3.13.
_TRACE_STACKLEVEL_OFFSET = 1 if sys.version_info >= (3, 11) else 0


def add_trace_method(logger_class: type) -> type:
    """Add a trace method to a logger class.

    Args:
        logger_class: Logger class to extend.

    Returns:
        The updated logger class.
    """

    # noinspection PyIncorrectDocstring
    def trace(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a message at TRACE level.

        Args:
            msg: Message to log.
            *args: Additional positional arguments for formatting.
            **kwargs: Additional keyword arguments for logging.
        """
        if self.isEnabledFor(TRACE):
            kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + _TRACE_STACKLEVEL_OFFSET
            self._log(TRACE, msg, args, **kwargs)

    logger_class.trace = trace
    return logger_class


# Install trace() on the global Logger class when pyclifer is imported, so get_logger() keeps its
# SupportsTraceLogger promise before any application is declared.
add_trace_method(logging.Logger)
