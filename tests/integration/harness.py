"""Scenario harness: build a real pyclifer application, then check that it works."""

import warnings
from dataclasses import dataclass
from typing import Any

import click

from pyclifer import Response, app_group
from pyclifer.testing import invoke

# app_group turns these on by default; the matching option name is what Click exposes.
AUTOMATIC_OPTIONS = {
    "add_config_option": "config",
    "add_verbosity_option": "verbosity",
    "add_log_file_option": "log_file",
    "add_version_option": "version",
    "add_output_format_option": "output_format",
}
UNKNOWN_COMMAND = "nosuchcommand"


@dataclass
class BuiltApp:
    """An application under test, its build config and the warnings raised while building it."""

    app: click.Group
    config: dict[str, Any]
    warnings: list[warnings.WarningMessage]


def build_app(**config: Any) -> BuiltApp:
    """Build an app_group named cli with one command, recording any warning raised while doing so.

    Args:
        **config: The keyword arguments given to app_group.

    Returns:
        The application, the config it was built with and the warnings caught during construction.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        @app_group(**config)
        def cli():
            """Test application."""

        @cli.command()
        def hello():
            """Say hello."""
            return Response(success=True, message="hello")

    return BuiltApp(app=cli, config=config, warnings=list(caught))


def assert_healthy(built: BuiltApp) -> None:
    """Check the contract that says an application works.

    The checks: no warning while building, unique option names, the automatic options present
    exactly when their flag is active, --help working, a command that returns a Response running
    with output in the requested format, and an unknown command exiting with code 2.

    Args:
        built: The application and its context, from build_app.

    Raises:
        AssertionError: With a message naming the check that failed and the config used.
    """
    context = f"config={built.config}"

    assert not built.warnings, (
        f"Warnings while building ({context}): {[str(w.message) for w in built.warnings]}"
    )
    _assert_options(built, context)
    _assert_help(built, context)
    _assert_command_runs(built, context)
    _assert_unknown_command(built, context)


def _assert_options(built: BuiltApp, context: str) -> None:
    """Check option names are unique and match the active flags."""
    names = [param.name for param in built.app.params]
    duplicated = sorted({name for name in names if names.count(name) > 1})
    assert not duplicated, f"Duplicated option names {duplicated} ({context})"

    expected = {**{flag: True for flag in AUTOMATIC_OPTIONS}, **built.config}
    for flag, name in AUTOMATIC_OPTIONS.items():
        assert (name in names) == bool(expected[flag]), (
            f"{flag}={expected[flag]} but option '{name}' is "
            f"{'present' if name in names else 'absent'} ({context})"
        )
    timer = "time" in names
    assert timer == bool(built.config.get("timer", False)), (
        f"timer={built.config.get('timer', False)} but option 'time' is "
        f"{'present' if timer else 'absent'} ({context})"
    )


def _assert_help(built: BuiltApp, context: str) -> None:
    """Check --help exits with code 0."""
    result = invoke(built.app, ["--help"])
    assert result.exit_code == 0, f"--help exited with {result.exit_code} ({context})"


def _assert_command_runs(built: BuiltApp, context: str) -> None:
    """Check the hello command runs and answers in the requested output format."""
    result = invoke(built.app, ["hello"])
    assert result.exit_code == 0, (
        f"Command hello exited with {result.exit_code}, exception {result.exception!r} ({context})"
    )
    if not built.config.get("handle_response", True):
        return

    assert result.output.strip(), f"Command hello printed nothing ({context})"
    output_format = built.config.get("output_format_default", "table")
    if output_format in ("json", "yaml"):
        try:
            parsed = result.json if output_format == "json" else result.yaml
        except ValueError as error:
            raise AssertionError(
                f"Command hello output is not valid {output_format} ({context}): {error}"
            ) from error
        assert parsed["success"] is True, f"Response is not a success: {parsed} ({context})"


def _assert_unknown_command(built: BuiltApp, context: str) -> None:
    """Check an unknown command exits with code 2."""
    result = invoke(built.app, [UNKNOWN_COMMAND])
    assert result.exit_code == 2, (
        f"Unknown command exited with {result.exit_code}, expected 2 ({context})"
    )
