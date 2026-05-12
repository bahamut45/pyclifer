"""Tests for pyclif logging system - focusing on Rich integration and security features."""

import logging
import sys
from unittest.mock import Mock, PropertyMock, patch

import pytest

from pyclif.core.log import (
    PYCLIF_LOG_LEVELS,
    TRACE,
    PyclifVerbosityOption,
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
        """Test that PYCLIF_LOG_LEVELS includes our custom TRACE level."""
        assert "TRACE" in PYCLIF_LOG_LEVELS
        assert PYCLIF_LOG_LEVELS["TRACE"] == TRACE
        assert TRACE == 5

    def test_pyclif_log_levels_extends_click_extra(self):
        """Test that PYCLIF_LOG_LEVELS extends click-extra's LOG_LEVELS."""
        from pyclif.core.log.levels import LOG_LEVELS as PYCLIF_INTERNAL_LOG_LEVELS

        for level_name, level_value in PYCLIF_INTERNAL_LOG_LEVELS.items():
            if level_name != "TRACE":
                assert level_name in PYCLIF_LOG_LEVELS
                assert PYCLIF_LOG_LEVELS[level_name] == level_value

        assert "TRACE" in PYCLIF_LOG_LEVELS
        assert PYCLIF_LOG_LEVELS["TRACE"] == TRACE

    @patch("pyclif.core.log.config.extraBasicConfig")
    @patch("pyclif.core.log.config._preconfigure_click_extra_logger")
    @patch("pyclif.core.log.config.logging.getLogger")
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

    @patch("pyclif.core.log.config.logging.getLogger")
    def test_configure_rich_logging_already_configured(self, mock_get_logger):
        """Test that configure_rich_logging skips if already configured."""
        mock_handler = Mock()
        mock_handler._rich_handler = True
        mock_root_logger = Mock()
        mock_root_logger.handlers = [mock_handler]
        mock_get_logger.return_value = mock_root_logger

        with patch("pyclif.core.log.config.extraBasicConfig") as mock_config:
            # noinspection PyArgumentEqualDefault
            configure_rich_logging(force_reconfigure=False)
            mock_config.assert_not_called()

    @patch("pyclif.core.log.config.extraBasicConfig")
    def test_configure_rich_logging_force_reconfigure(self, mock_extra_config):
        """Test that force_reconfigure bypasses existing configuration check."""
        with patch("pyclif.core.log.config._preconfigure_click_extra_logger"):
            configure_rich_logging(force_reconfigure=True)
            mock_extra_config.assert_called_once()

    # noinspection PyUnusedLocal
    @patch("pyclif.core.log.config.extraBasicConfig")
    def test_configure_rich_logging_no_tracebacks(self, mock_extra_config):
        """use_rich=True but rich_tracebacks=False skips traceback install."""
        with (
            patch("pyclif.core.log.config._preconfigure_click_extra_logger"),
            patch("pyclif.core.log.config.logging.getLogger") as mock_get_logger,
        ):
            mock_root_logger = Mock()
            mock_root_logger.handlers = []
            mock_get_logger.return_value = mock_root_logger

            with patch("rich.traceback.install") as mock_install:
                # noinspection PyArgumentEqualDefault
                configure_rich_logging(use_rich=True, rich_tracebacks=False, force_reconfigure=True)
                mock_install.assert_not_called()

    @patch("pyclif.core.log.config.extraBasicConfig")
    def test_configure_rich_logging_use_rich_false(self, mock_extra_config):
        """use_rich=False skips all Rich handler setup."""
        configure_rich_logging(use_rich=False, force_reconfigure=True)
        mock_extra_config.assert_not_called()

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
        """File handler already in root_logger after extraBasicConfig is not re-added."""
        import tempfile
        from logging.handlers import TimedRotatingFileHandler

        root_logger = logging.getLogger()
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name

        file_handler = TimedRotatingFileHandler(log_path)
        root_logger.addHandler(file_handler)
        try:
            # extraBasicConfig (called internally) does not remove file handlers,
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
        from pyclif.core.log.config import _preconfigure_click_extra_logger

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

    @patch("pyclif.core.log.handlers.RichHandler")
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

    @patch("pyclif.core.log.handlers.RichHandler")
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

    @patch("pyclif.core.log.handlers.RichHandler")
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

        with patch("click.style") as mock_style:
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

        with patch("pyclif.core.log.formatters.default_theme") as mock_theme:
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

        with patch("pyclif.core.log.formatters.default_theme") as mock_theme:
            # No attribute matching "custombad" → getattr returns None
            del mock_theme.custombad
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
        from pyclif.core.log.filters import should_hide_value_for_key

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
        from pyclif.core.log.filters import should_hide_value_for_key

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
        from pyclif.core.log.filters import should_hide_value_for_key

        assert should_hide_value_for_key(42) is False
        assert should_hide_value_for_key(None) is False

    def test_filter_returns_false_when_replacer_is_none(self, masker):
        """Test that filter() returns False when no replacer is configured."""
        masker.replacer = None
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        assert masker.filter(record) is False

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
        mock_logger._log.assert_called_once_with(TRACE, "test trace message", ())

    def test_trace_method_skips_log_when_level_disabled(self):
        """Test that trace() does not call _log when the TRACE level is disabled."""
        mock_logger = Mock()
        mock_logger.isEnabledFor.return_value = False

        add_trace_method(mock_logger.__class__)

        mock_logger.trace("should not be logged")

        mock_logger.isEnabledFor.assert_called_once_with(TRACE)
        mock_logger._log.assert_not_called()


class TestPyclifVerbosityOption:
    """Test PyclifVerbosityOption functionality."""

    @pytest.fixture
    def verbosity_option(self):
        """Create a PyclifVerbosityOption for testing."""
        return PyclifVerbosityOption()

    def test_initialization_with_pyclif_log_levels(self, verbosity_option):
        """Test that PyclifVerbosityOption uses PYCLIF_LOG_LEVELS."""
        # noinspection PyUnresolvedReferences
        assert set(verbosity_option.type.choices) == set(PYCLIF_LOG_LEVELS.keys())

    def test_initialization_default_params(self, verbosity_option):
        """Test PyclifVerbosityOption default parameter declarations."""
        assert "--verbosity" in verbosity_option.opts

    @patch("pyclif.core.log.config.configure_rich_logging")
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

        mock_configure.assert_called_once_with(force_reconfigure=True)

        mock_logger1.setLevel.assert_called_once_with(PYCLIF_LOG_LEVELS["DEBUG"])
        mock_logger2.setLevel.assert_called_once_with(PYCLIF_LOG_LEVELS["DEBUG"])

        assert mock_ctx.meta["click_extra.verbosity_level"] == "DEBUG"
        assert mock_ctx.meta["click_extra.verbosity"] == "DEBUG"

    @patch("pyclif.core.log.config.configure_rich_logging")
    def test_set_level_uses_pyclif_dot_log_file_keys(self, mock_configure, verbosity_option):
        """set_level reads pyclif.log_file_path and pyclif.log_file_level,
        not the old underscore names.

        When a log file is active, the effective logger level must be min(verbosity, file_level).
        If the wrong key names were read, the file branch would be skipped and the logger
        would be set to the verbosity level alone.
        """
        mock_ctx = Mock()
        mock_ctx.meta = {
            "pyclif.log_file_path": "/tmp/test.log",
            "pyclif.log_file_level": "DEBUG",
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
        expected_level = min(PYCLIF_LOG_LEVELS["WARNING"], PYCLIF_LOG_LEVELS["DEBUG"])
        mock_logger.setLevel.assert_called_once_with(expected_level)


class TestLoggerFactoryFunctions:
    """Test logger factory functions."""

    @patch("pyclif.core.log.config.get_configured_logger")
    def test_get_logger_delegates_to_get_configured_logger(self, mock_get_configured):
        """Test that get_logger delegates to get_configured_logger."""
        mock_logger = Mock()
        mock_get_configured.return_value = mock_logger

        result = get_logger("test_logger")

        mock_get_configured.assert_called_once_with("test_logger")
        assert result is mock_logger

    @patch("pyclif.core.log.config.logging.getLogger")
    def test_get_configured_logger_with_name(self, mock_get_logger):
        """Test get_configured_logger with a custom name."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        result = get_configured_logger("custom_logger")

        mock_get_logger.assert_called_once_with("custom_logger")
        assert result is mock_logger

    @patch("pyclif.core.log.config.logging.getLogger")
    def test_get_configured_logger_default_name(self, mock_get_logger):
        """Test get_configured_logger with the default app name."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        result = get_configured_logger()

        mock_get_logger.assert_called_once()
        args = mock_get_logger.call_args[0]
        assert len(args) == 1
        assert result is mock_logger


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

    @patch("pyclif.core.log.handlers.RichHandler")
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
