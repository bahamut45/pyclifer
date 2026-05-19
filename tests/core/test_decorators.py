"""Tests for GroupDecorator configuration branches and option factory functions."""

from unittest.mock import patch

import click
from click.testing import CliRunner

from pyclif.core.classes import GroupConfig
from pyclif.core.decorators import (
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

# ---------------------------------------------------------------------------
# GroupDecorator — _setup_logging
# ---------------------------------------------------------------------------


# noinspection PyUnusedLocal
class TestGroupDecoratorSetupLogging:
    """Tests for _setup_logging behavior ."""

    def test_use_rich_logging_false_skips_configure(self):
        """use_rich_logging=False must not call configure_rich_logging."""
        with patch("pyclif.core.log.config.configure_rich_logging") as mock_cfg:

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
        with patch("pyclif.core.rich_help_config.get_rich_config", return_value=None):

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
# GroupDecorator — _inject_dynamic_envvar
# ---------------------------------------------------------------------------


class TestGroupDecoratorInjectDynamicEnvvar:
    """Tests for _inject_dynamic_envvar ."""

    def test_dynamic_injection_skipped_when_prefix_is_set(self):
        """When auto_envvar_prefix is not None, make_context is not replaced."""
        config = GroupConfig(auto_envvar_prefix="MY_APP")
        decorator = GroupDecorator(config, {})

        class _FakeGroup:
            # noinspection PyMethodMayBeStatic,PyMissingOrEmptyDocstring,PyUnusedLocal
            def make_context(self, info_name, args, parent=None, **extra):
                return None

        g = _FakeGroup()
        # noinspection PyTypeChecker
        decorator._inject_dynamic_envvar(g)

        # make_context must NOT have been replaced as an instance attribute
        assert "make_context" not in g.__dict__


# ---------------------------------------------------------------------------
# GroupDecorator — _inject_early_verbosity
# ---------------------------------------------------------------------------


# noinspection PyUnusedLocal
class TestGroupDecoratorInjectEarlyVerbosity:
    """Tests for _inject_early_verbosity edge cases."""

    def test_empty_args_skips_verbosity_extraction(self):
        """Invoking the app with no args skips early verbosity extraction."""

        @app_group(add_verbosity_option=True, invoke_without_command=True)
        @click.pass_context
        def app(ctx):
            """App"""
            if ctx.invoked_subcommand is None:
                click.echo("root")

        runner = CliRunner()
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "root" in result.output

    def test_invalid_verbosity_level_extracted_is_silently_ignored(self):
        """Extracted level not in PYCLIF_LOG_LEVELS is silently ignored."""

        @app_group(add_verbosity_option=True)
        @click.pass_context
        def app(ctx):
            """App"""

        @app.command()
        @click.pass_context
        def probe(ctx):
            """Probe"""
            click.echo("ok")

        # Patch _extract_early_verbosity to return an unrecognized level so that
        # original_make_context can still succeed (click validation is not triggered).
        with patch.object(GroupDecorator, "_extract_early_verbosity", return_value="NOTINLEVELS"):
            runner = CliRunner()
            result = runner.invoke(app, ["probe"])

        assert "ok" in result.output


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
        assert captured["meta"].get("pyclif.tag") == "hello"


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
            captured["page"] = ctx.meta.get("pyclif.page")
            captured["limit"] = ctx.meta.get("pyclif.limit")

        runner.invoke(app, ["cmd", "--page", "3", "--limit", "5"])
        assert captured["page"] == 3
        assert captured["limit"] == 5
