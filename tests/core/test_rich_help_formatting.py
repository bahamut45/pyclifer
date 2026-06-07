"""Tests for rich-help formatting functionality in app_group."""

import pytest

from pyclifer.core import app_group
from pyclifer.core.rich_help_config import (
    PYCLIFER_CONFIGS,
    get_rich_config,
)


# noinspection PyUnresolvedReferences,PyNoneFunctionAssignment,PyTypeChecker
class TestRichHelpConfiguration:
    """Test rich-help configuration functionality."""

    def test_get_rich_config_with_none(self):
        """Test get_rich_config with None returns the default config."""
        config = get_rich_config(None)
        assert config is not None
        assert config.style_option == "bold blue"
        assert config.style_command == "bold green"

    def test_get_rich_config_with_predefined_name(self):
        """Test get_rich_config with predefined configuration names."""
        config = get_rich_config("default")
        assert config is not None
        assert config.style_option == "bold blue"
        assert "metavar" in config.options_table_column_types
        assert "metavar" not in config.options_table_help_sections

        config = get_rich_config("minimal")
        assert config is not None
        assert config.style_option == "cyan"
        assert config.show_arguments is False

        config = get_rich_config("verbose")
        assert config is not None
        assert "metavar" in config.options_table_column_types
        assert "metavar" in config.options_table_help_sections

    def test_get_rich_config_with_invalid_name(self):
        """Test get_rich_config with an invalid configuration name."""
        with pytest.raises(ValueError, match="Unknown configuration 'invalid'"):
            get_rich_config("invalid")

    def test_get_rich_config_with_dict(self):
        """Test get_rich_config with dictionary configuration."""
        config_dict = {
            "style_option": "red",
            "style_command": "yellow",
            "show_arguments": True,
        }
        config = get_rich_config(config_dict)
        assert config is not None
        assert config.style_option == "red"
        assert config.style_command == "yellow"
        assert config.show_arguments is True

    def test_get_rich_config_with_instance_returns_it_unchanged(self):
        """Test get_rich_config passes a RichHelpConfiguration instance through."""
        from rich_click import RichHelpConfiguration

        instance = RichHelpConfiguration(style_option="magenta")
        result = get_rich_config(instance)
        assert result is instance

    def test_pyclif_configs_availability(self):
        """Test that PYCLIFER_CONFIGS contains expected configurations."""
        expected_configs = ["default", "minimal", "verbose"]
        for config_name in expected_configs:
            assert config_name in PYCLIFER_CONFIGS
            config_func = PYCLIFER_CONFIGS[config_name]
            config = config_func()
            assert config is not None


# noinspection PyArgumentEqualDefault
class TestRichHelpFormatting:
    """Test rich-help formatting integration with app_group."""

    def test_app_group_with_rich_help_disabled(self):
        """Test app_group with rich help explicitly disabled."""

        @app_group(use_rich_help=False)
        def app():
            """Test app"""
            pass

        assert hasattr(app, "main")

    def test_app_group_with_rich_help_enabled_by_default(self):
        """Test app_group with rich help enabled by default (no explicit parameter)."""

        @app_group()
        def app():
            """Test app"""
            pass

        assert hasattr(app, "main")

    def test_app_group_with_rich_help_enabled_explicit(self):
        """Test app_group with rich help explicitly enabled using the default config."""

        @app_group(use_rich_help=True)
        def app():
            """Test app"""
            pass

        assert hasattr(app, "main")
        if hasattr(app, "__rich_context_settings__"):
            assert "rich_help_config" in app.__rich_context_settings__

    def test_app_group_with_rich_help_predefined_config(self):
        """Test app_group with a predefined rich help configuration."""
        for config_name in ["default", "minimal", "verbose"]:

            @app_group(use_rich_help=True, rich_help_config=config_name)
            def app():
                """Test app"""
                pass

            assert hasattr(app, "main")

    def test_app_group_with_rich_help_custom_config(self):
        """Test app_group with a custom rich help configuration."""
        custom_config = {
            "style_option": "bold magenta",
            "style_command": "bold cyan",
            "show_arguments": True,
        }

        @app_group(use_rich_help=True, rich_help_config=custom_config)
        def app():
            """Test app"""
            pass

        assert hasattr(app, "main")

    def test_app_group_with_rich_help_invalid_config(self):
        """Test app_group with an invalid rich help configuration."""
        with pytest.raises(ValueError):

            @app_group(use_rich_help=True, rich_help_config="invalid_config")
            def app():
                """Test app"""
                pass


# noinspection PyArgumentEqualDefault
class TestRichHelpIntegration:
    """Test integration of rich-help with other app_group features."""

    def test_rich_help_with_other_options(self):
        """Test that rich-help works with other app_group options."""

        @app_group(
            use_rich_help=True,
            rich_help_config="verbose",
            use_rich_logging=True,
            add_config_option=True,
            add_verbosity_option=True,
            add_version_option=True,
        )
        def app():
            """Test app with all options enabled"""
            pass

        assert hasattr(app, "main")

    def test_rich_help_parameter_precedence(self):
        """Test that rich-help parameters work correctly with kwargs."""

        @app_group(
            use_rich_help=True,
            rich_help_config="minimal",
            context_settings={"max_content_width": 120},
        )
        def app():
            """Test app"""
            pass

        assert hasattr(app, "main")
