"""Tests for PycliferOption and GroupConfig attributes."""

from typing import Any

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
