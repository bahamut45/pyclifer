"""Tests for PycliferOption and GroupConfig attributes."""

from typing import Any

import click_extra

from pyclifer.core.classes import GroupConfig, PycliferOption

# ---------------------------------------------------------------------------
# PycliferOption — context attribute
# ---------------------------------------------------------------------------


class TestPycliferOptionContextAttr:
    """PycliferOption stores the context attribute correctly."""

    def test_context_defaults_to_false(self):
        """context defaults to False when not passed."""
        opt = PycliferOption(["--host"])
        assert opt.context is False

    def test_context_true_is_stored(self):
        """context=True is stored on the instance."""
        opt = PycliferOption(["--host"], context=True)
        assert opt.context is True

    def test_context_false_explicit(self):
        """context=False explicit is stored correctly."""
        opt = PycliferOption(["--host"], context=False)
        assert opt.context is False

    def test_context_and_is_global_independent(self):
        """context and is_global can both be True simultaneously."""
        opt = PycliferOption(["--resource"], context=True, is_global=True)
        assert opt.context is True
        assert opt.is_global is True

    def test_is_global_unchanged_when_context_added(self):
        """Adding context=True does not change is_global default."""
        opt = PycliferOption(["--host"], context=True)
        assert opt.is_global is False


# ---------------------------------------------------------------------------
# GroupConfig — context_factory attribute
# ---------------------------------------------------------------------------


class TestGroupConfigContextFactory:
    """GroupConfig stores context_factory correctly."""

    def test_context_factory_defaults_to_none(self):
        """context_factory is None by default."""
        cfg = GroupConfig()
        assert cfg.context_factory is None

    def test_context_factory_callable_stored(self):
        """A callable passed as context_factory is stored."""

        class AppContext:
            def __init__(self, **kwargs: Any) -> None:
                self.kwargs = kwargs

        cfg = GroupConfig(context_factory=AppContext)
        assert cfg.context_factory is AppContext

    def test_context_factory_lambda_stored(self):
        """A lambda is stored as context_factory."""
        factory = lambda **kw: kw  # noqa: E731
        cfg = GroupConfig(context_factory=factory)
        assert cfg.context_factory is factory


# ---------------------------------------------------------------------------
# PycliferOption — show_in_subcommand_help attribute
# ---------------------------------------------------------------------------


class TestPycliferOptionShowInSubcommandHelp:
    """PycliferOption stores show_in_subcommand_help correctly."""

    def test_show_in_subcommand_help_defaults_to_true(self):
        """show_in_subcommand_help defaults to True when not passed."""
        opt = PycliferOption(["--host"])
        assert opt.show_in_subcommand_help is True

    def test_show_in_subcommand_help_false_is_stored(self):
        """show_in_subcommand_help=False is stored on the instance."""
        opt = PycliferOption(["--host"], show_in_subcommand_help=False)
        assert opt.show_in_subcommand_help is False

    def test_show_in_subcommand_help_independent_from_context(self):
        """show_in_subcommand_help and context are independent attributes."""
        opt = PycliferOption(["--host"], context=True, show_in_subcommand_help=False)
        assert opt.context is True
        assert opt.show_in_subcommand_help is False


# ---------------------------------------------------------------------------
# GroupConfig — context_options_panel attribute
# ---------------------------------------------------------------------------


class TestGroupConfigContextOptionsPanel:
    """GroupConfig stores context_options_panel correctly."""

    def test_context_options_panel_has_default(self):
        """context_options_panel defaults to the expected panel label."""
        cfg = GroupConfig()
        assert cfg.context_options_panel == "Context Options (anywhere-passable)"

    def test_context_options_panel_custom_value(self):
        """context_options_panel accepts a custom string."""
        cfg = GroupConfig(context_options_panel="Connection")
        assert cfg.context_options_panel == "Connection"


class TestPycliferOptionEnvironmentVariable:
    """A global option reads the environment variable of the root, in any command."""

    @staticmethod
    def _contexts():
        """A root context with prefix CLI and a child context for the command leaf."""
        root_command = click_extra.Group("cli")
        leaf_command = click_extra.Command("leaf")
        root = click_extra.Context(root_command, info_name="cli", auto_envvar_prefix="CLI")
        leaf = click_extra.Context(leaf_command, info_name="leaf", parent=root)
        return root, leaf

    def test_a_global_option_reads_the_variable_of_the_root_in_a_child_context(self, monkeypatch):
        monkeypatch.setenv("CLI_REGION", "E1")
        _, leaf = self._contexts()
        option = PycliferOption(["--region"], is_global=True)

        assert option.resolve_envvar_value(leaf) == "E1"

    def test_a_global_option_ignores_the_variable_built_from_the_command_path(self, monkeypatch):
        monkeypatch.setenv("CLI_LEAF_REGION", "E2")
        _, leaf = self._contexts()
        option = PycliferOption(["--region"], is_global=True)

        assert option.resolve_envvar_value(leaf) is None

    def test_a_global_option_reads_the_variable_of_the_root_in_the_root_context(self, monkeypatch):
        monkeypatch.setenv("CLI_REGION", "E1")
        root, _ = self._contexts()
        option = PycliferOption(["--region"], is_global=True)

        assert option.resolve_envvar_value(root) == "E1"

    def test_an_explicit_variable_is_read_in_a_child_context(self, monkeypatch):
        monkeypatch.setenv("MY_REGION", "E3")
        _, leaf = self._contexts()
        option = PycliferOption(["--region"], is_global=True, envvar="MY_REGION")

        assert option.resolve_envvar_value(leaf) == "E3"

    def test_an_option_that_is_not_global_keeps_the_variable_of_its_command(self, monkeypatch):
        monkeypatch.setenv("CLI_LEAF_NAME", "E4")
        monkeypatch.setenv("CLI_NAME", "E5")
        _, leaf = self._contexts()
        option = PycliferOption(["--name"])

        assert option.resolve_envvar_value(leaf) == "E4"

    def test_nothing_is_read_when_no_variable_is_set(self):
        _, leaf = self._contexts()
        option = PycliferOption(["--region"], is_global=True)

        assert option.resolve_envvar_value(leaf) is None
