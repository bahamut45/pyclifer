"""Where each pyclifer feature is exercised, or why it is not.

Every feature found by inventory.discover_inventory() appears in exactly one of the three
mappings below. PENDING held the features not yet exercised while the integration-test-matrix
spec was written; it is empty now and stays so: a new feature goes to COVERED or EXCLUDED.
"""

_MATRIX = "tests/integration/test_group_config_matrix.py"
_OPTIONS = "tests/integration/test_automatic_options.py"
_PROPAGATION = "tests/integration/test_propagation.py"
_PUBLIC_API = "tests/integration/test_public_api.py"

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
    "GroupConfig.replace_root_handlers": f"{_OPTIONS}::TestReplaceRootHandlers",
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
    # Propagation and parity on three levels, both help paths (item 5).
    "GroupConfig.context_factory": f"{_PROPAGATION}::TestContextFactory",
    "GroupConfig.context_options_panel": f"{_PROPAGATION}::TestContextOptionsPanel",
    "GroupConfig.on": f"{_PROPAGATION}::TestEvents",
    "public.Event": f"{_PROPAGATION}::TestEvents",
    "public.EventsMixin": f"{_PROPAGATION}::TestPublicGroupClasses",
    "public.GlobalOptionsMixin": f"{_PROPAGATION}::TestPublicGroupClasses",
    "public.HandleResponseMixin": f"{_PROPAGATION}::TestPublicGroupClasses",
    "public.PycliferGroup": f"{_PROPAGATION}::TestPublicGroupClasses",
    "option_factory.option": f"{_OPTIONS}::TestOptionFactories",
    "option_factory.config_option": f"{_OPTIONS}::TestOptionFactories",
    "option_factory.verbosity_option": f"{_OPTIONS}::TestOptionFactories",
    "option_factory.log_file_option": f"{_OPTIONS}::TestOptionFactories",
    "option_factory.output_filter_option": f"{_OPTIONS}::TestOptionFactories",
    "option_factory.pagination_options": f"{_OPTIONS}::TestOptionFactories",
    "option_factory.output_format_option": f"{_OPTIONS}::TestOptionFactories",
    # Every symbol of pyclifer.__all__ is imported and used in a real application (item 6).
    "public.app_group": f"{_PUBLIC_API}::TestDecorators",
    "public.group": f"{_PUBLIC_API}::TestDecorators",
    "public.command": f"{_PUBLIC_API}::TestDecorators",
    "public.option": f"{_PUBLIC_API}::TestDecorators",
    "public.argument": f"{_PUBLIC_API}::TestDecorators",
    "public.pass_context": f"{_PUBLIC_API}::TestDecorators",
    "public.pass_obj": f"{_PUBLIC_API}::TestDecorators",
    "public.make_pass_decorator": f"{_PUBLIC_API}::TestDecorators",
    "public.get_current_context": f"{_PUBLIC_API}::TestDecorators",
    "public.returns_response": f"{_PUBLIC_API}::TestDecorators",
    "public.Choice": f"{_PUBLIC_API}::TestClickTypes",
    "public.ClickPath": f"{_PUBLIC_API}::TestClickTypes",
    "public.File": f"{_PUBLIC_API}::TestClickTypes",
    "public.INT": f"{_PUBLIC_API}::TestClickTypes",
    "public.FLOAT": f"{_PUBLIC_API}::TestClickTypes",
    "public.BOOL": f"{_PUBLIC_API}::TestClickTypes",
    "public.STRING": f"{_PUBLIC_API}::TestClickTypes",
    "public.UUID": f"{_PUBLIC_API}::TestClickTypes",
    "public.DateTime": f"{_PUBLIC_API}::TestClickTypes",
    "public.Tuple": f"{_PUBLIC_API}::TestClickTypes",
    "public.IntRange": f"{_PUBLIC_API}::TestClickTypes",
    "public.FloatRange": f"{_PUBLIC_API}::TestClickTypes",
    "public.echo": f"{_PUBLIC_API}::TestTerminalInput",
    "public.secho": f"{_PUBLIC_API}::TestTerminalInput",
    "public.style": f"{_PUBLIC_API}::TestTerminalInput",
    "public.unstyle": f"{_PUBLIC_API}::TestTerminalInput",
    "public.confirm": f"{_PUBLIC_API}::TestTerminalInput",
    "public.prompt": f"{_PUBLIC_API}::TestTerminalInput",
    "public.ClickException": f"{_PUBLIC_API}::TestClickErrors",
    "public.BadParameter": f"{_PUBLIC_API}::TestClickErrors",
    "public.UsageError": f"{_PUBLIC_API}::TestClickErrors",
    "public.Abort": f"{_PUBLIC_API}::TestClickErrors",
    "public.TimerOption": f"{_PUBLIC_API}::TestOptionFactories",
    "public.version_option": f"{_PUBLIC_API}::TestOptionFactories",
    "public.confirmation_option": f"{_PUBLIC_API}::TestOptionFactories",
    "public.password_option": f"{_PUBLIC_API}::TestOptionFactories",
    "public.output_filter_option": f"{_PUBLIC_API}::TestOptionFactories",
    "public.pagination_options": f"{_PUBLIC_API}::TestOptionFactories",
    "public.get_logger": f"{_PUBLIC_API}::TestLogging",
    "public.logger": f"{_PUBLIC_API}::TestLogging",
    "public.add_trace_method": f"{_PUBLIC_API}::TestLogging",
    "public.get_configured_logger": f"{_PUBLIC_API}::TestLogging",
    "public.configure_rich_logging": f"{_PUBLIC_API}::TestLogging",
    "public.RichExtraFormatter": f"{_PUBLIC_API}::TestLogging",
    "public.RichExtraStreamHandler": f"{_PUBLIC_API}::TestLogging",
    "public.SecretsMasker": f"{_PUBLIC_API}::TestLogging",
    "public.PYCLIFER_LOG_LEVELS": f"{_PUBLIC_API}::TestLogging",
    "public.TRACE": f"{_PUBLIC_API}::TestLogging",
    "public.Response": f"{_PUBLIC_API}::TestResponses",
    "public.OperationResult": f"{_PUBLIC_API}::TestResponses",
    "public.PaginatedResponse": f"{_PUBLIC_API}::TestResponses",
    "public.ExitCode": f"{_PUBLIC_API}::TestResponses",
    "public.BaseModel": f"{_PUBLIC_API}::TestResponses",
    "public.BaseInterface": f"{_PUBLIC_API}::TestResponses",
    "public.BaseRenderer": f"{_PUBLIC_API}::TestResponses",
    "public.ResponseRenderer": f"{_PUBLIC_API}::TestResponses",
    "public.CliTable": f"{_PUBLIC_API}::TestTables",
    "public.CliTableColumn": f"{_PUBLIC_API}::TestTables",
    "public.ExceptionTable": f"{_PUBLIC_API}::TestTables",
    "public.BaseContext": f"{_PUBLIC_API}::TestContext",
    "public.OutputFormatMixin": f"{_PUBLIC_API}::TestContext",
    "public.RichHelpersMixin": f"{_PUBLIC_API}::TestContext",
    "public.PycliferOption": f"{_PUBLIC_API}::TestContext",
    "public.CustomConfigOption": f"{_PUBLIC_API}::TestContext",
}

# Feature name -> reason it is not exercised, and why that is acceptable.
EXCLUDED: dict[str, str] = {}

# Item of the spec that will write the scenario -> feature names. Empty: every feature is covered.
PENDING: dict[str, list[str]] = {}
