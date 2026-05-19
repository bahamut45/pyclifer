"""Tests for the returns_response decorator and command/group handle_response support."""

import click
from click.testing import CliRunner

from pyclif.core import app_group, command, group, option, output_filter_option, returns_response
from pyclif.core.output import Response

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

        runner = CliRunner()
        result = runner.invoke(app, ["greet"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["-o", "json", "greet"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["greet"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["greet"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["greet", "--name", "Alice"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["greet"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["greet"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["greet"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["greet"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["status"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["status"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["storage", "status"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["storage", "status"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["greet", "--output-filter", "message"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["greet", "-f", "status"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["greet"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["greet", "-f", "nonexistent"])
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

        runner = CliRunner()
        result = runner.invoke(app, ["boom"])
        assert result.exit_code == 0
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
            captured["level"] = root.meta.get("pyclif.unhandled_exception_log_level")

        runner = CliRunner()
        runner.invoke(app, ["probe"])
        assert captured["level"] == "warning"

    def test_output_format_respected_on_unhandled_exception(self):
        """Even on unhandled exception, JSON output format is respected."""
        app = _make_app(handle_response_at_group=True, output_format_default="json")

        @app.command()
        @click.pass_context
        def boom(ctx):
            """Raise unexpectedly"""
            raise ValueError("bad input")

        runner = CliRunner()
        result = runner.invoke(app, ["boom"])
        assert result.exit_code == 0
        assert '"success"' in result.output

    def test_exception_without_click_context_returns_failed_response(self):
        """Exception handler works when there is no active click context (lines 327→330)."""
        from pyclif.core.output.responses import Response

        @returns_response
        def boom():
            raise RuntimeError("no ctx")

        result = boom()
        assert isinstance(result, Response)
        assert result.success is False
        assert "no ctx" in result.message

    def test_response_without_click_context_does_not_crash(self):
        """Response path works without an active click context (lines 352→360)."""
        from pyclif.core.output.responses import Response

        @returns_response
        def succeed():
            return Response(success=True, message="hi")

        result = succeed()
        assert isinstance(result, Response)
        assert result.success is True
        assert result.message == "hi"
