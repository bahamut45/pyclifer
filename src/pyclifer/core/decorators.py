"""Core decorators for pyclifer applications."""

import functools
import logging
from collections.abc import Callable
from dataclasses import fields
from time import perf_counter
from typing import Any, TypeVar, cast

import click_extra
from rich_click import rich_config
from rich_click.decorators import command as rich_command_decorator
from rich_click.decorators import group as rich_group_decorator

from .callbacks import get_meta_storing_callback
from .classes import (
    CustomConfigOption,
    GroupConfig,
    PycliferExtraGroup,
    PycliferOption,
    PycliferRichGroup,
    PycliferTimerOption,
    StoreInMetaMixin,
)
from .log.config import PycliferVerbosityOption, create_log_file_callback
from .output.exit_codes import ExitCode, validate_exit_codes_class

_F = TypeVar("_F", bound=Callable[..., Any])
_log = logging.getLogger(__name__)


def _split_group_kwargs(kwargs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split kwargs into GroupConfig fields and Click pass-through arguments."""
    config_fields = {f.name for f in fields(GroupConfig)}
    return (
        {k: v for k, v in kwargs.items() if k in config_fields},
        {k: v for k, v in kwargs.items() if k not in config_fields},
    )


def _get_root_context() -> click_extra.Context | None:
    """Return the root Click context by walking up the parent chain."""
    ctx = click_extra.get_current_context(silent=True)
    if ctx is None:
        return None
    while ctx.parent is not None:
        ctx = ctx.parent
    return ctx


class GroupDecorator:
    """Decorator class applying GroupConfig and Click logic to a group."""

    def __init__(self, config: GroupConfig, click_kwargs: dict[str, Any]):
        """Initialize the decorator with explicit config and pass-through click arguments."""
        self.config = config
        self.click_kwargs = click_kwargs

    def __call__(self, f: Callable) -> Any:
        """Apply the configuration and create the Click group."""
        self._setup_logging()

        f = self._apply_rich_help(f)
        self._configure_context()
        f = self._apply_automatic_options(f)
        f = self._apply_click_group(f)
        # noinspection PyTypeChecker
        self._patch_make_context(f)
        # noinspection PyTypeChecker
        self._configure_handle_response(f)

        return f

    def _setup_logging(self) -> None:
        """Configure the logging system based on the group config."""
        if self.config.use_rich_logging:
            from .log.config import configure_rich_logging

            # noinspection PyArgumentEqualDefault
            configure_rich_logging(
                use_rich=True,
                rich_tracebacks=True,
                enable_secrets_filter=self.config.enable_secrets_filter,
                sensitive_fields=self.config.sensitive_fields or None,
            )

    def _apply_rich_help(self, f: Callable) -> Callable:
        """Apply rich-click help formatting if enabled."""
        if self.config.use_rich_help:
            from .rich_help_config import get_rich_config

            # noinspection PyNoneFunctionAssignment
            config = get_rich_config(self.config.rich_help_config)
            if config:
                f = rich_config(help_config=config)(f)
        return f

    def _configure_context(self) -> None:
        """Configure the default Click context settings."""
        context_settings = self.click_kwargs.get("context_settings", {})
        context_settings.update(
            {
                "help_option_names": ["-h", "--help"],
                "show_default": True,
            }
        )
        if self.config.auto_envvar_prefix is not None:
            context_settings["auto_envvar_prefix"] = self.config.auto_envvar_prefix
        self.click_kwargs["context_settings"] = context_settings

    def _apply_automatic_options(self, f: Callable) -> Callable:
        """Inject options like --config, --verbosity, etc., based on the config."""
        if self.config.timer:
            f = click_extra.option("--time/--no-time", cls=PycliferTimerOption)(f)

        if self.config.add_output_format_option:
            f = output_format_option(
                default_output_format=self.config.output_format_default, is_global=True
            )(f)

        if self.config.add_config_option:
            f = config_option()(f)

        if self.config.add_verbosity_option:
            f = verbosity_option(default=self.config.verbosity_default_level)(f)

        if self.config.add_log_file_option:
            f = log_file_option(
                default_level=self.config.log_file_default_level,
                when=self.config.log_file_rotation_when,
                interval=self.config.log_file_rotation_interval,
                backup_count=self.config.log_file_rotation_backup_count,
                enable_secrets_filter=self.config.enable_secrets_filter,
                sensitive_fields=self.config.sensitive_fields or None,
            )(f)

        if self.config.add_version_option:
            version_kw = {}
            if "version" in self.click_kwargs:
                version_kw["version"] = self.click_kwargs.pop("version")
            f = click_extra.version_option(**version_kw)(f)

        return f

    # noinspection PyTypeChecker
    def _apply_click_group(self, f: Callable) -> click_extra.Group:
        """Apply the final Click group decorator using the custom PycliferGroup class."""
        if self.config.use_rich_help:
            self.click_kwargs["cls"] = PycliferRichGroup
            group_decorator = rich_group_decorator
        else:
            self.click_kwargs["cls"] = PycliferExtraGroup
            group_decorator = click_extra.group

        if self.config.name:
            self.click_kwargs["name"] = self.config.name
        result = group_decorator(**self.click_kwargs)(f)
        result._context_options_panel = self.config.context_options_panel
        return result

    def _patch_make_context(self, f: click_extra.Group) -> None:
        """Patch make_context once with all framework hooks applied in order.

        Concerns composed here (each guarded by its config flag):

        1. Dynamic auto_envvar_prefix (pre-call): derive prefix from the CLI name when not set.
        2. Early verbosity (pre-call and post-call): extract level before Click parses args,
           apply it after the context is built.
        3. Framework meta-injection (post-call): store log level and exit codes in ctx.meta
           so returns_response can read them without a GroupConfig reference.
        4. The context=True / is_global=True prescan (pre-call): reorder tokens, so Click
           parses root options placed after a subcommand boundary directly.
        5. The context_factory (post-call): build ctx.obj from context=True param values.

        Args:
            f: The Click group to patch.
        """
        original_make_context = f.make_context
        level = self.config.unhandled_exception_log_level
        exit_codes_cls = self.config.exit_codes_class

        @functools.wraps(original_make_context)
        def custom_make_context(
            info_name: str,
            args: list[str],
            parent: click_extra.Context | None = None,
            **extra: Any,
        ) -> click_extra.Context:
            """Apply all make_context hooks in a single wrapper."""
            # --- pre-call ---

            # Concern 1 — dynamic auto_envvar_prefix
            if self.config.auto_envvar_prefix is None and parent is None and info_name:
                derived_prefix = info_name.upper().replace("-", "_").replace(" ", "_")
                extra.setdefault("auto_envvar_prefix", derived_prefix)

            # Concern 2 — early verbosity extraction
            level_name = None
            if self.config.add_verbosity_option and parent is None and args:
                level_name = self._extract_early_verbosity(args)

            # Concern 4 — prescan: reorder after-boundary tokens so Click parses them at root level.
            if parent is None and args:
                # Pass 1: context=True, is_global=False — move (CLI arg priority over env var)
                context_only = [
                    p
                    for p in f.params
                    if getattr(p, "context", False) and not getattr(p, "is_global", False)
                ]
                args = GroupDecorator._prescan_boundary_tokens(args, f, context_only, copy=False)
                # Pass 2: is_global=True — copy (root callback must also see them after boundary)
                global_params = [p for p in f.params if getattr(p, "is_global", False)]
                args = GroupDecorator._prescan_boundary_tokens(args, f, global_params, copy=True)

            # --- call ---
            ctx = original_make_context(info_name, args, parent=parent, **extra)

            # --- post-call ---

            # Concern 2 — early verbosity application
            if self.config.add_verbosity_option and parent is None and level_name:
                from .log.config import PYCLIFER_LOG_LEVELS

                if level_name in PYCLIFER_LOG_LEVELS:
                    for param in ctx.command.params:  # pragma: no branch
                        if param.name == "verbosity" and hasattr(param, "set_level"):
                            param.set_level(ctx, param, level_name)
                            break

            # Concern 3 — framework meta injection
            if parent is None:
                ctx.meta.setdefault("pyclifer.unhandled_exception_log_level", level)
                ctx.meta.setdefault("pyclifer.exit_codes_class", exit_codes_cls)

            # Concern 5 — context_factory: build ctx.obj from context=True param values
            if parent is None and self.config.context_factory is not None:
                context_values = {
                    p.name: ctx.params.get(p.name) for p in f.params if getattr(p, "context", False)
                }
                ctx.obj = self.config.context_factory(**context_values)

            return ctx

        f.make_context = custom_make_context

    @staticmethod
    def _find_subcommand_boundary(args: list[str], f: click_extra.Group) -> int:
        """Return the index of the first subcommand token in args.

        Skips option value tokens correctly, so a subcommand name that happens
        to be an option value is not misidentified as a boundary.
        Returns len(args) when no subcommand boundary is found.

        Args:
            args: The raw argument list.
            f: The Click group whose registered commands define valid boundaries.

        Returns:
            Index of the first subcommand token, or len(args) if none is found.
        """
        # Map every declared option form to its nargs (0 for flags, n otherwise).
        # nargs=-1 (variadic) is treated as 0 — these options must be placed before
        # the boundary manually; the pre-scan skips them.
        option_nargs: dict[str, int] = {}
        for param in f.params:
            if not isinstance(param, click_extra.Option):
                continue
            nargs = getattr(param, "nargs", 1)
            if param.is_flag or nargs == -1:  # pragma: no cover
                nargs = 0
            for decl in param.opts:
                option_nargs[decl] = nargs

        commands = getattr(f, "commands", {}) or {}
        i = 0
        while i < len(args):
            token = args[i]
            if token == "--":
                return len(args)
            if token.startswith("-"):
                if "=" in token:
                    i += 1  # --key=val — value is inline, no next token consumed
                else:
                    nargs = option_nargs.get(token)
                    if nargs is None or nargs == -1:
                        i += 1  # unknown or variadic — treat as flag
                    else:
                        i += 1 + nargs
            else:
                if token in commands:
                    return i
                i += 1
        return len(args)

    @staticmethod
    def _extract_params(
        args: list[str], params: list[click_extra.Parameter]
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        """Extract option tokens matching params from args via linear scan.

        Does not use Click internals. Returns a 3-tuple:
        - opts_dict: {param.name: value} — first occurrence per param.
        - consumed_tokens: raw token strings matched and consumed, in order.
        - remainder: tokens not matched.

        nargs=-1 params are skipped entirely (not extracted).
        Stops at '--' (argument terminator); everything from '--' onwards
        goes to remainder unchanged.

        Args:
            args: The raw argument list to scan.
            params: The option params to extract.

        Returns:
            Tuple of (opts_dict, consumed_tokens, remainder).
        """
        if not args or not params:
            return {}, [], list(args)

        # Build lookup: option declaration → (param_name, nargs, is_flag)
        lookup: dict[str, tuple[str, int, bool]] = {}
        for param in params:
            nargs = getattr(param, "nargs", 1)
            if nargs == -1:  # pragma: no cover
                continue  # variadic — Click rejects nargs=-1 on Options; defensive guard
            is_flag = bool(getattr(param, "is_flag", False))
            effective_nargs = 0 if is_flag else nargs
            for decl in param.opts:
                lookup[decl] = (param.name, effective_nargs, is_flag)

        opts: dict[str, Any] = {}
        consumed: list[str] = []
        remainder: list[str] = []
        i = 0

        while i < len(args):
            token = args[i]

            if token == "--":
                remainder.extend(args[i:])
                break

            if token.startswith("-") and "=" in token:
                key, _, val = token.partition("=")
                if key in lookup:
                    name, _, _ = lookup[key]
                    consumed.append(token)
                    opts.setdefault(name, val)
                    i += 1
                else:
                    remainder.append(token)
                    i += 1
                continue

            if token in lookup:
                name, nargs, is_flag = lookup[token]
                if is_flag:
                    consumed.append(token)
                    opts.setdefault(name, True)
                    i += 1
                else:
                    value_tokens = args[i + 1 : i + 1 + nargs]
                    if len(value_tokens) == nargs:
                        consumed.append(token)
                        consumed.extend(value_tokens)
                        parsed_value = value_tokens[0] if nargs == 1 else tuple(value_tokens)
                        opts.setdefault(name, parsed_value)
                        i += 1 + nargs
                    else:
                        # Not enough value tokens — leave as remainder
                        remainder.append(token)
                        i += 1
            else:
                remainder.append(token)
                i += 1

        return opts, consumed, remainder

    @staticmethod
    def _prescan_boundary_tokens(
        args: list[str],
        f: click_extra.Group,
        params: list[click_extra.Parameter],
        *,
        copy: bool,
    ) -> list[str]:
        """Move or copy matched after-boundary tokens to before the boundary.

        Args:
            args: The raw argument list.
            f: The Click group whose subcommands define the boundary.
            params: The option params to extract from after the boundary.
            copy: If True, keep the matched tokens in their original position too
                (global options); if False, remove them from after the boundary
                (context-only options).

        Returns:
            The reordered argument list, or the original list if no change was needed.
        """
        if not args or not params:
            return args
        boundary = GroupDecorator._find_subcommand_boundary(args, f)
        before, after = args[:boundary], args[boundary:]
        if not after:
            return args
        _, consumed, after_remainder = GroupDecorator._extract_params(after, params)
        if not consumed:
            return args
        tail = after if copy else after_remainder
        return consumed + before + tail

    def _configure_handle_response(self, f: click_extra.Group) -> None:
        """Validate exit codes and propagate handle_response to the group instance.

        Args:
            f: The Click group instance to configure.

        Raises:
            ValueError: When exit_codes_class is not a valid ExitCode subclass.
        """
        validate_exit_codes_class(self.config.exit_codes_class)

        if self.config.handle_response:
            f.handle_response_by_default = True

    @staticmethod
    def _extract_early_verbosity(args: list[str]) -> str | None:
        """Extract the verbosity level from arguments without applying it.

        Args:
            args: The command line arguments.

        Returns:
            The extracted verbosity level, or None.
        """
        for i, arg in enumerate(args):
            if arg in ("-v", "--verbosity") and i + 1 < len(args):
                return args[i + 1].upper()
            elif arg.startswith("--verbosity="):
                return arg.split("=", 1)[1].upper()
            elif arg.startswith("-v") and len(arg) > 2:
                return arg[2:].upper()
        return None


def app_group(**kwargs: Any) -> Callable[[Callable[..., Any]], click_extra.Group]:
    """Decorator for the main CLI application entry point.

    Enables all automatic features (config, logging, version, etc.) by default.
    Options like --verbosity will be propagated to all subcommands.

    All keyword arguments map to `GroupConfig` fields or are forwarded to Click.
    Notable options:

    - `handle_response` (bool): intercept and print `Response` objects automatically.
    - `timer` (bool): inject `--time/--no-time`. Prints elapsed time in rich/table/raw;
      injects `execution_time` and `execution_time_str` into `Response.data` in json/yaml.
    - `output_format_default` (str): default for `--output-format`
      (json, yaml, table, rich, raw, text).

    Args:
        **kwargs: GroupConfig fields or Click group arguments.

    Returns:
        A decorator that wraps the function as a pyclifer CLI group.
    """
    config_kwargs, click_kwargs = _split_group_kwargs(kwargs)

    # Create config with App defaults
    config = GroupConfig(
        add_config_option=config_kwargs.pop("add_config_option", True),
        add_verbosity_option=config_kwargs.pop("add_verbosity_option", True),
        add_log_file_option=config_kwargs.pop("add_log_file_option", True),
        add_version_option=config_kwargs.pop("add_version_option", True),
        add_output_format_option=config_kwargs.pop("add_output_format_option", True),
        handle_response=config_kwargs.pop("handle_response", True),
        **config_kwargs,
    )

    return GroupDecorator(config, click_kwargs)


def group(**kwargs: Any) -> Callable[[Callable[..., Any]], click_extra.Group]:
    """Decorator for CLI subgroups.

    Creates a standard group without global application options by default.
    """
    config_kwargs, click_kwargs = _split_group_kwargs(kwargs)

    # Create config with Sub-group defaults (mostly False from the dataclass)
    config = GroupConfig(**config_kwargs)

    return GroupDecorator(config, click_kwargs)


def returns_response(f: Callable) -> Callable:
    """Decorator that intercepts a Response return value and prints it automatically.

    When the decorated command function returns a Response instance, this decorator
    reads the output format stored in ctx.meta['pyclifer.output_format'] (set by
    the --output-format option) and dispatches printing via BaseContext.
    Non-Response return values are left untouched.

    Example:

        @app.command()
        @returns_response
        @option("--name", default="world")
        @click.pass_context
        def hello(ctx, name):
            return Response(success=True, message=f"Hello {name}", data={"name": name})

    Args:
        f: The command function to wrap.

    Returns:
        The wrapped function.
    """

    @functools.wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper for returning a Response object based on command output"""
        # Lazy import to avoid circular dependency at module load time
        from .output.responses import Response as _Response

        root = _get_root_context()
        meta = root.meta if root is not None else {}

        try:
            result = f(*args, **kwargs)
        except Exception as e:
            log_level = meta.get("pyclifer.unhandled_exception_log_level", "error")
            _log.log(
                getattr(logging, log_level.upper(), logging.ERROR),
                "Unhandled exception in command '%s'",
                f.__name__,
                exc_info=True,
            )
            result = _Response(success=False, message=str(e), error_code=ExitCode.ERROR)
        _log.debug(
            "returns_response: command '%s' returned %s",
            f.__name__,
            type(result).__name__,
        )
        if isinstance(result, _Response):
            from pyclifer.core.context import BaseContext

            ctx = click_extra.get_current_context(silent=True)

            # Use the actual context object (ctx.obj) if it is a BaseContext
            # subclass so that custom overrides (e.g., print_result_based_on_format)
            # are respected.  Fall back to a fresh BaseContext when ctx.obj is
            # absent or of an unrelated type.
            obj = ctx.obj if ctx is not None else None
            output_ctx = obj if isinstance(obj, BaseContext) else BaseContext()
            output_format = meta.get("pyclifer.output_format", "table")

            # Inject execution time into structured output when timer is active.
            start_time = meta.get("click_extra.start_time")
            if (
                start_time is not None
                and output_format in ("json", "yaml")
                and isinstance(result.data, dict)
            ):
                # noinspection PyTypeChecker
                elapsed = perf_counter() - start_time
                result.data["execution_time"] = round(elapsed, 3)
                result.data["execution_time_str"] = f"{elapsed:.3f}s"
            output_ctx.output_format = output_format
            _log.debug(
                "returns_response: ctx.obj type=%s, using output_ctx type=%s, "
                "output_format=%r, meta keys=%s",
                type(obj).__name__,
                type(output_ctx).__name__,
                output_format,
                list(meta.keys()),
            )
            output_filter = meta.get("pyclifer.output_filter")
            options = {"filter_value": output_filter} if output_filter else {}
            output_ctx.print_result_based_on_format(result, options=options)
            if not result.success and result.error_code and ctx is not None:
                ctx.exit(result.error_code)
        else:
            _log.debug(
                "returns_response: result is not a Response instance — skipping output dispatch"
            )
        return result

    return wrapper


def command(
    name: str | None = None,
    handle_response: bool = False,
    **kwargs: Any,
) -> Callable[[_F], click_extra.Command]:
    """Create a Click command with optional automatic response handling.

    When handle_response=True, any Response returned by the command function
    is automatically printed using the output format resolved from ctx.meta
    (--output-format option). This is equivalent to manually applying the
    returns_response decorator.

    Args:
        name: Name of the command.
        handle_response: If True, wrap the function with returns_response.
        **kwargs: Additional arguments passed to click_extra.command().

    Returns:
        Decorated function as a Click command.
    """
    command_decorator = rich_command_decorator

    if not handle_response:
        decorate = command_decorator(name=name, **kwargs) if name else command_decorator(**kwargs)
        return cast(Callable[[_F], click_extra.Command], decorate)

    def decorator(f: _F) -> click_extra.Command:
        """Decorator for Click commands with automatic response handling"""
        wrapped = returns_response(f)
        deco = command_decorator(name=name, **kwargs) if name else command_decorator(**kwargs)
        cmd = deco(wrapped)
        return cast(click_extra.Command, cmd)

    return decorator


def option(
    *param_decls: str,
    is_global: bool = False,
    context: bool = False,
    show_envvar: bool = True,
    store_in_meta: bool = False,
    show_in_subcommand_help: bool = True,
    **kwargs: Any,
) -> Callable[[Callable], Callable]:
    """Create a Click option with global propagation support.

    Ensures a consistent environment variable display and allows options
    to be marked as global to be available on all subcommands.

    Args:
        *param_decls: Parameter declarations for the option.
        is_global: If True, the option is propagated to all subcommands.
        context: If True, the option feeds ctx.obj construction and is accepted
            at any position in the command chain.
        show_envvar: Show environment variables in the help output.
        store_in_meta: If True, stores the option value in ctx.meta automatically.
        show_in_subcommand_help: If True, display-only copy of the option appears
            in subcommand help when context=True.
        **kwargs: Additional arguments passed to click_extra.option().

    Returns:
        Option decorator function.
    """
    cls = kwargs.get("cls", PycliferOption)
    kwargs["cls"] = cls
    kwargs["is_global"] = is_global
    kwargs.setdefault("show_envvar", show_envvar)

    # Only forward context to classes that declare the attribute (PycliferOption subclasses).
    if isinstance(cls, type) and issubclass(cls, PycliferOption):
        kwargs["context"] = context
        kwargs["show_in_subcommand_help"] = show_in_subcommand_help

    # Delegate to the Mixin if the class supports it
    if isinstance(cls, type) and issubclass(cls, StoreInMetaMixin):
        kwargs["store_in_meta"] = store_in_meta
    elif store_in_meta:
        # Fallback for external classes (like PycliferVerbosityOption) that don't use
        # StoreInMetaMixin
        kwargs["callback"] = get_meta_storing_callback(kwargs.get("callback"))
        kwargs.setdefault("expose_value", False)

    return click_extra.option(*param_decls, **kwargs)


def config_option(
    *param_decls: str, is_global: bool = False, show_envvar: bool = True, **kwargs: Any
) -> Callable[[Callable], Callable]:
    """Add a configuration file option to a command or group.

    Args:
        *param_decls: Parameter declarations (default: '--config', '-C').
        is_global: If True, the option is propagated to all subcommands.
        show_envvar: Show environment variables in the help output.
        **kwargs: Additional arguments passed to the option decorator.

    Returns:
        The decorated function.
    """
    if not param_decls:
        param_decls = ("--config", "-C")

    kwargs.setdefault("cls", CustomConfigOption)
    kwargs.setdefault(
        "help", "Configuration file location. Supports glob patterns and remote URLs."
    )

    return option(*param_decls, is_global=is_global, show_envvar=show_envvar, **kwargs)


def verbosity_option(
    *param_decls: str, is_global: bool = True, show_envvar: bool = True, **kwargs: Any
) -> Callable[[Callable], Callable]:
    """Add a verbosity option to a command or group.

    Args:
        *param_decls: Parameter declarations (default: '--verbosity', '-v').
        is_global: If True, the option is propagated to all subcommands.
        show_envvar: Show environment variables in the help output.
        **kwargs: Additional arguments passed to the option decorator.

    Returns:
        The decorated function.
    """
    if not param_decls:
        param_decls = ("--verbosity", "-v")

    kwargs.setdefault("cls", PycliferVerbosityOption)
    kwargs.setdefault("default", "INFO")
    # Do not pass as a function argument; the value is in ctx.meta['verbosity']
    # The PycliferVerbosityOption class handles storing the value in the context.
    kwargs.setdefault("expose_value", False)
    kwargs.setdefault("is_eager", True)

    return option(*param_decls, is_global=is_global, show_envvar=show_envvar, **kwargs)


def log_file_option(
    *param_decls: str,
    default_level: str = "INFO",
    when: str = "midnight",
    interval: int = 1,
    backup_count: int = 7,
    enable_secrets_filter: bool = False,
    sensitive_fields: list[str] | None = None,
    is_global: bool = False,
    show_envvar: bool = True,
    **kwargs: Any,
) -> Callable[[Callable], Callable]:
    """Add a log file option with automatic rotation to a command or group.

    Args:
        *param_decls: Parameter declarations (default: '--log-file').
        default_level: Default logging level for the file.
        when: Rotation interval type.
        interval: Rotation interval value.
        backup_count: Number of backup files to keep.
        enable_secrets_filter: Enable secrets filtering in logs.
        sensitive_fields: Additional field names to mask on top of the defaults.
                          Merged into SecretsMasker.DEFAULT_FIELDS — does not replace them.
        is_global: If True, the option is propagated to all subcommands.
        show_envvar: Show environment variables in the help output.
        **kwargs: Additional arguments passed to the option decorator.

    Returns:
        The decorated function.
    """
    if not param_decls:
        param_decls = ("--log-file",)

    kwargs.setdefault("type", click_extra.Path(dir_okay=False, writable=True))
    kwargs.setdefault("is_eager", True)
    kwargs.setdefault("expose_value", False)
    kwargs.setdefault("help", "Path to the log file (with daily automatic rotation).")
    kwargs["callback"] = create_log_file_callback(
        default_level=default_level,
        when=when,
        interval=interval,
        backup_count=backup_count,
        enable_secrets_filter=enable_secrets_filter,
        sensitive_fields=sensitive_fields,
    )

    return option(*param_decls, is_global=is_global, show_envvar=show_envvar, **kwargs)


def output_filter_option(
    *param_decls: str,
    show_envvar: bool = True,
    **kwargs: Any,
) -> Callable[[Callable], Callable]:
    """Add an output filter option to a command.

    When combined with --output-format raw, json, or yaml, this option lets
    users extract a value from the Response data using a dotted key path.

    The selected path is stored in ctx.meta['pyclifer.output_filter'] and is
    automatically picked up by returns_response.

    Numeric path segments are treated as list indices. Resolution order:
    data["data"] first, then top-level response fields.

    Example:

        @app.command()
        @output_filter_option()
        @returns_response
        @click.pass_context
        def articles(ctx):
            return Response(
                success=True,
                message="2 articles",
                data={"results": [{"id": 1, "title": "Hello"}, {"id": 2}]},
            )

        # myapp articles -o raw -f results.0.title  -> Hello
        # myapp articles -o json -f results.0       -> {"id": 1, "title": "Hello"}
        # myapp articles -o raw -f message          -> 2 articles

    Args:
        *param_decls: Parameter declarations (default: --output-filter, -f).
        show_envvar: Show environment variables in the help output.
        **kwargs: Additional arguments passed to the option decorator.

    Returns:
        The decorated function.
    """
    if not param_decls:
        param_decls = ("--output-filter", "-f")

    kwargs.setdefault("help", "Dotted path to extract from the response (raw, json, yaml).")
    # noinspection PyArgumentEqualDefault
    kwargs.setdefault("default", None)
    kwargs.setdefault("store_in_meta", True)

    return option(*param_decls, show_envvar=show_envvar, **kwargs)


def pagination_options(
    default_limit: int = 20,
    max_limit: int = 100,
) -> Callable[[_F], _F]:
    """Inject --page and --limit options into a command.

    Options are stored in ctx.meta under the keys 'pyclifer.page' and
    'pyclifer.limit' via store_in_meta.

    Args:
        default_limit: Default number of results per page.
        max_limit: Maximum allowed value for --limit (enforced via IntRange).

    Returns:
        A decorator that adds --page and --limit to the decorated function.
    """

    def decorator(f: _F) -> _F:
        """Add --page and --limit options to the command."""
        f = option(
            "--limit",
            "-l",
            default=default_limit,
            type=click_extra.IntRange(1, max_limit),
            help=f"Results per page (max {max_limit}).",
            store_in_meta=True,
        )(f)
        f = option(
            "--page",
            "-p",
            default=1,
            type=click_extra.IntRange(min=1),
            help="Page number (1-indexed).",
            store_in_meta=True,
        )(f)
        return f

    return decorator


def output_format_option(
    *param_decls: str,
    default_output_format: str = "table",
    is_global: bool = False,
    show_envvar: bool = True,
    **kwargs: Any,
) -> Callable[[Callable], Callable]:
    """Add an output format option to a command or group.

    This decorator leverages the custom `option` function to ensure consistent
    behavior, including global propagation and environment variable support.

    It automatically stores the chosen format in the Click context
    (`ctx.meta['output_format']`) and does not pass it as a function argument,
    preventing `TypeError` in commands that do not explicitly handle it.

    Args:
        *param_decls: Parameter declarations (default: '--output-format', '-o').
        default_output_format: Default output format.
        is_global: If True, the option is propagated to all subcommands.
        show_envvar: Show environment variables in the help output.
        **kwargs: Additional arguments passed to the option decorator.

    Returns:
        The decorated function.
    """
    if not param_decls:
        param_decls = ("--output-format", "-o")

    kwargs.setdefault(
        "type",
        click_extra.Choice(["json", "yaml", "table", "rich", "raw", "text"], case_sensitive=False),
    )
    kwargs.setdefault("help", "Specify the output format for the command.")

    kwargs.setdefault("store_in_meta", True)
    kwargs.setdefault("is_eager", True)
    kwargs.setdefault("default", default_output_format)

    return option(*param_decls, is_global=is_global, show_envvar=show_envvar, **kwargs)
