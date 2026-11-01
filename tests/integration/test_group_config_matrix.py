"""Item 3 of the integration-test-matrix spec: GroupConfig exercised in real applications.

The main axes are run as a full product (48 configurations), every other field, timer included, is
varied one at a time on both help paths. Every expectation below was measured on the code before
being written.
"""

import itertools
import logging
from contextlib import contextmanager

import click
import pytest

from pyclifer import ExitCode, Response
from pyclifer.testing import invoke
from tests.integration.harness import assert_healthy, build_app

AUTOMATIC_OFF = {
    "add_config_option": False,
    "add_verbosity_option": False,
    "add_log_file_option": False,
    "add_version_option": False,
    "add_output_format_option": False,
}
FORMATS = ("json", "yaml", "table", "rich", "raw", "text")
KNOWN_DEFECT = (
    "Measured at item 3: output_format_default is ignored when add_output_format_option is False, "
    "although an unknown command is answered in that format. Fixed by a later item."
)
# The logger that reports an unhandled exception raised by a command.
_UNHANDLED_EXCEPTION_LOGGER = "pyclifer.core.decorators"


class QuotaExitCode(ExitCode):
    """A project exit code on top of the framework ones."""

    QUOTA_EXCEEDED = 10


def _main_axes() -> list[dict]:
    """Full product of the axes that change how an application is built and answers."""
    cases = []
    for rich, automatic, output_format, handle in itertools.product(
        (True, False), ("default", "off"), FORMATS, (True, False)
    ):
        config = {
            "use_rich_help": rich,
            "output_format_default": output_format,
            "handle_response": handle,
        }
        if automatic == "off":
            config.update(AUTOMATIC_OFF)
        cases.append(config)
    return cases


def _single_fields() -> list[dict]:
    """Every other field varied alone, on both help paths."""
    variations = [
        {"timer": True},
        {"name": "custom"},
        {"rich_help_config": "minimal"},
        {"rich_help_config": "verbose"},
        {"use_rich_logging": False},
        {"enable_secrets_filter": False},
        {"sensitive_fields": ["token"]},
        {"unhandled_exception_log_level": "warning"},
        {"unhandled_exception_log_level": "critical"},
        {"exit_codes_class": QuotaExitCode},
        {"auto_envvar_prefix": "MYAPP"},
        {"show_envvar": False},
        {"verbosity_default_level": "DEBUG"},
        {"context_options_panel": "Context"},
    ]
    return [
        {**variation, "use_rich_help": rich} for variation in variations for rich in (True, False)
    ]


def _loses_the_default_format(config: dict) -> bool:
    """Whether the config hits the defect measured at item 3."""
    return (
        not config.get("add_output_format_option", True)
        and config.get("handle_response", True)
        and config.get("output_format_default") in ("json", "yaml")
    )


def _case_id(config: dict) -> str:
    """Readable pytest id built from the config."""
    parts = []
    for key, value in config.items():
        if key == "use_rich_help":
            parts.append("rich" if value else "plain")
        elif key == "handle_response":
            parts.append("response" if value else "noresponse")
        elif key == "timer":
            parts.append("timer" if value else "notimer")
        elif key == "add_config_option":
            parts.append("autooff")
        elif key.startswith("add_"):
            continue
        elif key == "output_format_default":
            parts.append(str(value))
        else:
            parts.append(f"{key}={getattr(value, '__name__', value)}")
    return "-".join(parts)


def _params(cases, *, known_defect=False, only=None):
    """Turn configs into pytest params, marking the known defect and filtering when asked."""
    params = []
    for config in cases:
        if only is not None and not only(config):
            continue
        marks = []
        if known_defect and _loses_the_default_format(config):
            marks.append(pytest.mark.xfail(strict=True, reason=KNOWN_DEFECT))
        params.append(pytest.param(config, id=_case_id(config), marks=marks))
    return params


def _answers_failures_in_a_structured_format(config: dict) -> bool:
    """Whether a failing command is expected to answer in json or yaml."""
    return config["output_format_default"] in ("json", "yaml") and config["handle_response"]


def _has_config_option(config: dict) -> bool:
    """Whether the application exposes --config."""
    return config.get("add_config_option", True)


def _with_failing_command(built):
    """Register a command that raises, to exercise the unhandled exception path."""

    @built.app.command()
    def boom():
        """Fail on purpose."""
        raise RuntimeError("kaboom")

    return built


class _Matrix:
    """Checks shared by the main axes and the single fields."""

    def _check_healthy(self, config):
        assert_healthy(build_app(**config))

    def _check_bare_call(self, config):
        result = invoke(build_app(**config).app, [])

        assert result.exit_code == 2

    def _check_config_file(self, config, tmp_path):
        config_file = tmp_path / "explicit.toml"
        config_file.write_text("[cli]\n")

        result = invoke(build_app(**config).app, ["--config", str(config_file), "hello"])

        assert result.exit_code == 0

    def _check_failing_command_exit_code(self, config):
        result = invoke(_with_failing_command(build_app(**config)).app, ["boom"])

        assert result.exit_code == 1

    def _check_failing_command_answer(self, config):
        output_format = config["output_format_default"]
        result = invoke(_with_failing_command(build_app(**config)).app, ["boom"])

        parsed = result.json if output_format == "json" else result.yaml

        assert parsed["success"] is False
        assert parsed["error_code"] == 1


class TestMainAxes(_Matrix):
    """Full product of use_rich_help, automatic options, output format, response handling, timer."""

    @pytest.mark.parametrize("config", _params(_main_axes(), known_defect=True))
    def test_application_is_healthy(self, config):
        self._check_healthy(config)

    @pytest.mark.parametrize("config", _params(_main_axes()))
    def test_bare_call_shows_the_help_with_exit_code_two(self, config):
        self._check_bare_call(config)

    @pytest.mark.parametrize("config", _params(_main_axes(), only=_has_config_option))
    def test_explicit_config_file_loads(self, config, tmp_path):
        self._check_config_file(config, tmp_path)

    @pytest.mark.parametrize("config", _params(_main_axes()))
    def test_failing_command_exits_with_one(self, config):
        self._check_failing_command_exit_code(config)

    @pytest.mark.parametrize(
        "config",
        _params(_main_axes(), known_defect=True, only=_answers_failures_in_a_structured_format),
    )
    def test_failing_command_answers_in_the_default_structured_format(self, config):
        self._check_failing_command_answer(config)


class TestSingleFields(_Matrix):
    """Every other GroupConfig field varied alone, with the same checks."""

    @pytest.mark.parametrize("config", _params(_single_fields()))
    def test_application_is_healthy(self, config):
        self._check_healthy(config)

    @pytest.mark.parametrize("config", _params(_single_fields()))
    def test_bare_call_shows_the_help_with_exit_code_two(self, config):
        self._check_bare_call(config)

    @pytest.mark.parametrize("config", _params(_single_fields(), only=_has_config_option))
    def test_explicit_config_file_loads(self, config, tmp_path):
        self._check_config_file(config, tmp_path)

    @pytest.mark.parametrize("config", _params(_single_fields()))
    def test_failing_command_exits_with_one(self, config):
        self._check_failing_command_exit_code(config)


@contextmanager
def _logged_levels():
    """Collect the level names of the records emitted by the unhandled exception logger."""
    levels = []

    class Collector(logging.Handler):
        def emit(self, record):
            levels.append(record.levelname)

    logger = logging.getLogger(_UNHANDLED_EXCEPTION_LOGGER)
    handler = Collector()
    logger.addHandler(handler)
    try:
        yield levels
    finally:
        logger.removeHandler(handler)


class TestFieldEffects:
    """Fields whose effect can be observed directly."""

    @pytest.mark.parametrize("rich", [True, False])
    def test_name_sets_the_application_name(self, rich):
        built = build_app(name="custom", use_rich_help=rich)

        assert built.app.name == "custom"
        assert "custom" in invoke(built.app, ["--help"]).output

    @pytest.mark.parametrize("level", ["error", "warning", "critical"])
    def test_unhandled_exception_log_level_sets_the_record_level(self, level):
        built = _with_failing_command(build_app(unhandled_exception_log_level=level))

        with _logged_levels() as levels:
            invoke(built.app, ["boom"])

        assert levels == [level.upper()]

    def test_exit_codes_class_provides_the_exit_code_of_a_response(self):
        built = build_app(exit_codes_class=QuotaExitCode)

        @built.app.command()
        def quota():
            """Exceed the quota."""
            return Response(success=False, message="no", error_code=QuotaExitCode.QUOTA_EXCEEDED)

        assert invoke(built.app, ["quota"]).exit_code == 10

    def test_exit_codes_class_must_subclass_exit_code(self):
        with pytest.raises(ValueError, match="must be a subclass of ExitCode"):
            build_app(exit_codes_class=int)

    @pytest.mark.parametrize("rich_help_config", ["default", "minimal", "verbose"])
    def test_every_rich_help_configuration_renders_the_help(self, rich_help_config):
        built = build_app(rich_help_config=rich_help_config)

        assert invoke(built.app, ["--help"]).exit_code == 0

    def test_a_click_command_added_by_the_user_keeps_working(self):
        built = build_app()
        built.app.add_command(click.Command("plain", callback=lambda: click.echo("plain")))

        assert "plain" in invoke(built.app, ["plain"]).output
