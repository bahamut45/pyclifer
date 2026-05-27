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

        TRACE records are styled directly because click-extra's theme has no
        TRACE entry; all other levels delegate to the parent's colorization system.

        Args:
            record: LogRecord to format.

        Returns:
            Formatted message string.
        """
        if record.levelno == TRACE:
            record.levelname = style("TRACE", fg="blue", dim=True)
        else:
            level = record.levelname.lower()
            level_style = getattr(get_default_theme(), level, None)
            if level_style:
                record.levelname = level_style(record.levelname.upper())

        message = super().formatMessage(record)

        if hasattr(record, "rich") and record.rich:
            rich_text = Text.from_markup(record.getMessage())
            record.msg = rich_text.markup

        return message
