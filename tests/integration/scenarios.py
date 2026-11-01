"""Where each pyclifer feature is exercised, or why it is not.

Every feature found by inventory.discover_inventory() appears in exactly one of the three
mappings below. PENDING is temporary: each item of the integration-test-matrix spec removes
the entries it exercises and moves them to COVERED, until PENDING is empty.
"""

_MATRIX = "tests/integration/test_group_config_matrix.py"
_OPTIONS = "tests/integration/test_automatic_options.py"

# Feature name -> "path/to/test_file.py::TestClass" that exercises it.
COVERED: dict[str, str] = {
    "event.config.loaded": (
        "tests/core/options/test_custom_config_option.py::TestCustomConfigOptionConfigLoadedEvent"
    ),
    # Full product of the main axes, with the effect observed (answer format, response handling).
    "GroupConfig.use_rich_help": f"{_MATRIX}::TestMainAxes",
    "GroupConfig.output_format_default": f"{_MATRIX}::TestMainAxes",
    "GroupConfig.handle_response": f"{_MATRIX}::TestMainAxes",
    # Effect observed directly: application name, exit code, record level, help rendering.
    "GroupConfig.name": f"{_MATRIX}::TestFieldEffects",
    "GroupConfig.exit_codes_class": f"{_MATRIX}::TestFieldEffects",
    "GroupConfig.unhandled_exception_log_level": f"{_MATRIX}::TestFieldEffects",
    "GroupConfig.rich_help_config": f"{_MATRIX}::TestFieldEffects",
    # Effect observed on the real log output (items 4 and 11).
    "GroupConfig.use_rich_logging": f"{_OPTIONS}::TestRichLogging",
    "GroupConfig.enable_secrets_filter": f"{_OPTIONS}::TestSecretsFiltering",
    "GroupConfig.sensitive_fields": f"{_OPTIONS}::TestSecretsFiltering",
    "GroupConfig.mask_free_text": f"{_OPTIONS}::TestFreeTextMasking",
    "GroupConfig.add_config_option": f"{_OPTIONS}::TestConfigOption",
    "GroupConfig.add_verbosity_option": f"{_OPTIONS}::TestVerbosityOption",
    "GroupConfig.verbosity_default_level": f"{_OPTIONS}::TestVerbosityOption",
    "GroupConfig.add_log_file_option": f"{_OPTIONS}::TestLogFileOption",
    "GroupConfig.log_file_default_level": f"{_OPTIONS}::TestLogFileOption",
    "GroupConfig.log_file_rotation_when": f"{_OPTIONS}::TestLogFileOption",
    "GroupConfig.log_file_rotation_interval": f"{_OPTIONS}::TestLogFileOption",
    "GroupConfig.log_file_rotation_backup_count": f"{_OPTIONS}::TestLogFileOption",
    "GroupConfig.add_version_option": f"{_OPTIONS}::TestVersionOption",
    "GroupConfig.add_output_format_option": f"{_OPTIONS}::TestOutputFormatOption",
    "GroupConfig.timer": f"{_OPTIONS}::TestTimerOption",
    "GroupConfig.auto_envvar_prefix": f"{_OPTIONS}::TestEnvironmentVariables",
    "GroupConfig.show_envvar": f"{_OPTIONS}::TestEnvironmentVariables",
    "option_factory.option": f"{_OPTIONS}::TestOptionFactories",
    "option_factory.config_option": f"{_OPTIONS}::TestOptionFactories",
    "option_factory.verbosity_option": f"{_OPTIONS}::TestOptionFactories",
    "option_factory.log_file_option": f"{_OPTIONS}::TestOptionFactories",
    "option_factory.output_filter_option": f"{_OPTIONS}::TestOptionFactories",
    "option_factory.pagination_options": f"{_OPTIONS}::TestOptionFactories",
    "option_factory.output_format_option": f"{_OPTIONS}::TestOptionFactories",
}

# Feature name -> reason it is not exercised, and why that is acceptable.
EXCLUDED: dict[str, str] = {}

# Item of the spec that will write the scenario -> feature names.
PENDING: dict[str, list[str]] = {
    "item 5 (propagation and parity)": [
        "GroupConfig.context_factory",
        "GroupConfig.context_options_panel",
        "GroupConfig.on",
        "public.Event",
        "public.EventsMixin",
        "public.GlobalOptionsMixin",
        "public.HandleResponseMixin",
        "public.PycliferGroup",
    ],
    "item 6 (public API)": [
        "public.Abort",
        "public.BOOL",
        "public.BadParameter",
        "public.BaseContext",
        "public.BaseInterface",
        "public.BaseModel",
        "public.BaseRenderer",
        "public.Choice",
        "public.CliTable",
        "public.CliTableColumn",
        "public.ClickException",
        "public.ClickPath",
        "public.CustomConfigOption",
        "public.DateTime",
        "public.ExceptionTable",
        "public.ExitCode",
        "public.FLOAT",
        "public.File",
        "public.FloatRange",
        "public.INT",
        "public.IntRange",
        "public.OperationResult",
        "public.OutputFormatMixin",
        "public.PYCLIFER_LOG_LEVELS",
        "public.PaginatedResponse",
        "public.PycliferOption",
        "public.Response",
        "public.ResponseRenderer",
        "public.RichExtraFormatter",
        "public.RichExtraStreamHandler",
        "public.RichHelpersMixin",
        "public.STRING",
        "public.SecretsMasker",
        "public.TRACE",
        "public.TimerOption",
        "public.Tuple",
        "public.UUID",
        "public.UsageError",
        "public.add_trace_method",
        "public.app_group",
        "public.argument",
        "public.command",
        "public.configure_rich_logging",
        "public.confirm",
        "public.confirmation_option",
        "public.echo",
        "public.get_configured_logger",
        "public.get_current_context",
        "public.get_logger",
        "public.group",
        "public.logger",
        "public.make_pass_decorator",
        "public.option",
        "public.output_filter_option",
        "public.pagination_options",
        "public.pass_context",
        "public.pass_obj",
        "public.password_option",
        "public.prompt",
        "public.returns_response",
        "public.secho",
        "public.style",
        "public.unstyle",
        "public.version_option",
    ],
}
