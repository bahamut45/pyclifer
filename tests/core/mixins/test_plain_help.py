"""Tests for the plain-help twins of rich-click commands."""

import click
import click_extra
import pytest
from rich_click import RichCommand, RichGroup

from pyclifer import command, group
from pyclifer.core.mixins.plain_help import has_plain_help, make_help_plain
from pyclifer.testing import invoke

RICH_BOX = "╭"


def _leaf(name: str = "leaf") -> RichCommand:
    """A command made by command(), which is a rich-click command."""
    cmd = command(name=name)(lambda: None)
    cmd.help = "Leaf command."
    return cmd


def _group(name: str = "ops") -> RichGroup:
    """A group made by group(), which is a rich-click group."""
    grp = group(name=name)(lambda: None)
    grp.help = "Ops group."
    return grp


def _root(*children) -> click_extra.Group:
    """A plain click-extra group holding the given commands."""
    root = click_extra.Group(name="cli", callback=lambda: None)
    for child in children:
        root.add_command(child)
    return root


class TestHasPlainHelp:
    """has_plain_help tells whether a command prints plain Click help."""

    def test_a_click_extra_group_has_plain_help(self):
        assert has_plain_help(click_extra.Group(name="cli")) is True

    def test_a_plain_click_command_has_plain_help(self):
        assert has_plain_help(click.Command("plain")) is True

    def test_a_rich_command_does_not(self):
        assert has_plain_help(_leaf()) is False

    def test_a_rich_group_does_not(self):
        assert has_plain_help(_group()) is False

    def test_a_rich_command_made_plain_does(self):
        cmd = _leaf()

        make_help_plain(cmd)

        assert has_plain_help(cmd) is True


class TestMakeHelpPlain:
    """make_help_plain switches a rich-click command, and what it holds, to Click's help."""

    def test_the_help_of_a_command_has_no_rich_panel(self):
        leaf = _leaf()
        root = _root(leaf)
        make_help_plain(leaf)

        result = invoke(root, ["leaf", "--help"])

        assert result.exit_code == 0, result.output
        assert RICH_BOX not in result.output
        assert "Usage: cli leaf [OPTIONS]" in result.output

    def test_the_help_of_a_group_lists_its_commands(self):
        grp = _group()
        grp.add_command(_leaf())
        root = _root(grp)
        make_help_plain(grp)

        result = invoke(root, ["ops", "--help"])

        assert result.exit_code == 0, result.output
        assert RICH_BOX not in result.output
        assert "Commands:" in result.output
        assert "leaf" in result.output

    def test_a_group_hands_the_switch_to_the_commands_it_holds(self):
        grp, leaf = _group(), _leaf()
        grp.add_command(leaf)

        make_help_plain(grp)

        assert has_plain_help(leaf) is True

    def test_nested_groups_are_all_switched(self):
        outer, inner, leaf = _group("outer"), _group("inner"), _leaf()
        inner.add_command(leaf)
        outer.add_command(inner)

        make_help_plain(outer)

        assert [has_plain_help(c) for c in (outer, inner, leaf)] == [True, True, True]

    def test_the_command_is_still_an_instance_of_its_original_class(self):
        leaf = _leaf()
        original_class = type(leaf)

        make_help_plain(leaf)

        assert isinstance(leaf, original_class)
        assert type(leaf).__name__ == "Plain" + original_class.__name__

    def test_the_twin_class_is_shared_by_commands_of_the_same_class(self):
        first, second = _leaf("first"), _leaf("second")

        make_help_plain(first)
        make_help_plain(second)

        assert type(first) is type(second)

    def test_switching_twice_changes_nothing(self):
        leaf = _leaf()
        make_help_plain(leaf)
        once = type(leaf)

        make_help_plain(leaf)

        assert type(leaf) is once

    def test_the_rich_help_configuration_is_dropped_but_other_settings_are_kept(self):
        leaf = _leaf()
        leaf.context_settings = {"rich_help_config": object(), "max_content_width": 60}

        make_help_plain(leaf)

        assert leaf.context_settings == {"max_content_width": 60}

    def test_a_command_that_is_not_rich_is_left_alone(self):
        plain = click_extra.Command("plain", callback=lambda: None)
        original_class = type(plain)

        make_help_plain(plain)

        assert type(plain) is original_class

    def test_the_commands_of_a_plain_group_are_reached_too(self):
        leaf = _leaf()
        root = _root(leaf)

        make_help_plain(root)

        assert has_plain_help(leaf) is True

    def test_a_usage_error_is_laid_out_like_the_root_one(self):
        grp = _group()
        root = _root(grp)
        make_help_plain(grp)

        result = invoke(root, ["ops", "nosuchcommand"])

        assert result.exit_code == 2
        assert result.stderr.startswith("Usage:")  # Click writes usage errors to stderr

    def test_the_handlers_and_options_of_the_command_are_kept(self):
        grp = _group()
        grp.params.append(click_extra.Option(["--flag"]))
        seen = []
        grp.on("config.loaded", lambda ctx: seen.append("handled"))

        make_help_plain(grp)

        assert [p.name for p in grp.params] == ["flag"]
        assert grp.emit("config.loaded", click.Context(grp)) == [None]
        assert seen == ["handled"]


@pytest.mark.parametrize("kind", ["command", "group"])
def test_the_switch_does_not_change_what_the_command_does(kind):
    """The command still parses its arguments and runs its callback after the switch."""
    seen = {}
    if kind == "command":
        target = command(name="run")(lambda: seen.update(ran=True))
        root = _root(target)
        args = ["run"]
    else:
        target = _group("run")
        target.add_command(command(name="inner")(lambda: seen.update(ran=True)))
        root = _root(target)
        args = ["run", "inner"]
    make_help_plain(target)

    result = invoke(root, args)

    assert result.exit_code == 0, result.output
    assert seen == {"ran": True}
