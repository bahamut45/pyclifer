"""Configuration utilities for pyclif logging."""

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import click
from click_extra import Choice
from click_extra.logging import VerbosityOption as BaseVerbosityOption
from click_extra.logging import extraBasicConfig

from .formatters import RichExtraFormatter
from .handlers import RichExtraStreamHandler
from .levels import PYCLIF_LOG_LEVELS, SupportsTraceLogger, add_trace_method


class PyclifVerbosityOption(BaseVerbosityOption):
    """Extended VerbosityOption with TRACE level support."""

    def set_level(self, ctx: click.Context, param: click.Parameter, value: str) -> None:
        """Set the level of all loggers configured on the option.

        Override the parent method to use PYCLIF_LOG_LEVELS instead of LOG_LEVELS
        to support our custom TRACE level.
        """
        # Skip setting the level if another option has already set it or is at an equal
        # or lower level.
        current_level = ctx.meta.get("click_extra.verbosity_level")
        if current_level:
            levels = tuple(PYCLIF_LOG_LEVELS)
            current_level_index = levels.index(current_level)
            new_level_index = levels.index(value)
            if new_level_index <= current_level_index:
                return

        ctx.meta["click_extra.verbosity_level"] = value
        ctx.meta["click_extra.verbosity"] = value

        verb_level_int = PYCLIF_LOG_LEVELS[value]

        # Check if file logging is active and requires a lower log level
        file_level_name = ctx.meta.get("pyclif.log_file_level", "DEBUG")
        file_level_int = PYCLIF_LOG_LEVELS.get(file_level_name, logging.DEBUG)
        has_file = ctx.meta.get("pyclif.log_file_path") is not None

        min_level: int = min(verb_level_int, file_level_int) if has_file else verb_level_int

        for logger in self.all_loggers:
            logger.setLevel(min_level)

        configure_rich_logging(force_reconfigure=True)

        # Restrict stream handlers so the console output respects its explicit verbosity
        root_logger = logging.getLogger()
        for h in root_logger.handlers:
            if isinstance(h, RichExtraStreamHandler):
                h.setLevel(verb_level_int)

        ctx.call_on_close(self.reset_loggers)

    # noinspection PyShadowingBuiltins
    def __init__(
        self,
        param_decls=None,
        type=Choice(PYCLIF_LOG_LEVELS, case_sensitive=False),  # noqa: B008
        help="Either TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL.",
        is_global: bool = False,
        **kwargs,
    ):
        """Initialize the Pyclif Verbosity Option.

        Args:
            param_decls: Parameter declarations.
            type: Choice type with PYCLIF_LOG_LEVELS.
            help: Help message.
            is_global: If True, this option will be propagated to subcommands.
            **kwargs: Additional keyword arguments.
        """
        if not param_decls:
            param_decls = ("--verbosity",)

        self.is_global = is_global
        kwargs.setdefault("show_default", True)
        super().__init__(param_decls=param_decls, type=type, help=help, **kwargs)


def configure_rich_logging(
    use_rich: bool = True,
    rich_tracebacks: bool = True,
    enable_secrets_filter: bool = True,
    sensitive_fields: list[str] | None = None,
    force_reconfigure: bool = False,
) -> None:
    """Configure the Rich logging system once and centrally.

    This function sets up the entire logging system in one place:
    - Global configuration via extraBasicConfig
    - Adds trace() method to all Python loggers
    - Prevents multiple configurations with built-in checks

    Args:
        use_rich: Enable Rich logging capabilities.
        rich_tracebacks: Enable Rich tracebacks for exceptions.
        enable_secrets_filter: Enable automatic secrets filtering.
        sensitive_fields: Additional field names to mask on top of the defaults.
                          Merged into SecretsMasker.DEFAULT_FIELDS — does not replace them.
        force_reconfigure: Force reconfiguration even if already configured.
    """
    # Check if Rich configuration is already active
    if not force_reconfigure:
        root_logger = logging.getLogger()
        has_rich_handler = any(
            hasattr(handler, "_rich_handler") for handler in root_logger.handlers
        )
        if has_rich_handler:
            return  # Already configured, do nothing

    if use_rich and rich_tracebacks:
        from rich.traceback import install as install_rich_traceback

        # noinspection PyArgumentEqualDefault
        install_rich_traceback(show_locals=False)

    if use_rich:
        shared_handler = RichExtraStreamHandler(
            rich_tracebacks=rich_tracebacks,
            enable_secrets_filter=enable_secrets_filter,
            sensitive_fields=sensitive_fields,
        )
        shared_handler.setFormatter(RichExtraFormatter())

        # Save existing file handlers before force configuration wipes them
        root_logger = logging.getLogger()
        file_handlers = [h for h in root_logger.handlers if isinstance(h, TimedRotatingFileHandler)]

        _preconfigure_click_extra_logger(shared_handler)

        extraBasicConfig(
            stream_handler_class=RichExtraStreamHandler,
            formatter_class=RichExtraFormatter,
            force=True,
        )

        # Replace the generic handler added by extraBasicConfig with our configured shared instance
        root_logger = logging.getLogger()
        for h in list(root_logger.handlers):
            if type(h) is RichExtraStreamHandler and h is not shared_handler:
                root_logger.removeHandler(h)

        if shared_handler not in root_logger.handlers:  # pragma: no branch
            root_logger.addHandler(shared_handler)

        # Restore file handlers
        for h in file_handlers:
            if h not in root_logger.handlers:  # pragma: no branch
                root_logger.addHandler(h)

    add_trace_method(logging.Logger)


def _preconfigure_click_extra_logger(handler: logging.Handler):
    """Preconfigure the click_extra logger with the shared Rich handler."""
    click_extra_logger = logging.getLogger("click_extra")

    if handler in click_extra_logger.handlers:
        return

    # Preserve existing file handlers
    file_handlers = [
        h for h in click_extra_logger.handlers if isinstance(h, TimedRotatingFileHandler)
    ]

    click_extra_logger.handlers.clear()
    for h in file_handlers:
        click_extra_logger.addHandler(h)

    click_extra_logger.addHandler(handler)
    click_extra_logger.propagate = False


def setup_file_logging(
    log_file: str,
    level: str = "TRACE",
    when: str = "midnight",
    interval: int = 1,
    backup_count: int = 7,
    enable_secrets_filter: bool = True,
    sensitive_fields: list[str] | None = None,
) -> None:
    """Configure a time-based rotating file handler for logging.

    Args:
        log_file: Path to the log file.
        level: Log level for the file handler.
        when: Type of interval (e.g., 'midnight', 'h', 'd').
        interval: Interval value.
        backup_count: Number of historical files to keep.
        enable_secrets_filter: Apply the secret filter to the file logs.
        sensitive_fields: Additional field names to mask on top of the defaults.
                          Merged into SecretsMasker.DEFAULT_FIELDS — does not replace them.
    """
    root_logger = logging.getLogger()
    abs_log_file = str(Path(log_file).resolve())

    level_name = level.upper() if isinstance(level, str) else "DEBUG"
    file_level_int: int = PYCLIF_LOG_LEVELS.get(level_name, logging.DEBUG)

    # Get current console verbosity to restrict stream handlers
    ctx = click.get_current_context(silent=True)

    # Check if a custom default level was set on the GroupConfig via ctx.command
    default_verbosity = "WARNING"
    if ctx and hasattr(ctx.command, "params"):
        for param in ctx.command.params:
            if param.name == "verbosity":
                default_verbosity = getattr(param, "default", "WARNING")
                break

    console_level_name = (
        ctx.meta.get("click_extra.verbosity_level", default_verbosity) if ctx else default_verbosity
    )
    console_level_int = PYCLIF_LOG_LEVELS.get(console_level_name, logging.WARNING)

    # Ensure stream handlers don't spam if we lower the root logger level
    for h in root_logger.handlers:
        if isinstance(h, RichExtraStreamHandler) and h.level == logging.NOTSET:
            h.setLevel(console_level_int)

    click_extra_logger = logging.getLogger("click_extra")

    # Lower the root logger level if necessary so messages reach the file handler
    for logger in [root_logger, click_extra_logger]:
        # noinspection PyTypeChecker
        if logger.level == logging.NOTSET or logger.level > file_level_int:
            logger.setLevel(file_level_int)

    # Prevent duplicate handlers if called multiple times, just update the level
    for h in list(root_logger.handlers):
        if (
            isinstance(h, TimedRotatingFileHandler)
            and getattr(h, "baseFilename", "") == abs_log_file
        ):
            h.setLevel(file_level_int)
            return

    handler = TimedRotatingFileHandler(
        filename=log_file,
        when=when,
        interval=interval,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(file_level_int)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    if enable_secrets_filter:
        from .filters import SecretsMasker

        handler.addFilter(SecretsMasker(sensitive_fields=sensitive_fields))

    root_logger.addHandler(handler)

    click_extra_logger = logging.getLogger("click_extra")
    if not click_extra_logger.propagate:
        click_extra_logger.addHandler(handler)


def create_log_file_callback(
    default_level: str = "TRACE",
    when: str = "midnight",
    interval: int = 1,
    backup_count: int = 7,
    enable_secrets_filter: bool = True,
    sensitive_fields: list[str] | None = None,
):
    """Create a Click callback for the log file option."""

    # noinspection PyUnusedLocal
    def callback(ctx, param, value):
        """Callback function for the log file option."""
        if value:
            ctx.meta["pyclif.log_file_path"] = value
            ctx.meta["pyclif.log_file_level"] = default_level
            setup_file_logging(
                log_file=value,
                level=default_level,
                when=when,
                interval=interval,
                backup_count=backup_count,
                enable_secrets_filter=enable_secrets_filter,
                sensitive_fields=sensitive_fields,
            )
        return value

    return callback


def get_configured_logger(name: str = None) -> SupportsTraceLogger:
    """Get a logger that automatically benefits from global Rich configuration.

    This function simply retrieves a standard logger that automatically
    inherits the global Rich configuration.

    Args:
        name: Logger name (optional).

    Returns:
        Logger automatically configured with Rich capabilities.
    """
    from pyclif import __app_name__

    return logging.getLogger(name or __app_name__)  # type: ignore[return-value]
