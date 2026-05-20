"""Rich formatters for pyclif logging."""

import logging

from click_extra import get_default_theme, style
from click_extra.logging import ExtraFormatter
from rich.text import Text

from .levels import TRACE


class RichExtraFormatter(ExtraFormatter):
    """Enhanced ExtraFormatter with Rich text capabilities and TRACE level support.

    Extends click-extra's ExtraFormatter to support Rich markup and custom TRACE level
    while preserving a click-extra's colorization system.
    """

    def formatMessage(self, record: logging.LogRecord) -> str:
        """Enhanced formatting with Rich support and TRACE level.

        Args:
            record: LogRecord to format.

        Returns:
            Formatted message string.
        """
        # Handle TRACE level coloring
        if record.levelno == TRACE:
            # Style TRACE level with a custom color (dim blue, for example)
            record.levelname = style("TRACE", fg="blue", dim=True)
        else:
            # Let the parent handle click-extra's standard colorization
            level = record.levelname.lower()
            level_style = getattr(get_default_theme(), level, None)
            if level_style:
                record.levelname = level_style(record.levelname.upper())

        # Let parent handle the standard formatting
        message = super().formatMessage(record)

        # Add Rich enhancements if needed
        if hasattr(record, "rich") and record.rich:
            # Allow records to specify Rich formatting
            rich_text = Text.from_markup(record.getMessage())
            record.msg = rich_text.markup

        return message
