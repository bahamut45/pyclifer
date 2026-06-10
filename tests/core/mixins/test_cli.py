"""Tests for GlobalOptionsMixin — context option display propagation."""

import click_extra

from pyclifer.core.classes import PycliferOption
from pyclifer.core.mixins.cli import CONTEXT_OPTIONS_PANEL, GlobalOptionsMixin

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Group(GlobalOptionsMixin, click_extra.Group):
    pass


def _make_context_opt(name: str = "--host", **kwargs) -> PycliferOption:
    return PycliferOption([name], context=True, **kwargs)


# ---------------------------------------------------------------------------
# _get_context_option_display_copy
# ---------------------------------------------------------------------------


class TestGetContextOptionDisplayCopy:
    """_get_context_option_display_copy returns a correctly configured display copy."""

    def test_expose_value_is_false(self):
        """Display copy has expose_value=False so it is not injected into callback kwargs."""
        opt = _make_context_opt()
        result = GlobalOptionsMixin._get_context_option_display_copy(opt, CONTEXT_OPTIONS_PANEL)
        assert result.expose_value is False

    def test_required_is_false(self):
        """Display copy has required=False so subcommand does not fail if option absent."""
        opt = _make_context_opt(required=True)
        result = GlobalOptionsMixin._get_context_option_display_copy(opt, CONTEXT_OPTIONS_PANEL)
        assert result.required is False

    def test_rich_help_panel_set_to_given_name(self):
        """Display copy has rich_help_panel equal to the given panel_name."""
        opt = _make_context_opt()
        result = GlobalOptionsMixin._get_context_option_display_copy(opt, "My Panel")
        assert result.rich_help_panel == "My Panel"

    def test_context_attr_is_false(self):
        """Display copy has context=False so prescan ignores it on subcommands."""
        opt = _make_context_opt()
        result = GlobalOptionsMixin._get_context_option_display_copy(opt, CONTEXT_OPTIONS_PANEL)
        assert result.context is False

    def test_name_preserved(self):
        """Display copy retains the same param name as the original."""
        opt = _make_context_opt("--pool")
        result = GlobalOptionsMixin._get_context_option_display_copy(opt, CONTEXT_OPTIONS_PANEL)
        assert result.name == "pool"

    def test_original_is_not_mutated(self):
        """Original option attributes are unchanged after creating a display copy."""
        opt = _make_context_opt(required=True)
        GlobalOptionsMixin._get_context_option_display_copy(opt, CONTEXT_OPTIONS_PANEL)
        assert opt.required is True
        assert opt.expose_value is True
        assert opt.context is True
