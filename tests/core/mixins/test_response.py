"""Tests for HandleResponseMixin and _apply_handle_response_to_group."""

from unittest.mock import MagicMock, patch

import click

from pyclifer.core import app_group, command, option

# noinspection PyProtectedMember
from pyclifer.core.mixins.response import (
    _PYCLIFER_RESPONSE_DECIDED,
    HandleResponseMixin,
    _apply_handle_response_to_group,
)
from pyclifer.core.output import Response
from pyclifer.core.output.exit_codes import ExitCode
from pyclifer.testing import invoke


class _PlainGroup:
    """Minimal group that is NOT a HandleResponseMixin, used to test the isinstance branch."""

    def __init__(self):
        self.commands = {}


class _MixinGroup(HandleResponseMixin, click.Group):
    pass


class TestApplyHandleResponseToGroup:
    """Tests for _apply_handle_response_to_group."""

    def test_non_mixin_group_does_not_set_handle_response_by_default(self):
        """Groups that are not HandleResponseMixin are left untouched."""
        group = _PlainGroup()
        # Should not raise and must not add the attribute.
        _apply_handle_response_to_group(group)
        assert not hasattr(group, "handle_response_by_default")

    def test_nested_group_leaf_is_wrapped_via_recursion(self):
        """Recursion into a nested group wraps its leaf commands (lines 38-39)."""

        # noinspection PyMissingOrEmptyDocstring
        def leaf_callback():
            pass

        leaf_cmd = MagicMock()
        leaf_cmd.commands = None  # leaf
        leaf_cmd.callback = leaf_callback

        inner_group = MagicMock()
        inner_group.commands = {"leaf": leaf_cmd}  # non-None → treated as group

        outer = _PlainGroup()
        outer.commands = {"sub": inner_group}

        patch_target = "pyclifer.core.decorators.returns_response"
        with patch(patch_target, side_effect=lambda f: f) as mock_wrap:
            _apply_handle_response_to_group(outer)

        mock_wrap.assert_called_once_with(leaf_callback)

    def test_command_with_none_callback_is_skipped(self):
        """Commands whose callback is None are skipped without error."""
        cmd = MagicMock()
        cmd.commands = None  # leaf
        cmd.callback = None

        group = _PlainGroup()
        group.commands = {"noop": cmd}

        _apply_handle_response_to_group(group)
        # callback must remain None — not wrapped
        assert cmd.callback is None

    def test_already_decided_callback_is_not_rewrapped(self):
        """Commands marked _PYCLIFER_RESPONSE_DECIDED are skipped (lines 44-48)."""

        # noinspection PyMissingOrEmptyDocstring
        def my_callback():
            pass

        setattr(my_callback, _PYCLIFER_RESPONSE_DECIDED, True)

        cmd = MagicMock()
        cmd.commands = None
        cmd.callback = my_callback

        group = _PlainGroup()
        group.commands = {"decided": cmd}

        _apply_handle_response_to_group(group)
        # callback must be the original function, not a wrapped version
        assert cmd.callback is my_callback


def _raise_click_exception(ctx, param, value):
    """Option callback raising a plain ClickException (exit code 1) when a value is given."""
    if value:
        raise click.ClickException("boom")
    return value


def _make_usage_app(handle_response=True, output_format_default="json"):
    """Build an application with a required global option and a required command option."""

    @app_group(
        name="repro",
        output_format_default=output_format_default,
        handle_response=handle_response,
    )
    @option("--token", required=True, help="A required global option.")
    def app(**kwargs):
        """Demo application."""

    @command()
    @option("--name", required=True, help="A required command option.")
    @option("--check", callback=_raise_click_exception, help="Raises a plain ClickException.")
    def greet(name, **kwargs):
        """Say hello."""
        return Response(success=True, message=f"hello {name}")

    app.add_command(greet)
    return app


class TestUsageErrorsInStructuredFormat:
    """Click usage errors are answered with a Response when the format is structured."""

    @staticmethod
    def _assert_usage_response(result, message_part):
        assert result.exit_code == 2
        payload = result.json
        assert payload["success"] is False
        assert message_part in payload["message"]
        assert payload["error_code"] == ExitCode.USAGE_ERROR
        assert payload["data"]["error_type"] == "usage_error"
        assert payload["data"]["results"] == []

    def test_missing_command_option_answers_json(self):
        result = invoke(_make_usage_app(), ["--token", "t", "greet"])
        self._assert_usage_response(result, "Missing option '--name'")
        assert result.json["data"]["command"] == "repro greet"

    def test_unknown_option_answers_json(self):
        result = invoke(_make_usage_app(), ["--token", "t", "greet", "--nope"])
        self._assert_usage_response(result, "No such option '--nope'")

    def test_unknown_command_answers_json(self):
        result = invoke(_make_usage_app(), ["--token", "t", "nosuchcommand"])
        self._assert_usage_response(result, "No such command")

    def test_missing_global_option_answers_json_with_default_format(self):
        """The error occurs before --output-format is read: the app default applies."""
        result = invoke(_make_usage_app(), ["greet", "--name", "bob"])
        self._assert_usage_response(result, "Missing option '--token'")

    def test_invalid_value_answers_json(self):
        result = invoke(_make_usage_app(), ["--token", "t", "--verbosity", "NOPE", "greet"])
        self._assert_usage_response(result, "NOPE")

    def test_explicit_yaml_format_answers_yaml(self):
        result = invoke(_make_usage_app(), ["--token", "t", "-o", "yaml", "greet"])
        assert result.exit_code == 2
        payload = result.yaml
        assert payload["success"] is False
        assert payload["error_code"] == ExitCode.USAGE_ERROR

    def test_default_format_from_the_application_is_used(self):
        """A yaml default is honored even when the error hides --output-format."""
        result = invoke(_make_usage_app(output_format_default="yaml"), ["greet", "--name", "bob"])
        assert result.exit_code == 2
        assert result.yaml["success"] is False

    def test_stderr_message_is_kept(self):
        result = invoke(_make_usage_app(), ["--token", "t", "greet"])
        assert "Missing option '--name'" in result.stderr

    def test_plain_click_exception_uses_click_error_type(self):
        result = invoke(
            _make_usage_app(), ["--token", "t", "greet", "--name", "bob", "--check", "x"]
        )
        assert result.exit_code == 1
        payload = result.json
        assert payload["success"] is False
        assert payload["message"] == "boom"
        assert payload["error_code"] == ExitCode.ERROR
        assert payload["data"]["error_type"] == "click_error"

    def test_successful_call_is_unchanged(self):
        result = invoke(_make_usage_app(), ["--token", "t", "greet", "--name", "bob"])
        assert result.exit_code == 0
        assert result.json["success"] is True


class TestUsageErrorsKeepClickBehavior:
    """Cases where Click keeps handling usage errors itself."""

    def test_table_format_keeps_click_behavior(self):
        result = invoke(_make_usage_app(), ["--token", "t", "-o", "table", "greet"])
        assert result.exit_code == 2
        assert result.output == ""
        assert "Missing option '--name'" in result.stderr

    def test_global_error_with_table_default_keeps_click_behavior(self):
        result = invoke(_make_usage_app(output_format_default="table"), ["greet", "--name", "bob"])
        assert result.exit_code == 2
        assert result.output == ""
        assert "Missing option '--token'" in result.stderr

    def test_without_handle_response_keeps_click_behavior(self):
        result = invoke(_make_usage_app(handle_response=False), ["--token", "t", "greet"])
        assert result.exit_code == 2
        assert result.output == ""
        assert "Missing option '--name'" in result.stderr

    def test_help_is_unaffected(self):
        result = invoke(_make_usage_app(), ["--help"])
        assert result.exit_code == 0
        assert "Usage" in result.output

    def test_subcommand_help_is_unaffected(self):
        result = invoke(_make_usage_app(), ["--token", "t", "greet", "--help"])
        assert result.exit_code == 0
        assert "Say hello" in result.output


class TestAddCommandForwardsKeywordArguments:
    """add_command passes extra keyword arguments to Click, such as a cloup section.

    Sections exist on cloup groups only, hence use_rich_help=False: the rich-click group
    that app_group builds by default has no section support.
    """

    def test_section_keyword_files_the_command_in_that_section(self):
        from cloup import Section

        section = Section("Extras")

        @app_group(use_rich_help=False)
        def app():
            """App"""

        @click.command()
        def greet():
            """Greet"""

        app.add_command(greet, section=section)

        assert app.commands["greet"] is greet
        assert greet in section.commands.values()

    def test_command_decorator_works_on_a_group_without_rich_help(self):
        """cloup's Group.command() calls add_command with a section internally."""

        @app_group(use_rich_help=False)
        def app():
            """App"""

        @app.command()
        def hello():
            """Hello"""

        assert "hello" in app.commands

    def test_response_handling_still_applies_to_a_command_added_with_a_section(self):
        import cloup

        class _SectionGroup(HandleResponseMixin, cloup.Group):
            pass

        group = _SectionGroup(name="app")
        group.handle_response_by_default = True

        @click.command()
        def greet():
            """Greet"""
            return Response(success=True, message="hi")

        group.add_command(greet, section=cloup.Section("Extras"))
        result = invoke(group, ["greet"])

        assert result.exit_code == 0
        # A command left unwrapped would print nothing for the Response it returns.
        assert result.output.strip() != ""
