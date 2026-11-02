"""Tests for pyclifer logging system - focusing on Rich integration and security features."""

import logging
import sys
import time
from unittest.mock import Mock, PropertyMock, patch

import pytest
from click_extra import ParameterSource

from pyclifer.core.log import (
    PYCLIFER_LOG_LEVELS,
    TRACE,
    PycliferVerbosityOption,
    RichExtraFormatter,
    RichExtraStreamHandler,
    SecretsMasker,
    add_trace_method,
    configure_rich_logging,
    get_configured_logger,
    get_logger,
)


class TestLoggingConfiguration:
    """Test logging configuration and setup functionality."""

    def test_pyclif_log_levels_contains_trace(self):
        """Test that PYCLIFER_LOG_LEVELS includes our custom TRACE level."""
        assert "TRACE" in PYCLIFER_LOG_LEVELS
        assert PYCLIFER_LOG_LEVELS["TRACE"] == TRACE
        assert TRACE == 5

    def test_pyclif_log_levels_extends_click_extra(self):
        """Test that PYCLIFER_LOG_LEVELS extends click-extra's LOG_LEVELS."""
        from pyclifer.core.log.levels import LOG_LEVELS as PYCLIFER_INTERNAL_LOG_LEVELS

        for level_name, level_value in PYCLIFER_INTERNAL_LOG_LEVELS.items():
            if level_name != "TRACE":
                assert level_name in PYCLIFER_LOG_LEVELS
                assert PYCLIFER_LOG_LEVELS[level_name] == level_value

        assert "TRACE" in PYCLIFER_LOG_LEVELS
        assert PYCLIFER_LOG_LEVELS["TRACE"] == TRACE

    @patch("pyclifer.core.log.config.basicConfig")
    @patch("pyclifer.core.log.config._preconfigure_click_extra_logger")
    @patch("pyclifer.core.log.config.logging.getLogger")
    def test_configure_rich_logging_basic(
        self, mock_get_logger, mock_preconfigure, mock_extra_config
    ):
        """Test basic configure_rich_logging functionality."""
        mock_root_logger = Mock()
        mock_root_logger.handlers = []
        mock_get_logger.return_value = mock_root_logger

        configure_rich_logging()

        mock_preconfigure.assert_called_once()
        mock_extra_config.assert_called_once_with(
            stream_handler_class=RichExtraStreamHandler,
            formatter_class=RichExtraFormatter,
            force=True,
        )

    @patch("pyclifer.core.log.config.logging.getLogger")
    def test_configure_rich_logging_already_configured(self, mock_get_logger):
        """Test that configure_rich_logging skips if already configured."""
        mock_handler = Mock()
        mock_handler._rich_handler = True
        mock_root_logger = Mock()
        mock_root_logger.handlers = [mock_handler]
        mock_get_logger.return_value = mock_root_logger

        with patch("pyclifer.core.log.config.basicConfig") as mock_config:
            # noinspection PyArgumentEqualDefault
            configure_rich_logging(force_reconfigure=False)
            mock_config.assert_not_called()

    @patch("pyclifer.core.log.config.basicConfig")
    def test_configure_rich_logging_force_reconfigure(self, mock_extra_config):
        """Test that force_reconfigure bypasses existing configuration check."""
        with patch("pyclifer.core.log.config._preconfigure_click_extra_logger"):
            configure_rich_logging(force_reconfigure=True)
            mock_extra_config.assert_called_once()

    # noinspection PyUnusedLocal
    @patch("pyclifer.core.log.config.basicConfig")
    def test_configure_rich_logging_no_tracebacks(self, mock_extra_config):
        """use_rich=True but rich_tracebacks=False skips traceback install."""
        with (
            patch("pyclifer.core.log.config._preconfigure_click_extra_logger"),
            patch("pyclifer.core.log.config.logging.getLogger") as mock_get_logger,
        ):
            mock_root_logger = Mock()
            mock_root_logger.handlers = []
            mock_get_logger.return_value = mock_root_logger

            with patch("rich.traceback.install") as mock_install:
                # noinspection PyArgumentEqualDefault
                configure_rich_logging(use_rich=True, rich_tracebacks=False, force_reconfigure=True)
                mock_install.assert_not_called()

    @patch("pyclifer.core.log.config.basicConfig")
    def test_configure_rich_logging_use_rich_false(self, mock_extra_config):
        """use_rich=False installs the standard console handler and no Rich one."""
        configure_rich_logging(use_rich=False, force_reconfigure=True)
        mock_extra_config.assert_called_once_with(force=True)

    def test_configure_rich_logging_shared_handler_already_present(self):
        """If shared_handler is already in root_logger, addHandler is skipped."""
        configure_rich_logging(force_reconfigure=True)
        root_logger = logging.getLogger()
        handler_count_before = len(root_logger.handlers)

        # Force reconfigure again — shared_handler is already there.
        configure_rich_logging(force_reconfigure=True)
        handler_count_after = len(root_logger.handlers)

        # Handler count should not grow on the second call.
        assert handler_count_after == handler_count_before

    def test_configure_rich_logging_preserves_file_handler_already_present(self):
        """File handler already in root_logger after basicConfig is not re-added."""
        import tempfile
        from logging.handlers import TimedRotatingFileHandler

        root_logger = logging.getLogger()
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name

        file_handler = TimedRotatingFileHandler(log_path)
        root_logger.addHandler(file_handler)
        try:
            # basicConfig (called internally) does not remove file handlers,
            # so the restore loop finds the handler already present and skips addHandler.
            configure_rich_logging(force_reconfigure=True)
            file_handlers = [
                h for h in root_logger.handlers if isinstance(h, TimedRotatingFileHandler)
            ]
            assert len(file_handlers) == 1
        finally:
            root_logger.removeHandler(file_handler)
            file_handler.close()


class TestPreconfigureClickExtraLogger:
    """Tests for _preconfigure_click_extra_logger."""

    def test_handler_already_present_returns_early(self):
        """If the handler is already in click_extra_logger.handlers, the function returns early"""
        from pyclifer.core.log.config import _preconfigure_click_extra_logger

        handler = logging.NullHandler()
        click_extra_logger = logging.getLogger("click_extra")
        click_extra_logger.addHandler(handler)
        try:
            original_handlers = list(click_extra_logger.handlers)
            _preconfigure_click_extra_logger(handler)
            assert list(click_extra_logger.handlers) == original_handlers
        finally:
            click_extra_logger.removeHandler(handler)


class TestRichExtraStreamHandler:
    """Test RichExtraStreamHandler functionality."""

    def test_handler_initialization_default(self):
        """Test RichExtraStreamHandler initialization with defaults."""
        handler = RichExtraStreamHandler()

        assert hasattr(handler, "_rich_handler")
        assert hasattr(handler, "rich_console")
        assert len(handler.filters) > 0  # Should have SecretsMasker by default

    def test_handler_initialization_no_secrets_filter(self):
        """Test RichExtraStreamHandler initialization without a secret filter."""
        handler = RichExtraStreamHandler(enable_secrets_filter=False)

        secrets_filters = [f for f in handler.filters if isinstance(f, SecretsMasker)]
        assert len(secrets_filters) == 0

    def test_handler_initialization_custom_stream(self):
        """Test RichExtraStreamHandler initialization with sys.stderr."""
        # noinspection PyTypeChecker
        handler = RichExtraStreamHandler(stream=sys.stderr)

        assert handler.stream is sys.stderr
        assert handler.rich_console.file is sys.stderr

    @patch("pyclifer.core.log.handlers.RichHandler")
    def test_emit_uses_rich_handler(self, mock_rich_handler_class):
        """Test that emit method delegates to Rich handler."""
        mock_rich_handler = Mock()
        mock_rich_handler_class.return_value = mock_rich_handler

        # noinspection PyTypeChecker
        handler = RichExtraStreamHandler(stream=sys.stderr)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)
        mock_rich_handler.emit.assert_called_once_with(record)

    @patch("pyclifer.core.log.handlers.RichHandler")
    def test_emit_fallback_on_exception(self, mock_rich_handler_class):
        """Test that emit falls back to the parent on exception."""
        mock_rich_handler = Mock()
        mock_rich_handler.emit.side_effect = ValueError("Test error")
        mock_rich_handler_class.return_value = mock_rich_handler

        # noinspection PyTypeChecker
        handler = RichExtraStreamHandler(stream=sys.stderr)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        with patch.object(handler.__class__.__bases__[0], "emit") as mock_parent_emit:
            handler.emit(record)
            mock_parent_emit.assert_called_once_with(record)

    @patch("pyclifer.core.log.handlers.RichHandler")
    def test_emit_recursion_error_is_reraised(self, mock_rich_handler_class):
        """RecursionError from emitting is re-raised, not swallowed."""
        mock_rich_handler = Mock()
        mock_rich_handler.emit.side_effect = RecursionError("infinite loop")
        mock_rich_handler_class.return_value = mock_rich_handler

        # noinspection PyTypeChecker
        handler = RichExtraStreamHandler(stream=sys.stderr)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="boom",
            args=(),
            exc_info=None,
        )

        with pytest.raises(RecursionError, match="infinite loop"):
            handler.emit(record)


class TestRichExtraFormatter:
    """Test RichExtraFormatter functionality."""

    @pytest.fixture
    def formatter(self):
        """Create a RichExtraFormatter for testing."""
        return RichExtraFormatter()

    def test_trace_level_formatting(self, formatter):
        """Test that TRACE level gets special formatting."""
        record = logging.LogRecord(
            name="test",
            level=TRACE,
            pathname="",
            lineno=0,
            msg="trace message",
            args=(),
            exc_info=None,
        )
        record.levelname = "TRACE"
        record.message = "trace message"

        with patch("pyclifer.core.log.formatters.style") as mock_style:
            mock_style.return_value = "STYLED_TRACE"
            result = formatter.formatMessage(record)
            mock_style.assert_called_once_with("TRACE", fg="blue", dim=True)

            assert result is not None
            assert isinstance(result, str)
            assert "trace message" in result or record.message in result

    def test_standard_level_formatting(self, formatter):
        """Test that standard levels use click-extra theming."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="info message",
            args=(),
            exc_info=None,
        )
        record.levelname = "INFO"
        record.message = "info message"

        with patch("pyclifer.core.log.formatters.get_default_theme") as mock_get_theme:
            mock_theme = Mock()
            mock_get_theme.return_value = mock_theme
            mock_info_style = Mock(return_value="STYLED_INFO")
            mock_theme.info = mock_info_style

            result = formatter.formatMessage(record)
            mock_info_style.assert_called_once_with("INFO")

            assert result is not None
            assert isinstance(result, str)
            assert "info message" in result or record.message in result

    def test_unknown_level_no_style_does_not_raise(self, formatter):
        """Test that an unrecognized level name with no theme style is handled gracefully."""
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="custom message",
            args=(),
            exc_info=None,
        )
        record.levelname = "CUSTOMBAD"
        record.message = "custom message"

        with patch("pyclifer.core.log.formatters.get_default_theme") as mock_get_theme:
            mock_theme = Mock()
            mock_get_theme.return_value = mock_theme
            mock_theme.configure_mock(**{"custombad": None})

            result = formatter.formatMessage(record)

        assert result is not None
        assert isinstance(result, str)

    def test_rich_record_attribute_applies_markup(self, formatter):
        """Test that a record with rich=True has its message processed as Rich markup."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="[bold]hello[/bold]",
            args=(),
            exc_info=None,
        )
        record.levelname = "INFO"
        record.message = "[bold]hello[/bold]"
        record.rich = True

        result = formatter.formatMessage(record)

        assert result is not None
        assert isinstance(result, str)


class TestSecretsMasker:
    """Test SecretsMasker security filtering functionality."""

    @pytest.fixture
    def masker(self):
        """Create a SecretsMasker for testing."""
        return SecretsMasker()

    def test_should_mask_sensitive_keys(self):
        """Test that sensitive keys are identified correctly."""
        from pyclifer.core.log.filters import should_hide_value_for_key

        sensitive_keys = [
            "password",
            "api_key",
            "token",
            "secret",
            "PASSWORD",
            " Token ",
        ]
        for key in sensitive_keys:
            assert should_hide_value_for_key(key) is True

    def test_should_not_mask_normal_keys(self):
        """Test that normal keys are not identified as sensitive."""
        from pyclifer.core.log.filters import should_hide_value_for_key

        normal_keys = ["username", "email", "name", "value", "data"]
        for key in normal_keys:
            assert should_hide_value_for_key(key) is False

    def test_masker_filters_sensitive_data(self, masker):
        """Test that SecretsMasker redacts sensitive information."""
        test_data = {
            "username": "john_doe",
            "password": "secret123",
            "api_key": "abc123def456",
        }

        redacted = masker.redact(test_data)

        assert redacted["username"] == "john_doe"
        assert redacted["password"] == "*CENSORED*"
        assert redacted["api_key"] == "*CENSORED*"

    def test_masker_handles_nested_structures(self, masker):
        """Test that SecretsMasker handles nested data structures."""
        test_data = {"config": {"database": {"host": "localhost", "password": "db_secret"}}}

        redacted = masker.redact(test_data)

        assert redacted["config"]["database"]["host"] == "localhost"
        assert redacted["config"]["database"]["password"] == "*CENSORED*"

    # noinspection PyTypeChecker
    def test_should_hide_value_for_key_non_string(self):
        """Test that non-string inputs are not flagged as sensitive."""
        from pyclifer.core.log.filters import should_hide_value_for_key

        assert should_hide_value_for_key(42) is False
        assert should_hide_value_for_key(None) is False

    def test_filter_returns_false_when_regex_is_none(self, masker):
        """filter() returns False when _regex is set to None."""
        masker._regex = None
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        assert masker.filter(record) is False

    def test_sensitive_fields_are_added_to_defaults(self):
        """sensitive_fields extends DEFAULT_FIELDS — defaults remain active."""
        masker = SecretsMasker(sensitive_fields=["bearer_token"])
        test_data = {"bearer_token": "abc", "password": "xyz"}
        redacted = masker.redact(test_data)
        assert redacted["bearer_token"] == "*CENSORED*"
        assert redacted["password"] == "*CENSORED*"

    def test_a_custom_field_unrelated_to_the_defaults_is_censored(self):
        """A name that contains no default field is masked only because it was declared.

        bearer_token would pass for the wrong reason: it contains the default field token.
        """
        masker = SecretsMasker(sensitive_fields=["mycode"])

        assert masker.redact({"mycode": "mc-777"}) == {"mycode": "*CENSORED*"}

    def test_a_custom_field_is_matched_whatever_its_case_and_surroundings(self):
        masker = SecretsMasker(sensitive_fields=["MyCode"])

        redacted = masker.redact({" MYCODE ": "a", "user_mycode_2": "b", "name": "c"})

        assert redacted == {" MYCODE ": "*CENSORED*", "user_mycode_2": "*CENSORED*", "name": "c"}

    def test_a_custom_field_does_not_leak_to_another_masker(self):
        SecretsMasker(sensitive_fields=["mycode"])

        assert SecretsMasker().redact({"mycode": "mc-777"}) == {"mycode": "mc-777"}

    def test_a_custom_field_is_censored_in_a_log_record(self):
        masker = SecretsMasker(sensitive_fields=["mycode"])
        record = logging.LogRecord(
            "t", logging.INFO, "", 0, "payload %s", ({"mycode": "mc-777"},), None
        )

        masker.filter(record)

        # LogRecord unwraps a lone dict argument, as it does for a real log call.
        assert record.args == {"mycode": "*CENSORED*"}

    def test_a_key_that_is_not_a_string_is_left_alone(self):
        """A security filter must never fail on a dict keyed by something other than text."""
        masker = SecretsMasker(sensitive_fields=["mycode"])

        data = {42: "value", ("a", "b"): "other"}

        assert masker.redact(data) == data

    def test_sensitive_fields_empty_list_behaves_like_none(self):
        """sensitive_fields=[] and sensitive_fields=None produce identical results."""
        masker_none = SecretsMasker(sensitive_fields=None)
        masker_empty = SecretsMasker(sensitive_fields=[])
        test_data = {"api_key": "secret123", "name": "alice"}
        assert masker_none.redact(test_data) == masker_empty.redact(test_data)

    def test_default_fields_always_present_with_sensitive_fields(self):
        """Passing sensitive_fields does not remove any DEFAULT_FIELDS entry."""
        masker = SecretsMasker(sensitive_fields=["custom_field"])
        for field_name in SecretsMasker.DEFAULT_FIELDS:
            data = {field_name: "should_be_censored"}
            redacted = masker.redact(data)
            assert redacted[field_name] == "*CENSORED*", f"{field_name} was not censored"

    def test_redact_all_dict(self, masker):
        """Test _redact_all censors all string values in a dict."""
        result = masker._redact_all({"key": "value"}, depth=0)
        assert result == {"key": "*CENSORED*"}

    def test_redact_all_list(self, masker):
        """Test _redact_all censors all string values in a list."""
        result = masker._redact_all(["a", "b"], depth=0)
        assert result == ["*CENSORED*", "*CENSORED*"]

    def test_redact_all_tuple(self, masker):
        """Test _redact_all censors all string values in a tuple and returns a tuple."""
        result = masker._redact_all(("a", "b"), depth=0)
        assert result == ("*CENSORED*", "*CENSORED*")

    def test_redact_all_non_string_scalar(self, masker):
        """Test _redact_all returns non-string scalars unchanged."""
        assert masker._redact_all(42, depth=0) == 42

    def test_redact_namedtuple(self, masker):
        """Test _redact handles named-tuples and redacts sensitive fields."""
        from collections import namedtuple

        Creds = namedtuple("Creds", ["username", "password"])
        result = masker.redact(Creds(username="user", password="secret"))
        assert result.username == "user"
        assert result.password == "*CENSORED*"

    def test_redact_list_in_non_sensitive_context(self, masker):
        """Test _redact traverses lists when the key is not sensitive."""
        result = masker.redact({"items": ["a", "b"]})
        assert result["items"] == ["a", "b"]

    def test_redact_exception_returns_item_unchanged(self, masker):
        """Test _redact returns the original item when an exception occurs during redaction."""
        with patch.object(masker, "_redact_all", side_effect=ValueError("boom")):
            result = masker.redact({"password": "secret"})
        assert result == {"password": "secret"}


class TestAddTraceMethod:
    """Test add_trace_method functionality."""

    def test_adds_trace_method_to_logger_class(self):
        """Test that add_trace_method adds trace() method to logger class."""
        mock_logger_class = type("MockLogger", (), {})

        add_trace_method(mock_logger_class)

        assert hasattr(mock_logger_class, "trace")
        # noinspection PyUnresolvedReferences
        assert callable(mock_logger_class.trace)

    def test_trace_method_logs_at_trace_level(self):
        """Test that trace() method logs at TRACE level."""
        mock_logger = Mock()
        mock_logger.isEnabledFor.return_value = True

        add_trace_method(mock_logger.__class__)

        mock_logger.trace("test trace message")

        mock_logger.isEnabledFor.assert_called_once_with(TRACE)
        mock_logger._log.assert_called_once()
        assert mock_logger._log.call_args.args == (TRACE, "test trace message", ())

    def test_trace_method_skips_log_when_level_disabled(self):
        """Test that trace() does not call _log when the TRACE level is disabled."""
        mock_logger = Mock()
        mock_logger.isEnabledFor.return_value = False

        add_trace_method(mock_logger.__class__)

        mock_logger.trace("should not be logged")

        mock_logger.isEnabledFor.assert_called_once_with(TRACE)
        mock_logger._log.assert_not_called()


class TestPycliferVerbosityOption:
    """Test PycliferVerbosityOption functionality."""

    @pytest.fixture
    def verbosity_option(self):
        """Create a PycliferVerbosityOption for testing."""
        return PycliferVerbosityOption()

    def test_initialization_with_pyclif_log_levels(self, verbosity_option):
        """Test that PycliferVerbosityOption uses PYCLIFER_LOG_LEVELS."""
        # noinspection PyUnresolvedReferences
        assert set(verbosity_option.type.choices) == set(PYCLIFER_LOG_LEVELS.keys())

    def test_initialization_default_params(self, verbosity_option):
        """Test PycliferVerbosityOption default parameter declarations."""
        assert "--verbosity" in verbosity_option.opts

    @patch("pyclifer.core.log.config.configure_rich_logging")
    def test_set_level_reconfigures_logging_with_the_secrets_settings_of_the_option(
        self, mock_configure
    ):
        """The handler rebuilt on a level change keeps the application's secrets settings."""
        option = PycliferVerbosityOption(enable_secrets_filter=False, sensitive_fields=["mycode"])
        mock_ctx = Mock()
        mock_ctx.meta = {}

        with patch.object(
            type(option), "all_loggers", new_callable=PropertyMock
        ) as mock_all_loggers:
            mock_all_loggers.return_value = iter([])
            with patch.object(option, "reset_loggers"):
                option.set_level(mock_ctx, Mock(), "DEBUG")

        mock_configure.assert_called_with(
            use_rich=True,
            enable_secrets_filter=False,
            sensitive_fields=["mycode"],
            mask_free_text=False,
            force_reconfigure=True,
        )

    @patch("pyclifer.core.log.config.configure_rich_logging")
    def test_secrets_settings_default_to_the_filter_with_the_default_fields(
        self, mock_configure, verbosity_option
    ):
        mock_ctx = Mock()
        mock_ctx.meta = {}

        with patch.object(
            type(verbosity_option), "all_loggers", new_callable=PropertyMock
        ) as mock_all_loggers:
            mock_all_loggers.return_value = iter([])
            with patch.object(verbosity_option, "reset_loggers"):
                verbosity_option.set_level(mock_ctx, Mock(), "DEBUG")

        mock_configure.assert_called_with(
            use_rich=True,
            enable_secrets_filter=True,
            sensitive_fields=None,
            mask_free_text=False,
            force_reconfigure=True,
        )

    @staticmethod
    def _set_level(option, meta, value, source):
        """Call set_level with a context whose parameter was filled from the given source."""
        mock_ctx = Mock()
        mock_ctx.meta = meta
        mock_ctx.get_parameter_source.return_value = source
        with (
            patch("pyclifer.core.log.config.configure_rich_logging"),
            patch.object(
                type(option), "all_loggers", new_callable=PropertyMock
            ) as mock_all_loggers,
        ):
            mock_all_loggers.return_value = iter([])
            with patch.object(option, "reset_loggers"):
                option.set_level(mock_ctx, Mock(), value)
        return meta

    def test_a_default_value_never_overrides_a_level_already_chosen(self, verbosity_option):
        """The default a sub-command's copy of the option carries is not a choice."""
        meta = self._set_level(
            verbosity_option,
            {"click_extra.verbosity_level": "ERROR"},
            "WARNING",
            ParameterSource.DEFAULT,
        )

        assert meta["click_extra.verbosity_level"] == "ERROR"

    def test_a_chosen_level_overrides_a_level_that_came_from_a_default(self, verbosity_option):
        """A stricter level typed by the user replaces the default set earlier."""
        meta = {"click_extra.verbosity_level": "WARNING", "pyclifer.verbosity_from_default": True}

        self._set_level(verbosity_option, meta, "ERROR", ParameterSource.COMMANDLINE)

        assert meta["click_extra.verbosity_level"] == "ERROR"

    def test_a_chosen_level_from_the_environment_counts_as_a_choice(self, verbosity_option):
        meta = {"click_extra.verbosity_level": "WARNING", "pyclifer.verbosity_from_default": True}

        self._set_level(verbosity_option, meta, "CRITICAL", ParameterSource.ENVIRONMENT)

        assert meta["click_extra.verbosity_level"] == "CRITICAL"

    def test_two_chosen_levels_keep_the_most_verbose(self, verbosity_option):
        """Several options can each set a level: the most verbose one still wins."""
        meta = {"click_extra.verbosity_level": "DEBUG"}

        self._set_level(verbosity_option, meta, "ERROR", ParameterSource.COMMANDLINE)

        assert meta["click_extra.verbosity_level"] == "DEBUG"

    def test_the_first_level_is_recorded_with_where_it_came_from(self, verbosity_option):
        from_default = self._set_level(
            {}.copy() or verbosity_option, {}, "WARNING", ParameterSource.DEFAULT
        )
        from_user = self._set_level(verbosity_option, {}, "ERROR", ParameterSource.COMMANDLINE)

        assert from_default["pyclifer.verbosity_from_default"] is True
        assert from_user["pyclifer.verbosity_from_default"] is False

    @patch("pyclifer.core.log.config.configure_rich_logging")
    def test_set_level_more_verbose_overrides_current_level(self, mock_configure, verbosity_option):
        """set_level proceeds when new level is more verbose than current (not skipped)."""
        mock_ctx = Mock()
        mock_ctx.meta = {"click_extra.verbosity_level": "WARNING"}
        mock_param = Mock()

        with patch.object(
            type(verbosity_option), "all_loggers", new_callable=PropertyMock
        ) as mock_all_loggers:
            mock_all_loggers.return_value = iter([])
            with patch.object(verbosity_option, "reset_loggers"):
                verbosity_option.set_level(mock_ctx, mock_param, "DEBUG")

        assert mock_ctx.meta["click_extra.verbosity_level"] == "DEBUG"

    @patch("pyclifer.core.log.config.configure_rich_logging")
    def test_set_level_calls_configure_rich_logging(self, mock_configure, verbosity_option):
        """Test that set_level calls configure_rich_logging."""
        mock_ctx = Mock()
        mock_ctx.meta = {}
        mock_param = Mock()

        mock_logger1 = Mock()
        mock_logger2 = Mock()
        mock_loggers = [mock_logger1, mock_logger2]

        with patch.object(
            type(verbosity_option), "all_loggers", new_callable=PropertyMock
        ) as mock_all_loggers:
            mock_all_loggers.return_value = iter(mock_loggers)

            with patch.object(verbosity_option, "reset_loggers"):
                # noinspection PyTypeChecker
                verbosity_option.set_level(mock_ctx, mock_param, "DEBUG")

        mock_configure.assert_called_once_with(
            use_rich=True,
            enable_secrets_filter=True,
            sensitive_fields=None,
            mask_free_text=False,
            force_reconfigure=True,
        )

        mock_logger1.setLevel.assert_called_once_with(PYCLIFER_LOG_LEVELS["DEBUG"])
        mock_logger2.setLevel.assert_called_once_with(PYCLIFER_LOG_LEVELS["DEBUG"])

        assert mock_ctx.meta["click_extra.verbosity_level"] == "DEBUG"
        assert mock_ctx.meta["click_extra.verbosity"] == "DEBUG"

    @patch("pyclifer.core.log.config.configure_rich_logging")
    def test_set_level_uses_pyclif_dot_log_file_keys(self, mock_configure, verbosity_option):
        """set_level reads pyclifer.log_file_path and pyclifer.log_file_level,
        not the old underscore names.

        When a log file is active, the effective logger level must be min(verbosity, file_level).
        If the wrong key names were read, the file branch would be skipped and the logger
        would be set to the verbosity level alone.
        """
        mock_ctx = Mock()
        mock_ctx.meta = {
            "pyclifer.log_file_path": "/tmp/test.log",
            "pyclifer.log_file_level": "DEBUG",
        }
        mock_param = Mock()
        mock_logger = Mock()

        with patch.object(
            type(verbosity_option), "all_loggers", new_callable=PropertyMock
        ) as mock_all_loggers:
            mock_all_loggers.return_value = iter([mock_logger])
            with patch.object(verbosity_option, "reset_loggers"):
                # noinspection PyTypeChecker
                verbosity_option.set_level(mock_ctx, mock_param, "WARNING")

        # file_level=DEBUG (10) < verbosity=WARNING (30) → min level is DEBUG
        expected_level = min(PYCLIFER_LOG_LEVELS["WARNING"], PYCLIFER_LOG_LEVELS["DEBUG"])
        mock_logger.setLevel.assert_called_once_with(expected_level)


class TestLoggerFactoryFunctions:
    """Test logger factory functions."""

    @patch("pyclifer.core.log.config.get_configured_logger")
    def test_get_logger_delegates_to_get_configured_logger(self, mock_get_configured):
        """Test that get_logger delegates to get_configured_logger."""
        mock_logger = Mock()
        mock_get_configured.return_value = mock_logger

        result = get_logger("test_logger")

        mock_get_configured.assert_called_once_with("test_logger")
        assert result is mock_logger

    @patch("pyclifer.core.log.config.logging.getLogger")
    def test_get_configured_logger_with_name(self, mock_get_logger):
        """Test get_configured_logger with a custom name."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        result = get_configured_logger("custom_logger")

        mock_get_logger.assert_called_once_with("custom_logger")
        assert result is mock_logger

    @patch("pyclifer.core.log.config.logging.getLogger")
    def test_get_configured_logger_default_name(self, mock_get_logger):
        """Test get_configured_logger with the default app name."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        result = get_configured_logger()

        mock_get_logger.assert_called_once()
        args = mock_get_logger.call_args[0]
        assert len(args) == 1
        assert result is mock_logger

    def test_get_configured_logger_name_annotation_accepts_none(self) -> None:
        """name parameter annotation must be str | None, not str, since default is None."""
        import inspect

        sig = inspect.signature(get_configured_logger)
        annotation = sig.parameters["name"].annotation
        assert annotation == str | None, (
            f"Expected 'str | None', got {annotation!r}. "
            "Default is None but annotation was str — incorrect type."
        )


class TestLoggingIntegration:
    """Integration tests for the complete logging system."""

    def test_logging_system_can_be_configured(self):
        """Test that the complete logging system can be configured without errors."""
        try:
            configure_rich_logging(force_reconfigure=True)
            logger = get_logger("integration_test")

            assert hasattr(logger, "trace")
            # noinspection PyUnresolvedReferences
            assert callable(logger.trace)

        except Exception as e:
            pytest.fail(f"Logging system configuration failed: {e}")

    def test_logger_hierarchy_inheritance(self):
        """Test that loggers properly inherit configuration."""
        configure_rich_logging(force_reconfigure=True)

        parent_logger = get_logger("parent")
        child_logger = get_logger("parent.child")

        assert hasattr(parent_logger, "trace")
        assert hasattr(child_logger, "trace")

    @patch("pyclifer.core.log.handlers.RichHandler")
    def test_secrets_filtering_in_real_logging(self, mock_rich_handler_class):
        """Test that secrets are actually filtered in real logging scenarios."""
        mock_rich_handler = Mock()
        mock_rich_handler_class.return_value = mock_rich_handler

        # noinspection PyArgumentEqualDefault,PyTypeChecker
        handler = RichExtraStreamHandler(stream=sys.stderr, enable_secrets_filter=True)

        logger = logging.getLogger("secrets_test")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.info("User logged in with password: secret123")

        secrets_filters = [f for f in handler.filters if isinstance(f, SecretsMasker)]
        assert len(secrets_filters) == 1


class TestPlainConsoleLogging:
    """configure_rich_logging(use_rich=False) installs click-extra's standard console handler."""

    @pytest.fixture(autouse=True)
    def clean_root_logger(self):
        """Start from a root logger with no handler and give the original ones back."""
        root = logging.getLogger()
        original = list(root.handlers)
        root.handlers.clear()
        yield root
        for handler in root.handlers:
            if handler not in original:
                handler.close()
        root.handlers[:] = original

    @staticmethod
    def _console_handlers(root):
        """The handlers writing to a stream, files left out."""
        return [
            h
            for h in root.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
            and not type(h).__module__.startswith("_pytest")
        ]

    def test_a_standard_stream_handler_replaces_the_rich_one(self, clean_root_logger):
        from pyclifer.core.log import configure_rich_logging

        configure_rich_logging(use_rich=False, force_reconfigure=True)

        handlers = self._console_handlers(clean_root_logger)
        assert len(handlers) == 1
        assert not isinstance(handlers[0], RichExtraStreamHandler)

    def test_the_secrets_filter_is_on_by_default(self, clean_root_logger):
        from pyclifer.core.log import configure_rich_logging

        configure_rich_logging(use_rich=False, force_reconfigure=True)

        (handler,) = self._console_handlers(clean_root_logger)
        assert [type(f) for f in handler.filters] == [SecretsMasker]

    def test_the_secrets_filter_can_be_turned_off(self, clean_root_logger):
        from pyclifer.core.log import configure_rich_logging

        configure_rich_logging(use_rich=False, enable_secrets_filter=False, force_reconfigure=True)

        (handler,) = self._console_handlers(clean_root_logger)
        assert handler.filters == []

    def test_sensitive_fields_reach_the_filter(self, clean_root_logger):
        from pyclifer.core.log import configure_rich_logging

        configure_rich_logging(use_rich=False, sensitive_fields=["mycode"], force_reconfigure=True)

        (handler,) = self._console_handlers(clean_root_logger)
        assert handler.filters[0].redact({"mycode": "mc-777"}) == {"mycode": "*CENSORED*"}

    @patch("pyclifer.core.log.config.basicConfig")
    def test_a_handler_it_did_not_create_is_left_untouched(self, _basic_config, clean_root_logger):
        """Only the handler basicConfig creates is marked and filtered, never a foreign one."""
        from pyclifer.core.log import configure_rich_logging

        foreign = logging.StreamHandler()
        clean_root_logger.addHandler(foreign)

        configure_rich_logging(use_rich=False, force_reconfigure=True)

        assert foreign.filters == []
        assert not hasattr(foreign, "_pyclifer_console")

    def test_a_file_handler_survives_the_reconfiguration(self, clean_root_logger, tmp_path):
        from logging.handlers import TimedRotatingFileHandler

        from pyclifer.core.log import configure_rich_logging

        file_handler = TimedRotatingFileHandler(tmp_path / "keep.log")
        clean_root_logger.addHandler(file_handler)

        configure_rich_logging(use_rich=False, force_reconfigure=True)

        assert file_handler in clean_root_logger.handlers

    def test_without_force_an_existing_console_handler_is_left_alone(self, clean_root_logger):
        from pyclifer.core.log import configure_rich_logging

        configure_rich_logging(use_rich=False, force_reconfigure=True)
        (first,) = self._console_handlers(clean_root_logger)

        configure_rich_logging(use_rich=False, enable_secrets_filter=False)

        assert self._console_handlers(clean_root_logger) == [first]


class TestSecretsMaskerFreeText:
    """With mask_free_text, secrets written as key=value inside a message are masked too."""

    @staticmethod
    def _masked(text: str, **options) -> str:
        return SecretsMasker(mask_free_text=True, **options).redact_text(text)

    def test_free_text_is_left_alone_by_default(self):
        record = logging.LogRecord("t", logging.INFO, "", 0, "password=hunter2", (), None)

        SecretsMasker().filter(record)

        assert record.getMessage() == "password=hunter2"

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("login with password=hunter2 for bob", "login with password=*CENSORED* for bob"),
            ("password: hunter2", "password: *CENSORED*"),
            ('{"password": "hunter2", "user": "bob"}', '{"password": "*CENSORED*", "user": "bob"}'),
            ('{"password": "my long phrase"}', '{"password": "*CENSORED*"}'),
            ("GET /api?api_key=abc123&user=bob", "GET /api?api_key=*CENSORED*&user=bob"),
            ("Authorization: Bearer eyJhb.abc.def", "Authorization: Bearer *CENSORED*"),
            ("refresh_token=rt_9 expires in 3600", "refresh_token=*CENSORED* expires in 3600"),
            ("PASSWORD=HunTer2", "PASSWORD=*CENSORED*"),
        ],
    )
    def test_the_value_of_a_sensitive_key_is_masked(self, text, expected):
        assert self._masked(text) == expected

    def test_a_custom_field_is_masked(self):
        assert self._masked("mycode=mc-777 accepted", sensitive_fields=["mycode"]) == (
            "mycode=*CENSORED* accepted"
        )

    @pytest.mark.parametrize(
        "text",
        [
            "the password is hunter2",
            "token expired for user bob",
            "/etc/secret/file.txt not found",
            "nothing sensitive here",
        ],
    )
    def test_text_without_a_key_and_a_separator_is_kept(self, text):
        assert self._masked(text) == text

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("used max_tokens=100 out of 4000", "used max_tokens=*CENSORED* out of 4000"),
            ("token: expired, please log in again", "token: *CENSORED*, please log in again"),
        ],
    )
    def test_known_false_positives_are_masked(self, text, expected):
        """A name that contains a sensitive field is masked, whatever its value means."""
        assert self._masked(text) == expected

    @pytest.mark.parametrize(
        "text",
        [
            "a" * 50_000,
            "Zm9v" * 12_500,
            "/usr/lib/x." * 4_500,
        ],
        ids=["word-characters", "base64-like", "paths"],
    )
    def test_a_long_text_without_a_separator_is_masked_in_bounded_time(self, text):
        """The cost grows linearly with the text, not with its square."""
        started = time.perf_counter()

        assert self._masked(text) == text

        assert time.perf_counter() - started < 0.5

    def test_masking_twice_changes_nothing(self):
        once = self._masked("password=hunter2")

        assert self._masked(once) == once

    def test_a_message_is_masked_once_its_arguments_are_filled_in(self):
        record = logging.LogRecord("t", logging.INFO, "", 0, "pwd=%s", ("hunter2",), None)

        SecretsMasker(mask_free_text=True).filter(record)

        assert record.getMessage() == "pwd=*CENSORED*"

    def test_structured_arguments_are_still_masked_by_key(self):
        record = logging.LogRecord(
            "t", logging.INFO, "", 0, "payload %s", ({"password": "hunter2", "user": "bob"},), None
        )

        SecretsMasker(mask_free_text=True).filter(record)

        assert "hunter2" not in record.getMessage()
        assert "bob" in record.getMessage()

    def test_a_malformed_message_does_not_break_the_filter(self):
        record = logging.LogRecord("t", logging.INFO, "", 0, "%d", ("not a number",), None)

        assert SecretsMasker(mask_free_text=True).filter(record) is True

    def test_a_message_that_is_not_text_is_masked_too(self):
        record = logging.LogRecord(
            "t", logging.INFO, "", 0, ValueError("password=hunter2"), (), None
        )

        SecretsMasker(mask_free_text=True).filter(record)

        assert record.getMessage() == "password=*CENSORED*"


_LEAKED = "tok-9f3a7c"  # the value that must never reach the output


def _exc_info_of(exception: BaseException):
    """Raise and catch an exception, then return its exc_info like logging records it."""
    try:
        raise exception
    except BaseException:
        return sys.exc_info()


def _record_with(exception: BaseException) -> logging.LogRecord:
    """A log record carrying the exception, as log.exception() builds it."""
    return logging.LogRecord("t", logging.ERROR, "", 0, "call failed", (), _exc_info_of(exception))


def _filtered(exception: BaseException, **options) -> logging.LogRecord:
    """The record, once the masker has seen it."""
    record = _record_with(exception)
    SecretsMasker(mask_free_text=True, **options).filter(record)
    return record


class TestSecretsMaskerExceptions:
    """With mask_free_text, the message of an exception is masked in the traceback too."""

    def test_the_message_of_the_exception_is_masked(self):
        record = _filtered(ValueError(f"login failed token={_LEAKED}"))

        assert str(record.exc_info[1]) == "login failed token=*CENSORED*"

    def test_the_traceback_text_no_longer_holds_the_secret(self):
        import traceback

        record = _filtered(ValueError(f"login failed token={_LEAKED}"))

        assert _LEAKED not in "".join(traceback.format_exception(*record.exc_info))

    def test_exceptions_are_left_alone_by_default(self):
        record = _record_with(ValueError(f"token={_LEAKED}"))

        SecretsMasker().filter(record)

        assert _LEAKED in str(record.exc_info[1])

    def test_the_type_name_and_module_are_kept(self):
        record = _filtered(ValueError(f"token={_LEAKED}"))

        exc_type, exc_value, _ = record.exc_info
        assert (exc_type.__name__, exc_type.__module__) == ("ValueError", "builtins")
        assert isinstance(exc_value, ValueError)

    def test_the_traceback_object_is_kept(self):
        original = _exc_info_of(ValueError(f"token={_LEAKED}"))
        record = logging.LogRecord("t", logging.ERROR, "", 0, "x", (), original)

        SecretsMasker(mask_free_text=True).filter(record)

        assert record.exc_info[2] is original[2]

    def test_the_original_exception_is_not_modified(self):
        original = ValueError(f"token={_LEAKED}")

        _filtered(original)

        assert str(original) == f"token={_LEAKED}"

    @pytest.mark.parametrize(
        "exception",
        [
            OSError(13, f"denied token={_LEAKED}", "/tmp/x"),
            KeyError(f"token={_LEAKED}"),
        ],
        ids=["oserror", "keyerror"],
    )
    def test_exceptions_that_format_their_arguments_are_masked(self, exception):
        record = _filtered(exception)

        assert _LEAKED not in str(record.exc_info[1])

    def test_an_exception_with_its_own_constructor_and_str_is_masked(self):
        class ApiError(Exception):
            def __init__(self, code, url):
                super().__init__(f"code {code}")
                self.code, self.url = code, url

            def __str__(self):
                return f"ApiError {self.code} {self.url}"

        record = _filtered(ApiError(7, f"https://h/?token={_LEAKED}"))

        assert str(record.exc_info[1]) == "ApiError 7 https://h/?token=*CENSORED*"
        assert record.exc_info[1].code == 7

    def test_the_cause_is_masked(self):
        try:
            try:
                raise ValueError(f"inner token={_LEAKED}")
            except ValueError as inner:
                raise RuntimeError("outer") from inner
        except RuntimeError as outer:
            record = logging.LogRecord("t", 40, "", 0, "x", (), sys.exc_info())
            assert outer is record.exc_info[1]

        SecretsMasker(mask_free_text=True).filter(record)

        assert str(record.exc_info[1]) == "outer"
        assert str(record.exc_info[1].__cause__) == "inner token=*CENSORED*"

    def test_the_context_is_masked(self):
        try:
            try:
                raise ValueError(f"inner token={_LEAKED}")
            except ValueError:
                raise RuntimeError("outer")  # noqa: B904 - the implicit context is the point
        except RuntimeError:
            record = logging.LogRecord("t", 40, "", 0, "x", (), sys.exc_info())

        SecretsMasker(mask_free_text=True).filter(record)

        assert str(record.exc_info[1].__context__) == "inner token=*CENSORED*"

    def test_the_traceback_of_the_cause_is_kept(self):
        import traceback

        def fail_inside_the_cause():
            raise ValueError(f"inner token={_LEAKED}")

        try:
            try:
                fail_inside_the_cause()
            except ValueError as inner:
                raise RuntimeError("outer") from inner
        except RuntimeError:
            record = logging.LogRecord("t", 40, "", 0, "x", (), sys.exc_info())

        SecretsMasker(mask_free_text=True).filter(record)

        text = "".join(traceback.format_exception(*record.exc_info))
        assert "in fail_inside_the_cause" in text

    def test_a_chain_that_loops_back_does_not_loop_forever(self):
        first, second = ValueError(f"a token={_LEAKED}"), ValueError("b")
        first.__cause__, second.__cause__ = second, first

        record = _filtered(first)

        assert record.exc_info[1].__cause__.__cause__ is record.exc_info[1]

    def test_an_implicit_context_is_still_shown(self):
        """Setting the cause of the copy hides the context unless the flag is given back."""
        import traceback

        try:
            try:
                raise ValueError(f"inner token={_LEAKED}")
            except ValueError:
                raise RuntimeError("outer")  # noqa: B904 - the implicit context is the point
        except RuntimeError:
            record = logging.LogRecord("t", 40, "", 0, "x", (), sys.exc_info())

        SecretsMasker(mask_free_text=True).filter(record)

        text = "".join(traceback.format_exception(*record.exc_info))
        assert "During handling of the above exception" in text
        assert "inner token=*CENSORED*" in text

    def test_the_suppress_context_flag_is_kept(self):
        try:
            try:
                raise ValueError("inner")
            except ValueError:
                raise RuntimeError("outer") from None
        except RuntimeError:
            record = logging.LogRecord("t", 40, "", 0, "x", (), sys.exc_info())

        SecretsMasker(mask_free_text=True).filter(record)

        assert record.exc_info[1].__suppress_context__ is True

    @pytest.mark.skipif(sys.version_info < (3, 11), reason="ExceptionGroup is 3.11+")
    def test_the_exceptions_of_a_group_are_masked(self):
        group = ExceptionGroup("batch", [ValueError(f"one token={_LEAKED}"), KeyError("two")])  # noqa: F821

        record = _filtered(group)

        assert isinstance(record.exc_info[1], ExceptionGroup)  # noqa: F821
        first, second = record.exc_info[1].exceptions
        assert str(first) == "one token=*CENSORED*"
        assert isinstance(second, KeyError)

    @pytest.mark.skipif(sys.version_info < (3, 11), reason="notes are 3.11+")
    def test_the_notes_of_an_exception_are_masked(self):
        exception = ValueError("failed")
        exception.add_note(f"retry with token={_LEAKED}")

        record = _filtered(exception)

        assert record.exc_info[1].__notes__ == ["retry with token=*CENSORED*"]

    def test_a_text_cached_by_another_handler_is_masked(self):
        record = _record_with(ValueError("failed"))
        record.exc_text = f"ValueError: token={_LEAKED}"

        SecretsMasker(mask_free_text=True).filter(record)

        assert record.exc_text == "ValueError: token=*CENSORED*"

    def test_a_record_without_exception_is_untouched(self):
        record = logging.LogRecord("t", logging.INFO, "", 0, "hello", (), None)

        SecretsMasker(mask_free_text=True).filter(record)

        assert (record.exc_info, record.exc_text) == (None, None)

    def test_an_exception_that_cannot_be_copied_is_replaced_by_its_masked_text(self):
        """The filter must never let the secret through, nor break the logging."""

        class Hostile(Exception):
            def __new__(cls, *args):
                if args:
                    raise TypeError("cannot copy")
                return super().__new__(cls)

        exception = Exception.__new__(Hostile)
        exception.args = (f"token={_LEAKED}",)

        record = _filtered(exception)

        assert str(record.exc_info[1]) == "token=*CENSORED*"
        assert record.exc_info[2] is not None

    def test_a_masked_record_is_not_masked_again(self):
        record = _record_with(ValueError(f"token={_LEAKED}"))
        masker = SecretsMasker(mask_free_text=True)
        masker.filter(record)
        once = record.exc_info[1]

        masker.filter(record)

        assert record.exc_info[1] is once


class TestExceptionMaskingEndToEnd:
    """What a handler really writes for log.exception(), Rich and plain."""

    @staticmethod
    def _log_exception(handler: logging.Handler) -> None:
        logger = logging.getLogger("pyclifer.test.exception_masking")
        logger.handlers[:] = [handler]
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        try:
            raise ConnectionError(f"GET /x failed token={_LEAKED}")
        except ConnectionError:
            logger.exception("call failed")

    def test_rich_masks_the_message_and_keeps_its_traceback_panel(self, capsys):
        handler = RichExtraStreamHandler(mask_free_text=True)  # writes to the captured stderr

        self._log_exception(handler)

        output = capsys.readouterr().err
        assert _LEAKED not in output
        assert "token=*CENSORED*" in output
        assert "Traceback" in output
        assert "╭" in output  # the Rich panel, not the plain "Traceback (most recent call last)"

    def test_plain_masks_the_message_of_the_exception(self):
        from io import StringIO

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.addFilter(SecretsMasker(mask_free_text=True))
        handler.setFormatter(logging.Formatter("%(message)s"))

        self._log_exception(handler)

        output = stream.getvalue()
        assert "ConnectionError: GET /x failed token=*CENSORED*" in output
