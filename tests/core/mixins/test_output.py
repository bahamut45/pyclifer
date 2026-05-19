"""Unit tests for the OutputFormatMixin."""

import json
from unittest.mock import MagicMock, patch

import pytest
from rich.panel import Panel

# noinspection PyProtectedMember
from pyclif.core.mixins.output import OutputFormatMixin, _ExceptionRenderer
from pyclif.core.output import Response
from pyclif.core.output.renderer import BaseRenderer
from pyclif.core.output.responses import OperationResult


class DummyOutputContext(OutputFormatMixin):
    """Minimal context for testing OutputFormatMixin."""

    def __init__(self, output_format: str | None = "table") -> None:
        """Initialize with a mocked console and specific format.

        Args:
            output_format: The output format to use during dispatch.
        """
        self.console = MagicMock()
        self.output_format = output_format


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(item: str = "a", **data_kwargs) -> OperationResult:
    return OperationResult.ok(item, data=data_kwargs if data_kwargs else None)


# noinspection PyTypeChecker
def _response_with_renderer(
    results: list[OperationResult] | None = None,
    renderer: BaseRenderer | None = None,
) -> Response:
    if results is None:
        results = [_ok()]
    return Response.from_results(results, renderer=renderer or BaseRenderer())


# ---------------------------------------------------------------------------
# TestPrintErrorBasedOnFormat
# ---------------------------------------------------------------------------


# noinspection PyArgumentEqualDefault
class TestPrintErrorBasedOnFormat:
    """Tests for print_error_based_on_format."""

    def test_creates_response_and_dispatches(self) -> None:
        ctx = DummyOutputContext(output_format="text")
        ctx.print_result_based_on_format = MagicMock()  # type: ignore[method-assign]
        ctx.print_error_based_on_format(ValueError("something went wrong"))
        ctx.print_result_based_on_format.assert_called_once()
        arg = ctx.print_result_based_on_format.call_args[0][0]
        assert isinstance(arg, Response)
        assert arg.success is False
        assert "something went wrong" in arg.message

    def test_renderer_is_exception_renderer(self) -> None:
        ctx = DummyOutputContext(output_format="text")
        ctx.print_result_based_on_format = MagicMock()  # type: ignore[method-assign]
        ctx.print_error_based_on_format(RuntimeError("boom"))
        arg = ctx.print_result_based_on_format.call_args[0][0]
        assert isinstance(arg.renderer, _ExceptionRenderer)

    def test_table_format_uses_exception_renderer_table(self) -> None:
        ctx = DummyOutputContext(output_format="table")
        ctx.print_error_based_on_format(ValueError("oops"))
        ctx.console.print.assert_called_once()

    def test_rich_format_prints_error_panel(self) -> None:
        """_ExceptionRenderer.rich prints a red panel."""
        ctx = DummyOutputContext(output_format="rich")
        ctx.print_error_based_on_format(RuntimeError("rich error"))
        ctx.console.print.assert_called_once()
        panel = ctx.console.print.call_args[0][0]
        assert isinstance(panel, Panel)
        assert "rich error" in str(panel.renderable)


# ---------------------------------------------------------------------------
# TestPrintResultFallbackRenderer
# ---------------------------------------------------------------------------


# noinspection PyArgumentEqualDefault
class TestPrintResultFallbackRenderer:
    """print_result_based_on_format uses BaseRenderer when renderer is None."""

    def test_bare_response_uses_base_renderer(self) -> None:
        ctx = DummyOutputContext(output_format="text")
        response = Response(success=True, message="bare response", renderer=BaseRenderer())
        ctx.print_result_based_on_format(response)
        ctx.console.print.assert_called_once_with("bare response")

    def test_renderer_is_attached_to_response(self) -> None:
        ctx = DummyOutputContext(output_format="table")
        response = Response(success=True, message="ok")
        assert response.renderer is None
        ctx.print_result_based_on_format(response)
        assert isinstance(response.renderer, BaseRenderer)


# ---------------------------------------------------------------------------
# TestResolveFilterPath
# ---------------------------------------------------------------------------


class TestResolveFilterPath:
    """Tests for _resolve_filter_path."""

    def test_key_found_returns_value_and_true(self) -> None:
        data = {"results": [{"id": 42}]}
        value, found = OutputFormatMixin._resolve_filter_path(data, "results")
        assert found is True
        assert value == [{"id": 42}]

    def test_missing_key_returns_none_and_false(self) -> None:
        data = {"results": []}
        value, found = OutputFormatMixin._resolve_filter_path(data, "nonexistent")
        assert found is False
        assert value is None

    def test_null_value_returns_none_and_true(self) -> None:
        data = {"key": None}
        value, found = OutputFormatMixin._resolve_filter_path(data, "key")
        assert found is True
        assert value is None

    def test_dotted_path_into_nested_dict(self) -> None:
        data = {"article": {"id": 7, "title": "hello"}}
        value, found = OutputFormatMixin._resolve_filter_path(data, "article.title")
        assert found is True
        assert value == "hello"

    def test_dotted_path_with_list_index(self) -> None:
        data = {"results": [{"id": 1}, {"id": 2}]}
        value, found = OutputFormatMixin._resolve_filter_path(data, "results.0.id")
        assert found is True
        assert value == 1

    def test_negative_index_resolves_from_end(self) -> None:
        data = {"results": [{"id": 1}, {"id": 2}, {"id": 3}]}
        value, found = OutputFormatMixin._resolve_filter_path(data, "results.-1.id")
        assert found is True
        assert value == 3

    def test_list_index_out_of_bounds_returns_false(self) -> None:
        data = {"results": [{"id": 1}]}
        value, found = OutputFormatMixin._resolve_filter_path(data, "results.5.id")
        assert found is False
        assert value is None

    def test_non_numeric_list_index_returns_false(self) -> None:
        data = {"results": [{"id": 1}]}
        value, found = OutputFormatMixin._resolve_filter_path(data, "results.x.id")
        assert found is False
        assert value is None

    def test_missing_intermediate_key_returns_false(self) -> None:
        data = {"results": [{"id": 1}]}
        value, found = OutputFormatMixin._resolve_filter_path(data, "results.0.missing")
        assert found is False
        assert value is None

    def test_traverse_scalar_with_remaining_segments_returns_false(self) -> None:
        data = {"leaf": "scalar"}
        value, found = OutputFormatMixin._resolve_filter_path(data, "leaf.nested")
        assert found is False
        assert value is None


# ---------------------------------------------------------------------------
# TestApplyOutputFilter
# ---------------------------------------------------------------------------


class TestApplyOutputFilter:
    """Tests for _apply_output_filter."""

    def test_valid_path_in_data_sub_dict(self) -> None:
        ctx = DummyOutputContext(output_format="json")
        data = {"success": True, "data": {"results": [{"id": 42}]}}
        assert ctx._apply_output_filter(data, "results") == [{"id": 42}]

    def test_valid_path_at_top_level(self) -> None:
        ctx = DummyOutputContext(output_format="json")
        data = {"success": True, "message": "done", "data": {}}
        assert ctx._apply_output_filter(data, "message") == "done"

    def test_data_sub_dict_takes_priority_over_top_level(self) -> None:
        ctx = DummyOutputContext(output_format="json")
        data = {"message": "top", "data": {"message": "nested"}}
        assert ctx._apply_output_filter(data, "message") == "nested"

    def test_data_sub_not_a_dict_falls_back_to_top_level(self) -> None:
        ctx = DummyOutputContext(output_format="json")
        data = {"data": ["list", "not", "dict"], "message": "found"}
        assert ctx._apply_output_filter(data, "message") == "found"

    def test_invalid_path_calls_print_result_with_failure_response(self) -> None:
        ctx = DummyOutputContext(output_format="json")
        ctx.print_result_based_on_format = MagicMock()  # type: ignore[method-assign]
        data = {"success": True, "data": {"results": []}}
        with pytest.raises(SystemExit) as exc_info:
            ctx._apply_output_filter(data, "nonexistent.path")
        assert exc_info.value.code == 2
        ctx.print_result_based_on_format.assert_called_once()
        error_response = ctx.print_result_based_on_format.call_args[0][0]
        assert isinstance(error_response, Response)
        assert error_response.success is False

    def test_invalid_path_error_message_contains_path(self) -> None:
        ctx = DummyOutputContext(output_format="json")
        ctx.print_result_based_on_format = MagicMock()  # type: ignore[method-assign]
        data = {"success": True, "data": {}}
        with pytest.raises(SystemExit):
            ctx._apply_output_filter(data, "bad.path")
        error_response = ctx.print_result_based_on_format.call_args[0][0]
        assert "bad.path" in error_response.message

    def test_invalid_path_error_includes_available_keys(self) -> None:
        ctx = DummyOutputContext(output_format="json")
        ctx.print_result_based_on_format = MagicMock()  # type: ignore[method-assign]
        data = {"success": True, "data": {"alpha": 1, "beta": 2}}
        with pytest.raises(SystemExit):
            ctx._apply_output_filter(data, "nonexistent")
        error_response = ctx.print_result_based_on_format.call_args[0][0]
        result = error_response.data["results"][0]
        assert isinstance(result, OperationResult)
        assert result.data["available_keys"] == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# TestPrintRawDict
# ---------------------------------------------------------------------------


class TestPrintRawDict:
    """Tests for _print_raw_dict."""

    def test_no_filter_prints_compact_json(self) -> None:
        ctx = DummyOutputContext()
        data = {"success": True, "message": "ok"}
        ctx._print_raw_dict(data, None)
        args, _ = ctx.console.print.call_args
        parsed = json.loads(args[0])
        assert parsed["success"] is True

    def test_filter_prints_raw_value_without_re_serialization(self) -> None:
        ctx = DummyOutputContext()
        data = {"success": True, "data": {"status": "running"}}
        ctx._print_raw_dict(data, "status")
        ctx.console.print.assert_called_once_with("running")

    def test_filter_top_level_prints_raw_value(self) -> None:
        ctx = DummyOutputContext()
        data = {"success": True, "message": "done", "data": {}}
        ctx._print_raw_dict(data, "message")
        ctx.console.print.assert_called_once_with("done")

    def test_filter_missing_key_raises_system_exit(self) -> None:
        ctx = DummyOutputContext()
        ctx.print_result_based_on_format = MagicMock()  # type: ignore[method-assign]
        data = {"success": True, "data": {}}
        with pytest.raises(SystemExit) as exc_info:
            ctx._print_raw_dict(data, "nonexistent")
        assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# TestPrintJson
# ---------------------------------------------------------------------------


class TestPrintJson:
    def test_calls_print_json_with_json_string(self) -> None:
        ctx = DummyOutputContext()
        ctx._print_json({"key": "value"})
        ctx.console.print_json.assert_called_once()
        args, _ = ctx.console.print_json.call_args
        parsed = json.loads(args[0])
        assert parsed == {"key": "value"}

    def test_non_serializable_falls_back_gracefully(self) -> None:
        ctx = DummyOutputContext()

        class _Obj:
            __slots__ = ()

            def __str__(self) -> str:
                return "obj"

        ctx._print_json({"x": _Obj()})
        args, _ = ctx.console.print_json.call_args
        parsed = json.loads(args[0])
        assert isinstance(parsed["x"], str)

    def test_to_dict_method_used_by_fallback_encoder(self) -> None:
        """_FallbackEncoder calls to_dict() when available."""
        from pyclif.core.mixins.output import _FallbackEncoder

        # noinspection PyMethodMayBeStatic,PyMissingOrEmptyDocstring
        class _WithToDict:
            def to_dict(self):
                return {"serialized": True}

        result = json.loads(json.dumps({"obj": _WithToDict()}, cls=_FallbackEncoder))
        assert result["obj"] == {"serialized": True}


# ---------------------------------------------------------------------------
# TestPrintYaml
# ---------------------------------------------------------------------------


class TestPrintYaml:
    @patch("pyclif.core.mixins.output.Syntax")
    def test_calls_print_with_syntax(self, mock_syntax: MagicMock) -> None:
        ctx = DummyOutputContext()
        ctx._print_yaml({"name": "Alice"})
        mock_syntax.assert_called_once()
        yaml_content = mock_syntax.call_args[0][0]
        assert "name: Alice" in yaml_content
        ctx.console.print.assert_called_once()


# ---------------------------------------------------------------------------
# TestRendererPathBatchDispatch
# ---------------------------------------------------------------------------


# noinspection PyMethodMayBeStatic
class TestRendererPathBatchDispatch:
    """Dispatch tests for the renderer path in print_result_based_on_format."""

    def _ctx(self, fmt: str | None) -> DummyOutputContext:
        return DummyOutputContext(output_format=fmt)

    def test_text_format_prints_message(self) -> None:
        ctx = self._ctx("text")
        response = _response_with_renderer()
        response.message = "hello"
        ctx.print_result_based_on_format(response)
        ctx.console.print.assert_called_once_with("hello")

    @pytest.mark.parametrize("fmt", [None, "table"])
    def test_table_formats_call_renderer_table(self, fmt: str | None) -> None:
        ctx = self._ctx(fmt)
        renderer = MagicMock(spec=BaseRenderer)
        renderer.table.return_value = "table output"
        response = Response.from_results([_ok()], renderer=renderer)
        ctx.print_result_based_on_format(response)
        renderer.table.assert_called_once_with(response)
        ctx.console.print.assert_called_once_with("table output")

    def test_raw_format_prints_compact_json(self) -> None:
        ctx = self._ctx("raw")
        response = _response_with_renderer()
        ctx.print_result_based_on_format(response)
        args, _ = ctx.console.print.call_args
        parsed = json.loads(args[0])
        assert "success" in parsed

    def test_raw_format_with_filter(self) -> None:
        ctx = self._ctx("raw")
        response = _response_with_renderer()
        response.message = "filtered"
        ctx.print_result_based_on_format(response, options={"filter_value": "message"})
        ctx.console.print.assert_called_once_with("filtered")

    def test_rich_format_calls_renderer_rich(self) -> None:
        ctx = self._ctx("rich")
        renderer = MagicMock(spec=BaseRenderer)
        response = Response.from_results([_ok()], renderer=renderer)
        ctx.print_result_based_on_format(response)
        renderer.rich.assert_called_once_with(response, ctx.console)

    @pytest.mark.parametrize("fmt,method", [("json", "_print_json"), ("yaml", "_print_yaml")])
    def test_serialized_format_calls_print_method(self, fmt: str, method: str) -> None:
        ctx = self._ctx(fmt)
        mock = MagicMock()
        setattr(ctx, method, mock)
        response = _response_with_renderer()
        ctx.print_result_based_on_format(response)
        mock.assert_called_once()

    @pytest.mark.parametrize("fmt,method", [("json", "_print_json"), ("yaml", "_print_yaml")])
    def test_serialized_format_with_filter_re_serializes(self, fmt: str, method: str) -> None:
        ctx = self._ctx(fmt)
        mock_print = MagicMock()
        setattr(ctx, method, mock_print)
        ctx._print_raw_dict = MagicMock()  # type: ignore[method-assign]
        response = _response_with_renderer()
        response.message = "done"
        ctx.print_result_based_on_format(response, options={"filter_value": "message"})
        mock_print.assert_called_once_with("done")
        ctx._print_raw_dict.assert_not_called()


# ---------------------------------------------------------------------------
# TestRendererPathStreamDispatch
# ---------------------------------------------------------------------------


# noinspection PyArgumentEqualDefault
class TestRendererPathStreamDispatch:
    """Streaming dispatch tests for print_result_based_on_format."""

    def test_non_rich_stream_is_materialised(self) -> None:
        ctx = DummyOutputContext(output_format="text")
        renderer = BaseRenderer()
        gen = iter([_ok("a"), _ok("b")])
        response = Response.from_stream(gen, renderer=renderer)
        ctx.print_result_based_on_format(response)
        assert "stream" not in response.data
        assert "results" in response.data

    def test_rich_stream_calls_live_hooks(self) -> None:
        ctx = DummyOutputContext(output_format="rich")
        renderer = MagicMock(spec=BaseRenderer)
        renderer.rich_setup.return_value = MagicMock()
        items = [_ok("a"), _ok("b")]
        response = Response.from_stream(iter(items), renderer=renderer)

        with patch("pyclif.core.mixins.output.Live") as mock_live:
            mock_live.return_value.__enter__ = MagicMock(return_value=None)
            mock_live.return_value.__exit__ = MagicMock(return_value=False)
            ctx.print_result_based_on_format(response)

        renderer.rich_setup.assert_called_once()
        assert renderer.rich_on_item.call_count == 2
        renderer.rich_summary.assert_called_once()

    def test_non_rich_stream_then_text_dispatch(self) -> None:
        ctx = DummyOutputContext(output_format="text")

        class _MsgRenderer(BaseRenderer):
            success_message = "stream complete"

        response = Response.from_stream(iter([_ok()]), renderer=_MsgRenderer())
        ctx.print_result_based_on_format(response)
        ctx.console.print.assert_called_once_with("stream complete")
