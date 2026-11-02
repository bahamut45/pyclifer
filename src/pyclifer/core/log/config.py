"""Configuration utilities for pyclifer logging."""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from click_extra import Choice, Context, Parameter, ParameterSource, get_current_context
from click_extra.logging import VerbosityOption as BaseVerbosityOption
from click_extra.logging import basicConfig

from .filters import SecretsMasker
from .formatters import RichExtraFormatter
from .handlers import RichExtraStreamHandler
from .levels import PYCLIFER_LOG_LEVELS, SupportsTraceLogger


class PycliferVerbosityOption(BaseVerbosityOption):
    """Extended VerbosityOption with TRACE level support."""

    def set_level(self, ctx: Context, param: Parameter, value: str) -> None:
        """Set the level of all loggers configured on the option.

        Override the parent method to use PYCLIFER_LOG_LEVELS instead of LOG_LEVELS
        to support our custom TRACE level.
        """
        # A value nobody typed (the default every copy of a global option carries) is not a
        # choice: it never overrides a level already set, and a level the user did choose
        # replaces one that only came from a default.
        from_default = ctx.get_parameter_source(param.name) is ParameterSource.DEFAULT
        current_level = ctx.meta.get("click_extra.verbosity_level")
        if current_level:
            if from_default:
                return
            # Between two chosen levels, skip the new one if it is not more verbose.
            if not ctx.meta.get("pyclifer.verbosity_from_default", False):
                levels = tuple(PYCLIFER_LOG_LEVELS)
                if levels.index(value) <= levels.index(current_level):
                    return

        ctx.meta["pyclifer.verbosity_from_default"] = from_default
        ctx.meta["click_extra.verbosity_level"] = value
        ctx.meta["click_extra.verbosity"] = value

        verb_level_int = PYCLIFER_LOG_LEVELS[value]

        # Check if file logging is active and requires a lower log level
        file_level_name = ctx.meta.get("pyclifer.log_file_level", "DEBUG")
        file_level_int = PYCLIFER_LOG_LEVELS.get(file_level_name, logging.DEBUG)
        has_file = ctx.meta.get("pyclifer.log_file_path") is not None

        min_level: int = min(verb_level_int, file_level_int) if has_file else verb_level_int

        for logger in self.all_loggers:
            logger.setLevel(min_level)

        # Rebuild the console handler with the application's own settings: calling this with
        # no arguments would put back the defaults chosen at declaration time.
        configure_rich_logging(
            use_rich=self.use_rich,
            enable_secrets_filter=self.enable_secrets_filter,
            sensitive_fields=self.sensitive_fields,
            mask_free_text=self.mask_free_text,
            force_reconfigure=True,
            replace_root_handlers=self.replace_root_handlers,
        )

        # Restrict stream handlers so the console output respects its explicit verbosity
        root_logger = logging.getLogger()
        for h in root_logger.handlers:
            if _is_console_handler(h):
                h.setLevel(verb_level_int)

        ctx.call_on_close(self.reset_loggers)

    # noinspection PyShadowingBuiltins
    def __init__(
        self,
        param_decls=None,
        type=Choice(PYCLIFER_LOG_LEVELS, case_sensitive=False),  # noqa: B008
        help="Either TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL.",
        is_global: bool = False,
        use_rich: bool = True,
        enable_secrets_filter: bool = True,
        sensitive_fields: list[str] | None = None,
        mask_free_text: bool = False,
        replace_root_handlers: bool = False,
        **kwargs,
    ):
        """Initialize the Pyclif Verbosity Option.

        Args:
            param_decls: Parameter declarations.
            type: Choice type with PYCLIFER_LOG_LEVELS.
            help: Help message.
            is_global: If True, this option will be propagated to subcommands.
            use_rich: Rebuild a Rich console handler, or a plain one when False.
            enable_secrets_filter: Mask secrets in the console handler it rebuilds.
            sensitive_fields: Field names to mask on top of the defaults.
            mask_free_text: Also mask key=value pairs written inside the text of a message.
            replace_root_handlers: Also remove the root handlers that pyclifer did not create.
            **kwargs: Additional keyword arguments.
        """
        if not param_decls:
            param_decls = ("--verbosity",)

        self.is_global = is_global
        self.use_rich = use_rich
        self.enable_secrets_filter = enable_secrets_filter
        self.sensitive_fields = sensitive_fields
        self.mask_free_text = mask_free_text
        self.replace_root_handlers = replace_root_handlers
        kwargs.setdefault("show_default", True)
        super().__init__(param_decls=param_decls, type=type, help=help, **kwargs)


def configure_rich_logging(
    use_rich: bool = True,
    rich_tracebacks: bool = True,
    enable_secrets_filter: bool = True,
    sensitive_fields: list[str] | None = None,
    mask_free_text: bool = False,
    force_reconfigure: bool = False,
    replace_root_handlers: bool = False,
) -> None:
    """Configure the Rich logging system once and centrally.

    This function sets up the entire logging system in one place:
    - Global configuration via basicConfig
    - Adds trace() method to all Python loggers
    - Prevents multiple configurations with built-in checks

    Args:
        use_rich: Enable Rich logging capabilities.
        rich_tracebacks: Enable Rich tracebacks for exceptions.
        enable_secrets_filter: Enable automatic secrets filtering.
        sensitive_fields: Additional field names to mask on top of the defaults.
                          Merged into SecretsMasker.DEFAULT_FIELDS — does not replace them.
        mask_free_text: Also mask key=value pairs written inside the text of a message.
        force_reconfigure: Force reconfiguration even if already configured.
        replace_root_handlers: Also remove the handlers of the root logger that pyclifer did not
            create (Sentry, syslog, pytest's caplog). By default only the console handler of
            pyclifer is replaced and those are kept.
    """
    # Check if the console is already configured, with Rich or without
    if not force_reconfigure:
        root_logger = logging.getLogger()
        if any(_is_console_handler(handler) for handler in root_logger.handlers):
            return  # Already configured, do nothing

    if use_rich and rich_tracebacks:
        # Deferred import: keeps rich.traceback (about 10 ms) off the startup path of every CLI.
        from rich.traceback import install as install_rich_traceback

        # noinspection PyArgumentEqualDefault
        install_rich_traceback(show_locals=False)

    if use_rich:
        shared_handler = RichExtraStreamHandler(
            rich_tracebacks=rich_tracebacks,
            enable_secrets_filter=enable_secrets_filter,
            sensitive_fields=sensitive_fields,
            mask_free_text=mask_free_text,
        )
        shared_handler.setFormatter(RichExtraFormatter())

        # Save the handlers to keep before force configuration wipes them
        root_logger = logging.getLogger()
        kept_handlers = _handlers_to_keep(replace_root_handlers)

        _preconfigure_click_extra_logger(shared_handler)

        basicConfig(
            stream_handler_class=RichExtraStreamHandler,
            formatter_class=RichExtraFormatter,
            force=True,
        )

        # Replace the generic handler added by basicConfig with our configured shared instance
        root_logger = logging.getLogger()
        for h in list(root_logger.handlers):
            if type(h) is RichExtraStreamHandler and h is not shared_handler:
                root_logger.removeHandler(h)

        if shared_handler not in root_logger.handlers:  # pragma: no branch
            root_logger.addHandler(shared_handler)

        # Restore the saved handlers
        for h in kept_handlers:
            if h not in root_logger.handlers:  # pragma: no branch
                root_logger.addHandler(h)

    else:
        _configure_plain_logging(
            enable_secrets_filter, sensitive_fields, mask_free_text, replace_root_handlers
        )


def _is_console_handler(handler: logging.Handler) -> bool:
    """Tell whether a handler is the console handler pyclifer installed, Rich or plain."""
    return hasattr(handler, "_rich_handler") or getattr(handler, "_pyclifer_console", False)


def _handlers_to_keep(replace_root_handlers: bool) -> list[logging.Handler]:
    """List the handlers of the root logger that survive a reconfiguration of the console.

    File handlers always survive. The console handlers never do, since they are the ones being
    replaced: the one pyclifer installed, the one click-extra lends to the root logger for the
    length of a run, and the plain StreamHandler on stderr that logging.basicConfig() installs,
    which would write every record a second time and without the secrets filter. Any other
    handler survives unless replace_root_handlers is set. The last one is recognised by its exact
    type, not with isinstance, because pytest's caplog handler is a StreamHandler subclass too.

    Args:
        replace_root_handlers: If True, only the file handlers survive.

    Returns:
        The handlers to put back on the root logger once the console is configured.
    """
    return [
        h
        for h in logging.getLogger().handlers
        if isinstance(h, TimedRotatingFileHandler)
        or (
            not replace_root_handlers
            and not _is_console_handler(h)
            and type(h).__module__ != "click_extra.logging"
            and not _is_basic_config_console(h)
        )
    ]


def _is_basic_config_console(handler: logging.Handler) -> bool:
    """Tell whether a handler is the console one logging.basicConfig() installs by default.

    It is a plain StreamHandler on stderr with the standard Formatter, the basic format, no date
    format and no filter. A StreamHandler a user wrote by hand differs on at least the formatter,
    which basicConfig always sets, so it is kept.
    """
    formatter = handler.formatter
    return (
        type(handler) is logging.StreamHandler
        and handler.stream in (sys.stderr, sys.__stderr__)
        and type(formatter) is logging.Formatter
        and formatter._fmt == logging.BASIC_FORMAT
        and formatter.datefmt is None
        and not handler.filters
    )


def _configure_plain_logging(
    enable_secrets_filter: bool,
    sensitive_fields: list[str] | None,
    mask_free_text: bool,
    replace_root_handlers: bool,
) -> None:
    """Install click-extra's standard console handler, with the same secrets filter as Rich.

    Args:
        enable_secrets_filter: Add the SecretsMasker filter to the console handler.
        sensitive_fields: Field names to mask on top of the defaults.
        mask_free_text: Also mask key=value pairs written inside the text of a message.
        replace_root_handlers: Also remove the handlers that pyclifer did not create.
    """
    root_logger = logging.getLogger()
    existing = list(root_logger.handlers)
    # basicConfig(force=True) removes every handler: keep the ones that must survive.
    kept_handlers = _handlers_to_keep(replace_root_handlers)

    basicConfig(force=True)

    # Only the handler basicConfig just created is the console one. Never touch another.
    for handler in root_logger.handlers:
        if handler in existing:
            continue
        handler._pyclifer_console = True  # type: ignore[attr-defined]
        if enable_secrets_filter:
            handler.addFilter(
                SecretsMasker(sensitive_fields=sensitive_fields, mask_free_text=mask_free_text)
            )

    for handler in kept_handlers:
        if handler not in root_logger.handlers:  # pragma: no branch
            root_logger.addHandler(handler)


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
    mask_free_text: bool = False,
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
        mask_free_text: Also mask key=value pairs written inside the text of a message.
    """
    root_logger = logging.getLogger()
    abs_log_file = str(Path(log_file).resolve())

    level_name = level.upper()
    file_level_int: int = PYCLIFER_LOG_LEVELS.get(level_name, logging.DEBUG)

    # Get current console verbosity to restrict stream handlers
    ctx = get_current_context(silent=True)

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
    console_level_int = PYCLIFER_LOG_LEVELS.get(console_level_name, logging.WARNING)

    # Ensure stream handlers don't spam if we lower the root logger level
    for h in root_logger.handlers:
        if isinstance(h, RichExtraStreamHandler) and h.level == logging.NOTSET:
            h.setLevel(
                console_level_int
            )  # pragma: no cover — requires a pre-existing handler at NOTSET

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
        handler.addFilter(
            SecretsMasker(sensitive_fields=sensitive_fields, mask_free_text=mask_free_text)
        )

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
    mask_free_text: bool = False,
):
    """Create a Click callback for the log file option."""

    # noinspection PyUnusedLocal
    def callback(ctx: Context, _param: Parameter, value: Any) -> Any:
        """Callback function for the log file option."""
        if value:
            ctx.meta["pyclifer.log_file_path"] = value
            ctx.meta["pyclifer.log_file_level"] = default_level
            setup_file_logging(
                log_file=value,
                level=default_level,
                when=when,
                interval=interval,
                backup_count=backup_count,
                enable_secrets_filter=enable_secrets_filter,
                sensitive_fields=sensitive_fields,
                mask_free_text=mask_free_text,
            )
        return value

    return callback


def get_configured_logger(name: str | None = None) -> SupportsTraceLogger:
    """Get a logger that automatically benefits from global Rich configuration.

    This function simply retrieves a standard logger that automatically
    inherits the global Rich configuration.

    Args:
        name: Logger name (optional).

    Returns:
        Logger automatically configured with Rich capabilities.
    """
    # Lazy: pyclifer/__init__.py imports this module. The name is read when the function runs,
    # so it does not depend on the order of the imports in that file.
    from pyclifer import __app_name__

    return logging.getLogger(name or __app_name__)  # type: ignore[return-value]
