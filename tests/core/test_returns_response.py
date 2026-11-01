"""Tests for the returns_response decorator and command/group handle_response support."""

from unittest.mock import patch

import click

from pyclifer.core import app_group, command, group, option, output_filter_option, returns_response
from pyclifer.core.output import Response
from pyclifer.core.output.exit_codes import ExitCode
from pyclifer.core.output.renderer import BaseRenderer
from pyclifer.testing import invoke

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(handle_response_at_group=False, output_format_default="raw"):
    """Build a minimal CLI for testing."""

    @app_group(
        handle_response=handle_response_at_group,
        output_format_default=output_format_default,
    )
    @click.pass_context
    def app(ctx):
        """Test app"""

    return app


# ---------------------------------------------------------------------------
# returns_response decorator
# ---------------------------------------------------------------------------


class TestReturnsResponseDecorator:
    """Tests for the standalone @returns_response decorator."""

    def test_response_is_printed_with_raw_format_by_default(self):
        """When output_format_default='raw', response message appears in output."""
        app = _make_app(output_format_default="raw")

        @app.command()
        @returns_response
        @click.pass_context
        def greet(ctx):
            """Greet"""
            return Response(success=True, message="hello", data={"key": "value"})

        result = invoke(app, ["greet"])
        assert result.exit_code == 0
        assert "hello" in result.output

    def test_response_is_printed_with_json_format(self):
        """When --output-format json is passed, response is serialized as JSON."""
        app = _make_app(output_format_default="raw")

        @app.command()
        @returns_response
        @click.pass_context
        def greet(ctx):
            """Greet"""
            return Response(success=True, message="hello", data={"key": "value"})

        result = invoke(app, ["-o", "json", "greet"])
        assert result.exit_code == 0
        assert '"message"' in result.output
        assert '"hello"' in result.output

    def test_non_response_return_value_is_not_affected(self):
        """A command returning a plain string is not intercepted."""
        app = _make_app()

        @app.command()
        @returns_response
        @click.pass_context
        def greet(ctx):
            """Greet"""
            click.echo("plain output")
            return "plain string"

        result = invoke(app, ["greet"])
        assert result.exit_code == 0
        assert "plain output" in result.output

    def test_none_return_value_is_not_affected(self):
        """A command returning None (implicit) is not intercepted."""
        app = _make_app()

        @app.command()
        @returns_response
        @click.pass_context
        def greet(ctx):
            """Greet"""
            click.echo("done")

        result = invoke(app, ["greet"])
        assert result.exit_code == 0
        assert "done" in result.output


# ---------------------------------------------------------------------------
# @command(handle_response=True) — standalone decorator
# ---------------------------------------------------------------------------


class TestCommandHandleResponse:
    """Tests for @command(handle_response=True) used with add_command."""

    def test_response_printed_via_command_decorator(self):
        """A standalone command with handle_response=True prints its Response."""
        app = _make_app(output_format_default="raw")

        @command(handle_response=True)
        @option("--name", default="world")
        @click.pass_context
        def greet(ctx, name):
            """Greet"""
            return Response(success=True, message=f"Hello {name}", data={"name": name})

        app.add_command(greet)

        result = invoke(app, ["greet", "--name", "Alice"])
        assert result.exit_code == 0
        assert "Hello Alice" in result.output

    def test_handle_response_false_does_not_intercept(self):
        """A command with handle_response=False (default) does not intercept returns."""
        app = _make_app()

        @command(handle_response=False)
        @click.pass_context
        def greet(ctx):
            """Greet"""
            click.echo("explicit echo")
            return Response(success=True, message="ignored")

        app.add_command(greet)

        result = invoke(app, ["greet"])
        assert result.exit_code == 0
        assert "explicit echo" in result.output
        assert "ignored" not in result.output


# ---------------------------------------------------------------------------
# @app_group(handle_response=True) — group-level default
# ---------------------------------------------------------------------------


class TestGroupHandleResponse:
    """Tests for handle_response propagation from @app_group."""

    def test_all_commands_inherit_group_default(self):
        """Commands registered on a group with handle_response=True auto-dispatch."""
        app = _make_app(handle_response_at_group=True, output_format_default="raw")

        @app.command()
        @click.pass_context
        def greet(ctx):
            """Greet"""
            return Response(success=True, message="from group default", data={})

        result = invoke(app, ["greet"])
        assert result.exit_code == 0
        assert "from group default" in result.output

    def test_per_command_override_disables_group_default(self):
        """A command with handle_response=False overrides the group default."""
        app = _make_app(handle_response_at_group=True)

        @app.command(handle_response=False)
        @click.pass_context
        def greet(ctx):
            """Greet"""
            click.echo("manual output")
            return Response(success=True, message="should not appear")

        result = invoke(app, ["greet"])
        assert result.exit_code == 0
        assert "manual output" in result.output
        assert "should not appear" not in result.output

    def test_group_default_false_does_not_intercept(self):
        """When handle_response=False (default) on the group, no interception occurs."""
        app = _make_app(handle_response_at_group=False)

        @app.command()
        @click.pass_context
        def greet(ctx):
            """Greet"""
            click.echo("raw")
            return Response(success=True, message="not printed")

        result = invoke(app, ["greet"])
        assert result.exit_code == 0
        assert "raw" in result.output
        assert "not printed" not in result.output

    def test_add_command_inherits_group_default(self):
        """Commands added via add_command() respect handle_response_by_default."""
        app = _make_app(handle_response_at_group=True, output_format_default="raw")

        @command()
        @click.pass_context
        def status(ctx):
            """Status"""
            return Response(success=True, message="via add_command", data={})

        app.add_command(status)

        result = invoke(app, ["status"])
        assert result.exit_code == 0
        assert "via add_command" in result.output

    def test_add_command_group_default_false_does_not_intercept(self):
        """Commands added via add_command() are not wrapped when group default is False."""
        app = _make_app(handle_response_at_group=False)

        @command()
        @click.pass_context
        def status(ctx):
            """Status"""
            click.echo("manual")
            return Response(success=True, message="not printed")

        app.add_command(status)

        result = invoke(app, ["status"])
        assert result.exit_code == 0
        assert "manual" in result.output
        assert "not printed" not in result.output

    def test_add_command_subgroup_propagates_to_leaf_commands(self):
        """handle_response propagates into a sub-group added via add_command()."""
        app = _make_app(handle_response_at_group=True, output_format_default="raw")

        @group()
        @click.pass_context
        def storage(ctx):
            """Storage sub-group"""

        @command()
        @click.pass_context
        def status(ctx):
            """Status"""
            return Response(success=True, message="from subgroup", data={})

        storage.add_command(status)
        app.add_command(storage)

        result = invoke(app, ["storage", "status"])
        assert result.exit_code == 0
        assert "from subgroup" in result.output

    def test_add_command_subgroup_nested_does_not_double_wrap(self):
        """Leaf commands already wrapped with returns_response are not wrapped again."""
        app = _make_app(handle_response_at_group=True, output_format_default="raw")

        call_count = {"n": 0}

        @group()
        @click.pass_context
        def storage(ctx):
            """Storage sub-group"""

        @command()
        @click.pass_context
        def status(ctx):
            """Status"""
            call_count["n"] += 1
            return Response(success=True, message="once", data={})

        storage.add_command(status)
        app.add_command(storage)

        result = invoke(app, ["storage", "status"])
        assert result.exit_code == 0
        assert result.output.count("once") == 1
        assert call_count["n"] == 1


# ---------------------------------------------------------------------------
# output_filter_option decorator
# ---------------------------------------------------------------------------


class TestOutputFilterOption:
    """Tests for the @output_filter_option() decorator."""

    def test_filter_extracts_key_from_response_data(self):
        """--output-filter extracts a single key from response data."""
        app = _make_app(output_format_default="raw")

        @app.command()
        @output_filter_option()
        @returns_response
        @click.pass_context
        def greet(ctx):
            """Greet"""
            return Response(
                success=True,
                message="Hello",
                data={"message": "Hello", "status": "ok"},
            )

        result = invoke(app, ["greet", "--output-filter", "message"])
        assert result.exit_code == 0
        assert "Hello" in result.output
        assert "status" not in result.output

    def test_filter_short_flag(self):
        """Short flag -f works identically to --output-filter."""
        app = _make_app(output_format_default="raw")

        @app.command()
        @output_filter_option()
        @returns_response
        @click.pass_context
        def greet(ctx):
            """Greet"""
            return Response(
                success=True,
                message="Hello",
                data={"message": "Hello", "status": "ok"},
            )

        result = invoke(app, ["greet", "-f", "status"])
        assert result.exit_code == 0
        assert "ok" in result.output
        assert "message" not in result.output

    def test_no_filter_returns_full_response(self):
        """Without --output-filter, the full response is printed."""
        app = _make_app(output_format_default="raw")

        @app.command()
        @output_filter_option()
        @returns_response
        @click.pass_context
        def greet(ctx):
            """Greet"""
            return Response(
                success=True,
                message="Hello",
                data={"message": "Hello", "status": "ok"},
            )

        result = invoke(app, ["greet"])
        assert result.exit_code == 0
        assert "Hello" in result.output
        assert "ok" in result.output

    def test_filter_missing_key_exits_with_error(self):
        """Filtering a non-existent key prints an error and exits with code 2."""

        app = _make_app(output_format_default="raw")

        @app.command()
        @output_filter_option()
        @returns_response
        @click.pass_context
        def greet(ctx):
            """Greet"""
            return Response(
                success=True,
                message="Hello",
                data={"message": "Hello"},
            )

        result = invoke(app, ["greet", "-f", "nonexistent"])
        assert result.exit_code == 2
        assert "nonexistent" in result.output


# ---------------------------------------------------------------------------
# Last resort handler
# ---------------------------------------------------------------------------


class TestLastResortHandler:
    """Tests for the unhandled exception handler in returns_response."""

    def test_unhandled_exception_returns_failed_response(self):
        """An exception escaping a command is caught and returned as a failed Response."""
        app = _make_app(handle_response_at_group=True, output_format_default="raw")

        @app.command()
        @click.pass_context
        def boom(ctx):
            """Raise unexpectedly"""
            raise RuntimeError("something broke")

        result = invoke(app, ["boom"])
        assert result.exit_code == 1
        assert "something broke" in result.output

    def test_unhandled_exception_log_level_stored_in_meta(self):
        """unhandled_exception_log_level is stored in ctx.meta at root context creation."""
        captured = {}

        @app_group(
            handle_response=True,
            output_format_default="raw",
            unhandled_exception_log_level="warning",
        )
        @click.pass_context
        def app(ctx):
            """Test app"""

        @app.command()
        @click.pass_context
        def probe(ctx):
            """Capture meta"""
            root = ctx
            while root.parent:
                root = root.parent
            captured["level"] = root.meta.get("pyclifer.unhandled_exception_log_level")

        invoke(app, ["probe"])
        assert captured["level"] == "warning"

    def test_output_format_respected_on_unhandled_exception(self):
        """Even on unhandled exception, JSON output format is respected."""
        app = _make_app(handle_response_at_group=True, output_format_default="json")

        @app.command()
        @click.pass_context
        def boom(ctx):
            """Raise unexpectedly"""
            raise ValueError("bad input")

        result = invoke(app, ["boom"])
        assert result.exit_code == 1
        assert '"success"' in result.output

    def test_exception_without_click_context_returns_failed_response(self):
        """Exception handler works when there is no active click context (lines 327→330)."""
        from pyclifer.core.output.responses import Response

        @returns_response
        def boom():
            raise RuntimeError("no ctx")

        result = boom()
        assert isinstance(result, Response)
        assert result.success is False
        assert "no ctx" in result.message

    def test_response_without_click_context_does_not_crash(self):
        """Response path works without an active click context (lines 352→360)."""
        from pyclifer.core.output.responses import Response

        @returns_response
        def succeed():
            return Response(success=True, message="hi")

        result = succeed()
        assert isinstance(result, Response)
        assert result.success is True
        assert result.message == "hi"

    def test_unhandled_exception_carries_exit_code_error(self):
        """An unhandled exception response carries ExitCode.ERROR as its error_code."""
        from pyclifer.core.output.responses import Response

        @returns_response
        def boom():
            raise RuntimeError("explodes")

        result = boom()
        assert isinstance(result, Response)
        assert result.error_code == ExitCode.ERROR


# ---------------------------------------------------------------------------
# ctx.exit integration
# ---------------------------------------------------------------------------


class TestCtxExitIntegration:
    """Tests for OS exit code propagation via ctx.exit()."""

    def test_failed_response_exits_with_error_code(self):
        """A failed Response causes the process to exit with its error_code."""
        app = _make_app(handle_response_at_group=True, output_format_default="raw")

        @app.command()
        @click.pass_context
        def fail(ctx):
            """Fail"""
            return Response(success=False, message="nope", error_code=ExitCode.NOT_FOUND)

        result = invoke(app, ["fail"])
        assert result.exit_code == ExitCode.NOT_FOUND

    def test_successful_response_does_not_call_ctx_exit(self):
        """A successful Response leaves the exit code at 0."""
        app = _make_app(handle_response_at_group=True, output_format_default="raw")

        @app.command()
        @click.pass_context
        def succeed(ctx):
            """Succeed"""
            return Response(success=True, message="ok")

        result = invoke(app, ["succeed"])
        assert result.exit_code == 0

    def test_exit_codes_class_stored_in_ctx_meta(self):
        """exit_codes_class registered via @app_group is stored in ctx.meta."""
        captured = {}

        class MyExitCode(ExitCode):
            QUOTA_EXCEEDED = 10

        @app_group(
            exit_codes_class=MyExitCode,
            handle_response=True,
            output_format_default="raw",
        )
        @click.pass_context
        def app(ctx):
            """Test app"""

        @app.command()
        @click.pass_context
        def probe(ctx):
            """Capture meta"""
            root = ctx
            while root.parent:
                root = root.parent
            captured["cls"] = root.meta.get("pyclifer.exit_codes_class")

        invoke(app, ["probe"])
        assert captured["cls"] is MyExitCode

    def test_default_exit_codes_class_is_base_exit_code(self):
        """When no exit_codes_class is provided, the ExitCode base class is stored in ctx.meta."""
        captured = {}

        @app_group(handle_response=True, output_format_default="raw")
        @click.pass_context
        def app(ctx):
            """Test app"""

        @app.command()
        @click.pass_context
        def probe(ctx):
            """Capture meta"""
            root = ctx
            while root.parent:
                root = root.parent
            captured["cls"] = root.meta.get("pyclifer.exit_codes_class")

        invoke(app, ["probe"])
        assert captured["cls"] is ExitCode


# ---------------------------------------------------------------------------
# Traceback suppression in structured output modes
# ---------------------------------------------------------------------------


def _unhandled_log_call(mock_log):
    """Extract the single _log.log() call for an unhandled exception, or None."""
    matches = [c for c in mock_log.log.call_args_list if "Unhandled exception" in str(c)]
    return matches[0] if matches else None


class TestTracebackSuppression:
    """Tests for exc_info suppression when output format is json or yaml."""

    def test_returns_response_suppresses_traceback_in_json_mode(self):
        """Exception in JSON mode at WARNING level emits exc_info=False."""
        app = _make_app(handle_response_at_group=True, output_format_default="json")

        @app.command()
        @click.pass_context
        def boom(ctx):
            """Raise unexpectedly"""
            raise KeyError("some_field")

        with patch("pyclifer.core.decorators._log") as mock_log:
            mock_log.isEnabledFor.return_value = False
            invoke(app, ["boom"])
            call = _unhandled_log_call(mock_log)
            assert call is not None, "Expected a log call for unhandled exception"
            _, kwargs = call
            assert kwargs.get("exc_info") is False

    def test_returns_response_keeps_traceback_in_table_mode(self):
        """Exception in table mode emits exc_info=True regardless of verbosity."""
        app = _make_app(handle_response_at_group=True, output_format_default="table")

        @app.command()
        @click.pass_context
        def boom(ctx):
            """Raise unexpectedly"""
            raise RuntimeError("broken")

        with patch("pyclifer.core.decorators._log") as mock_log:
            mock_log.isEnabledFor.return_value = False
            invoke(app, ["boom"])
            call = _unhandled_log_call(mock_log)
            assert call is not None
            _, kwargs = call
            assert kwargs.get("exc_info") is True

    def test_returns_response_debug_verbosity_restores_traceback_in_json_mode(self):
        """Exception in JSON mode with logger at DEBUG level emits exc_info=True."""
        app = _make_app(handle_response_at_group=True, output_format_default="json")

        @app.command()
        @click.pass_context
        def boom(ctx):
            """Raise unexpectedly"""
            raise RuntimeError("broken")

        with patch("pyclifer.core.decorators._log") as mock_log:
            mock_log.isEnabledFor.return_value = True  # DEBUG enabled
            invoke(app, ["boom"])
            call = _unhandled_log_call(mock_log)
            assert call is not None
            _, kwargs = call
            assert kwargs.get("exc_info") is True

    def test_returns_response_trace_verbosity_restores_traceback_in_json_mode(self):
        """Exception in JSON mode with logger at TRACE (5) emits exc_info=True."""
        app = _make_app(handle_response_at_group=True, output_format_default="json")

        @app.command()
        @click.pass_context
        def boom(ctx):
            """Raise unexpectedly"""
            raise RuntimeError("broken")

        with patch("pyclifer.core.decorators._log") as mock_log:
            # TRACE=5, isEnabledFor(DEBUG=10) returns True when effective level <= 10
            mock_log.isEnabledFor.side_effect = lambda level: level >= 5
            invoke(app, ["boom"])
            call = _unhandled_log_call(mock_log)
            assert call is not None
            _, kwargs = call
            assert kwargs.get("exc_info") is True


def _raise(error):
    """Raise error, so a lambda can raise."""
    raise error


class TestClickControlFlow:
    """Click errors and exits raised in a command keep Click's own handling."""

    @staticmethod
    def _run(raiser, *, handle_response):
        """Invoke a command that calls raiser(ctx), on an app with the given handle_response."""
        app = _make_app(handle_response_at_group=handle_response)

        @app.command()
        @click.pass_context
        def act(ctx):
            """Raise what the test asks for"""
            raiser(ctx)

        return invoke(app, ["act"])

    def test_bad_parameter_exits_with_usage_code(self):
        """BadParameter exits with code 2 and is not logged as unhandled."""
        result = self._run(lambda ctx: _raise(click.BadParameter("nope")), handle_response=True)
        assert result.exit_code == 2
        assert "Unhandled exception" not in result.stderr
        assert "nope" in result.stderr

    def test_usage_error_exits_with_usage_code(self):
        """UsageError exits with code 2 and is not logged as unhandled."""
        result = self._run(lambda ctx: _raise(click.UsageError("bad use")), handle_response=True)
        assert result.exit_code == 2
        assert "Unhandled exception" not in result.stderr

    def test_click_exception_exits_with_its_own_code(self):
        """ClickException exits with code 1, prints its message, and is not logged as unhandled."""
        result = self._run(lambda ctx: _raise(click.ClickException("boom")), handle_response=True)
        assert result.exit_code == 1
        assert "boom" in result.stderr
        assert "Unhandled exception" not in result.stderr

    def test_abort_prints_aborted(self):
        """Abort prints Aborted. on stderr and is not logged as unhandled."""
        result = self._run(lambda ctx: _raise(click.Abort()), handle_response=True)
        assert result.exit_code == 1
        assert "Aborted." in result.stderr
        assert "Unhandled exception" not in result.stderr

    def test_ctx_exit_keeps_the_requested_code(self):
        """ctx.exit(3) exits with 3 instead of being turned into a failure."""
        result = self._run(lambda ctx: ctx.exit(3), handle_response=True)
        assert result.exit_code == 3
        assert "Unhandled exception" not in result.stderr

    def test_ctx_exit_zero_succeeds(self):
        """ctx.exit(0) exits with 0."""
        result = self._run(lambda ctx: ctx.exit(0), handle_response=True)
        assert result.exit_code == 0
        assert "Unhandled exception" not in result.stderr

    def test_handling_is_identical_without_handle_response(self):
        """The same errors give the same exit codes when handle_response is off."""
        with_handling = self._run(
            lambda ctx: _raise(click.BadParameter("nope")), handle_response=True
        )
        without_handling = self._run(
            lambda ctx: _raise(click.BadParameter("nope")), handle_response=False
        )
        assert with_handling.exit_code == without_handling.exit_code

    def test_bad_parameter_in_json_is_a_usage_error_response(self):
        """In a structured format, an error from the command body gets the usage_error schema."""
        app = _make_app(handle_response_at_group=True, output_format_default="json")

        @app.command()
        def act():
            """Raise a usage problem"""
            raise click.BadParameter("nope")

        result = invoke(app, ["act"])
        assert result.exit_code == 2
        assert result.json["success"] is False
        assert result.json["data"]["error_type"] == "usage_error"


class _BrokenRenderer(BaseRenderer):
    """Renderer whose output methods fail, like a user renderer with a bug."""

    fields = ["item"]
    columns = ["item"]

    def serialize(self, response):
        raise RuntimeError("serialize broke")

    def table(self, response):
        raise RuntimeError("table broke")


class TestRenderFailure:
    """An exception raised while rendering is answered like one raised by the command."""

    @staticmethod
    def _run(output_format, data=None, **config):
        app = _make_app(handle_response_at_group=True, output_format_default=output_format)

        @app.command()
        def show():
            """Return a response rendered by a broken renderer"""
            return Response(
                success=True,
                message="m",
                data={} if data is None else data,
                renderer=_BrokenRenderer(),
            )

        return invoke(app, ["show"])

    def test_json_gets_a_failure_response_on_stdout(self):
        result = self._run("json")
        assert result.exit_code == ExitCode.ERROR
        assert result.json["success"] is False
        assert "serialize broke" in result.json["message"]
        assert result.json["error_code"] == ExitCode.ERROR

    def test_yaml_gets_a_failure_response_on_stdout(self):
        result = self._run("yaml")
        assert result.exit_code == ExitCode.ERROR
        assert result.yaml["success"] is False
        assert "serialize broke" in result.yaml["message"]

    def test_json_stderr_has_the_log_line_without_a_traceback(self):
        result = self._run("json")
        assert "Unhandled exception" in result.stderr
        assert "Traceback" not in result.stderr

    def test_table_logs_the_traceback_and_exits_with_error(self):
        result = self._run("table")
        assert result.exit_code == ExitCode.ERROR
        assert "table broke" in result.stderr
        assert "Unhandled exception" in result.stderr

    def test_log_line_says_the_failure_happened_while_rendering(self):
        result = self._run("json")
        assert "rendering" in result.stderr

    def test_list_data_is_a_json_failure_response_naming_the_fix(self):
        app = _make_app(handle_response_at_group=True, output_format_default="json")

        class Items(BaseRenderer):
            fields = ["item"]

        @app.command()
        def show():
            """Return list data to a renderer that reads results"""
            return Response(success=True, message="m", data=[1], renderer=Items())

        result = invoke(app, ["show"])
        assert result.exit_code == ExitCode.ERROR
        assert "'results'" in result.json["message"]

    def test_a_working_renderer_is_unaffected(self):
        app = _make_app(handle_response_at_group=True, output_format_default="json")

        @app.command()
        def show():
            """Return a normal response"""
            return Response(success=True, message="ok", data={"results": []})

        result = invoke(app, ["show"])
        assert result.exit_code == 0
        assert result.json["success"] is True

    def test_click_errors_raised_while_rendering_keep_click_handling(self):
        class Refusing(BaseRenderer):
            fields = ["item"]

            def serialize(self, response):
                raise click.UsageError("render refused")

        app = _make_app(handle_response_at_group=True, output_format_default="json")

        @app.command()
        def show():
            """Return a response whose renderer raises a Click error"""
            return Response(success=True, message="m", data={}, renderer=Refusing())

        result = invoke(app, ["show"])
        assert result.exit_code == 2
        assert "Unhandled exception" not in result.stderr
