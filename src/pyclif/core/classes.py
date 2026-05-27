"""Custom Click classes for pyclif."""

from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

import click_extra
from boltons.iterutils import flatten, unique
from click_extra import TimerOption, get_app_dir, get_current_context
from click_extra.config import ConfigOption
from extra_platforms import is_linux
from rich_click import RichGroup, RichHelpConfiguration

from .mixins import GlobalOptionsMixin, HandleResponseMixin, StoreInMetaMixin
from .output.exit_codes import ExitCode


class PyclifOption(StoreInMetaMixin, click_extra.Option):
    """Custom Click Option that can be marked as global for propagation."""

    def __init__(self, *args: Any, is_global: bool = False, **kwargs: Any) -> None:
        """Initialize the option.

        Args:
            *args: Positional arguments for click.Option.
            is_global: If True, this option will be propagated to subcommands.
            **kwargs: Keyword arguments for click.Option.
        """
        self.is_global = is_global
        super().__init__(*args, **kwargs)


class PyclifTimerOption(TimerOption):
    """TimerOption integrated with pyclif output format.

    Skips the text echo in json/yaml mode — timing data is injected directly
    into the Response by returns_response instead.
    """

    # noinspection PyAttributeOutsideInit
    def init_timer(
        self, ctx: click_extra.Context, param: click_extra.Parameter, value: bool
    ) -> None:
        """Register the timer and store the context for deferred format check."""
        if not value:
            return
        self.start_time = perf_counter()
        self._close_ctx = ctx
        ctx.meta["click_extra.start_time"] = self.start_time
        ctx.call_on_close(self.print_timer)

    def print_timer(self) -> None:
        """Print elapsed time unless the output format is json or yaml.

        Output format is read at close time so that eager option processing
        order does not matter — meta is fully populated by then.
        """
        output_format = self._close_ctx.find_root().meta.get("pyclif.output_format", "table")
        if output_format in ("json", "yaml"):
            return
        elapsed = perf_counter() - self.start_time
        click_extra.echo(f"Execution time: {elapsed:.3f} seconds.")


class PyclifExtraGroup(HandleResponseMixin, GlobalOptionsMixin, click_extra.ExtraGroup):
    """Custom group based on click-extra that propagates global options."""


class PyclifRichGroup(HandleResponseMixin, GlobalOptionsMixin, RichGroup):
    """Custom group based on rich-click that propagates global options."""


PyclifGroup = PyclifExtraGroup


class CustomConfigOption(StoreInMetaMixin, ConfigOption):
    """Custom ConfigOption to add support for /etc/<cli_name> on Linux systems.

    This class extends the default click-extra ConfigOption to include system-wide
    configuration directories following Linux conventions while maintaining
    cross-platform compatibility.
    """

    def __init__(self, *args: Any, is_global: bool = False, **kwargs: Any) -> None:
        """Initialize the custom config option.

        Args:
            *args: Positional arguments.
            is_global: If True, this option will be propagated to subcommands.
            **kwargs: Keyword arguments.
        """
        self.is_global = is_global
        super().__init__(*args, **kwargs)

    def get_default(self, ctx, call=True):
        """Override get_default to fix rich-click help rendering.

        rich-click fetches the default with call=False during help generation,
        which returns the raw bound method. We intercept this and force
        evaluation to display the actual path cleanly.
        """
        default = super().get_default(ctx, call=call)
        if not call and callable(default):
            # noinspection PyBroadException
            try:
                return default()
            except Exception:
                pass
        return default

    def default_pattern(self) -> str:
        """Generate the default configuration search pattern.

        Creates search patterns for configuration files, prioritizing Linux system
        directories when running on Linux platforms. Falls back to standard
        user configuration directories on other platforms.

        Patterns are joined with "|" so that wcmatch's SPLIT flag (active on
        click-extra's ConfigOption) treats each path as a separate glob target.

        Returns:
            The pipe-separated glob pattern covering all config locations.

        Raises:
            RuntimeError: If no click, context is available to determine CLI name.
        """
        all_patterns = self._get_all_config_patterns()

        if not all_patterns:
            return self._get_fallback_pattern()

        return "|".join(all_patterns)

    def _get_extension_pattern(self) -> str:
        """Build a file extension pattern from supported formats.

        Creates a glob-compatible extension pattern from the configured
        formats, using either single extension or brace notation for
        multiple extensions.

        Returns:
            str: Extension pattern for glob matching (e.g., 'toml' or '{toml,yaml,json}').
        """
        extensions = []

        if self.file_format_patterns:
            patterns = unique(flatten(self.file_format_patterns.values()))
            # Keep only generic extensions (e.g., "*.toml" -> "toml")
            # and ignore specific file patterns like "pyproject.toml"
            extensions.extend(pat[2:] for pat in patterns if pat.startswith("*."))

        extensions = unique([ext for ext in extensions if ext])

        if not extensions:
            return "*"

        if len(extensions) == 1:
            return extensions[0]
        return f"{{{','.join(extensions)}}}"

    def _get_all_config_patterns(self) -> list[str]:
        """Get all configuration search patterns in priority order.

        Constructs file search patterns for different configuration locations
        based on the current platform and supported file formats.

        Returns:
            List of glob patterns for configuration file search, ordered by
            priority (system-wide first, then user-specific).

        Raises:
            RuntimeError: If no click, context is available to determine CLI name.
        """
        patterns = []

        ext_pattern = self._get_extension_pattern()

        try:
            ctx = get_current_context()
            cli_name = ctx.find_root().info_name
        except RuntimeError:
            # No click context available - this can happen during testing
            # or when called outside a click command context
            return []

        if not cli_name:
            return []

        if is_linux():
            system_config_dir = Path(f"/etc/{cli_name}")
            system_pattern = str(system_config_dir / f"*.{ext_pattern}")
            patterns.append(system_pattern)

        try:
            roaming = getattr(self, "roaming", False)
            force_posix = getattr(self, "force_posix", False)
            app_dir = Path(
                get_app_dir(cli_name, roaming=roaming, force_posix=force_posix)
            ).resolve()
            user_pattern = str(app_dir / f"*.{ext_pattern}")
            patterns.append(user_pattern)
        except (OSError, ValueError, TypeError) as e:
            # Handle specific exceptions that can be raised by get_app_dir or Path operations:
            # - OSError: File system-related errors (permissions, path issues, etc.)
            # - ValueError: Invalid arguments passed to get_app_dir or Path
            # - TypeError: Type-related issues with arguments
            import logging

            # noinspection PyUnresolvedReferences
            logger = logging.getLogger(__name__)
            logger.debug(f"Failed to get user config directory: {e}")
            # Continue without user config pattern - system config may still work

        return patterns

    def _get_fallback_pattern(self) -> str:
        """Get a fallback configuration pattern when normal detection fails.

        Provides a basic configuration search pattern for cases where
        the click context is not available or CLI name cannot be determined.

        Returns:
            str: A basic configuration file search pattern.
        """
        ext_pattern = self._get_extension_pattern()
        return f"*.{ext_pattern}"


@dataclass
class GroupConfig:
    """Configuration settings for CLI groups and applications."""

    name: str | None = None
    auto_envvar_prefix: str | None = None
    show_envvar: bool = True

    # Feature flags
    add_config_option: bool = False
    add_verbosity_option: bool = False
    add_log_file_option: bool = False
    add_version_option: bool = False
    add_output_format_option: bool = False

    # Logging settings
    verbosity_default_level: str = "WARNING"
    use_rich_logging: bool = True
    enable_secrets_filter: bool = True

    # Log file settings
    log_file_default_level: str = "TRACE"
    log_file_rotation_when: str = "midnight"
    log_file_rotation_interval: int = 1
    log_file_rotation_backup_count: int = 7

    # Output format settings
    output_format_default: str = "table"
    handle_response: bool = False
    timer: bool = False

    # Help formatting
    use_rich_help: bool = True
    rich_help_config: "dict | str | RichHelpConfiguration | None" = None

    # Error handling
    unhandled_exception_log_level: str = "error"

    # Exit codes
    exit_codes_class: type[ExitCode] = ExitCode

    # Security
    sensitive_fields: list[str] = field(default_factory=list)
