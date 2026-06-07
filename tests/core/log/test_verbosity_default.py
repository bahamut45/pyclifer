"""Tests for the verbosity default level configuration."""

import logging

from click.testing import CliRunner

from pyclifer.core.decorators import app_group
from pyclifer.core.log.config import configure_rich_logging

# Store original logging state to restore after tests
original_level = logging.getLogger().level
original_handlers = logging.getLogger().handlers[:]


# noinspection PyTypeChecker
class TestVerbosityDefaultLevel:
    """Tests for the default verbosity level behavior of app_group."""

    @staticmethod
    def setup_method():
        """Reset logging state before each test.

        Restores the root logger to its original level and handlers,
        resets the click_extra logger, and forces Rich logging
        reconfiguration to ensure a clean state.
        """
        root = logging.getLogger()
        root.setLevel(original_level)
        root.handlers.clear()
        for handler in original_handlers:
            root.addHandler(handler)

        click_extra_logger = logging.getLogger("click_extra")
        click_extra_logger.handlers.clear()
        click_extra_logger.propagate = True

        configure_rich_logging(force_reconfigure=True)

    @staticmethod
    def teardown_method():
        """Restore logging state after each test.

        Resets the root logger level and handlers to their original values
        captured at module load time.
        """
        root = logging.getLogger()
        root.setLevel(original_level)
        root.handlers.clear()
        for handler in original_handlers:
            root.addHandler(handler)

    def test_default_verbosity_warning(self):
        """Test that WARNING is the default level when no verbosity_default_level is set."""

        @app_group()
        def cli():
            """Test CLI"""
            pass

        @cli.command()
        def do_work():
            """Dummy command."""
            logger = logging.getLogger()
            print(f"ROOT_LEVEL:{logger.level}")

        runner = CliRunner()
        result = runner.invoke(cli, ["do-work"])

        assert result.exit_code == 0
        assert f"ROOT_LEVEL:{logging.WARNING}" in result.output

    def test_custom_verbosity_default_level(self):
        """Test that a custom verbosity_default_level is applied correctly."""

        @app_group(verbosity_default_level="INFO")
        def cli():
            """Test CLI"""
            pass

        @cli.command()
        def do_work():
            """Dummy command."""
            logger = logging.getLogger()
            print(f"ROOT_LEVEL:{logger.level}")

        runner = CliRunner()
        result = runner.invoke(cli, ["do-work"])

        assert result.exit_code == 0
        assert f"ROOT_LEVEL:{logging.INFO}" in result.output

    def test_cli_override_default_verbosity(self):
        """Test that passing --verbosity on the CLI overrides the default level."""

        @app_group(verbosity_default_level="INFO")
        def cli():
            """Test CLI"""
            pass

        @cli.command()
        def do_work():
            """Dummy command."""
            logger = logging.getLogger()
            print(f"ROOT_LEVEL:{logger.level}")

        runner = CliRunner()
        result = runner.invoke(cli, ["--verbosity", "DEBUG", "do-work"])

        assert result.exit_code == 0
        assert f"ROOT_LEVEL:{logging.DEBUG}" in result.output


# noinspection PyTypeChecker
class TestVerbosityIsGlobalPropagation:
    """Tests that the is_global flag on --verbosity propagates to subgroups."""

    @staticmethod
    def setup_method():
        """Reset logging state before each test.

        Restores the root logger to its original level and handlers,
        resets the click_extra logger, and forces Rich logging
        reconfiguration to ensure a clean state.
        """
        root = logging.getLogger()
        root.setLevel(original_level)
        root.handlers.clear()
        for handler in original_handlers:
            root.addHandler(handler)

        click_extra_logger = logging.getLogger("click_extra")
        click_extra_logger.handlers.clear()
        click_extra_logger.propagate = True

        configure_rich_logging(force_reconfigure=True)

    @staticmethod
    def teardown_method():
        """Restore logging state after each test.

        Resets the root logger level and handlers to their original values
        captured at module load time.
        """
        root = logging.getLogger()
        root.setLevel(original_level)
        root.handlers.clear()
        for handler in original_handlers:
            root.addHandler(handler)

    def test_verbosity_option_is_global_flag_is_true(self):
        """Test that the --verbosity option on app_group has is_global=True."""

        @app_group()
        def cli():
            """Test CLI"""
            pass

        verbosity_param = next((p for p in cli.params if p.name == "verbosity"), None)
        assert verbosity_param is not None, "The --verbosity option must exist on app_group"
        assert getattr(verbosity_param, "is_global", False) is True, (
            "The --verbosity option must have is_global=True to be propagated to subcommands"
        )

    def test_verbosity_propagated_to_subcommand(self):
        """Test that --verbosity is injected into a direct sub-command's params."""

        @app_group()
        def cli():
            """Test CLI"""
            pass

        @cli.command()
        def do_work():
            """Dummy command."""
            pass

        verbosity_param = next((p for p in do_work.params if p.name == "verbosity"), None)
        assert verbosity_param is not None, (
            "The --verbosity parameter must be propagated to the subcommand via is_global=True"
        )

    def test_verbosity_propagated_to_subgroup(self):
        """Test that --verbosity is injected into a subgroup added to app_group."""

        @app_group()
        def cli():
            """Test CLI"""
            pass

        @cli.group()
        def sub():
            """Sub-group."""
            pass

        @sub.command()
        def do_work():
            """Dummy command."""
            pass

        verbosity_param = next((p for p in sub.params if p.name == "verbosity"), None)
        assert verbosity_param is not None, (
            "The --verbosity parameter must be propagated to the subgroup via is_global=True"
        )

    def test_verbosity_not_duplicated_in_subcommand(self):
        """Test that --verbosity is not duplicated when already present in a subcommand."""

        @app_group()
        def cli():
            """Test CLI"""
            pass

        @cli.command()
        def do_work():
            """Dummy command."""
            pass

        verbosity_params = [p for p in do_work.params if p.name == "verbosity"]
        assert len(verbosity_params) == 1, (
            "The --verbosity parameter must be injected only once, "
            f"but found {len(verbosity_params)}"
        )

    def test_verbosity_passed_to_subgroup_affects_logging(self):
        """Test that --verbosity on the root group propagates the level to subgroup commands."""

        @app_group()
        def cli():
            """Test CLI"""
            pass

        @cli.group()
        def sub():
            """Sub-group."""
            pass

        @sub.command()
        def do_work():
            """Dummy command inside a subgroup."""
            logger = logging.getLogger()
            print(f"ROOT_LEVEL:{logger.level}")

        runner = CliRunner()
        result = runner.invoke(cli, ["--verbosity", "DEBUG", "sub", "do-work"])

        assert result.exit_code == 0, f"Unexpected error: {result.output}"
        assert f"ROOT_LEVEL:{logging.DEBUG}" in result.output, (
            "DEBUG level must be active in the subgroup command "
            "when --verbosity DEBUG is passed to the root group"
        )

    def test_verbosity_on_subgroup_level_affects_logging(self):
        """Test that passing --verbosity directly on the subgroup also works."""

        @app_group()
        def cli():
            """Test CLI"""
            pass

        @cli.group()
        def sub():
            """Sub-group."""
            pass

        @sub.command()
        def do_work():
            """Dummy command inside a subgroup."""
            logger = logging.getLogger()
            print(f"ROOT_LEVEL:{logger.level}")

        runner = CliRunner()
        result = runner.invoke(cli, ["sub", "--verbosity", "INFO", "do-work"])

        assert result.exit_code == 0, f"Unexpected error: {result.output}"
        assert f"ROOT_LEVEL:{logging.INFO}" in result.output, (
            "INFO level must be active in the subgroup command "
            "when --verbosity INFO is passed directly to the subgroup"
        )
