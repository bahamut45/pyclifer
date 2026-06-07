"""Tests for core callback functions."""

from unittest.mock import Mock

from click_extra import ParameterSource

from pyclifer.core.callbacks import get_meta_storing_callback


class TestGetMetaStoringCallback:
    """Tests for get_meta_storing_callback."""

    # noinspection PyMethodMayBeStatic
    def _make_ctx(self, source=ParameterSource.COMMANDLINE):
        ctx = Mock()
        ctx.meta = {}
        ctx.get_parameter_source.return_value = source
        return ctx

    # noinspection PyMethodMayBeStatic
    def _make_param(self, name="output_format"):
        param = Mock()
        param.name = name
        return param

    def test_without_original_callback_stores_value(self):
        """Callback with original_callback=None stores the value directly."""
        callback = get_meta_storing_callback(None)
        ctx = self._make_ctx()
        param = self._make_param()

        result = callback(ctx, param, "json")

        assert result == "json"
        assert ctx.meta["pyclifer.output_format"] == "json"

    def test_with_original_callback_calls_it_and_stores_result(self):
        """Callback with a non-None original_callback delegates to it."""
        original = Mock(return_value="transformed")
        callback = get_meta_storing_callback(original)
        ctx = self._make_ctx()
        param = self._make_param()

        result = callback(ctx, param, "raw")

        original.assert_called_once_with(ctx, param, "raw")
        assert result == "transformed"
        assert ctx.meta["pyclifer.output_format"] == "transformed"

    def test_commandline_source_overwrites_existing_meta(self):
        """COMMANDLINE source overwrites an existing meta-entry."""
        callback = get_meta_storing_callback(None)
        # noinspection PyArgumentEqualDefault
        ctx = self._make_ctx(ParameterSource.COMMANDLINE)
        ctx.meta["pyclifer.output_format"] = "table"
        param = self._make_param()

        callback(ctx, param, "json")

        assert ctx.meta["pyclifer.output_format"] == "json"

    def test_default_source_uses_setdefault(self):
        """DEFAULT source does not overwrite an existing meta-entry."""
        callback = get_meta_storing_callback(None)
        ctx = self._make_ctx(ParameterSource.DEFAULT)
        ctx.meta["pyclifer.output_format"] = "table"
        param = self._make_param()

        callback(ctx, param, "json")

        assert ctx.meta["pyclifer.output_format"] == "table"

    def test_none_value_skips_meta_store(self):
        """A None value does not write to ctx.meta."""
        callback = get_meta_storing_callback(None)
        ctx = self._make_ctx()
        param = self._make_param()

        callback(ctx, param, None)

        assert "pyclifer.output_format" not in ctx.meta
