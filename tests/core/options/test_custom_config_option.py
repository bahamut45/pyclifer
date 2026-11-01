"""Tests for CustomConfigOption - focusing on custom logic only."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pyclifer.core.classes import CustomConfigOption


def patch_option_formats(option, formats_dict=None):
    """Patch file_format_patterns for the option."""
    option.file_format_patterns = formats_dict


class TestCustomConfigOption:
    """Test CustomConfigOption's specific functionality without retesting click-extra."""

    def test_extension_pattern_single_format(self):
        """Test _get_extension_pattern with a single format."""
        option = CustomConfigOption()
        patch_option_formats(option, {"toml": ["*.toml"]})

        pattern = option._get_extension_pattern()
        assert pattern == "toml"

    def test_extension_pattern_multiple_formats(self):
        """Test _get_extension_pattern with multiple formats."""
        option = CustomConfigOption()
        patch_option_formats(
            option,
            {"toml": ["*.toml"], "yaml": ["*.yaml", "*.yml"], "json": ["*.json"]},
        )

        pattern = option._get_extension_pattern()
        assert pattern == "{toml,yaml,yml,json}"

    def test_extension_pattern_empty(self):
        """Test _get_extension_pattern when no formats are provided."""
        option = CustomConfigOption()
        # noinspection PyArgumentEqualDefault
        patch_option_formats(option, None)

        pattern = option._get_extension_pattern()
        assert pattern == "*"

    @patch("pyclifer.core.classes.get_current_context")
    def test_get_all_config_patterns_no_context(self, mock_get_context):
        """Test _get_all_config_patterns when no click context is available."""
        mock_get_context.side_effect = RuntimeError("No context available")

        option = CustomConfigOption()
        patch_option_formats(option, {"toml": ["*.toml"]})

        patterns = option._get_all_config_patterns()
        assert patterns == []

    @patch("pyclifer.core.classes.get_current_context")
    def test_get_all_config_patterns_no_cli_name(self, mock_get_context):
        """Test _get_all_config_patterns when the CLI name is None."""
        mock_context = Mock()
        mock_context.find_root().info_name = None
        mock_get_context.return_value = mock_context

        option = CustomConfigOption()
        patch_option_formats(option, {"toml": ["*.toml"]})

        patterns = option._get_all_config_patterns()
        assert patterns == []

    @patch("pyclifer.core.classes.is_linux")
    @patch("pyclifer.core.classes.get_app_dir")
    @patch("pyclifer.core.classes.get_current_context")
    def test_get_all_config_patterns_linux(self, mock_get_context, mock_get_app_dir, mock_is_linux):
        """Test _get_all_config_patterns on a Linux platform."""
        mock_is_linux.return_value = True
        mock_context = Mock()
        mock_context.find_root().info_name = "test-cli"
        mock_get_context.return_value = mock_context
        mock_get_app_dir.return_value = "/home/user/.config/test-cli"

        option = CustomConfigOption()
        patch_option_formats(option, {"toml": ["*.toml"]})
        option.roaming = False
        option.force_posix = False

        patterns = option._get_all_config_patterns()

        assert len(patterns) == 2
        assert "/etc/test-cli" in patterns[0]
        assert "/home/user/.config/test-cli" in patterns[1]
        assert "*.toml" in patterns[0]
        assert "*.toml" in patterns[1]

    @patch("pyclifer.core.classes.is_linux")
    @patch("pyclifer.core.classes.get_app_dir")
    @patch("pyclifer.core.classes.get_current_context")
    def test_get_all_config_patterns_non_linux(
        self, mock_get_context, mock_get_app_dir, mock_is_linux
    ):
        """Test _get_all_config_patterns on a non-Linux platform."""
        mock_is_linux.return_value = False
        mock_context = Mock()
        mock_context.find_root().info_name = "test-cli"
        mock_get_context.return_value = mock_context
        mock_get_app_dir.return_value = "/Users/user/Library/Application Support/test-cli"

        option = CustomConfigOption()
        patch_option_formats(option, {"yaml": ["*.yaml"]})
        option.roaming = False
        option.force_posix = False

        patterns = option._get_all_config_patterns()

        assert len(patterns) == 1
        assert "/Users/user/Library/Application Support/test-cli" in patterns[0]
        assert "yaml" in patterns[0]

    @patch("pyclifer.core.classes.get_app_dir")
    @patch("pyclifer.core.classes.get_current_context")
    def test_get_all_config_patterns_app_dir_error(self, mock_get_context, mock_get_app_dir):
        """Test _get_all_config_patterns handles get_app_dir errors gracefully."""
        mock_context = Mock()
        mock_context.find_root().info_name = "test-cli"
        mock_get_context.return_value = mock_context
        mock_get_app_dir.side_effect = OSError("Permission denied")

        with patch("pyclifer.core.classes.is_linux", return_value=False):
            option = CustomConfigOption()
            patch_option_formats(option, {"json": ["*.json"]})

            patterns = option._get_all_config_patterns()

            assert patterns == []

    def test_fallback_pattern(self):
        """Test _get_fallback_pattern returns the current directory pattern."""
        option = CustomConfigOption()
        patch_option_formats(option, {"conf": ["*.conf"]})

        fallback = option._get_fallback_pattern()
        assert fallback == "*.conf"

    @patch("pyclifer.core.classes.get_current_context")
    def test_default_pattern_with_patterns(self, mock_get_context):
        """Test default_pattern when patterns are available."""
        mock_context = Mock()
        mock_context.find_root().info_name = "test-cli"
        mock_get_context.return_value = mock_context

        with (
            patch("pyclifer.core.classes.is_linux", return_value=True),
            patch(
                "pyclifer.core.classes.get_app_dir",
                return_value="/home/user/.config/test-cli",
            ),
        ):
            option = CustomConfigOption()
            patch_option_formats(option, {"toml": ["*.toml"]})
            option.roaming = False
            option.force_posix = False

            pattern = option.default_pattern()

            assert "/etc/test-cli" in pattern
            assert "/home/user/.config/test-cli" in pattern
            # Patterns must be pipe-separated so wcmatch SPLIT handles them correctly.
            assert "|" in pattern
            assert ", " not in pattern

    @patch("pyclifer.core.classes.get_current_context")
    def test_default_pattern_fallback(self, mock_get_context):
        """Test default_pattern falls back when no patterns available."""
        mock_get_context.side_effect = RuntimeError("No context")

        option = CustomConfigOption()
        patch_option_formats(option, {"ini": ["*.ini"]})

        pattern = option.default_pattern()
        assert pattern == "*.ini"

    def test_get_default_callable_raises_falls_through(self):
        """get_default with call=False, and a raising callable returns the callable."""
        from click_extra.config import ConfigOption

        option = CustomConfigOption()
        failing = Mock(side_effect=ValueError("boom"))

        with patch.object(ConfigOption, "get_default", return_value=failing):
            mock_ctx = Mock()
            result = option.get_default(mock_ctx, call=False)

        # Exception is swallowed; the original callable is returned unchanged.
        assert result is failing


class TestCustomConfigOptionIntegration:
    """Integration tests for CustomConfigOption with minimal mocking."""

    def test_can_be_instantiated(self):
        """Test that CustomConfigOption can be instantiated."""
        option = CustomConfigOption()
        assert isinstance(option, CustomConfigOption)
        assert hasattr(option, "roaming")

    def test_inherits_from_config_option(self):
        """Test that CustomConfigOption properly inherits from ConfigOption."""
        from click_extra.config import ConfigOption

        option = CustomConfigOption()
        assert isinstance(option, ConfigOption)

    def test_has_required_methods(self):
        """Test that all required methods are present."""
        option = CustomConfigOption()

        assert hasattr(option, "default_pattern")
        assert hasattr(option, "_get_extension_pattern")
        assert hasattr(option, "_get_all_config_patterns")
        assert hasattr(option, "_get_fallback_pattern")

        assert callable(option.default_pattern)


class TestCustomConfigOptionMultiPathSearch:
    """Guarantee that /etc/<app>/ and ~/.config/<app>/ are both searched.

    These tests use real temporary directories and real TOML config files so
    that they exercise the full click-extra glob pipeline — not just our
    default_pattern() output.
    """

    # noinspection PyMethodMayBeStatic
    def _make_option_with_patterns(self, *patterns: str) -> CustomConfigOption:
        """Return a CustomConfigOption whose _get_all_config_patterns is fixed."""
        option = CustomConfigOption()
        option._get_all_config_patterns = lambda: list(patterns)
        return option

    def test_default_pattern_uses_pipe_separator(self):
        """default_pattern joins multiple locations with | for wcmatch SPLIT."""
        option = self._make_option_with_patterns(
            "/etc/myapp/*.toml", "/home/u/.config/myapp/*.toml"
        )
        pattern = option.default_pattern()
        assert "|" in pattern
        assert "," not in pattern
        parts = pattern.split("|")
        assert len(parts) == 2

    def test_etc_config_file_is_found(self, tmp_path):
        """A TOML file in the /etc/<app>/ equivalent is discovered and parsed."""
        etc_dir = tmp_path / "etc" / "myapp"
        etc_dir.mkdir(parents=True)
        (etc_dir / "myapp.toml").write_text("[myapp]\nverbosity = 'DEBUG'\n")

        user_dir = tmp_path / "home" / ".config" / "myapp"
        user_dir.mkdir(parents=True)

        option = self._make_option_with_patterns(
            str(etc_dir / "*.toml"),
            str(user_dir / "*.toml"),
        )
        pattern = option.default_pattern()

        location, content = option.read_and_parse_conf(pattern)

        assert location is not None
        assert location.name == "myapp.toml"

    def test_user_config_file_is_found_when_no_etc(self, tmp_path):
        """A TOML file in the user config dir is found when /etc/ has no file."""
        etc_dir = tmp_path / "etc" / "myapp"
        etc_dir.mkdir(parents=True)  # empty — no config file

        user_dir = tmp_path / "home" / ".config" / "myapp"
        user_dir.mkdir(parents=True)
        (user_dir / "myapp.toml").write_text("[myapp]\nverbosity = 'INFO'\n")

        option = self._make_option_with_patterns(
            str(etc_dir / "*.toml"),
            str(user_dir / "*.toml"),
        )
        pattern = option.default_pattern()

        location, content = option.read_and_parse_conf(pattern)

        assert location is not None
        assert location.name == "myapp.toml"

    def _write_system_and_user(
        self, tmp_path, system_toml: str, user_toml: str
    ) -> tuple[CustomConfigOption, str]:
        """Write one system and one user config file; return the option and its pattern."""
        etc_dir = tmp_path / "etc" / "myapp"
        etc_dir.mkdir(parents=True)
        (etc_dir / "myapp.toml").write_text(system_toml)

        user_dir = tmp_path / "home" / ".config" / "myapp"
        user_dir.mkdir(parents=True)
        (user_dir / "myapp.toml").write_text(user_toml)

        option = self._make_option_with_patterns(
            str(etc_dir / "*.toml"),
            str(user_dir / "*.toml"),
        )
        return option, option.default_pattern()

    def test_user_overrides_system_on_conflict(self, tmp_path):
        """When both locations define a key, the user value wins."""
        option, pattern = self._write_system_and_user(
            tmp_path, "[myapp]\nsource = 'system'\n", "[myapp]\nsource = 'user'\n"
        )

        location, content = option.read_and_parse_conf(pattern)

        assert content["myapp"]["source"] == "user"

    def test_keys_from_both_files_are_merged(self, tmp_path):
        """A key defined in only one of the two files is kept."""
        option, pattern = self._write_system_and_user(
            tmp_path, "[myapp]\nonly_system = 1\n", "[myapp]\nonly_user = 2\n"
        )

        location, content = option.read_and_parse_conf(pattern)

        assert content["myapp"] == {"only_system": 1, "only_user": 2}

    def test_nested_tables_are_deep_merged(self, tmp_path):
        """Sub-command sections are merged key by key, not replaced as a whole."""
        option, pattern = self._write_system_and_user(
            tmp_path,
            "[myapp.hello]\na = 'system'\nb = 'system'\n",
            "[myapp.hello]\nb = 'user'\nc = 'user'\n",
        )

        location, content = option.read_and_parse_conf(pattern)

        assert content["myapp"]["hello"] == {"a": "system", "b": "user", "c": "user"}

    def test_returns_highest_priority_location(self, tmp_path):
        """The returned location is the user file, which has the highest priority."""
        option, pattern = self._write_system_and_user(
            tmp_path, "[myapp]\nx = 1\n", "[myapp]\ny = 2\n"
        )

        location, content = option.read_and_parse_conf(pattern)

        assert ".config" in location.parts

    def test_single_file_is_returned_unchanged(self, tmp_path):
        """With only one file present, its content is returned as is."""
        user_dir = tmp_path / "home" / ".config" / "myapp"
        user_dir.mkdir(parents=True)
        (user_dir / "myapp.toml").write_text("[myapp]\nx = 1\n")
        option = self._make_option_with_patterns(
            str(tmp_path / "etc" / "myapp" / "*.toml"), str(user_dir / "*.toml")
        )

        location, content = option.read_and_parse_conf(option.default_pattern())

        assert content == {"myapp": {"x": 1}}

    def test_later_file_in_a_directory_overrides_earlier_one(self, tmp_path):
        """Within a directory, files sorted later override files sorted earlier."""
        etc_dir = tmp_path / "etc" / "myapp"
        etc_dir.mkdir(parents=True)
        (etc_dir / "base.toml").write_text("[myapp]\nlevel = 'base'\nkept = 1\n")
        (etc_dir / "production.toml").write_text("[myapp]\nlevel = 'production'\n")
        option = self._make_option_with_patterns(str(etc_dir / "*.toml"))

        location, content = option.read_and_parse_conf(option.default_pattern())

        assert content["myapp"] == {"level": "production", "kept": 1}
        assert location.name == "production.toml"

    def test_no_file_raises_file_not_found(self, tmp_path):
        """FileNotFoundError is raised when no location holds a config file."""
        option = self._make_option_with_patterns(
            str(tmp_path / "etc" / "*.toml"), str(tmp_path / "home" / "*.toml")
        )

        with pytest.raises(FileNotFoundError, match="No file found"):
            option.read_and_parse_conf(option.default_pattern())

    def test_blank_files_are_ignored(self, tmp_path):
        """Blank files yield no layer; autodiscovery then reports no configuration."""
        option, pattern = self._write_system_and_user(tmp_path, "", "")

        location, content = option.read_and_parse_conf(pattern)

        assert location is None
        assert content is None

    def test_search_yields_triples_in_pattern_order(self, tmp_path):
        """Files come back as (location, content, media_type) in sub-pattern order."""
        first_dir = tmp_path / "zzz"
        first_dir.mkdir()
        (first_dir / "a.toml").write_text("[a]\nx = 1\n")
        second_dir = tmp_path / "aaa"
        second_dir.mkdir()
        (second_dir / "b.toml").write_text("[b]\nx = 2\n")

        option = self._make_option_with_patterns()
        results = list(
            option.search_and_read_file(f"{first_dir / '*.toml'}|{second_dir / '*.toml'}")
        )

        # Alphabetical order would put "aaa" first; the sub-pattern order must win.
        assert [location.name for location, _content, _media in results] == ["a.toml", "b.toml"]
        assert all(media_type is None for _location, _content, media_type in results)
        assert results[0][1] == "[a]\nx = 1\n"

    def test_search_skips_subpattern_without_match(self, tmp_path):
        """A sub-pattern matching nothing is ignored when another one matches."""
        empty_dir = tmp_path / "etc" / "myapp"
        empty_dir.mkdir(parents=True)
        user_dir = tmp_path / "home" / "myapp"
        user_dir.mkdir(parents=True)
        (user_dir / "myapp.toml").write_text("[myapp]\nsource = 'user'\n")

        option = self._make_option_with_patterns()
        results = list(option.search_and_read_file(f"{empty_dir / '*.toml'}|{user_dir / '*.toml'}"))

        assert [location.name for location, _content, _media in results] == ["myapp.toml"]

    def test_search_raises_when_no_subpattern_matches(self, tmp_path):
        """FileNotFoundError is raised when none of the sub-patterns match a file."""
        option = self._make_option_with_patterns()
        pattern = f"{tmp_path / 'one' / '*.toml'}|{tmp_path / 'two' / '*.toml'}"

        with pytest.raises(FileNotFoundError, match="No file found matching"):
            list(option.search_and_read_file(pattern))


@pytest.mark.tox
class TestCustomConfigOptionForTox:
    """Specific tests to validate tox compatibility across Python versions."""

    def test_import_compatibility(self):
        """Test that all imports work across different Python versions."""
        from click_extra import get_app_dir, get_current_context
        from click_extra.config import ConfigOption
        from extra_platforms import is_linux

        from pyclifer.core.classes import CustomConfigOption

        assert CustomConfigOption
        assert get_app_dir
        assert get_current_context
        assert ConfigOption
        assert is_linux

    def test_basic_functionality_across_versions(self):
        """Test basic functionality that should work across all Python versions."""
        option = CustomConfigOption()

        patch_option_formats(option, {"toml": ["*.toml"]})
        pattern = option._get_extension_pattern()
        assert isinstance(pattern, str)
        assert pattern == "toml"

    def test_pathlib_compatibility(self):
        """Test that Path operations work across Python versions."""
        test_path = Path("/etc/test-cli")
        assert isinstance(test_path, Path)
        assert str(test_path) == "/etc/test-cli"
