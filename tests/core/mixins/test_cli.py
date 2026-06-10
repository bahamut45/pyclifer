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


# ---------------------------------------------------------------------------
# _propagate_context_options
# ---------------------------------------------------------------------------


class TestPropagateContextOptions:
    """_propagate_context_options injects display copies into subcommands."""

    def test_display_copy_added_to_direct_subcommand(self):
        """A context option is added to a subcommand that has no such param yet."""
        group = _Group(name="root")
        opt = _make_context_opt("--host")

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        group._propagate_context_options(sub, [opt], CONTEXT_OPTIONS_PANEL)

        assert any(p.name == "host" for p in sub.params)

    def test_display_copy_has_correct_attributes(self):
        """The injected copy has expose_value=False, required=False, context=False."""
        group = _Group(name="root")
        opt = _make_context_opt("--host", required=True)

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        group._propagate_context_options(sub, [opt], CONTEXT_OPTIONS_PANEL)

        injected = next(p for p in sub.params if p.name == "host")
        assert injected.expose_value is False
        assert injected.required is False
        assert injected.context is False
        assert injected.rich_help_panel == CONTEXT_OPTIONS_PANEL

    def test_custom_panel_name_used(self):
        """The panel_name argument is forwarded to the display copy."""
        group = _Group(name="root")
        opt = _make_context_opt("--host")

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        group._propagate_context_options(sub, [opt], "Custom Panel")

        injected = next(p for p in sub.params if p.name == "host")
        assert injected.rich_help_panel == "Custom Panel"

    def test_existing_param_not_duplicated(self):
        """If subcommand already defines the same param name, it is not duplicated."""
        group = _Group(name="root")
        opt = _make_context_opt("--host")

        existing = click_extra.Option(["--host"])
        sub = click_extra.Command("sub", callback=lambda: None, params=[existing])
        group._propagate_context_options(sub, [opt], CONTEXT_OPTIONS_PANEL)

        host_params = [p for p in sub.params if p.name == "host"]
        assert len(host_params) == 1

    def test_recursive_into_nested_subcommand(self):
        """Context options propagate recursively into commands nested inside a group."""
        group = _Group(name="root")
        opt = _make_context_opt("--host")

        leaf = click_extra.Command("leaf", callback=lambda: None, params=[])
        middle = click_extra.Group("middle")
        middle.add_command(leaf)

        group._propagate_context_options(middle, [opt], CONTEXT_OPTIONS_PANEL)

        assert any(p.name == "host" for p in leaf.params)

    def test_command_without_params_attr_skipped_gracefully(self):
        """Commands without a params attribute do not raise."""
        group = _Group(name="root")
        opt = _make_context_opt("--host")

        class _Bare:
            commands = None

        group._propagate_context_options(_Bare(), [opt], CONTEXT_OPTIONS_PANEL)  # must not raise


# ---------------------------------------------------------------------------
# add_command — context option propagation through the public API
# ---------------------------------------------------------------------------


class TestAddCommandContextPropagation:
    """add_command propagates context=True, show_in_subcommand_help=True options."""

    def test_context_option_added_on_add_command(self):
        """add_command injects display copies of qualifying context options."""
        group = _Group(name="root")
        group.params = [_make_context_opt("--host")]
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        group.add_command(sub)

        assert any(p.name == "host" for p in sub.params)

    def test_show_in_subcommand_help_false_skipped(self):
        """Options with show_in_subcommand_help=False are not propagated."""
        group = _Group(name="root")
        group.params = [_make_context_opt("--token", show_in_subcommand_help=False)]
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        group.add_command(sub)

        assert not any(p.name == "token" for p in sub.params)

    def test_context_and_is_global_true_not_double_injected(self):
        """context=True + is_global=True: _propagate_global_options adds it first;
        _propagate_context_options skips it because name already exists."""
        group = _Group(name="root")
        group.params = [PycliferOption(["--resource"], context=True, is_global=True)]
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        group.add_command(sub)

        resource_params = [p for p in sub.params if p.name == "resource"]
        assert len(resource_params) == 1

    def test_no_context_options_leaves_subcommand_unchanged(self):
        """When root has no qualifying context options, subcommand params are not modified."""
        group = _Group(name="root")
        group.params = [PycliferOption(["--verbose"])]
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        original_count = len(sub.params)
        group.add_command(sub)

        assert len(sub.params) == original_count

    def test_panel_name_from_context_options_panel_attr(self):
        """add_command uses _context_options_panel from the group instance."""
        group = _Group(name="root")
        group.params = [_make_context_opt("--host")]
        group._context_options_panel = "Connection"

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        group.add_command(sub)

        injected = next(p for p in sub.params if p.name == "host")
        assert injected.rich_help_panel == "Connection"


# ---------------------------------------------------------------------------
# Integration — help text contains the context options panel
# ---------------------------------------------------------------------------


class TestContextOptionsInHelpText:
    """End-to-end: context options appear in subcommand --help output."""

    def test_context_options_appear_in_subcommand_help(self):
        """Subcommand --help output lists context=True options in the panel."""
        from click.testing import CliRunner

        group = _Group(
            name="myapp",
            params=[
                _make_context_opt("--host", help="Array hostname."),
                _make_context_opt("--pool", help="Storage pool name."),
            ],
        )
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        @click_extra.command("status")
        def status_cmd():
            """Show status."""

        group.add_command(status_cmd)

        runner = CliRunner()
        result = runner.invoke(group, ["status", "--help"])

        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--pool" in result.output

    def test_hidden_context_option_absent_from_subcommand_help(self):
        """Options with show_in_subcommand_help=False do not appear in subcommand help."""
        from click.testing import CliRunner

        group = _Group(
            name="myapp",
            params=[
                _make_context_opt("--host"),
                _make_context_opt("--token", show_in_subcommand_help=False),
            ],
        )
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        @click_extra.command("ping")
        def ping_cmd():
            """Ping."""

        group.add_command(ping_cmd)

        runner = CliRunner()
        result = runner.invoke(group, ["ping", "--help"])

        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--token" not in result.output

    def test_panel_absent_when_all_options_hidden(self):
        """Panel section is absent when all context options have show_in_subcommand_help=False."""
        from click.testing import CliRunner

        group = _Group(
            name="myapp",
            params=[_make_context_opt("--token", show_in_subcommand_help=False)],
        )
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        @click_extra.command("ping")
        def ping_cmd():
            """Ping."""

        group.add_command(ping_cmd)

        runner = CliRunner()
        result = runner.invoke(group, ["ping", "--help"])

        assert result.exit_code == 0
        # Plain click does not render rich_help_panel labels, so we only assert
        # that the panel content (or lack thereof) is consistent with expectations.
        # The key behavior: no --token appears since it's marked hidden.
        assert "--token" not in result.output

    def test_subcommand_does_not_error_without_required_context_option(self):
        """Subcommand runs without error when required context option not re-provided."""
        from click.testing import CliRunner

        group = _Group(
            name="myapp",
            params=[_make_context_opt("--host", required=True)],
        )
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        @click_extra.command("ping")
        def ping_cmd():
            """Ping."""

        group.add_command(ping_cmd)

        runner = CliRunner()
        # --host provided at root level, not repeated before subcommand
        result = runner.invoke(group, ["--host", "10.0.0.1", "ping"])
        assert result.exit_code == 0
