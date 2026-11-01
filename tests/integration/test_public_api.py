"""Item 6 of the integration-test-matrix spec: every symbol of pyclifer.__all__ in a real app.

Each class below builds a small application and drives it from the command line, so a symbol is
checked where a user meets it: imported from pyclifer, declared in a command, run. Expectations
were measured on the code before being written, in a fresh process.
"""

import datetime
import logging
import uuid

import click
import pytest
import yaml
from rich.console import Console

import pyclifer
from pyclifer import (
    BOOL,
    FLOAT,
    INT,
    STRING,
    UUID,
    Abort,
    BadParameter,
    BaseContext,
    BaseInterface,
    BaseModel,
    BaseRenderer,
    Choice,
    ClickException,
    ClickPath,
    CliTable,
    CliTableColumn,
    CustomConfigOption,
    DateTime,
    ExceptionTable,
    ExitCode,
    File,
    FloatRange,
    IntRange,
    OperationResult,
    OutputFormatMixin,
    PaginatedResponse,
    PycliferOption,
    Response,
    ResponseRenderer,
    RichExtraFormatter,
    RichExtraStreamHandler,
    RichHelpersMixin,
    SecretsMasker,
    TimerOption,
    Tuple,
    UsageError,
    app_group,
    argument,
    command,
    confirm,
    confirmation_option,
    echo,
    get_configured_logger,
    get_current_context,
    get_logger,
    group,
    make_pass_decorator,
    option,
    output_filter_option,
    pagination_options,
    pass_context,
    pass_obj,
    password_option,
    prompt,
    returns_response,
    secho,
    style,
    unstyle,
    version_option,
)
from pyclifer.testing import invoke

PUBLIC_SYMBOLS = [name for name in pyclifer.__all__ if not name.startswith("__")]


class TestPublicSurface:
    """Every name in __all__ can be imported and is not None."""

    @pytest.mark.parametrize("name", PUBLIC_SYMBOLS)
    def test_symbol_is_importable_from_the_package(self, name):
        namespace: dict = {}
        exec(f"from pyclifer import {name}", namespace)  # noqa: S102 - fixed names from __all__
        assert namespace[name] is not None

    def test_dunder_metadata_is_exported(self):
        assert pyclifer.__version__
        assert pyclifer.__app_name__ == "pyclifer"


class TestDecorators:
    """The decorators, argument, the pass_* helpers and get_current_context."""

    @staticmethod
    def _build():
        class Ctx(BaseContext):
            """Context built by the root callback."""

        pass_ctx = make_pass_decorator(Ctx, ensure=True)

        @app_group(name="cli", handle_response=False)
        @pass_context
        def cli(ctx):
            """Application."""
            ctx.obj = Ctx()

        @group()
        def ops():
            """A subgroup made with the group decorator."""

        @ops.command()
        @argument("name")
        @option("--times", type=INT, default=1)
        def hello(name, times):
            """Say hello."""
            echo(" ".join([f"hello {name}"] * times))

        @command()
        @pass_obj
        def whoami(obj):
            """A command made with the command decorator, added after its creation."""
            echo(f"obj={type(obj).__name__}")

        @command()
        @pass_ctx
        def made(obj):
            """A command using make_pass_decorator."""
            echo(f"made={type(obj).__name__}")

        @command()
        @pass_context
        def current(ctx):
            """A command comparing pass_context with get_current_context."""
            echo(f"same={get_current_context() is ctx}")

        @command()
        @returns_response
        def answer():
            """A command returning a Response through returns_response."""
            return Response(success=True, message="answered", data={"k": "v"})

        cli.add_command(ops)
        for added in (whoami, made, current, answer):
            cli.add_command(added)
        return cli

    def test_group_command_argument_and_option_run(self):
        result = invoke(self._build(), ["ops", "hello", "ada", "--times", "2"])
        assert result.exit_code == 0
        assert result.output.strip() == "hello ada hello ada"

    def test_pass_obj_gives_the_object_set_by_the_root(self):
        result = invoke(self._build(), ["whoami"])
        assert result.output.strip() == "obj=Ctx"

    def test_make_pass_decorator_gives_the_typed_context(self):
        result = invoke(self._build(), ["made"])
        assert result.output.strip() == "made=Ctx"

    def test_get_current_context_is_the_context_passed_by_pass_context(self):
        result = invoke(self._build(), ["current"])
        assert result.output.strip() == "same=True"

    def test_returns_response_prints_the_response_in_the_requested_format(self):
        result = invoke(self._build(), ["--output-format", "json", "answer"])
        assert result.exit_code == 0
        assert result.json["message"] == "answered"
        assert result.json["data"] == {"k": "v"}

    def test_missing_argument_is_a_usage_error(self):
        result = invoke(self._build(), ["ops", "hello"])
        assert result.exit_code == 2


class TestClickTypes:
    """The re-exported Click parameter types convert, and reject, values from the command line."""

    @staticmethod
    def _app(param_type, nargs=None):
        @app_group(name="cli", handle_response=False)
        def cli():
            """Application."""

        kwargs = {} if nargs is None else {"nargs": nargs}

        @cli.command()
        @option("--value", type=param_type, default=None, **kwargs)
        def show(value):
            """Print the converted value."""
            echo(value.read() if hasattr(value, "read") else repr(value))

        return cli

    def test_accepted_values_are_converted(self, tmp_path):
        existing = tmp_path / "data.txt"
        existing.write_text("content")
        identifier = uuid.UUID(int=1)
        cases = [
            (INT, ["3"], "3"),
            (FLOAT, ["2.5"], "2.5"),
            (BOOL, ["true"], "True"),
            (STRING, ["text"], "'text'"),
            (UUID, [str(identifier)], repr(identifier)),
            (DateTime(["%Y-%m-%d"]), ["2026-01-02"], repr(datetime.datetime(2026, 1, 2))),
            (Choice(["a", "b"]), ["b"], "'b'"),
            (Tuple([INT, STRING]), ["1", "z"], "(1, 'z')"),
            (IntRange(1, 5), ["3"], "3"),
            (FloatRange(0, 1), ["0.2"], "0.2"),
            (ClickPath(exists=True), [str(existing)], repr(str(existing))),
            (File("r"), [str(existing)], "content"),
        ]
        for param_type, values, expected in cases:
            app = self._app(param_type)
            result = invoke(app, ["show", "--value", *values])
            assert result.exit_code == 0, f"{param_type!r}: {result.exception!r}"
            assert result.output.strip() == expected, f"{param_type!r}"

    def test_rejected_values_are_usage_errors(self, tmp_path):
        missing = str(tmp_path / "missing.txt")
        cases = [
            (INT, "abc"),
            (FLOAT, "abc"),
            (BOOL, "maybe"),
            (UUID, "nope"),
            (DateTime(["%Y-%m-%d"]), "yesterday"),
            (Choice(["a", "b"]), "zz"),
            (IntRange(1, 5), "9"),
            (FloatRange(0, 1), "2"),
            (ClickPath(exists=True), missing),
            (File("r"), missing),
        ]
        for param_type, bad in cases:
            result = invoke(self._app(param_type), ["show", "--value", bad])
            assert result.exit_code == 2, f"{param_type!r} accepted {bad!r}"

    def test_a_type_is_shown_in_the_help(self):
        result = invoke(self._app(Choice(["alpha", "beta"])), ["show", "--help"])
        assert result.exit_code == 0
        assert "alpha" in result.output
        assert "beta" in result.output


class TestTerminalInput:
    """echo, secho, style, unstyle, confirm and prompt, run in a command."""

    @staticmethod
    def _app():
        @app_group(name="cli", handle_response=False)
        def cli():
            """Application."""

        @cli.command()
        def talk():
            """Print styled text and ask two questions."""
            echo("plain")
            secho("colored", fg="green")
            echo(unstyle(style("styled", fg="red", bold=True)))
            echo(f"confirmed={confirm('Sure?')} name={prompt('Name')}")

        return cli

    def test_output_functions_and_prompts_work_together(self):
        result = invoke(self._app(), ["talk"], input="y\nada\n")
        assert result.exit_code == 0
        assert "plain" in result.output
        assert "colored" in result.output
        assert "styled" in result.output
        assert "confirmed=True name=ada" in result.output

    def test_unstyle_removes_what_style_adds(self):
        styled = style("text", fg="red")
        assert styled != "text"
        assert unstyle(styled) == "text"

    def test_answering_no_is_returned_as_false(self):
        result = invoke(self._app(), ["talk"], input="n\nada\n")
        assert "confirmed=False" in result.output


class TestClickErrors:
    """Click errors give the same exit codes with and without handle_response."""

    @staticmethod
    def _app(handle_response):
        @app_group(name="cli", handle_response=handle_response)
        def cli():
            """Application."""

        @cli.command()
        def failure():
            """Raise a ClickException."""
            raise ClickException("boom")

        @cli.command()
        def parameter():
            """Raise a BadParameter."""
            raise BadParameter("nope")

        @cli.command()
        def usage():
            """Raise a UsageError."""
            raise UsageError("misused")

        @cli.command()
        def abort():
            """Raise an Abort."""
            raise Abort()

        return cli

    EXPECTED_EXIT_CODES = {"failure": 1, "parameter": 2, "usage": 2, "abort": 1}

    @pytest.mark.parametrize("handle_response", [True, False])
    @pytest.mark.parametrize("name", sorted(EXPECTED_EXIT_CODES))
    def test_exit_code_is_the_one_click_chooses(self, name, handle_response):
        result = invoke(self._app(handle_response), [name])
        assert result.exit_code == self.EXPECTED_EXIT_CODES[name]
        assert "Unhandled exception" not in result.stderr

    def test_abort_prints_aborted(self):
        result = invoke(self._app(True), ["abort"])
        assert "Aborted." in result.stderr

    def test_message_reaches_the_user(self):
        result = invoke(self._app(True), ["failure"])
        assert "boom" in result.stderr


class TestOptionFactories:
    """The option factories that are not on by default, and the timer."""

    def test_version_option_prints_the_given_version(self):
        @app_group(name="cli", handle_response=False, add_version_option=False)
        @version_option(version="9.9")
        def cli():
            """Application."""

        result = invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert result.output.strip() == "cli, version 9.9"

    def test_confirmation_option_skips_the_question_with_yes(self):
        @app_group(name="cli", handle_response=False)
        def cli():
            """Application."""

        @cli.command()
        @confirmation_option()
        def drop():
            """Do something dangerous."""
            echo("dropped")

        assert "dropped" in invoke(cli, ["drop", "--yes"]).output
        refused = invoke(cli, ["drop"], input="n\n")
        assert refused.exit_code == 1
        assert "dropped" not in refused.output

    def test_password_option_prompts_and_confirms(self):
        @app_group(name="cli", handle_response=False)
        def cli():
            """Application."""

        @cli.command()
        @password_option()
        def login(password):
            """Receive a password."""
            echo(f"length={len(password)}")

        result = invoke(cli, ["login"], input="secret\nsecret\n")
        assert result.exit_code == 0
        assert "length=6" in result.output

    def test_pagination_options_limit_the_range(self):
        @app_group(name="cli", handle_response=False)
        def cli():
            """Application."""

        @cli.command()
        @pagination_options(default_limit=2, max_limit=3)
        @pass_context
        def listing(ctx):
            """Print the pagination values."""
            echo(f"page={ctx.meta['pyclifer.page']} limit={ctx.meta['pyclifer.limit']}")

        assert "page=1 limit=2" in invoke(cli, ["listing"]).output
        assert "page=4 limit=3" in invoke(cli, ["listing", "--page", "4", "--limit", "3"]).output
        assert invoke(cli, ["listing", "--limit", "9"]).exit_code == 2

    def test_output_filter_option_is_offered_by_the_command(self):
        @app_group(name="cli", handle_response=True)
        def cli():
            """Application."""

        @cli.command()
        @output_filter_option()
        @returns_response
        def listing():
            """Return a response."""
            return Response(success=True, message="m", data={"results": [{"name": "a"}]})

        result = invoke(cli, ["listing", "--help"])
        assert result.exit_code == 0
        assert "--output-filter" in result.output

    def test_timer_option_class_works_through_option(self):
        @app_group(name="cli", handle_response=False)
        @option("--stopwatch/--no-stopwatch", cls=TimerOption, default=False)
        def cli(**kwargs):
            """Application."""

        @cli.command()
        def work():
            """Do nothing."""
            echo("done")

        result = invoke(cli, ["--stopwatch", "work"])
        assert result.exit_code == 0, result.exception
        assert "Execution time" in result.output

    def test_timer_option_prints_the_execution_time(self):
        @app_group(name="cli", handle_response=False, timer=True)
        def cli():
            """Application."""

        @cli.command()
        def work():
            """Do nothing."""
            echo("done")

        result = invoke(cli, ["--time", "work"])
        assert result.exit_code == 0
        assert "Execution time" in result.output


class TestLogging:
    """get_logger, logger, get_configured_logger, TRACE and the secrets filter, from a command."""

    @staticmethod
    def _app(**config):
        @app_group(name="cli", handle_response=False, **config)
        def cli():
            """Application."""

        @cli.command()
        def logs():
            """Log at every level."""
            named = get_logger("cli.part")
            named.trace("trace-line")
            named.debug("debug-line")
            named.info("info-line token=abc123")
            pyclifer.logger.warning("package-line")
            get_configured_logger("cli.other").info("configured-line")

        return cli

    def test_trace_verbosity_shows_every_level(self):
        result = invoke(self._app(), ["--verbosity", "TRACE", "logs"])
        assert result.exit_code == 0
        for line in ("trace-line", "debug-line", "info-line", "package-line", "configured-line"):
            assert line in result.stderr, line

    def test_info_verbosity_hides_trace_and_debug(self):
        result = invoke(self._app(), ["--verbosity", "INFO", "logs"])
        assert "trace-line" not in result.stderr
        assert "debug-line" not in result.stderr
        assert "info-line" in result.stderr

    def test_sensitive_values_are_masked_in_log_lines(self):
        app = self._app(sensitive_fields=["token"], mask_free_text=True)
        result = invoke(app, ["--verbosity", "INFO", "logs"])
        assert "abc123" not in result.stderr
        assert "token=*CENSORED*" in result.stderr

    def test_levels_include_trace_below_debug(self):
        assert pyclifer.TRACE == 5
        assert pyclifer.PYCLIFER_LOG_LEVELS["TRACE"] == pyclifer.TRACE
        assert pyclifer.PYCLIFER_LOG_LEVELS["TRACE"] < pyclifer.PYCLIFER_LOG_LEVELS["DEBUG"]

    def test_add_trace_method_gives_a_class_a_trace_method(self):
        class CustomLogger(logging.Logger):
            """A logger class without a trace method of its own."""

        assert pyclifer.add_trace_method(CustomLogger) is CustomLogger
        assert callable(CustomLogger("probe").trace)

    def test_configure_rich_logging_is_callable_with_its_documented_options(self):
        pyclifer.configure_rich_logging(use_rich=False, enable_secrets_filter=False)
        pyclifer.configure_rich_logging(use_rich=True, sensitive_fields=["token"])

    def test_formatter_formats_a_trace_record(self):
        record = logging.LogRecord("n", pyclifer.TRACE, "f", 1, "value %s", ("x",), None)
        assert "value x" in RichExtraFormatter().format(record)

    def test_stream_handler_is_a_logging_handler(self):
        handler = RichExtraStreamHandler()
        assert isinstance(handler, logging.Handler)

    def test_secrets_masker_masks_sensitive_keys_and_free_text(self):
        masker = SecretsMasker(sensitive_fields=["token"], mask_free_text=True)
        assert masker.redact("secret", "token") == "*CENSORED*"
        assert masker.redact_text("token=abc x") == "token=*CENSORED* x"


class TestResponses:
    """Responses, results, interfaces and renderers, through the output formats."""

    class ItemRenderer(BaseRenderer):
        """Renderer with declared fields."""

        fields = ["item", "message"]
        columns = ["item", "message"]
        rich_title = "Things"
        success_message = "all good"
        failure_message = "some failed"

    class ItemInterface(BaseInterface):
        """Interface whose methods all use ItemRenderer."""

        renderer_class = None  # set below, once ItemRenderer exists

        def good(self):
            """Return two successful results."""
            return [OperationResult.ok("a", message="m1"), OperationResult.ok("b", message="m2")]

        def mixed(self):
            """Return one success and one failure."""
            return [OperationResult.ok("a"), OperationResult.error("b", "bad")]

    ItemInterface.renderer_class = ItemRenderer

    class Item(BaseModel):
        """A pydantic model built on the public BaseModel."""

        name: str = "x"

    @classmethod
    def _app(cls):
        @app_group(name="cli", handle_response=True)
        def cli():
            """Application."""

        @cli.command()
        def good():
            """Answer with successful results."""
            return cls.ItemInterface(None).respond("good")

        @cli.command()
        def mixed():
            """Answer with a failing result."""
            return cls.ItemInterface(None).respond("mixed")

        @cli.command()
        def page():
            """Answer with a paginated response."""
            return PaginatedResponse(
                success=True,
                message="pg",
                data={"results": [{"a": 1}]},
                page=2,
                limit=1,
                total=5,
            )

        return cli

    @pytest.mark.parametrize("output_format", ["table", "json", "yaml", "rich", "raw"])
    def test_interface_answers_in_every_format(self, output_format):
        result = invoke(self._app(), ["--output-format", output_format, "good"])
        assert result.exit_code == 0
        assert result.output.strip()

    def test_json_follows_the_renderer_fields(self):
        parsed = invoke(self._app(), ["--output-format", "json", "good"]).json
        assert parsed["success"] is True
        assert parsed["message"] == "all good"
        assert [row["item"] for row in parsed["data"]["results"]] == ["a", "b"]

    def test_yaml_is_readable_by_a_safe_parser(self):
        result = invoke(self._app(), ["--output-format", "yaml", "good"])
        assert yaml.safe_load(result.output)["data"]["results"][0]["item"] == "a"

    def test_yaml_is_readable_without_a_renderer(self):
        @app_group(name="cli", handle_response=True)
        def cli():
            """Application."""

        @cli.command()
        def plain():
            """Answer from results, with no renderer."""
            return Response.from_results(
                [OperationResult.ok("a")], success_message="s", failure_message="f"
            )

        result = invoke(cli, ["--output-format", "yaml", "plain"])
        assert "!!python" not in result.output
        assert yaml.safe_load(result.output)["data"]["results"][0]["item"] == "a"

    def test_a_failed_result_exits_with_the_error_code(self):
        result = invoke(self._app(), ["--output-format", "json", "mixed"])
        assert result.exit_code == ExitCode.ERROR
        assert result.json["success"] is False
        assert result.json["message"] == "some failed"

    def test_paginated_response_adds_a_pagination_block(self):
        parsed = invoke(self._app(), ["--output-format", "json", "page"]).json
        assert parsed["pagination"] == {"page": 2, "limit": 1, "total": 5}

    def test_exit_codes_are_distinct_named_integers(self):
        assert ExitCode.SUCCESS == 0
        assert ExitCode.ERROR == 1
        assert ExitCode.USAGE_ERROR == 2

    def test_operation_result_constructors_set_the_success_flag(self):
        assert OperationResult.ok("a").success is True
        failed = OperationResult.error("b", "bad")
        assert failed.success is False
        assert failed.error_code == ExitCode.ERROR

    def test_base_model_is_a_pydantic_model(self):
        assert self.Item(name="y").model_dump() == {"name": "y"}

    def test_base_renderer_has_every_method_of_the_protocol(self):
        protocol_methods = [
            name
            for name, member in vars(ResponseRenderer).items()
            if callable(member) and not name.startswith("_")
        ]
        assert protocol_methods
        for name in protocol_methods:
            assert callable(getattr(BaseRenderer, name, None)), name


class TestTables:
    """CliTable, CliTableColumn and ExceptionTable render through Rich."""

    @staticmethod
    def _render(renderable) -> str:
        console = Console(width=60, record=True, file=open("/dev/null", "w"))  # noqa: SIM115
        console.print(renderable)
        return console.export_text()

    def test_cli_table_renders_its_rows(self):
        table = CliTable(
            fields={"name": CliTableColumn(header="Name")}, rows=[{"name": "ada"}, {"name": "bob"}]
        )
        text = self._render(table)
        assert "Name" in text
        assert "ada" in text
        assert "bob" in text

    def test_cli_table_without_rows_says_so(self):
        table = CliTable(fields={"name": CliTableColumn(header="Name")}, rows=[])
        assert "No dataset available." in self._render(table)

    def test_exception_table_shows_code_message_and_traceback(self):
        table = ExceptionTable({"error_code": 7, "message": "broken", "data": "trace text"})
        text = self._render(table)
        for expected in ("Error", "Message", "Traceback", "7", "broken", "trace text"):
            assert expected in text, expected


class TestContext:
    """BaseContext, OutputFormatMixin, RichHelpersMixin, PycliferOption and CustomConfigOption."""

    @staticmethod
    def _app(config_file=None):
        class Ctx(BaseContext):
            """Context built by the root callback."""

        @app_group(name="cli", handle_response=False)
        @option("--region", default="us", is_global=True)
        @pass_context
        def cli(ctx, region):
            """Application."""
            ctx.obj = Ctx()

        @cli.command()
        @pass_obj
        def helpers(obj, region):
            """Use the Rich helpers of the context."""
            obj.display_rule("Title")
            panel = obj.rich_panel("body", title="P")
            obj.rich_panel("direct", console_print=True)
            echo(f"panel={type(panel).__name__}")
            echo(f"ask={obj.ask_user('Name?', default='z')} sure={obj.ask_confirmation('Sure?')}")
            with obj.show_status("working") as status:
                echo(f"status={type(status).__name__}")

        @cli.command()
        @pass_context
        def where(ctx, region):
            """Print the region the root received."""
            echo(f"region={ctx.find_root().params['region']}")

        return cli

    def test_base_context_combines_both_mixins(self):
        assert issubclass(BaseContext, RichHelpersMixin)
        assert issubclass(BaseContext, OutputFormatMixin)

    def test_rich_helpers_work_inside_a_command(self):
        result = invoke(self._app(), ["helpers"], input="bob\ny\n")
        assert result.exit_code == 0
        assert "Title" in result.output
        assert "direct" in result.output
        assert "panel=Panel" in result.output
        assert "ask=bob sure=True" in result.output
        assert "status=Status" in result.output

    def test_rich_helpers_use_their_defaults_on_empty_answers(self):
        result = invoke(self._app(), ["helpers"], input="\n\n")
        assert "ask=z sure=False" in result.output

    def test_option_is_a_pycliferoption(self):
        cli = self._app()
        region = next(param for param in cli.params if param.name == "region")
        assert isinstance(region, PycliferOption)

    def test_config_file_supplies_option_values(self, tmp_path):
        config = tmp_path / "cli.toml"
        config.write_text('[cli]\nregion = "eu"\n')
        result = invoke(self._app(), ["--config", str(config), "where"])
        assert result.exit_code == 0
        assert "region=eu" in result.output

    def test_command_line_beats_the_config_file(self, tmp_path):
        config = tmp_path / "cli.toml"
        config.write_text('[cli]\nregion = "eu"\n')
        result = invoke(self._app(), ["--config", str(config), "--region", "ap", "where"])
        assert "region=ap" in result.output

    def test_config_option_is_a_custom_config_option(self):
        config_param = next(param for param in self._app().params if param.name == "config")
        assert isinstance(config_param, CustomConfigOption)

    def test_output_format_mixin_prints_a_result(self, capsys):
        context = BaseContext()
        context.output_format = "json"
        context.print_result_based_on_format(Response(success=True, message="hi"))
        assert '"message": "hi"' in capsys.readouterr().out


def test_click_is_still_the_engine_behind_the_exported_exceptions():
    """The exceptions re-exported by pyclifer are Click's own, so except clauses interoperate."""
    assert issubclass(BadParameter, click.ClickException)
    assert issubclass(UsageError, click.ClickException)
    assert issubclass(ClickException, click.ClickException)
    assert issubclass(Abort, click.Abort)
