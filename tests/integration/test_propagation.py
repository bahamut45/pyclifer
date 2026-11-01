"""Item 5 of the integration-test-matrix spec: propagation and parity.

An application with a global option, a context option and two nested subgroups is built in the
three ways a user registers commands, on both help paths. Every expectation below was measured on
the code before being written, in a fresh process.
"""

from dataclasses import dataclass, field

import click
import click_extra
import pytest

from pyclifer import (
    Event,
    EventsMixin,
    GlobalOptionsMixin,
    HandleResponseMixin,
    PycliferGroup,
    Response,
    app_group,
    command,
    group,
    option,
)
from pyclifer.testing import invoke

# How the tree is registered:
# - decorator: groups attached to the root first, leaves added with the group's own decorator.
# - bottom_up: every group is filled, then attached to its parent.
# - top_down: every group is attached to its parent, then filled with add_command.
ORDERS = ("decorator", "bottom_up", "top_down")
HELP_PATHS = (True, False)  # use_rich_help
LEAF_PATHS = {1: ["leaf1"], 2: ["ops", "leaf2"], 3: ["ops", "deep", "leaf3"]}
DEFAULT_REGION = "r0"


@dataclass
class Tree:
    """An application, and what each leaf and the context factory received."""

    cli: click.Group
    ops: click.Group
    deep: click.Group
    regions: dict[int, str] = field(default_factory=dict)
    factory_calls: list[dict] = field(default_factory=list)


def _tree(use_rich_help: bool, order: str, **config) -> Tree:
    """Root cli (global --region, context --env), groups ops and deep, a leaf at each depth."""
    tree = Tree(cli=None, ops=None, deep=None)

    def factory(**values):
        tree.factory_calls.append(values)
        return values

    @app_group(use_rich_help=use_rich_help, context_factory=factory, **config)
    @option("--region", is_global=True, default=DEFAULT_REGION)
    @option("--env", context=True, default="dev")
    def cli(region, env):
        """Root."""

    # A group callback receives the global options propagated to it, hence **kwargs.
    @group(name="ops")
    def ops(**_):
        """Ops."""

    @group(name="deep")
    def deep(**_):
        """Deep."""

    def leaf(depth):
        def run(region):
            tree.regions[depth] = region
            click.echo(f"leaf{depth} {region}")

        run.__doc__ = f"Leaf {depth}."
        return run

    if order == "decorator":
        cli.add_command(ops)
        ops.add_command(deep)
        cli.command(name="leaf1")(leaf(1))
        ops.command(name="leaf2")(leaf(2))
        deep.command(name="leaf3")(leaf(3))
    elif order == "bottom_up":
        deep.add_command(command(name="leaf3")(leaf(3)))
        ops.add_command(deep)
        ops.add_command(command(name="leaf2")(leaf(2)))
        cli.add_command(ops)
        cli.add_command(command(name="leaf1")(leaf(1)))
    else:
        cli.add_command(ops)
        ops.add_command(deep)
        deep.add_command(command(name="leaf3")(leaf(3)))
        ops.add_command(command(name="leaf2")(leaf(2)))
        cli.add_command(command(name="leaf1")(leaf(1)))
    tree.cli, tree.ops, tree.deep = cli, ops, deep
    return tree


def _names(params) -> list[str]:
    """Sorted option names."""
    return sorted(param.name for param in params)


@pytest.mark.parametrize("use_rich_help", HELP_PATHS, ids=["rich", "plain"])
@pytest.mark.parametrize("order", ORDERS)
class TestGlobalOptionPropagation:
    """An is_global option reaches the commands of three levels, however they were added."""

    @pytest.mark.parametrize("depth", LEAF_PATHS)
    def test_the_option_given_to_the_leaf_reaches_its_callback(self, use_rich_help, order, depth):
        tree = _tree(use_rich_help, order)

        result = invoke(tree.cli, [*LEAF_PATHS[depth], "--region", "X"])

        assert result.exit_code == 0, result.output
        assert tree.regions[depth] == "X"

    @pytest.mark.parametrize("depth", LEAF_PATHS)
    def test_the_default_applies_when_the_option_is_not_given(self, use_rich_help, order, depth):
        tree = _tree(use_rich_help, order)

        result = invoke(tree.cli, LEAF_PATHS[depth])

        assert result.exit_code == 0, result.output
        assert tree.regions[depth] == DEFAULT_REGION

    @pytest.mark.parametrize("depth", LEAF_PATHS)
    def test_the_option_is_listed_in_the_help_of_the_leaf(self, use_rich_help, order, depth):
        tree = _tree(use_rich_help, order)

        result = invoke(tree.cli, [*LEAF_PATHS[depth], "--help"])

        assert result.exit_code == 0, result.output
        assert "--region" in result.output


@pytest.mark.parametrize("order", ORDERS)
class TestGlobalValueBeforeTheSubcommand:
    """A value given before the subcommand is seen by the group that declares it, not by the leaf.

    The propagated option is a real parameter of the leaf (docs/api/mixins.md), so the leaf
    parses its own. Measured on both help paths, and documented.
    """

    @pytest.mark.parametrize("use_rich_help", HELP_PATHS, ids=["rich", "plain"])
    @pytest.mark.parametrize("depth", LEAF_PATHS)
    def test_the_leaf_keeps_its_default(self, use_rich_help, order, depth):
        tree = _tree(use_rich_help, order)

        result = invoke(tree.cli, ["--region", "X", *LEAF_PATHS[depth]])

        assert result.exit_code == 0, result.output
        assert tree.regions[depth] == DEFAULT_REGION

    def test_the_root_callback_sees_the_value(self, order):
        seen = {}

        @app_group()
        @option("--region", is_global=True, default=DEFAULT_REGION)
        def cli(region):
            """Root."""
            seen["region"] = region

        @cli.command(name="leaf")
        def leaf(region):
            """Leaf."""

        invoke(cli, ["--region", "X", "leaf"])

        assert seen["region"] == "X"

    def test_a_required_global_option_must_be_repeated_on_the_leaf(self, order):
        @app_group()
        @option("--token", is_global=True, required=True)
        def cli(token):
            """Root."""

        @cli.command(name="leaf")
        def leaf(token):
            """Leaf."""
            click.echo(f"token={token}")

        before = invoke(cli, ["--token", "T", "leaf"])
        after = invoke(cli, ["leaf", "--token", "T"])

        assert before.exit_code == 2
        assert (after.exit_code, "token=T" in after.output) == (0, True)


@pytest.mark.parametrize("use_rich_help", HELP_PATHS, ids=["rich", "plain"])
class TestGlobalOptionHelpWithoutContextOption:
    """The help of a leaf lists the global option even when no context option is declared.

    The tree above also has a context option, whose propagation rebuilds the help cache of the
    commands and used to hide that the global option alone did not.
    """

    @pytest.mark.parametrize("declaration", ["decorator", "add_command"])
    @pytest.mark.parametrize("nested", [False, True], ids=["first-level", "nested"])
    def test_the_option_is_listed(self, use_rich_help, declaration, nested):
        @app_group(use_rich_help=use_rich_help)
        @option("--region", is_global=True, default=DEFAULT_REGION)
        def cli(region):
            """Root."""

        def body(region):
            """Leaf."""

        owner = cli
        path = []
        if nested:
            owner = group(name="ops")(lambda **_: None)
            cli.add_command(owner)
            path = ["ops"]
        if declaration == "decorator":
            owner.command(name="leaf")(body)
        else:
            owner.add_command(command(name="leaf")(body))

        result = invoke(cli, [*path, "leaf", "--help"])

        assert result.exit_code == 0, result.output
        assert "--region" in result.output


class TestGlobalOptionEnvironmentVariable:
    """The environment variable of a global option, read by the commands it is propagated to.

    Measured, with an application named cli: on the Rich path a leaf reads CLI_LEAF_REGION and
    ignores CLI_REGION; on the plain path it reads CLI_REGION and ignores CLI_LEAF_REGION (the
    propagated option keeps the explicit variable of the root, and the context prefix of the leaf
    is LEAF instead of CLI_LEAF). The two paths must agree: use_rich_help only changes the help.
    """

    @staticmethod
    def _leaf_region(use_rich_help, environment):
        seen = {}

        @app_group(name="cli", use_rich_help=use_rich_help)
        @option("--region", is_global=True, default=DEFAULT_REGION)
        def cli(region):
            """Root."""

        @cli.command(name="leaf")
        def leaf(region):
            """Leaf."""
            seen["region"] = region

        invoke(cli, ["leaf"], env=environment)
        return seen["region"]

    @pytest.mark.xfail(strict=True, reason="item 18: the two help paths read different variables")
    def test_the_variable_of_the_root_reaches_the_leaf_the_same_way_on_both_paths(self):
        rich = self._leaf_region(True, {"CLI_REGION": "E1"})
        plain = self._leaf_region(False, {"CLI_REGION": "E1"})

        assert rich == plain

    @pytest.mark.xfail(strict=True, reason="item 18: the two help paths read different variables")
    def test_the_variable_of_the_leaf_is_read_the_same_way_on_both_paths(self):
        rich = self._leaf_region(True, {"CLI_LEAF_REGION": "E2"})
        plain = self._leaf_region(False, {"CLI_LEAF_REGION": "E2"})

        assert rich == plain


@pytest.mark.parametrize("order", ORDERS)
class TestHelpPathParity:
    """use_rich_help changes how help is drawn, never which options exist."""

    def test_every_command_has_the_same_options_on_both_paths(self, order):
        def snapshot(use_rich_help):
            tree = _tree(use_rich_help, order)
            return {
                "cli": _names(tree.cli.params),
                "ops": _names(tree.ops.params),
                "deep": _names(tree.deep.params),
                "leaf1": _names(tree.cli.commands["leaf1"].params),
                "leaf2": _names(tree.ops.commands["leaf2"].params),
                "leaf3": _names(tree.deep.commands["leaf3"].params),
            }

        assert snapshot(True) == snapshot(False)

    @pytest.mark.parametrize("use_rich_help", HELP_PATHS, ids=["rich", "plain"])
    def test_the_global_option_is_on_every_level_and_the_context_option_is_not_exposed(
        self, order, use_rich_help
    ):
        tree = _tree(use_rich_help, order)

        for level in (tree.ops, tree.deep, tree.deep.commands["leaf3"], tree.cli.commands["leaf1"]):
            assert "region" in _names(level.params)
        for param in tree.deep.commands["leaf3"].params:
            if param.name == "env":
                assert param.expose_value is False


@pytest.mark.parametrize("use_rich_help", HELP_PATHS, ids=["rich", "plain"])
@pytest.mark.parametrize("order", ORDERS)
class TestGroupsThatTakeNoArgument:
    """A group written the natural way, with no parameter, works under a global option."""

    @staticmethod
    def _plain_tree(use_rich_help, order):
        seen = {}

        @app_group(use_rich_help=use_rich_help)
        @option("--region", is_global=True, default=DEFAULT_REGION)
        def cli(region):
            """Root."""

        @group(name="ops")
        def ops():
            """Ops."""

        @group(name="deep")
        def deep():
            """Deep."""

        def leaf(region):
            """Leaf."""
            seen["region"] = region

        if order == "decorator":
            cli.add_command(ops)
            ops.add_command(deep)
            deep.command(name="leaf")(leaf)
        elif order == "bottom_up":
            deep.add_command(command(name="leaf")(leaf))
            ops.add_command(deep)
            cli.add_command(ops)
        else:
            cli.add_command(ops)
            ops.add_command(deep)
            deep.add_command(command(name="leaf")(leaf))
        return cli, seen

    def test_the_leaf_runs_and_receives_the_option(self, use_rich_help, order):
        cli, seen = self._plain_tree(use_rich_help, order)

        result = invoke(cli, ["ops", "deep", "leaf", "--region", "X"])

        assert result.exit_code == 0, result.output
        assert seen["region"] == "X"

    def test_the_help_of_the_leaf_is_shown(self, use_rich_help, order):
        cli, _ = self._plain_tree(use_rich_help, order)

        result = invoke(cli, ["ops", "deep", "leaf", "--help"])

        assert result.exit_code == 0, result.output
        assert "--region" in result.output


RICH_BOX = "\u256d"  # first corner of a Rich panel; plain Click help never draws one


@pytest.mark.parametrize("order", ORDERS)
class TestHelpRenderingFollowsTheApplication:
    """use_rich_help applies to the whole application, not only to its root group.

    Measured before the fix: with use_rich_help=False the root printed plain help, while a subgroup
    made by group() and a command made by command() printed Rich panels, and their usage errors
    were laid out the Rich way.
    """

    HELP_SCREENS = {
        "root": [],
        "subgroup": ["ops"],
        "second-level group": ["ops", "deep"],
        "first-level leaf": ["leaf1"],
        "nested leaf": ["ops", "deep", "leaf3"],
    }

    @pytest.mark.parametrize("screen", HELP_SCREENS)
    def test_a_plain_application_prints_plain_help_everywhere(self, order, screen):
        tree = _tree(False, order)

        result = invoke(tree.cli, [*self.HELP_SCREENS[screen], "--help"])

        assert result.exit_code == 0, result.output
        assert RICH_BOX not in result.output
        assert "Usage:" in result.output

    @pytest.mark.parametrize("screen", HELP_SCREENS)
    def test_a_rich_application_keeps_its_rich_help_everywhere(self, order, screen):
        tree = _tree(True, order)

        result = invoke(tree.cli, [*self.HELP_SCREENS[screen], "--help"])

        assert result.exit_code == 0, result.output
        assert RICH_BOX in result.output

    def test_the_options_of_a_plain_subcommand_help_are_listed(self, order):
        tree = _tree(False, order)

        output = invoke(tree.cli, ["ops", "deep", "leaf3", "--help"]).output

        assert "--region" in output
        assert "--env" in output

    def test_the_subcommands_of_a_plain_group_are_listed(self, order):
        tree = _tree(False, order)

        output = invoke(tree.cli, ["ops", "--help"]).output

        assert "Commands:" in output
        assert "leaf2" in output
        assert "deep" in output

    def test_a_usage_error_below_a_plain_group_is_laid_out_like_the_root(self, order):
        tree = _tree(False, order)

        below = invoke(tree.cli, ["ops", "nosuchcommand"])
        root = invoke(tree.cli, ["nosuchcommand"])

        assert below.exit_code == root.exit_code == 2
        assert below.stderr.startswith("Usage:")  # Click writes usage errors to stderr
        assert root.stderr.startswith("Usage:")

    def test_commands_still_run_and_parse_their_options(self, order):
        tree = _tree(False, order)

        result = invoke(tree.cli, ["ops", "deep", "leaf3", "--region", "X"])

        assert result.exit_code == 0, result.output
        assert tree.regions[3] == "X"


class TestOwnOptionsOfTheDecorators:
    """group() and command() declare no option of their own."""

    def test_a_group_created_by_group_has_no_option(self):
        assert group(name="solo")(lambda: None).params == []

    def test_a_command_created_by_command_has_no_option(self):
        assert command(name="solo")(lambda: None).params == []


@pytest.mark.parametrize("use_rich_help", HELP_PATHS, ids=["rich", "plain"])
class TestContextFactory:
    """context=True options feed context_factory, wherever they are given."""

    @pytest.mark.parametrize(
        ("label", "args", "env", "expected"),
        [
            ("default", LEAF_PATHS[3], None, "dev"),
            ("before the subcommand", ["--env", "prod", *LEAF_PATHS[3]], None, "prod"),
            ("on the leaf", [*LEAF_PATHS[3], "--env", "prod"], None, "prod"),
            ("environment variable", LEAF_PATHS[3], {"CLI_ENV": "staging"}, "staging"),
        ],
    )
    def test_the_factory_receives_the_value(self, use_rich_help, label, args, env, expected):
        tree = _tree(use_rich_help, "top_down")

        result = invoke(tree.cli, args, env=env)

        assert result.exit_code == 0, result.output
        assert tree.factory_calls == [{"env": expected}], label

    def test_the_factory_is_called_once_per_invocation(self, use_rich_help):
        tree = _tree(use_rich_help, "top_down")

        invoke(tree.cli, LEAF_PATHS[3])

        assert len(tree.factory_calls) == 1

    @pytest.mark.parametrize("args", [["--help"], [*LEAF_PATHS[3], "--help"]], ids=["root", "leaf"])
    def test_the_factory_is_not_called_to_show_help(self, use_rich_help, args):
        tree = _tree(use_rich_help, "top_down")

        result = invoke(tree.cli, args)

        assert result.exit_code == 0, result.output
        assert tree.factory_calls == []

    def test_the_object_reaches_the_command(self, use_rich_help):
        seen = {}

        @app_group(use_rich_help=use_rich_help, context_factory=lambda env: f"ctx-{env}")
        @option("--env", context=True, default="dev")
        def cli(env):
            """Root."""

        @cli.command(name="leaf")
        @click.pass_obj
        def leaf(obj):
            """Leaf."""
            seen["obj"] = obj

        invoke(cli, ["leaf", "--env", "prod"])

        assert seen["obj"] == "ctx-prod"


@pytest.mark.parametrize("use_rich_help", HELP_PATHS, ids=["rich", "plain"])
class TestContextOptionsPanel:
    """The context option is shown in the help of a subcommand, under the configured panel."""

    def test_a_first_level_command_shows_it_under_the_default_panel(self, use_rich_help):
        tree = _tree(use_rich_help, "top_down")

        result = invoke(tree.cli, ["leaf1", "--help"])

        assert "--env" in result.output
        if use_rich_help:  # the panel title is drawn by the Rich help only
            assert "Context Options" in result.output

    def test_a_first_level_command_shows_it_under_the_configured_panel(self, use_rich_help):
        tree = _tree(use_rich_help, "top_down", context_options_panel="Shared Options")

        result = invoke(tree.cli, ["leaf1", "--help"])

        assert "--env" in result.output
        if use_rich_help:  # the panel title is drawn by the Rich help only
            assert "Shared Options" in result.output
            assert "Context Options" not in result.output


@pytest.mark.parametrize("use_rich_help", HELP_PATHS, ids=["rich", "plain"])
@pytest.mark.parametrize("order", ORDERS)
class TestContextOptionsAtEveryDepth:
    """The context option and its panel are in the help of a command at any depth, in any order."""

    @pytest.mark.parametrize("depth", LEAF_PATHS)
    def test_the_option_is_listed_under_the_configured_panel(self, use_rich_help, order, depth):
        tree = _tree(use_rich_help, order, context_options_panel="Shared Options")

        result = invoke(tree.cli, [*LEAF_PATHS[depth], "--help"])

        assert result.exit_code == 0, result.output
        assert "--env" in result.output
        if use_rich_help:  # the panel title is drawn by the Rich help only
            assert "Shared Options" in result.output
            assert "Context Options" not in result.output


@pytest.mark.parametrize("use_rich_help", HELP_PATHS, ids=["rich", "plain"])
class TestEvents:
    """Handlers attached with on= or on() run, in order, on both help paths."""

    @staticmethod
    def _app(use_rich_help, calls, **config):
        @app_group(use_rich_help=use_rich_help, **config)
        def cli():
            """Root."""

        @cli.command(name="leaf")
        def leaf():
            """Leaf."""

        return cli

    def test_handlers_declared_with_on_run_in_order(self, use_rich_help):
        calls = []
        handlers = [lambda ctx: calls.append("first"), lambda ctx: calls.append("second")]
        cli = self._app(use_rich_help, calls, on={"config.loaded": handlers})

        result = invoke(cli, ["leaf"])

        assert result.exit_code == 0, result.output
        assert calls == ["first", "second"]

    def test_a_handler_registered_with_the_decorator_runs(self, use_rich_help):
        calls = []
        cli = self._app(use_rich_help, calls)

        @cli.on("config.loaded")
        def handler(ctx):
            calls.append(ctx.info_name)

        invoke(cli, ["leaf"])

        assert calls == ["cli"]

    def test_a_custom_event_is_emitted_to_its_handlers(self, use_rich_help):
        cli = self._app(use_rich_help, [])
        ready = Event("myapp.ready")
        cli.on(ready, lambda ctx: "one")
        cli.on(ready, lambda ctx: "two")

        assert cli.emit(ready, click.Context(cli)) == ["one", "two"]

    def test_an_unknown_event_name_is_refused(self, use_rich_help):
        cli = self._app(use_rich_help, [])

        with pytest.raises(ValueError, match="Unknown event 'nope'"):
            cli.on("nope", lambda ctx: None)


class TestPublicGroupClasses:
    """The public group class and the three mixins work in a group assembled by hand."""

    def test_public_group_is_the_plain_variant_of_the_application_group(self):
        @app_group(use_rich_help=False)
        def cli():
            """Root."""

        assert isinstance(cli, PycliferGroup)

    def test_a_group_built_from_the_public_mixins_does_everything(self):
        calls = []

        class MixedGroup(EventsMixin, HandleResponseMixin, GlobalOptionsMixin, click_extra.Group):
            """A group assembled from the public mixins."""

            handle_response_by_default = True

        @click_extra.group(cls=MixedGroup)
        @option("--region", is_global=True, default=DEFAULT_REGION)
        @click.pass_context
        def cli(ctx, region):
            """Root."""
            ctx.meta["pyclifer.output_format"] = "json"  # app_group sets it; a bare group does not

        cli.on("config.loaded", lambda ctx: calls.append("loaded"))

        @cli.command(name="leaf")
        def leaf(region):
            """Leaf."""
            return Response(success=True, message=f"region {region}")

        result = invoke(cli, ["leaf", "--region", "X"])

        assert result.exit_code == 0, result.output
        # GlobalOptionsMixin forwarded the value, HandleResponseMixin printed the Response.
        assert result.json["message"] == "region X"
        assert cli.emit("config.loaded", click.Context(cli)) == [None]  # EventsMixin ran it
        assert calls == ["loaded"]

    def test_pyclifer_group_can_be_used_as_the_class_of_a_plain_click_extra_group(self):
        @click_extra.group(cls=PycliferGroup)
        @option("--region", is_global=True, default=DEFAULT_REGION)
        def cli(region):
            """Root."""

        @cli.command(name="leaf")
        def leaf(region):
            """Leaf."""
            click.echo(f"region {region}")

        result = invoke(cli, ["leaf", "--region", "X"])

        assert result.exit_code == 0, result.output
        assert "region X" in result.output
