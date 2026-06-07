"""Logging module for pyclifer with Rich integration and click-extra compatibility."""

from .config import PycliferVerbosityOption, configure_rich_logging, get_configured_logger
from .filters import SecretsMasker
from .formatters import RichExtraFormatter
from .handlers import RichExtraStreamHandler

# Rich-enhanced logging components integrated with click-extra
from .levels import PYCLIFER_LOG_LEVELS, TRACE, SupportsTraceLogger, add_trace_method

# Export the main parts
__all__ = [
    "TRACE",
    "PYCLIFER_LOG_LEVELS",
    "add_trace_method",
    "RichExtraStreamHandler",
    "RichExtraFormatter",
    "configure_rich_logging",
    "get_configured_logger",
    "PycliferVerbosityOption",
    "SecretsMasker",
    "get_logger",
    "logger",
]


def get_logger(name: str = None) -> SupportsTraceLogger:
    """Factory function for creating loggers with Rich capabilities.

    This function uses the global configuration system to provide
    loggers that automatically benefit from Rich enhancements.

    Args:
        name: Logger name (optional).

    Returns:
        Logger configured with Rich capabilities.
    """
    from .config import get_configured_logger

    return get_configured_logger(name)


logger: SupportsTraceLogger = get_logger()
