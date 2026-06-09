"""Unit tests for BaseRenderer."""

from unittest.mock import MagicMock, patch

from rich.console import Console
from rich.panel import Panel

from pyclifer import BaseModel, OperationResult
from pyclifer.core.output.renderer import BaseRenderer
from pyclifer.core.output.responses import Response

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(item: str, **data) -> OperationResult:
    return OperationResult.ok(item, data=data if data else None)


def _err(item: str, msg: str = "boom") -> OperationResult:
    # noinspection PyArgumentEqualDefault
    return OperationResult.error(item, msg, error_code=1)


def _response(results: list[OperationResult], renderer: BaseRenderer | None = None) -> Response:
    return Response.from_results(results, renderer=renderer)


# ---------------------------------------------------------------------------
# Subclass fixtures
# ---------------------------------------------------------------------------


class _FullRenderer(BaseRenderer):
    fields = ["item", "success", "message"]
    columns = ["item", "success"]
    rich_title = "My Title"
    success_message = "All done."
    failure_message = "Something failed."


class _NoColumnsRenderer(BaseRenderer):
    fields = ["item", "success"]


class _ArticleModel(BaseModel):
    id: int
    title: str
    status: str


class _ModelClassRenderer(BaseRenderer):
    model_class = _ArticleModel
    columns = ["id", "title"]


# ---------------------------------------------------------------------------
# TestGetFields
# ---------------------------------------------------------------------------


class TestGetFields:
    def test_returns_copy(self) -> None:
        r = _FullRenderer()
        result = r.get_fields()
        assert result == ["item", "success", "message"]
        result.append("extra")
        assert _FullRenderer.fields == ["item", "success", "message"]

    def test_empty_by_default(self) -> None:
        assert BaseRenderer().get_fields() == []

    def test_falls_back_to_model_class_field_names(self) -> None:
        assert _ModelClassRenderer().get_fields() == ["id", "title", "status"]

    def test_explicit_fields_take_priority_over_model_class(self) -> None:
        class _Override(BaseRenderer):
            model_class = _ArticleModel
            fields = ["id"]

        assert _Override().get_fields() == ["id"]


# ---------------------------------------------------------------------------
# TestGetColumns
# ---------------------------------------------------------------------------


class TestGetColumns:
    def test_returns_columns_when_set(self) -> None:
        assert _FullRenderer().get_columns() == ["item", "success"]

    def test_falls_back_to_fields(self) -> None:
        assert _NoColumnsRenderer().get_columns() == ["item", "success"]

    def test_returns_copy(self) -> None:
        r = _FullRenderer()
        cols = r.get_columns()
        cols.append("extra")
        assert _FullRenderer.columns == ["item", "success"]


# ---------------------------------------------------------------------------
# TestResultToRow
# ---------------------------------------------------------------------------


class TestResultToRow:
    def test_reads_from_data_dict(self) -> None:
        result = OperationResult.ok("file.py", data={"action": "created"})
        row = BaseRenderer()._result_to_row(result, ["action"])
        assert row == {"action": "created"}

    def test_falls_back_to_attributes(self) -> None:
        result = OperationResult.ok("file.py", message="ok")
        row = BaseRenderer()._result_to_row(result, ["item", "success", "message"])
        assert row == {"item": "file.py", "success": True, "message": "ok"}

    def test_data_dict_takes_priority_over_attribute(self) -> None:
        result = OperationResult.ok("file.py", data={"item": "override"})
        row = BaseRenderer()._result_to_row(result, ["item"])
        assert row == {"item": "override"}

    def test_missing_column_returns_none(self) -> None:
        result = OperationResult.ok("file.py")
        row = BaseRenderer()._result_to_row(result, ["nonexistent"])
        assert row == {"nonexistent": None}

    def test_non_dict_data_falls_back_to_attributes(self) -> None:
        result = OperationResult.ok("file.py", data="raw string")
        row = BaseRenderer()._result_to_row(result, ["item"])
        assert row == {"item": "file.py"}

    def test_base_model_data_is_serialized(self) -> None:
        article = _ArticleModel(id=1, title="Hello", status="draft")
        result = OperationResult.ok("1", data=article)
        row = BaseRenderer()._result_to_row(result, ["id", "title", "status"])
        assert row == {"id": 1, "title": "Hello", "status": "draft"}

    def test_base_model_data_takes_priority_over_attributes(self) -> None:
        article = _ArticleModel(id=99, title="Override", status="published")
        result = OperationResult.ok("1", data=article)
        row = BaseRenderer()._result_to_row(result, ["id"])
        assert row == {"id": 99}


# ---------------------------------------------------------------------------
# TestSerialize
# ---------------------------------------------------------------------------


class TestSerialize:
    def test_no_fields_delegates_to_response_to_json(self) -> None:
        results = [_ok("a")]
        response = _response(results)
        serialized = BaseRenderer().serialize(response)
        assert "success" in serialized
        assert "message" in serialized

    def test_with_fields_filters_results(self) -> None:
        results = [_ok("a"), _err("b")]
        response = _response(results, renderer=_FullRenderer())
        serialized = _FullRenderer().serialize(response)
        assert "data" in serialized
        rows = serialized["data"]["results"]
        assert len(rows) == 2
        assert set(rows[0].keys()) == {"item", "success", "message", "error_code"}

    def test_serialized_row_values(self) -> None:
        results = [_ok("x", action="created")]
        response = _response(results)
        r = _FullRenderer()
        serialized = r.serialize(response)
        row = serialized["data"]["results"][0]
        assert row["item"] == "x"
        assert row["success"] is True

    def test_base_model_in_result_data_is_serialized(self) -> None:
        article = _ArticleModel(id=1, title="Hello", status="draft")
        result = OperationResult.ok("1", data=article)
        response = _response([result], renderer=_ModelClassRenderer())
        serialized = _ModelClassRenderer().serialize(response)
        rows = serialized["data"]["results"]
        assert len(rows) == 1
        assert rows[0]["id"] == 1
        assert rows[0]["title"] == "Hello"

    def test_base_model_fields_via_model_class(self) -> None:
        article = _ArticleModel(id=2, title="World", status="published")
        result = OperationResult.ok("2", data=article)
        response = _response([result], renderer=_ModelClassRenderer())
        serialized = _ModelClassRenderer().serialize(response)
        row = serialized["data"]["results"][0]
        assert set(row.keys()) == {"id", "title", "status", "item", "success", "error_code"}

    def test_serialize_failed_result_preserves_item(self) -> None:
        class _StorageRenderer(BaseRenderer):
            fields = ["total", "used"]

        result = OperationResult.error("px-store", "not found", error_code=3)
        response = _response([result])
        serialized = _StorageRenderer().serialize(response)
        row = serialized["data"]["results"][0]
        assert row["item"] == "px-store"
        assert row["total"] is None


# ---------------------------------------------------------------------------
# TestText
# ---------------------------------------------------------------------------


class TestText:
    def test_returns_response_message(self) -> None:
        response = Response(success=True, message="hello world")
        assert BaseRenderer().text(response) == "hello world"

    def test_returns_empty_string_when_no_message(self) -> None:
        response = Response(success=True, message="")
        assert BaseRenderer().text(response) == ""


# ---------------------------------------------------------------------------
# TestRaw
# ---------------------------------------------------------------------------


class TestRaw:
    def test_returns_dict(self) -> None:
        results = [_ok("a")]
        response = _response(results)
        result = BaseRenderer().raw(response)
        assert isinstance(result, dict)

    def test_delegates_to_serialize(self) -> None:
        results = [_ok("x")]
        response = _response(results, renderer=_FullRenderer())
        r = _FullRenderer()
        assert r.raw(response) == r.serialize(response)

    def test_contains_success_key(self) -> None:
        results = [_ok("a")]
        response = _response(results)
        assert "success" in BaseRenderer().raw(response)


# ---------------------------------------------------------------------------
# TestRich
# ---------------------------------------------------------------------------


class TestRich:
    def test_prints_panel_with_message(self) -> None:
        console = MagicMock(spec=Console)
        response = Response(success=True, message="done")
        BaseRenderer().rich(response, console)
        console.print.assert_called_once()
        panel = console.print.call_args[0][0]
        assert isinstance(panel, Panel)

    def test_uses_rich_title(self) -> None:
        console = MagicMock(spec=Console)
        response = Response(success=True, message="done")
        _FullRenderer().rich(response, console)
        panel = console.print.call_args[0][0]
        assert panel.title == "My Title"

    def test_no_title_when_rich_title_empty(self) -> None:
        console = MagicMock(spec=Console)
        response = Response(success=True, message="done")
        BaseRenderer().rich(response, console)
        panel = console.print.call_args[0][0]
        assert panel.title is None


# ---------------------------------------------------------------------------
# TestRichSetup
# ---------------------------------------------------------------------------


class TestRichSetup:
    def test_returns_panel(self) -> None:
        renderable = BaseRenderer().rich_setup()
        assert isinstance(renderable, Panel)


# ---------------------------------------------------------------------------
# TestRichOnItem
# ---------------------------------------------------------------------------


class TestRichOnItem:
    def test_is_noop(self) -> None:
        result = _ok("f.py")
        BaseRenderer().rich_on_item(result, [result])


# ---------------------------------------------------------------------------
# TestRichSummary
# ---------------------------------------------------------------------------


class TestRichSummary:
    def test_delegates_to_rich(self) -> None:
        console = MagicMock(spec=Console)
        response = Response(success=True, message="summary")
        r = BaseRenderer()
        with patch.object(r, "rich") as mock_rich:
            r.rich_summary(response, console)
        mock_rich.assert_called_once_with(response, console)


# ---------------------------------------------------------------------------
# TestGetSuccessMessage
# ---------------------------------------------------------------------------


class TestGetSuccessMessage:
    def test_uses_static_success_message(self) -> None:
        results = [_ok("a"), _ok("b")]
        assert _FullRenderer().get_success_message(results) == "All done."

    def test_generates_count_message_when_not_set(self) -> None:
        results = [_ok("a"), _ok("b")]
        msg = BaseRenderer().get_success_message(results)
        assert "2" in msg

    def test_count_reflects_list_length(self) -> None:
        results = [_ok(str(i)) for i in range(5)]
        msg = BaseRenderer().get_success_message(results)
        assert "5" in msg


# ---------------------------------------------------------------------------
# TestGetFailureMessage
# ---------------------------------------------------------------------------


class TestGetFailureMessage:
    def test_uses_static_failure_message(self) -> None:
        results = [_ok("a"), _err("b")]
        assert _FullRenderer().get_failure_message(results) == "Something failed."

    def test_generates_fraction_when_not_set(self) -> None:
        results = [_ok("a"), _err("b"), _err("c")]
        msg = BaseRenderer().get_failure_message(results)
        assert "2" in msg
        assert "3" in msg

    def test_all_failed(self) -> None:
        results = [_err("a"), _err("b")]
        msg = BaseRenderer().get_failure_message(results)
        assert "2/2" in msg

    def test_single_failed_result_returns_result_message(self) -> None:
        result = OperationResult.error("px-store", "Storage pool not found.")
        assert BaseRenderer().get_failure_message([result]) == "Storage pool not found."

    def test_single_successful_result_falls_through_to_count(self) -> None:
        result = OperationResult.ok("px-store")
        assert BaseRenderer().get_failure_message([result]) == "0/1 operation(s) failed."

    def test_static_failure_message_takes_precedence_over_single_result(self) -> None:
        result = OperationResult.error("px-store", "Storage pool not found.")
        assert _FullRenderer().get_failure_message([result]) == "Something failed."


# ---------------------------------------------------------------------------
# TestSerializeResult
# ---------------------------------------------------------------------------


class TestSerializeResult:
    def test_failed_result_item_always_in_row(self) -> None:
        result = OperationResult.error("px-store", "not found", error_code=3)
        row = BaseRenderer()._serialize_result(result, ["total", "used"])
        assert row["item"] == "px-store"

    def test_successful_result_extracts_fields_from_data(self) -> None:
        result = OperationResult.ok("px-store", data={"total": 1000, "used": 400})
        row = BaseRenderer()._serialize_result(result, ["total", "used"])
        assert row["total"] == 1000
        assert row["used"] == 400
        assert row["item"] == "px-store"

    def test_item_in_fields_is_overwritten_by_result_item(self) -> None:
        result = OperationResult.ok("authoritative", data={"item": "from-data", "total": 5})
        row = BaseRenderer()._serialize_result(result, ["item", "total"])
        assert row["item"] == "authoritative"

    def test_row_contains_success_and_error_code_by_default(self) -> None:
        result = OperationResult.error("px-store", "not found", error_code=3)
        row = BaseRenderer()._serialize_result(result, ["total"])
        assert row["success"] is False
        assert row["error_code"] == 3

    def test_include_row_meta_false_suppresses_meta(self) -> None:
        class _NoMetaRenderer(BaseRenderer):
            include_row_meta = False

        result = OperationResult.error("px-store", "not found")
        row = _NoMetaRenderer()._serialize_result(result, ["total"])
        assert "success" not in row
        assert "error_code" not in row


# ---------------------------------------------------------------------------
# TestRowStyle
# ---------------------------------------------------------------------------


class TestRowStyle:
    def test_row_style_returns_red_for_failed_result(self) -> None:
        result = OperationResult.error("px-store", "fail")
        assert BaseRenderer()._row_style(result) == "red"

    def test_row_style_returns_none_for_successful_result(self) -> None:
        result = OperationResult.ok("px-store")
        assert BaseRenderer()._row_style(result) is None


# ---------------------------------------------------------------------------
# TestTable
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TestDetailGrid
# ---------------------------------------------------------------------------


class TestDetailGrid:
    def test_returns_two_column_grid(self) -> None:
        grid = BaseRenderer._detail_grid()
        assert len(grid.columns) == 2

    def test_first_column_bold_cyan(self) -> None:
        grid = BaseRenderer._detail_grid()
        assert grid.columns[0].style == "bold cyan"
        assert grid.columns[0].no_wrap is True


# ---------------------------------------------------------------------------
# TestFirstResult
# ---------------------------------------------------------------------------


class TestFirstResult:
    def test_returns_first_result_when_successful(self) -> None:
        console = MagicMock(spec=Console)
        result = _ok("file.py")
        response = _response([result])
        response.data["results"] = [result]
        assert BaseRenderer()._first_result(response, console) is result

    def test_returns_none_and_prints_panel_when_empty(self) -> None:
        console = MagicMock(spec=Console)
        response = Response(success=False, message="nothing")
        response.data["results"] = []
        assert BaseRenderer()._first_result(response, console) is None
        console.print.assert_called_once()

    def test_returns_none_and_prints_panel_when_first_failed(self) -> None:
        console = MagicMock(spec=Console)
        result = _err("file.py")
        response = _response([result])
        response.data["results"] = [result]
        assert BaseRenderer()._first_result(response, console) is None
        console.print.assert_called_once()


# ---------------------------------------------------------------------------
# TestTable
# ---------------------------------------------------------------------------


class TestTable:
    def test_table_failed_row_styled_red(self) -> None:
        ok = OperationResult.ok("a")
        err = OperationResult.error("b", "fail")
        response = _response([ok, err], renderer=_FullRenderer())
        cli_table = _FullRenderer().table(response)
        assert cli_table.table.rows[0].style is None
        assert cli_table.table.rows[1].style == "red"
