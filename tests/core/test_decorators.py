"""Tests for GroupDecorator configuration branches and option factory functions."""

from unittest.mock import MagicMock, patch

import click
from click.testing import CliRunner

from pyclifer.core.classes import GroupConfig, PycliferOption
from pyclifer.core.decorators import (
    GroupDecorator,
    app_group,
    config_option,
    log_file_option,
    option,
    output_filter_option,
    output_format_option,
    pagination_options,
    verbosity_option,
)
from pyclifer.core.output.exit_codes import ExitCode

# ---------------------------------------------------------------------------
# GroupDecorator — _setup_logging
# ---------------------------------------------------------------------------


# noinspection PyUnusedLocal
class TestGroupDecoratorSetupLogging:
    """Tests for _setup_logging behavior ."""

    def test_use_rich_logging_false_skips_configure(self):
        """use_rich_logging=False must not call configure_rich_logging."""
        with patch("pyclifer.core.log.config.configure_rich_logging") as mock_cfg:

            @app_group(use_rich_logging=False)
            @click.pass_context
            def app(ctx):
                """App"""

            mock_cfg.assert_not_called()


# ---------------------------------------------------------------------------
# GroupDecorator — _apply_rich_help
# ---------------------------------------------------------------------------


# noinspection PyUnusedLocal
class TestGroupDecoratorApplyRichHelp:
    """Tests for _apply_rich_help behavior."""

    def test_rich_help_skipped_when_get_rich_config_returns_none(self):
        """When get_rich_config returns None, the rich_config decorator is not applied."""
        with patch("pyclifer.core.rich_help_config.get_rich_config", return_value=None):

            @app_group(use_rich_help=True)
            @click.pass_context
            def app(ctx):
                """App"""

            runner = CliRunner()
            result = runner.invoke(app, ["--help"])
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# GroupDecorator — _configure_context
# ---------------------------------------------------------------------------


class TestGroupDecoratorConfigureContext:
    """Tests for _configure_context behavior ."""

    def test_auto_envvar_prefix_forwarded_to_context_settings(self):
        """auto_envvar_prefix is added to context_settings when set."""
        config = GroupConfig(auto_envvar_prefix="MY_APP")
        decorator = GroupDecorator(config, {})
        decorator._configure_context()

        assert decorator.click_kwargs["context_settings"]["auto_envvar_prefix"] == "MY_APP"

    def test_auto_envvar_prefix_none_not_in_context_settings(self):
        """auto_envvar_prefix=None leaves context_settings without that key."""
        config = GroupConfig(auto_envvar_prefix=None)
        decorator = GroupDecorator(config, {})
        decorator._configure_context()

        assert "auto_envvar_prefix" not in decorator.click_kwargs["context_settings"]


# ---------------------------------------------------------------------------
# GroupDecorator — _apply_automatic_options (version in kwargs)
# ---------------------------------------------------------------------------


# noinspection PyUnusedLocal
class TestGroupDecoratorVersionKwarg:
    """Tests for the version popped from click_kwargs."""

    def test_version_kwarg_is_passed_to_version_option(self):
        """When version= is in kwargs alongside add_version_option=True, the app shows it."""

        @app_group(add_version_option=True, version="2.5.0")
        @click.pass_context
        def app(ctx):
            """App"""

        runner = CliRunner()
        result = runner.invoke(app, ["--version"])
        assert "2.5.0" in result.output


# ---------------------------------------------------------------------------
# GroupDecorator — _configure_context (envvar prefix static path)
# ---------------------------------------------------------------------------


class TestGroupDecoratorConfigureContextEnvvar:
    """Tests for _configure_context — the static auto_envvar_prefix path."""

    def test_explicit_prefix_not_derived_at_runtime(self):
        """When auto_envvar_prefix is set, derived prefix is NOT injected by _patch_make_context."""
        captured: dict = {}
        config = GroupConfig(auto_envvar_prefix="MY_APP", add_verbosity_option=False)
        decorator = GroupDecorator(config, {})

        class _FakeGroup:
            def make_context(self_inner, info_name, args, parent=None, **extra):
                """Record extra and return a minimal context-like object."""
                captured["extra"] = extra
                ctx = MagicMock()
                ctx.command.params = []
                ctx.meta = {}
                return ctx

        g = _FakeGroup()
        decorator._patch_make_context(g)
        g.make_context("my-app", [], parent=None)
        assert "auto_envvar_prefix" not in captured["extra"]


# ---------------------------------------------------------------------------
# GroupDecorator — _extract_early_verbosity
# ---------------------------------------------------------------------------


class TestExtractEarlyVerbosity:
    """Direct unit tests for _extract_early_verbosity static method."""

    def test_equals_format(self):
        """--verbosity=VALUE sets the level."""
        result = GroupDecorator._extract_early_verbosity(["--verbosity=debug"])
        assert result == "DEBUG"

    def test_short_flag_concatenated(self):
        """-vDEBUG (short flag with value concatenated) sets the level."""
        result = GroupDecorator._extract_early_verbosity(["-vDEBUG"])
        assert result == "DEBUG"

    def test_no_verbosity_returns_none(self):
        """No verbosity flag in args returns None."""
        result = GroupDecorator._extract_early_verbosity(["--output-format", "json"])
        assert result is None


# ---------------------------------------------------------------------------
# option() — store_in_meta fallback for non-StoreInMetaMixin cls
# ---------------------------------------------------------------------------


class TestOptionStoreInMetaFallback:
    """Tests for store_in_meta fallback with a non-StoreInMetaMixin class."""

    def test_store_in_meta_with_non_mixin_cls_sets_callback(self):
        """When cls does not use StoreInMetaMixin, a meta-storing callback is injected."""
        import click_extra as ce

        # click_extra.option always passes is_global= to the cls, so the cls must
        # accept it.  We subclass click_extra.Option and swallow is_global ourselves
        # while deliberately NOT inheriting StoreInMetaMixin.
        # noinspection PyUnusedLocal
        class _NoMixinOption(ce.Option):
            def __init__(self, *args, is_global: bool = False, **kwargs):
                super().__init__(*args, **kwargs)

        captured = {}

        @app_group(
            add_verbosity_option=False,
            add_config_option=False,
            add_log_file_option=False,
            add_version_option=False,
            invoke_without_command=True,
        )
        @option(
            "--tag",
            cls=_NoMixinOption,
            store_in_meta=True,
            expose_value=False,
            default=None,
            is_eager=False,
        )
        @click.pass_context
        def app(ctx):
            """App"""
            captured["meta"] = dict(ctx.meta)

        runner = CliRunner()
        runner.invoke(app, ["--tag", "hello"])
        assert captured["meta"].get("pyclifer.tag") == "hello"


# ---------------------------------------------------------------------------
# Option factory functions — custom param_decls
# ---------------------------------------------------------------------------


# noinspection PyUnusedLocal
class TestOptionFactoryCustomParamDecls:
    """Tests for option factory functions when custom param_decls are provided.

    Each factory has an "if not param_decls" guard that assigns defaults.
    When the caller supplies decls, that block is skipped.
    """

    def test_config_option_custom_decls(self):
        """config_option with a custom flag skips the default --config."""

        @app_group(add_config_option=False)
        @config_option("--cfg")
        @click.pass_context
        def app(ctx):
            """App"""

        opt_names = [n for p in app.params for n in p.opts]
        assert "--cfg" in opt_names
        assert "--config" not in opt_names

    def test_verbosity_option_custom_decls(self):
        """verbosity_option with a custom flag skips the default --verbosity."""

        @app_group(add_verbosity_option=False)
        @verbosity_option("--verbose", "-V")
        @click.pass_context
        def app(ctx):
            """App"""

        opt_names = [n for p in app.params for n in p.opts]
        assert "--verbose" in opt_names
        assert "--verbosity" not in opt_names

    def test_log_file_option_custom_decls(self):
        """log_file_option with a custom flag skips the default --log-file."""

        @app_group(add_log_file_option=False)
        @log_file_option("--log")
        @click.pass_context
        def app(ctx):
            """App"""

        opt_names = [n for p in app.params for n in p.opts]
        assert "--log" in opt_names
        assert "--log-file" not in opt_names

    def test_output_filter_option_custom_decls(self):
        """output_filter_option with a custom flag skips the default --output-filter."""

        @app_group()
        @click.pass_context
        def app(ctx):
            """App"""

        @app.command()
        @output_filter_option("--filter")
        @click.pass_context
        def cmd(ctx):
            """Cmd"""

        # noinspection PyUnresolvedReferences
        opt_names = [n for p in cmd.params for n in p.opts]
        assert "--filter" in opt_names
        assert "--output-filter" not in opt_names

    def test_output_format_option_custom_decls(self):
        """output_format_option with a custom flag skips the default --output-format."""

        @app_group(add_output_format_option=False)
        @output_format_option("--fmt")
        @click.pass_context
        def app(ctx):
            """App"""

        opt_names = [n for p in app.params for n in p.opts]
        assert "--fmt" in opt_names
        assert "--output-format" not in opt_names


# ---------------------------------------------------------------------------
# pagination_options
# ---------------------------------------------------------------------------


class TestPaginationOptions:
    """Test suite for the pagination_options decorator."""

    def _make_cmd(self, **kwargs):
        """Build a command decorated with pagination_options."""

        @app_group()
        @click.pass_context
        def app(ctx):
            """App"""

        @app.command()
        @pagination_options(**kwargs)
        @click.pass_context
        def cmd(ctx):
            """Cmd"""

        return cmd

    def test_injects_page_and_limit_options(self):
        """pagination_options adds --page and --limit to the command."""
        cmd = self._make_cmd()
        opt_names = [n for p in cmd.params for n in p.opts]
        assert "--page" in opt_names
        assert "--limit" in opt_names

    def test_page_short_flag(self):
        """--page has the -p short flag."""
        cmd = self._make_cmd()
        opt_names = [n for p in cmd.params for n in p.opts]
        assert "-p" in opt_names

    def test_limit_short_flag(self):
        """--limit has the -l short flag."""
        cmd = self._make_cmd()
        opt_names = [n for p in cmd.params for n in p.opts]
        assert "-l" in opt_names

    def test_default_limit(self):
        """--limit default is 20 when not overridden."""
        cmd = self._make_cmd()
        limit_param = next(p for p in cmd.params if "--limit" in p.opts)
        assert limit_param.default == 20

    def test_custom_default_limit(self):
        """default_limit overrides the --limit default."""
        cmd = self._make_cmd(default_limit=50)
        limit_param = next(p for p in cmd.params if "--limit" in p.opts)
        assert limit_param.default == 50

    def test_default_page(self):
        """--page default is 1."""
        cmd = self._make_cmd()
        page_param = next(p for p in cmd.params if "--page" in p.opts)
        assert page_param.default == 1

    def test_max_limit_enforced(self):
        """--limit rejects values above max_limit."""
        runner = CliRunner()

        @app_group()
        @click.pass_context
        def app(ctx):
            """App"""

        @app.command()
        @pagination_options(max_limit=10)
        @click.pass_context
        def cmd(ctx):
            """Cmd"""

        result = runner.invoke(app, ["cmd", "--limit", "11"])
        assert result.exit_code != 0

    def test_values_stored_in_meta(self):
        """--page and --limit values are stored in ctx.meta."""
        runner = CliRunner()
        captured: dict = {}

        @app_group()
        @click.pass_context
        def app(ctx):
            """App"""

        @app.command()
        @pagination_options()
        @click.pass_context
        def cmd(ctx):
            """Cmd"""
            captured["page"] = ctx.meta.get("pyclifer.page")
            captured["limit"] = ctx.meta.get("pyclifer.limit")

        runner.invoke(app, ["cmd", "--page", "3", "--limit", "5"])
        assert captured["page"] == 3
        assert captured["limit"] == 5


# ---------------------------------------------------------------------------
# GroupDecorator — _patch_make_context / Concern 1: dynamic envvar prefix
# ---------------------------------------------------------------------------


class TestPatchMakeContextDynamicEnvvar:
    """Tests concern 1: dynamic auto_envvar_prefix injection in composite wrapper."""

    def _make_fake_group(self, captured: dict):
        """Build a fake group that records the extra kwargs received by make_context."""

        class _FakeGroup:
            def make_context(self_inner, info_name, args, parent=None, **extra):
                """Capture extra and return a minimal context-like object."""
                captured["extra"] = extra
                ctx = MagicMock()
                ctx.command.params = []
                ctx.meta = {}
                return ctx

        return _FakeGroup()

    def test_prefix_derived_from_info_name_when_config_prefix_is_none(self):
        """auto_envvar_prefix is derived from info_name when config.auto_envvar_prefix is None."""
        captured: dict = {}
        config = GroupConfig(auto_envvar_prefix=None, add_verbosity_option=False)
        decorator = GroupDecorator(config, {})
        g = self._make_fake_group(captured)
        decorator._patch_make_context(g)
        g.make_context("my-app", [], parent=None)
        assert captured["extra"].get("auto_envvar_prefix") == "MY_APP"

    def test_prefix_not_injected_when_explicitly_set(self):
        """When config.auto_envvar_prefix is not None, derived prefix is not injected."""
        captured: dict = {}
        config = GroupConfig(auto_envvar_prefix="EXPLICIT", add_verbosity_option=False)
        decorator = GroupDecorator(config, {})
        g = self._make_fake_group(captured)
        decorator._patch_make_context(g)
        g.make_context("my-app", [], parent=None)
        assert "auto_envvar_prefix" not in captured["extra"]

    def test_hyphens_and_spaces_become_underscores_in_derived_prefix(self):
        """Hyphens and spaces in info_name are uppercased and underscored."""
        captured: dict = {}
        config = GroupConfig(auto_envvar_prefix=None, add_verbosity_option=False)
        decorator = GroupDecorator(config, {})
        g = self._make_fake_group(captured)
        decorator._patch_make_context(g)
        g.make_context("my cli-app", [], parent=None)
        assert captured["extra"].get("auto_envvar_prefix") == "MY_CLI_APP"


# ---------------------------------------------------------------------------
# GroupDecorator — _patch_make_context / Concern 2: early verbosity
# ---------------------------------------------------------------------------


class TestPatchMakeContextEarlyVerbosity:
    """Tests concern 2: early verbosity extraction in composite make_context wrapper."""

    def test_add_verbosity_option_false_skips_verbosity_extraction(self):
        """no-op when add_verbosity_option=False."""

        @app_group(add_verbosity_option=False, invoke_without_command=True)
        @click.pass_context
        def app(ctx):
            """App"""
            click.echo("root")

        runner = CliRunner()
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "root" in result.output

    def test_no_op_when_no_args_supplied(self):
        """no-op when args list is empty."""

        @app_group(add_verbosity_option=True, invoke_without_command=True)
        @click.pass_context
        def app(ctx):
            """App"""
            click.echo("root")

        runner = CliRunner()
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "root" in result.output

    def test_unknown_level_silently_skipped(self):
        """Level not in PYCLIFER_LOG_LEVELS is silently ignored, command still runs."""

        @app_group(add_verbosity_option=True)
        @click.pass_context
        def app(ctx):
            """App"""

        @app.command()
        @click.pass_context
        def probe(ctx):
            """Probe"""
            click.echo("ok")

        with patch.object(GroupDecorator, "_extract_early_verbosity", return_value="NOTINLEVELS"):
            runner = CliRunner()
            result = runner.invoke(app, ["probe"])

        assert "ok" in result.output


# ---------------------------------------------------------------------------
# GroupDecorator — _patch_make_context / Concern 3: framework meta injection
# ---------------------------------------------------------------------------


class TestPatchMakeContextMetaInjection:
    """Tests concern 3: framework meta injection in composite make_context wrapper."""

    def _make_fake_group(self, preset_meta: dict | None = None):
        """Build a fake group returning a context with a real meta dict."""

        class _FakeGroup:
            def make_context(self_inner, info_name, args, parent=None, **extra):
                """Return a minimal context-like object with a real meta dict."""
                ctx = MagicMock()
                ctx.command.params = []
                ctx.meta = dict(preset_meta) if preset_meta else {}
                return ctx

        return _FakeGroup()

    def test_unhandled_exception_log_level_stored_in_root_ctx_meta(self):
        """pyclifer.unhandled_exception_log_level is stored in ctx.meta at root."""
        config = GroupConfig(unhandled_exception_log_level="warning", add_verbosity_option=False)
        decorator = GroupDecorator(config, {})
        g = self._make_fake_group()
        decorator._patch_make_context(g)
        ctx = g.make_context("app", [], parent=None)
        assert ctx.meta["pyclifer.unhandled_exception_log_level"] == "warning"

    def test_exit_codes_class_stored_in_root_ctx_meta(self):
        """pyclifer.exit_codes_class is stored in ctx.meta at root."""
        config = GroupConfig(add_verbosity_option=False)
        decorator = GroupDecorator(config, {})
        g = self._make_fake_group()
        decorator._patch_make_context(g)
        ctx = g.make_context("app", [], parent=None)
        assert ctx.meta["pyclifer.exit_codes_class"] is ExitCode

    def test_meta_keys_not_set_when_parent_is_not_none(self):
        """Framework meta keys are not set when a parent context exists."""
        config = GroupConfig(add_verbosity_option=False)
        decorator = GroupDecorator(config, {})
        g = self._make_fake_group()
        decorator._patch_make_context(g)
        ctx = g.make_context("sub", [], parent=MagicMock())
        assert "pyclifer.unhandled_exception_log_level" not in ctx.meta
        assert "pyclifer.exit_codes_class" not in ctx.meta

    def test_setdefault_does_not_overwrite_existing_meta_value(self):
        """setdefault semantics: a pre-existing value in ctx.meta is preserved."""
        config = GroupConfig(unhandled_exception_log_level="error", add_verbosity_option=False)
        decorator = GroupDecorator(config, {})
        g = self._make_fake_group(
            preset_meta={"pyclifer.unhandled_exception_log_level": "critical"}
        )
        decorator._patch_make_context(g)
        ctx = g.make_context("app", [], parent=None)
        assert ctx.meta["pyclifer.unhandled_exception_log_level"] == "critical"


# ---------------------------------------------------------------------------
# GroupDecorator — _patch_make_context / Integration: all concerns together
# ---------------------------------------------------------------------------


class TestPatchMakeContextIntegration:
    """Integration: all three concerns active simultaneously via default app_group config."""

    def test_all_concerns_active_with_default_app_group(self):
        """app_group with defaults activates all three concerns simultaneously."""
        captured: dict = {}

        @app_group(invoke_without_command=True)
        @click.pass_context
        def myapp(ctx):
            """My app"""
            if ctx.invoked_subcommand is None:
                captured["meta"] = dict(ctx.meta)

        runner = CliRunner()
        result = runner.invoke(myapp, [])
        assert result.exit_code == 0
        assert "pyclifer.unhandled_exception_log_level" in captured["meta"]
        assert "pyclifer.exit_codes_class" in captured["meta"]


# ---------------------------------------------------------------------------
# option() — context kwarg forwarded to PycliferOption
# ---------------------------------------------------------------------------


class TestOptionContextKwarg:
    """option() forwards context kwarg to PycliferOption."""

    def test_option_context_true_sets_attribute(self):
        """option(..., context=True) creates a PycliferOption with context=True."""

        @app_group(
            add_verbosity_option=False,
            add_config_option=False,
            add_log_file_option=False,
            add_version_option=False,
            invoke_without_command=True,
        )
        @option("--host", context=True, default="localhost")
        @click.pass_context
        def app(ctx, host):
            """App"""

        host_param = next(p for p in app.params if p.name == "host")
        assert isinstance(host_param, PycliferOption)
        assert host_param.context is True

    def test_option_context_false_by_default(self):
        """option() without context= defaults to context=False."""

        @app_group(
            add_verbosity_option=False,
            add_config_option=False,
            add_log_file_option=False,
            add_version_option=False,
            invoke_without_command=True,
        )
        @option("--host", default="localhost")
        @click.pass_context
        def app(ctx, host):
            """App"""

        host_param = next(p for p in app.params if p.name == "host")
        assert isinstance(host_param, PycliferOption)
        assert host_param.context is False


# ---------------------------------------------------------------------------
# app_group() — context_factory kwarg forwarded to GroupConfig
# ---------------------------------------------------------------------------


class TestAppGroupContextFactory:
    """app_group() accepts and stores context_factory."""

    def test_context_factory_forwarded_to_group_config(self):
        """context_factory kwarg is stored in the GroupConfig on the decorator."""

        class AppCtx:
            """App context."""

            def __init__(self, **kwargs):
                self.kwargs = kwargs

        # We capture the GroupDecorator before it is called.
        captured: list = []
        original_init = GroupDecorator.__init__

        def patched_init(self, config, click_kwargs):
            """Record the config and call original."""
            captured.append(config)
            original_init(self, config, click_kwargs)

        with patch.object(GroupDecorator, "__init__", patched_init):
            app_group(
                context_factory=AppCtx,
                add_verbosity_option=False,
                add_config_option=False,
                add_log_file_option=False,
                add_version_option=False,
            )

        assert captured[0].context_factory is AppCtx


# ---------------------------------------------------------------------------
# Helpers shared by prescan integration tests
# ---------------------------------------------------------------------------


def _minimal_app_group(**extra_kwargs):
    """Return an app_group decorator with framework options stripped for isolation."""
    defaults = dict(
        add_verbosity_option=False,
        add_config_option=False,
        add_log_file_option=False,
        add_version_option=False,
        add_output_format_option=False,
    )
    defaults.update(extra_kwargs)
    return app_group(**defaults)


# ---------------------------------------------------------------------------
# _find_subcommand_boundary
# ---------------------------------------------------------------------------


class TestFindSubcommandBoundary:
    """Unit tests for GroupDecorator._find_subcommand_boundary static helper."""

    def _make_group(self, commands: list[str]) -> click.Group:
        """Build a minimal Click group with the given subcommand names."""

        @_minimal_app_group()
        @click.pass_context
        def grp(ctx):
            """Group"""

        for name in commands:

            @grp.command(name=name)
            def _cmd():
                """Sub"""

        return grp

    def test_no_subcommand_returns_len_args(self):
        """Returns len(args) when no subcommand name found."""
        grp = self._make_group(["serve"])
        result = GroupDecorator._find_subcommand_boundary(["--host", "prod"], grp)
        assert result == 2

    def test_subcommand_at_index_zero(self):
        """Returns 0 when the first token is the subcommand name."""
        grp = self._make_group(["serve"])
        result = GroupDecorator._find_subcommand_boundary(["serve", "--port", "8080"], grp)
        assert result == 0

    def test_subcommand_after_options(self):
        """Returns correct index when options precede the subcommand."""
        grp = self._make_group(["serve"])

        @option("--host", context=True, default="localhost")
        @click.pass_context
        def _f(ctx, host):
            """f"""

        host_param = _f.__click_params__[0]
        grp.params.append(host_param)
        result = GroupDecorator._find_subcommand_boundary(["--host", "prod", "serve"], grp)
        assert result == 2

    def test_option_value_looks_like_subcommand_not_treated_as_boundary(self):
        """A value token matching a subcommand name is skipped if preceded by an option."""
        grp = self._make_group(["serve"])

        @option("--output", default="table")
        @click.pass_context
        def _f(ctx, output):
            """f"""

        out_param = _f.__click_params__[0]
        grp.params.append(out_param)
        # "serve" here is the value of --output, not the subcommand invocation
        result = GroupDecorator._find_subcommand_boundary(
            ["--output", "serve", "--host", "prod"], grp
        )
        assert result == 4  # no subcommand boundary found

    def test_key_equals_value_form_subcommand_index_unchanged(self):
        """--key=val inline form does not consume the next token."""
        grp = self._make_group(["serve"])

        @option("--output", default="table")
        @click.pass_context
        def _f(ctx, output):
            """f"""

        out_param = _f.__click_params__[0]
        grp.params.append(out_param)
        result = GroupDecorator._find_subcommand_boundary(["--output=table", "serve"], grp)
        assert result == 1

    def test_double_dash_before_subcommand_returns_len_args(self):
        """-- argument terminator stops boundary search; returns len(args)."""
        grp = self._make_group(["serve"])
        result = GroupDecorator._find_subcommand_boundary(["--", "serve"], grp)
        assert result == 2

    def test_group_with_no_commands_returns_len_args(self):
        """Group with no registered commands always returns len(args)."""
        grp = self._make_group([])
        result = GroupDecorator._find_subcommand_boundary(["serve", "--host", "prod"], grp)
        assert result == 3

    def test_non_option_param_skipped_in_option_nargs_map(self):
        """Argument params (non-Option) in f.params are skipped without error."""
        grp = self._make_group(["serve"])
        # Inject a click Argument into the group's params to exercise the isinstance guard
        grp.params.append(click.Argument(["name"]))
        result = GroupDecorator._find_subcommand_boundary(["serve"], grp)
        assert result == 0


# ---------------------------------------------------------------------------
# _extract_params
# ---------------------------------------------------------------------------


class TestExtractParams:
    """Unit tests for GroupDecorator._extract_params static helper."""

    def _make_param(self, name: str, short: str | None = None, **kwargs) -> PycliferOption:
        """Build a PycliferOption for testing."""
        decls = [f"--{name}"]
        if short:
            decls.append(short)
        return PycliferOption(decls, **kwargs)

    def test_long_form_space_separated(self):
        """--option VALUE → opts dict and consumed tokens."""
        p = self._make_param("host")
        opts, consumed, remainder = GroupDecorator._extract_params(["--host", "prod", "serve"], [p])
        assert opts == {"host": "prod"}
        assert consumed == ["--host", "prod"]
        assert remainder == ["serve"]

    def test_key_equals_value_form(self):
        """--option=VALUE → single consumed token."""
        p = self._make_param("host")
        opts, consumed, remainder = GroupDecorator._extract_params(["--host=prod", "serve"], [p])
        assert opts == {"host": "prod"}
        assert consumed == ["--host=prod"]
        assert remainder == ["serve"]

    def test_short_form(self):
        """-s VALUE short form extracted correctly."""
        p = self._make_param("host", short="-H")
        opts, consumed, remainder = GroupDecorator._extract_params(["-H", "prod", "serve"], [p])
        assert opts == {"host": "prod"}
        assert consumed == ["-H", "prod"]
        assert remainder == ["serve"]

    def test_flag_option(self):
        """is_flag=True option extracted as True, no value token consumed."""
        p = self._make_param("verbose", is_flag=True)
        opts, consumed, remainder = GroupDecorator._extract_params(["--verbose", "serve"], [p])
        assert opts == {"verbose": True}
        assert consumed == ["--verbose"]
        assert remainder == ["serve"]

    def test_absent_option_not_in_result(self):
        """Option not present → not in opts dict and not in consumed."""
        p = self._make_param("host")
        opts, consumed, remainder = GroupDecorator._extract_params(["serve"], [p])
        assert "host" not in opts
        assert consumed == []
        assert remainder == ["serve"]

    def test_first_occurrence_wins_in_opts(self):
        """opts dict records first occurrence; all occurrences in consumed."""
        p = self._make_param("host")
        opts, consumed, remainder = GroupDecorator._extract_params(
            ["--host", "first", "--host", "second"], [p]
        )
        assert opts["host"] == "first"
        assert consumed == ["--host", "first", "--host", "second"]

    def test_nargs_2_consumes_two_value_tokens(self):
        """nargs=2 option consumes exactly two value tokens."""
        p = self._make_param("coord", nargs=2)
        opts, consumed, remainder = GroupDecorator._extract_params(
            ["--coord", "1.0", "2.0", "serve"], [p]
        )
        assert opts == {"coord": ("1.0", "2.0")}
        assert consumed == ["--coord", "1.0", "2.0"]
        assert remainder == ["serve"]

    def test_double_dash_stops_extraction(self):
        """Everything from -- onward goes to remainder; extraction stops."""
        p = self._make_param("host")
        opts, consumed, remainder = GroupDecorator._extract_params(["--", "--host", "prod"], [p])
        assert opts == {}
        assert consumed == []
        assert remainder == ["--", "--host", "prod"]

    def test_empty_args(self):
        """Empty args returns empty results."""
        p = self._make_param("host")
        opts, consumed, remainder = GroupDecorator._extract_params([], [p])
        assert opts == {}
        assert consumed == []
        assert remainder == []

    def test_empty_params(self):
        """Empty params list → all tokens go to remainder."""
        opts, consumed, remainder = GroupDecorator._extract_params(["--host", "prod"], [])
        assert opts == {}
        assert consumed == []
        assert remainder == ["--host", "prod"]

    def test_unknown_option_key_equals_value_goes_to_remainder(self):
        """--unknown=val where unknown is not in params goes to remainder."""
        p = self._make_param("host")
        opts, consumed, remainder = GroupDecorator._extract_params(
            ["--unknown=val", "--host", "prod"], [p]
        )
        assert opts == {"host": "prod"}
        assert "--unknown=val" in remainder

    def test_not_enough_value_tokens_goes_to_remainder(self):
        """Option at end of args without enough value tokens is left in remainder."""
        p = self._make_param("host")
        opts, consumed, remainder = GroupDecorator._extract_params(["--host"], [p])
        assert opts == {}
        assert consumed == []
        assert remainder == ["--host"]


# ---------------------------------------------------------------------------
# Pass 1 — context=True, is_global=False
# ---------------------------------------------------------------------------


class TestContextTrueNonGlobal:
    """Pass 1: context=True (non-global) tokens reordered before boundary."""

    def _make_app(self, required: bool = True):
        """Build a test app with a context=True --host option."""
        captured: dict = {}

        @_minimal_app_group()
        @option("--host", required=required, context=True, default=None)
        @click.pass_context
        def app(ctx, host):
            """App"""
            captured["host"] = host

        @app.command()
        @click.pass_context
        def serve(ctx):
            """Serve"""
            click.echo("serving")

        return app, captured

    def test_token_after_boundary_received_by_root_callback(self):
        """Token placed after subcommand name is received by root callback."""
        app, captured = self._make_app(required=True)
        runner = CliRunner()
        result = runner.invoke(app, ["serve", "--host", "prod"])
        assert result.exit_code == 0, result.output
        assert captured["host"] == "prod"

    def test_token_before_boundary_wins_over_after_boundary(self):
        """Pre-boundary value wins when same option appears both before and after."""
        app, captured = self._make_app(required=False)
        runner = CliRunner()
        result = runner.invoke(app, ["--host", "before", "serve", "--host", "after"])
        assert result.exit_code == 0, result.output
        assert captured["host"] == "before"

    def test_required_option_after_boundary_no_missing_parameter(self):
        """required=True option placed after boundary does not raise MissingParameter."""
        app, captured = self._make_app(required=True)
        runner = CliRunner()
        result = runner.invoke(app, ["serve", "--host", "prod"])
        assert result.exit_code == 0, result.output

    def test_env_var_does_not_override_token_after_boundary(self):
        """Explicit token after boundary wins over env var (direct CLI parse priority)."""
        app, captured = self._make_app(required=False)
        runner = CliRunner()
        result = runner.invoke(app, ["serve", "--host", "from-cli"], env={"APP_HOST": "from-env"})
        assert result.exit_code == 0, result.output
        assert captured["host"] == "from-cli"

    def test_context_factory_not_set_root_callback_receives_value(self):
        """Without context_factory, root callback still receives the value."""
        app, captured = self._make_app(required=True)
        runner = CliRunner()
        result = runner.invoke(app, ["serve", "--host", "direct"])
        assert result.exit_code == 0, result.output
        assert captured["host"] == "direct"


# ---------------------------------------------------------------------------
# Pass 2 — is_global=True prescan
# ---------------------------------------------------------------------------


class TestIsGlobalPrescan:
    """Pass 2: is_global=True tokens copied before boundary for root callback."""

    def _make_app(self):
        """Build a test app with an is_global=True --resource option."""
        root_captured: dict = {}
        sub_captured: dict = {}

        @_minimal_app_group()
        @option("--resource", is_global=True, default=None)
        @click.pass_context
        def app(ctx, resource):
            """App"""
            root_captured["resource"] = resource

        @app.command()
        @option("--resource", default=None)
        @click.pass_context
        def items(ctx, resource):
            """Items"""
            sub_captured["resource"] = resource

        return app, root_captured, sub_captured

    def test_post_boundary_token_received_by_root_callback(self):
        """Token after subcommand boundary reaches root callback."""
        app, root, _ = self._make_app()
        runner = CliRunner()
        result = runner.invoke(app, ["items", "--resource", "acme"])
        assert result.exit_code == 0, result.output
        assert root["resource"] == "acme"

    def test_subcommand_still_sees_its_token(self):
        """Subcommand receives its own copy of the token (not consumed)."""
        app, _, sub = self._make_app()
        runner = CliRunner()
        result = runner.invoke(app, ["items", "--resource", "acme"])
        assert result.exit_code == 0, result.output
        assert sub["resource"] == "acme"

    def test_pre_boundary_value_wins_over_post_boundary(self):
        """Pre-boundary explicit arg wins when same option appears on both sides."""
        app, root, _ = self._make_app()
        runner = CliRunner()
        result = runner.invoke(app, ["--resource", "before", "items", "--resource", "after"])
        assert result.exit_code == 0, result.output
        assert root["resource"] == "before"

    def test_no_op_when_no_post_boundary_global_tokens(self):
        """No-op when all global tokens are already before the boundary."""
        app, root, _ = self._make_app()
        runner = CliRunner()
        result = runner.invoke(app, ["--resource", "explicit", "items"])
        assert result.exit_code == 0, result.output
        assert root["resource"] == "explicit"


# ---------------------------------------------------------------------------
# context=True + is_global=True combo
# ---------------------------------------------------------------------------


class TestContextTrueIsGlobalCombo:
    """Options with both context=True and is_global=True."""

    def _make_app(self):
        """Build a test app with context=True, is_global=True --resource."""
        root_captured: dict = {}
        sub_captured: dict = {}

        @_minimal_app_group()
        @option("--resource", context=True, is_global=True, default=None)
        @click.pass_context
        def app(ctx, resource):
            """App"""
            root_captured["resource"] = resource

        @app.command()
        @click.pass_context
        def items(ctx, **kwargs):
            """Items"""
            # GlobalOptionsMixin injects --resource; it arrives as a kwarg
            sub_captured["resource"] = kwargs.get("resource")

        return app, root_captured, sub_captured

    def test_root_callback_receives_post_boundary_value(self):
        """Root callback gets the value even when placed after subcommand name."""
        app, root, _ = self._make_app()
        runner = CliRunner()
        result = runner.invoke(app, ["items", "--resource", "acme"])
        assert result.exit_code == 0, result.output
        assert root["resource"] == "acme"

    def test_subcommand_receives_propagated_value(self):
        """Subcommand receives its own copy via GlobalOptionsMixin propagation."""
        app, _, sub = self._make_app()
        runner = CliRunner()
        result = runner.invoke(app, ["items", "--resource", "acme"])
        assert result.exit_code == 0, result.output
        assert sub["resource"] == "acme"


# ---------------------------------------------------------------------------
# context_factory
# ---------------------------------------------------------------------------


class TestContextFactoryBehavior:
    """Tests for GroupConfig.context_factory integration."""

    def _make_app_with_factory(self, factory=None, required: bool = True):
        """Build a test app with a context_factory."""
        obj_captured: dict = {}

        @_minimal_app_group(context_factory=factory, invoke_without_command=True)
        @option("--host", required=required, context=True, default=None)
        @click.pass_context
        def app(ctx, host):
            """App"""
            obj_captured["obj"] = ctx.obj

        @app.command()
        @click.pass_context
        def serve(ctx):
            """Serve"""

        return app, obj_captured

    def test_ctx_obj_set_before_root_callback(self):
        """ctx.obj is populated by context_factory before root callback runs."""

        class AppCtx:
            """App context."""

            def __init__(self, host=None, **kwargs):
                self.host = host

        app, captured = self._make_app_with_factory(factory=AppCtx)
        runner = CliRunner()
        result = runner.invoke(app, ["--host", "prod"])
        assert result.exit_code == 0, result.output
        assert isinstance(captured["obj"], AppCtx)
        assert captured["obj"].host == "prod"

    def test_ctx_obj_built_from_context_true_params(self):
        """context_factory receives context=True param values as kwargs."""
        received: dict = {}

        def factory(**kwargs):
            """Factory."""
            received.update(kwargs)
            return object()

        app, _ = self._make_app_with_factory(factory=factory)
        runner = CliRunner()
        runner.invoke(app, ["--host", "myhost"])
        assert received.get("host") == "myhost"

    def test_context_factory_none_ctx_obj_not_set(self):
        """When context_factory=None, ctx.obj is not set by pyclifer."""
        app, captured = self._make_app_with_factory(factory=None, required=False)
        runner = CliRunner()
        result = runner.invoke(app, [])
        assert result.exit_code == 0, result.output
        assert captured["obj"] is None

    def test_context_factory_only_at_root_level(self):
        """context_factory is called only at root level (parent is None)."""
        call_count: list = []

        def factory(**kwargs):
            """Factory."""
            call_count.append(1)
            return object()

        app, _ = self._make_app_with_factory(factory=factory)
        runner = CliRunner()
        runner.invoke(app, ["serve"])
        # factory called once: for root context, not for subcommand context
        assert len(call_count) == 1

    def test_absent_optional_param_passes_none_to_factory(self):
        """An absent optional context=True param passes None to context_factory."""
        received: dict = {}

        def factory(**kwargs):
            """Factory."""
            received.update(kwargs)
            return object()

        app, _ = self._make_app_with_factory(factory=factory, required=False)
        runner = CliRunner()
        runner.invoke(app, [])
        assert "host" in received
        assert received["host"] is None

    def test_exception_in_context_factory_propagates(self):
        """Exception raised in context_factory propagates to the caller."""

        def broken_factory(**kwargs):
            """Broken factory."""
            raise ValueError("factory broken")

        app, _ = self._make_app_with_factory(factory=broken_factory)
        runner = CliRunner()
        result = runner.invoke(app, ["--host", "x"])
        assert result.exit_code != 0
