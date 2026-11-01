"""Tests of the scenario harness itself: it must accept a healthy app and catch a broken one."""

import warnings

import click
import pytest

from tests.integration.harness import BuiltApp, assert_healthy, build_app


class TestHealthyApplications:
    """The contract passes for applications that work."""

    def test_default_app_group_is_healthy(self):
        assert_healthy(build_app())

    @pytest.mark.parametrize("output_format", ["json", "yaml", "table", "rich", "raw", "text"])
    def test_every_output_format_is_healthy(self, output_format):
        assert_healthy(build_app(output_format_default=output_format))

    def test_app_without_rich_help_is_healthy(self):
        assert_healthy(build_app(use_rich_help=False))

    def test_app_without_automatic_options_is_healthy(self):
        built = build_app(
            add_config_option=False,
            add_verbosity_option=False,
            add_log_file_option=False,
            add_version_option=False,
            add_output_format_option=False,
        )

        assert_healthy(built)

    def test_app_without_response_handling_is_healthy(self):
        assert_healthy(build_app(handle_response=False))

    def test_timer_adds_its_option_and_stays_healthy(self):
        assert_healthy(build_app(timer=True))

    def test_the_config_is_kept_for_the_diagnosis(self):
        assert build_app(use_rich_help=False).config == {"use_rich_help": False}


class TestBrokenApplicationsAreCaught:
    """The contract fails, with a message that names the problem."""

    def test_a_duplicated_option_is_reported(self):
        built = build_app()
        built.app.params.append(click.Option(["--verbosity"]))

        with pytest.raises(AssertionError, match="Duplicated option names.*verbosity"):
            assert_healthy(built)

    def test_an_option_missing_for_an_active_flag_is_reported(self):
        built = build_app()
        built.app.params = [p for p in built.app.params if p.name != "version"]

        with pytest.raises(AssertionError, match="add_version_option.*version"):
            assert_healthy(built)

    def test_an_option_present_for_an_inactive_flag_is_reported(self):
        built = build_app(add_version_option=False)
        built.app.params.append(click.Option(["--version"], is_flag=True))

        with pytest.raises(AssertionError, match="add_version_option.*version"):
            assert_healthy(built)

    def test_a_warning_raised_while_building_is_reported(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            warnings.warn("--config is used more than once", UserWarning, stacklevel=1)
        built = build_app()
        broken = BuiltApp(built.app, built.config, list(caught))

        with pytest.raises(AssertionError, match="Warnings while building.*used more than once"):
            assert_healthy(broken)

    def test_a_command_that_fails_is_reported(self):
        built = build_app()

        def failing():
            raise RuntimeError("boom")

        built.app.commands["hello"].callback = failing

        with pytest.raises(AssertionError, match="Command hello"):
            assert_healthy(built)

    def test_output_that_is_not_valid_json_is_reported(self):
        built = build_app(output_format_default="json")

        def not_json():
            click.echo("not json")

        built.app.commands["hello"].callback = not_json

        with pytest.raises(AssertionError, match="not valid json"):
            assert_healthy(built)

    def test_an_unknown_command_that_does_not_exit_with_two_is_reported(self):
        built = build_app()
        built.app.add_command(click.Command("nosuchcommand", callback=lambda: None))

        with pytest.raises(AssertionError, match="Unknown command"):
            assert_healthy(built)
