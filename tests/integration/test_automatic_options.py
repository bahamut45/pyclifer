"""Item 4 of the integration-test-matrix spec: the effect of every automatic option.

Each expectation was measured on the code before being written, in a fresh process whenever
the global logging state could change the answer. A strict xfail records a defect found by that
measurement; it must be removed by the item that fixes it.
"""

import io
import logging
import logging.handlers

import click_extra
import pytest
from click.testing import CliRunner

from pyclifer import app_group, get_logger, option
from pyclifer.core import decorators
from pyclifer.core.log.handlers import RichExtraStreamHandler
from pyclifer.core.output import Response
from pyclifer.testing import invoke

LEVELS = ("DEBUG-LINE", "INFO-LINE", "WARNING-LINE", "ERROR-LINE")


def _app(**config):
    """An app named cli whose hello command logs one line per level and returns a Response."""

    @app_group(**{"output_format_default": "json", **config})
    def cli():
        """Test application."""

    @cli.command()
    @option("--name", default="World")
    def hello(name):
        """Say hello."""
        log = get_logger("probe")
        log.debug("DEBUG-LINE")
        log.info("INFO-LINE")
        log.warning("WARNING-LINE")
        log.error("ERROR-LINE")
        return Response(success=True, message=f"hello {name}")

    return cli


def _logged(result) -> set[str]:
    """The probe lines that reached the console."""
    return {line for line in LEVELS if line in result.stderr}


class TestVersionOption:
    """--version prints the version of the application."""

    def test_prints_the_declared_version(self):
        result = invoke(_app(version="1.2.3"), ["--version"])

        assert result.exit_code == 0
        assert "cli, version 1.2.3" in result.output


class TestVerbosityOption:
    """--verbosity sets the console log level."""

    def test_warning_is_the_default_level(self):
        assert _logged(invoke(_app(), ["hello"])) == {"WARNING-LINE", "ERROR-LINE"}

    @pytest.mark.parametrize(
        ("level", "expected"),
        [
            ("DEBUG", {"DEBUG-LINE", "INFO-LINE", "WARNING-LINE", "ERROR-LINE"}),
            ("INFO", {"INFO-LINE", "WARNING-LINE", "ERROR-LINE"}),
        ],
    )
    def test_a_more_verbose_level_shows_more(self, level, expected):
        assert _logged(invoke(_app(), ["--verbosity", level, "hello"])) == expected

    def test_the_option_is_accepted_after_the_subcommand(self):
        result = invoke(_app(), ["hello", "--verbosity", "INFO"])

        assert "INFO-LINE" in _logged(result)

    def test_an_invalid_level_exits_with_two(self):
        assert invoke(_app(), ["--verbosity", "BOGUS", "hello"]).exit_code == 2

    def test_verbosity_default_level_changes_the_default(self):
        result = invoke(_app(verbosity_default_level="DEBUG"), ["hello"])

        assert "DEBUG-LINE" in _logged(result)

    def test_the_environment_variable_sets_the_level(self):
        result = invoke(_app(), ["hello"], env={"CLI_VERBOSITY": "DEBUG"})

        assert "DEBUG-LINE" in _logged(result)

    @pytest.mark.parametrize("level", ["ERROR", "CRITICAL"])
    def test_a_stricter_level_than_the_default_hides_warnings(self, level):
        result = invoke(_app(), ["--verbosity", level, "hello"])

        assert "WARNING-LINE" not in _logged(result)

    def test_a_stricter_level_after_the_subcommand_hides_warnings(self):
        result = invoke(_app(), ["hello", "--verbosity", "ERROR"])

        assert _logged(result) == {"ERROR-LINE"}

    def test_a_stricter_level_from_the_environment_hides_warnings(self):
        result = invoke(_app(), ["hello"], env={"CLI_VERBOSITY": "ERROR"})

        assert "WARNING-LINE" not in _logged(result)

    def test_an_error_default_is_kept_when_nothing_is_chosen(self):
        result = invoke(_app(verbosity_default_level="ERROR"), ["hello"])

        assert _logged(result) == {"ERROR-LINE"}


class TestRichLogging:
    """use_rich_logging chooses the console handler; records reach the console either way."""

    @pytest.mark.parametrize("use_rich_logging", [True, False])
    def test_a_warning_reaches_the_console(self, use_rich_logging):
        result = invoke(_app(use_rich_logging=use_rich_logging), ["hello"])

        assert "WARNING-LINE" in _logged(result)

    def test_false_does_not_install_the_rich_handler(self):
        logging.getLogger().handlers.clear()

        invoke(_app(use_rich_logging=False), ["hello"])

        handlers = logging.getLogger().handlers
        assert not any(isinstance(handler, RichExtraStreamHandler) for handler in handlers)

    def test_false_writes_plain_lines_without_a_timestamp(self):
        result = invoke(_app(use_rich_logging=False), ["hello"])

        assert "warning: WARNING-LINE" in result.stderr
        assert "[" not in result.stderr.split("WARNING-LINE")[0]

    @pytest.mark.parametrize("level", ["DEBUG", "ERROR"])
    def test_false_still_follows_the_verbosity_level(self, level):
        result = invoke(_app(use_rich_logging=False), ["--verbosity", level, "hello"])

        assert ("DEBUG-LINE" in _logged(result)) == (level == "DEBUG")
        assert ("WARNING-LINE" in _logged(result)) == (level == "DEBUG")

    def test_false_still_masks_secrets(self, tmp_path):
        console, _ = _log_with_secrets(
            tmp_path, use_rich_logging=False, sensitive_fields=["mycode"]
        )

        assert "hunter2" not in console
        assert "mc-777" not in console
        assert "bob" in console

    def test_false_still_writes_the_log_file(self, tmp_path):
        log_file = tmp_path / "app.log"

        invoke(_app(use_rich_logging=False), ["--log-file", str(log_file), "hello"])

        assert "WARNING-LINE" in log_file.read_text()


def _rotating_handlers() -> list[logging.handlers.TimedRotatingFileHandler]:
    """Every rotating file handler attached to any logger, each counted once.

    One handler object is attached to several loggers, so handlers are told apart by identity.
    """
    loggers = [logging.getLogger()] + [
        logging.getLogger(name) for name in list(logging.root.manager.loggerDict)
    ]
    unique = {
        id(handler): handler
        for logger in loggers
        for handler in logger.handlers
        if isinstance(handler, logging.handlers.TimedRotatingFileHandler)
    }
    return list(unique.values())


class TestLogFileOption:
    """--log-file writes the records to a rotating file."""

    def test_the_file_receives_the_records(self, tmp_path):
        log_file = tmp_path / "app.log"

        invoke(_app(), ["--log-file", str(log_file), "hello"])

        assert "WARNING-LINE" in log_file.read_text()

    def test_the_file_level_is_independent_of_the_console(self, tmp_path):
        log_file = tmp_path / "app.log"

        result = invoke(_app(), ["--log-file", str(log_file), "hello"])

        assert "DEBUG-LINE" not in _logged(result)
        assert "DEBUG-LINE" in log_file.read_text()

    def test_log_file_default_level_filters_the_file(self, tmp_path):
        log_file = tmp_path / "app.log"

        invoke(_app(log_file_default_level="ERROR"), ["--log-file", str(log_file), "hello"])

        content = log_file.read_text()
        assert "ERROR-LINE" in content
        assert "WARNING-LINE" not in content

    def test_rotation_settings_reach_the_file_handler(self, tmp_path):
        config = {
            "log_file_rotation_when": "H",
            "log_file_rotation_interval": 3,
            "log_file_rotation_backup_count": 9,
        }

        invoke(_app(**config), ["--log-file", str(tmp_path / "app.log"), "hello"])

        assert [(h.when, h.interval, h.backupCount) for h in _rotating_handlers()] == [
            ("H", 3 * 3600, 9)
        ]


class TestConfigOption:
    """--config turns the values of a file into defaults."""

    @staticmethod
    def _config_file(tmp_path):
        config_file = tmp_path / "app.toml"
        config_file.write_text('[cli.hello]\nname = "FromConfig"\n')
        return config_file

    def test_a_value_in_the_file_becomes_the_default(self, tmp_path):
        result = invoke(_app(), ["--config", str(self._config_file(tmp_path)), "hello"])

        assert result.json["message"] == "hello FromConfig"

    def test_an_explicit_argument_wins_over_the_file(self, tmp_path):
        args = ["--config", str(self._config_file(tmp_path)), "hello", "--name", "Cli"]

        assert invoke(_app(), args).json["message"] == "hello Cli"


class TestOutputFormatOption:
    """--output-format picks how the answer is rendered."""

    @pytest.mark.parametrize("flag", ["-o", "--output-format"])
    def test_the_option_overrides_the_default(self, flag):
        result = invoke(_app(output_format_default="table"), [flag, "yaml", "hello"])

        assert result.yaml["success"] is True

    def test_the_environment_variable_picks_the_format(self):
        result = invoke(
            _app(output_format_default="table"), ["hello"], env={"CLI_OUTPUT_FORMAT": "json"}
        )

        assert result.json["success"] is True

    def test_an_invalid_format_exits_with_two(self):
        assert invoke(_app(), ["-o", "xml", "hello"]).exit_code == 2


class TestTimerOption:
    """timer adds --time, which reports the execution time."""

    def test_the_time_is_added_to_structured_data(self):
        result = invoke(_app(timer=True), ["--time", "hello"])

        assert {"execution_time", "execution_time_str"} <= set(result.json["data"])

    def test_nothing_is_added_without_the_flag(self):
        assert invoke(_app(timer=True), ["hello"]).json["data"] == {}

    def test_the_time_is_printed_in_table_format(self):
        result = invoke(_app(timer=True, output_format_default="table"), ["--time", "hello"])

        assert "Execution time:" in result.output


class TestEnvironmentVariables:
    """Options read an environment variable named after the application."""

    def test_the_help_shows_the_variable(self):
        assert "CLI_VERBOSITY" in invoke(_app(), ["--help"]).output

    def test_auto_envvar_prefix_renames_the_variables(self):
        app = _app(auto_envvar_prefix="MYAPP")

        assert "MYAPP_VERBOSITY" in invoke(app, ["--help"]).output

    def test_a_prefixed_variable_drives_the_option(self):
        app = _app(auto_envvar_prefix="MYAPP", output_format_default="table")

        result = invoke(app, ["hello"], env={"MYAPP_OUTPUT_FORMAT": "yaml"})

        assert result.yaml["success"] is True

    ENV_VARS = ("CLI_OUTPUT_FORMAT", "CLI_CONFIG", "CLI_VERBOSITY", "CLI_LOG_FILE")

    @pytest.mark.parametrize("env_var", ENV_VARS)
    def test_the_help_shows_every_variable_by_default(self, env_var):
        assert env_var in invoke(_app(), ["--help"]).output.replace("\n", "")

    @pytest.mark.parametrize("env_var", ENV_VARS)
    def test_show_envvar_false_hides_the_variables(self, env_var):
        assert env_var not in invoke(_app(show_envvar=False), ["--help"]).output.replace("\n", "")

    def test_show_envvar_false_leaves_no_variable_in_the_help_at_all(self):
        assert "env var" not in invoke(_app(show_envvar=False, timer=True), ["--help"]).output


def _log_with_secrets(tmp_path, **config):
    """Log a dict holding two secrets and one plain value, to the console and to a file."""

    @app_group(**{"output_format_default": "json", **config})
    def cli():
        """Test application."""

    @cli.command()
    def hello():
        """Log secrets."""
        get_logger("probe").warning(
            "payload %s", {"password": "hunter2", "mycode": "mc-777", "user": "bob"}
        )
        return Response(success=True, message="ok")

    log_file = tmp_path / "secrets.log"
    result = invoke(cli, ["--log-file", str(log_file), "hello"])
    return result.stderr, log_file.read_text()


class TestSecretsFiltering:
    """Records are redacted by key name, in the console and in the file."""

    def test_a_default_sensitive_field_is_masked(self, tmp_path):
        console, file = _log_with_secrets(tmp_path)

        assert "hunter2" not in console
        assert "hunter2" not in file

    def test_a_plain_value_is_kept(self, tmp_path):
        console, file = _log_with_secrets(tmp_path)

        assert "bob" in console
        assert "bob" in file

    def test_a_custom_sensitive_field_is_masked(self, tmp_path):
        console, file = _log_with_secrets(tmp_path, sensitive_fields=["mycode"])

        assert "mc-777" not in console
        assert "mc-777" not in file

    def test_disabling_the_filter_shows_the_values(self, tmp_path):
        console, file = _log_with_secrets(tmp_path, enable_secrets_filter=False)

        assert "hunter2" in console
        assert "hunter2" in file


def _log_free_text(tmp_path, *args, **config):
    """Log a plain message holding two secrets as key=value, to the console and to a file."""

    @app_group(**{"output_format_default": "json", **config})
    def cli():
        """Test application."""

    @cli.command()
    def hello():
        """Log a message."""
        get_logger("probe").warning("login password=hunter2 mycode=mc-777 for bob")
        return Response(success=True, message="ok")

    log_file = tmp_path / "free.log"
    result = invoke(cli, ["--log-file", str(log_file), *args, "hello"])
    return result.stderr, log_file.read_text()


class TestFreeTextMasking:
    """mask_free_text hides key=value secrets written inside a message, on every path."""

    # Without the verbosity option rebuilding the console handler, and with it.
    PATHS = [(), ("--verbosity", "DEBUG")]

    @pytest.mark.parametrize("use_rich_logging", [True, False])
    @pytest.mark.parametrize("args", PATHS)
    def test_the_secrets_are_masked_on_the_console_and_in_the_file(
        self, tmp_path, use_rich_logging, args
    ):
        console, file = _log_free_text(
            tmp_path,
            *args,
            mask_free_text=True,
            sensitive_fields=["mycode"],
            use_rich_logging=use_rich_logging,
        )

        for output in (console, file):
            assert "hunter2" not in output
            assert "mc-777" not in output
            assert "bob" in output

    @pytest.mark.parametrize("use_rich_logging", [True, False])
    def test_without_the_option_free_text_is_kept(self, tmp_path, use_rich_logging):
        console, file = _log_free_text(tmp_path, use_rich_logging=use_rich_logging)

        assert "password=hunter2" in console
        assert "password=hunter2" in file

    @pytest.mark.parametrize("use_rich_logging", [True, False])
    def test_the_file_masks_by_itself_when_the_console_never_sees_the_record(
        self, tmp_path, use_rich_logging
    ):
        """A record below the console level skips its filters, so the file must mask it itself."""
        console, file = _log_free_text(
            tmp_path,
            "--verbosity",
            "ERROR",
            mask_free_text=True,
            use_rich_logging=use_rich_logging,
        )

        assert "login" not in console
        assert "login" in file
        assert "hunter2" not in file

    def test_the_option_does_nothing_when_the_filter_is_off(self, tmp_path):
        console, file = _log_free_text(tmp_path, mask_free_text=True, enable_secrets_filter=False)

        assert "hunter2" in console
        assert "hunter2" in file

    def test_it_applies_without_a_verbosity_option(self, tmp_path):
        console, _ = _log_free_text(tmp_path, mask_free_text=True, add_verbosity_option=False)

        assert "hunter2" not in console


class _ThirdPartyHandler(logging.StreamHandler):
    """A handler another library put on the root logger, a StreamHandler subclass like caplog's."""


def _declare_after_a_third_party_handler(**config):
    """Put a foreign handler on the root logger, then declare an application that logs."""
    foreign = _ThirdPartyHandler(io.StringIO())
    logging.getLogger().addHandler(foreign)

    @app_group(**{"output_format_default": "json", **config})
    def cli():
        """Test application."""

    @cli.command()
    def hello():
        """Log a message."""
        get_logger("probe").warning("probe message")
        return Response(success=True, message="ok")

    return cli, foreign


def _with_format(handler, fmt, datefmt=None):
    """Give a handler a formatter of its own."""
    handler.setFormatter(logging.Formatter(fmt, datefmt))
    return handler


class TestReplaceRootHandlers:
    """pyclifer replaces only its own console handler, unless replace_root_handlers is set."""

    @pytest.mark.parametrize("use_rich_logging", [True, False])
    def test_a_foreign_handler_survives_the_declaration(self, use_rich_logging):
        _, foreign = _declare_after_a_third_party_handler(use_rich_logging=use_rich_logging)

        assert foreign in logging.getLogger().handlers

    @pytest.mark.parametrize("use_rich_logging", [True, False])
    def test_a_foreign_handler_survives_the_verbosity_option_and_keeps_receiving(
        self, use_rich_logging
    ):
        cli, foreign = _declare_after_a_third_party_handler(use_rich_logging=use_rich_logging)

        result = invoke(cli, ["--verbosity", "DEBUG", "hello"])

        assert foreign in logging.getLogger().handlers
        assert "probe message" in foreign.stream.getvalue()
        assert result.stderr.count("probe message") == 1

    @pytest.mark.parametrize("use_rich_logging", [True, False])
    def test_the_console_is_written_once_by_default(self, use_rich_logging):
        cli, _ = _declare_after_a_third_party_handler(use_rich_logging=use_rich_logging)

        result = invoke(cli, ["hello"])

        assert result.stderr.count("probe message") == 1

    @pytest.mark.parametrize("use_rich_logging", [True, False])
    def test_the_console_handler_of_logging_basic_config_is_replaced(self, use_rich_logging):
        """A StreamHandler on stderr, what logging.basicConfig() installs, is a console too.

        Kept, it would write each record a second time, without the secrets filter.
        """
        logging.basicConfig(force=True)
        basic = logging.getLogger().handlers[0]

        cli, _ = _declare_after_a_third_party_handler(use_rich_logging=use_rich_logging)
        assert basic not in logging.getLogger().handlers

        invoke(cli, ["--verbosity", "DEBUG", "hello"])

        assert basic not in logging.getLogger().handlers

    @pytest.mark.parametrize("use_rich_logging", [True, False])
    @pytest.mark.parametrize(
        "make_handler",
        [
            lambda: logging.StreamHandler(),
            lambda: _with_format(logging.StreamHandler(), "%(message)s"),
            lambda: _with_format(logging.StreamHandler(), logging.BASIC_FORMAT, datefmt="%H:%M"),
        ],
        ids=["no-formatter", "own-format", "own-date-format"],
    )
    def test_a_stream_handler_written_by_hand_is_kept(self, use_rich_logging, make_handler):
        """A StreamHandler on stderr that nobody got from basicConfig() is the user's own."""
        mine = make_handler()
        logging.getLogger().addHandler(mine)

        _declare_after_a_third_party_handler(use_rich_logging=use_rich_logging)

        assert mine in logging.getLogger().handlers

    @pytest.mark.parametrize("use_rich_logging", [True, False])
    def test_a_stream_handler_on_another_stream_is_kept(self, use_rich_logging):
        other = logging.StreamHandler(io.StringIO())
        logging.getLogger().addHandler(other)

        _declare_after_a_third_party_handler(use_rich_logging=use_rich_logging)

        assert other in logging.getLogger().handlers

    @pytest.mark.parametrize("use_rich_logging", [True, False])
    def test_replace_root_handlers_removes_the_foreign_handler(self, use_rich_logging):
        cli, foreign = _declare_after_a_third_party_handler(
            use_rich_logging=use_rich_logging, replace_root_handlers=True
        )
        assert foreign not in logging.getLogger().handlers

        invoke(cli, ["--verbosity", "DEBUG", "hello"])

        assert foreign not in logging.getLogger().handlers
        assert "probe message" not in foreign.stream.getvalue()


def _plain_command(factory, args):
    """Run a command that carries a single option factory, outside any app_group."""

    @click_extra.command(params=[])
    @factory
    def cmd(**kwargs):
        """Command under test."""
        click_extra.echo("RAN")

    return CliRunner().invoke(cmd, ["--help"]), CliRunner().invoke(cmd, args)


class TestOptionFactories:
    """Each option factory works on a command of its own, without app_group."""

    @pytest.mark.parametrize(
        ("factory", "args"),
        [
            (decorators.option("--x", default="1"), ["--x", "2"]),
            (decorators.verbosity_option(), ["--verbosity", "DEBUG"]),
            (decorators.output_format_option(), ["-o", "json"]),
            (decorators.output_filter_option(), ["--output-filter", "data"]),
            (decorators.pagination_options(), []),
        ],
        ids=[
            "option",
            "verbosity_option",
            "output_format_option",
            "output_filter_option",
            "pagination_options",
        ],
    )
    def test_the_factory_renders_help_and_runs(self, factory, args):
        help_result, run_result = _plain_command(factory, args)

        assert help_result.exit_code == 0
        assert run_result.exit_code == 0

    def test_config_option_loads_a_file(self, tmp_path):
        config_file = tmp_path / "app.toml"
        config_file.write_text("[cmd]\n")

        _, result = _plain_command(decorators.config_option(), ["--config", str(config_file)])

        assert result.exit_code == 0
        assert "Load configuration matching" in result.stderr + result.output

    def test_log_file_option_writes_a_file(self, tmp_path):
        log_file = tmp_path / "plain.log"

        _, result = _plain_command(decorators.log_file_option(), ["--log-file", str(log_file)])

        assert result.exit_code == 0
        assert log_file.exists()
