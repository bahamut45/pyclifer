"""Tests for the timer option integration in app_group."""

import json

import click
from click.testing import CliRunner

from pyclifer.core import app_group
from pyclifer.core.output import Response


def _make_timed_app(output_format_default: str = "raw"):
    """Build a minimal CLI with timer=True for testing."""

    @app_group(
        handle_response=True,
        timer=True,
        output_format_default=output_format_default,
    )
    @click.pass_context
    def app(ctx):
        """Test app with timer."""

    @app.command()
    @click.pass_context
    def run(ctx):
        """Run command."""
        return Response(success=True, message="done", data={"result": "ok"})

    return app


class TestTimerOptionWiring:
    """Tests for app_group timer=True flag."""

    def test_time_flag_appears_in_help(self):
        """--time/--no-time option is present when timer=True."""
        runner = CliRunner()
        result = runner.invoke(_make_timed_app(), ["--help"])
        assert "--time" in result.output

    def test_no_timer_by_default(self):
        """--time/--no-time is absent when timer=False (default)."""

        @app_group(handle_response=True)
        @click.pass_context
        def app(ctx):
            """App without timer."""

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert "--time" not in result.output


class TestTimerRichOutput:
    """Tests for timer display in rich/table/raw output formats."""

    def test_elapsed_time_printed_in_raw_mode(self):
        """Execution time line appears in output when --time is passed in raw mode."""
        runner = CliRunner()
        result = runner.invoke(_make_timed_app(output_format_default="raw"), ["--time", "run"])
        assert "Execution time:" in result.output

    def test_no_elapsed_time_without_flag(self):
        """No execution time line when --time is not passed."""
        runner = CliRunner()
        result = runner.invoke(_make_timed_app(output_format_default="raw"), ["run"])
        assert "Execution time:" not in result.output


class TestTimerJsonOutput:
    """Tests for timer injection in json output format."""

    def test_execution_time_injected_in_json(self):
        """execution_time and execution_time_str are injected in JSON output with --time."""
        runner = CliRunner()
        result = runner.invoke(_make_timed_app(output_format_default="json"), ["--time", "run"])
        payload = json.loads(result.output)
        assert "execution_time" in payload["data"]
        assert "execution_time_str" in payload["data"]
        assert isinstance(payload["data"]["execution_time"], float)

    def test_no_execution_time_in_json_without_flag(self):
        """execution_time is absent from JSON output when --time is not passed."""
        runner = CliRunner()
        result = runner.invoke(_make_timed_app(output_format_default="json"), ["run"])
        payload = json.loads(result.output)
        assert "execution_time" not in payload.get("data", {})

    def test_no_echo_in_json_mode(self):
        """No 'Execution time:' text line is printed in JSON mode."""
        runner = CliRunner()
        result = runner.invoke(_make_timed_app(output_format_default="json"), ["--time", "run"])
        assert "Execution time:" not in result.output
