"""Unit tests for the context module."""

from unittest.mock import patch

import pytest
from rich.console import Console

from pyclifer.core.context import BaseContext, ContextException
from pyclifer.core.mixins.output import OutputFormatMixin
from pyclifer.core.mixins.rich import RichHelpersMixin


class TestContextException:
    """Test suite for the ContextException class."""

    def test_context_exception_raises(self) -> None:
        """Test that ContextException can be raised and caught properly."""
        error_message = "A context error occurred"

        with pytest.raises(ContextException) as exc_info:
            raise ContextException(error_message)

        assert str(exc_info.value) == error_message
        assert isinstance(exc_info.value, Exception)


class TestBaseContext:
    """Test suite for the BaseContext class."""

    @patch("sys.stdout.isatty")
    def test_initialization_with_tty(self, mock_isatty) -> None:
        """Test BaseContext initialization when running in a real terminal (TTY)."""
        mock_isatty.return_value = True

        context = BaseContext()

        assert isinstance(context.console, Console)
        assert context.is_atty is True
        assert context.output_format is None

    @patch("sys.stdout.isatty")
    def test_initialization_without_tty(self, mock_isatty) -> None:
        """Test BaseContext initialization when output is piped or redirected (no TTY)."""
        mock_isatty.return_value = False

        context = BaseContext()

        assert context.is_atty is False

    def test_mixins_inheritance(self) -> None:
        """Test that BaseContext properly inherits from the required mixins."""
        context = BaseContext()

        assert isinstance(context, RichHelpersMixin)
        assert isinstance(context, OutputFormatMixin)

        assert hasattr(context, "display_rule")
        assert hasattr(context, "print_result_based_on_format")
        assert callable(context.display_rule)
