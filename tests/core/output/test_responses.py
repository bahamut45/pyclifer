"""Unit tests for the Response and OperationResult classes in the output module."""

from unittest.mock import MagicMock

from pyclifer import BaseModel
from pyclifer.core.mixins.output import OutputFormatMixin
from pyclifer.core.output.renderer import BaseRenderer
from pyclifer.core.output.responses import (
    NON_SERIALIZABLE_FIELDS,
    OperationResult,
    PaginatedResponse,
    Response,
)


class TestOperationResult:
    """Test suite for OperationResult."""

    def test_ok_sets_success_true(self) -> None:
        """OperationResult.ok produces a successful result with error_code 0."""
        result = OperationResult.ok("file.py")
        assert result.success is True
        assert result.error_code == 0
        assert result.item == "file.py"

    def test_ok_carries_data(self) -> None:
        """OperationResult.ok stores the data payload."""
        result = OperationResult.ok("file.py", data={"action": "created"})
        assert result.data == {"action": "created"}

    def test_ok_carries_message(self) -> None:
        """OperationResult.ok stores the message parameter."""
        result = OperationResult.ok("file.py", message="done")
        assert result.message == "done"

    def test_error_sets_success_false(self) -> None:
        """OperationResult.error produces a failed result."""
        result = OperationResult.error("file.py", "already exists")
        assert result.success is False
        assert result.message == "already exists"
        assert result.error_code == 1

    def test_error_custom_error_code(self) -> None:
        """OperationResult.error respects a custom error_code."""
        result = OperationResult.error("file.py", "conflict", error_code=2)
        assert result.error_code == 2


class TestResponseFromResults:
    """Test suite for Response.from_results."""

    def test_all_success_produces_success_response(self) -> None:
        """from_results returns success=True and error_code=0 when all results succeeded."""
        results = [OperationResult.ok("a.py"), OperationResult.ok("b.py")]
        response = Response.from_results(results)
        assert response.success is True
        assert response.error_code == 0

    def test_all_success_error_code_present_in_json(self) -> None:
        """error_code=0 appears in to_json() output when all results succeeded."""
        results = [OperationResult.ok("a.py")]
        response = Response.from_results(results)
        data = response.to_json()
        assert data["error_code"] == 0

    def test_one_failure_produces_failed_response(self) -> None:
        """from_results returns success=False when any result failed."""
        results = [
            OperationResult.ok("a.py"),
            OperationResult.error("b.py", "conflict", error_code=2),
        ]
        response = Response.from_results(results)
        assert response.success is False
        assert response.error_code == 2

    def test_error_code_from_first_failure(self) -> None:
        """error_code is taken from the first failed result."""
        results = [
            OperationResult.error("a.py", "err", error_code=3),
            OperationResult.error("b.py", "err", error_code=5),
        ]
        response = Response.from_results(results)
        assert response.error_code == 3

    def test_results_stored_in_data(self) -> None:
        """All OperationResult objects are accessible via data['results']."""
        results = [OperationResult.ok("a.py")]
        response = Response.from_results(results)
        assert response.data["results"] == results

    def test_fixed_message_is_used(self) -> None:
        """message is used regardless of outcome."""
        results = [OperationResult.ok("a.py")]
        response = Response.from_results(results, message="Project created.")
        assert response.message == "Project created."

    def test_success_message_on_success(self) -> None:
        """success_message is used when all results succeeded."""
        results = [OperationResult.ok("a.py")]
        response = Response.from_results(
            results, success_message="All good.", failure_message="Bad."
        )
        assert response.message == "All good."

    def test_failure_message_on_failure(self) -> None:
        """failure_message is used when at least one result failed."""
        results = [OperationResult.error("a.py", "conflict")]
        response = Response.from_results(
            results, success_message="All good.", failure_message="Bad."
        )
        assert response.message == "Bad."

    def test_fixed_message_takes_precedence_over_success_message(self) -> None:
        """message overrides success_message / failure_message."""
        results = [OperationResult.ok("a.py")]
        response = Response.from_results(results, message="Fixed.", success_message="Good.")
        assert response.message == "Fixed."

    def test_default_message_success(self) -> None:
        """Default message reports success count when no message is provided."""
        results = [OperationResult.ok("a.py"), OperationResult.ok("b.py")]
        response = Response.from_results(results)
        assert "2" in response.message

    def test_default_message_failure(self) -> None:
        """Default message reports failure ratio when no message is provided."""
        results = [
            OperationResult.ok("a.py"),
            OperationResult.error("b.py", "conflict"),
        ]
        response = Response.from_results(results)
        assert "1/2" in response.message


class MockDataModel:
    """Mock model with a to_dict method for serialization testing."""

    def to_dict(self) -> dict:
        """Return a dictionary representation of the mock model.

        Returns:
            dict: A simple dictionary with a mocked key and value.
        """
        return {"mock_key": "mock_value"}


class TestResponse:
    """Test suite for the Response class."""

    def test_initialization_defaults(self) -> None:
        """Test that a Response initializes with correct default values."""
        response = Response(success=True, message="Operation successful")

        assert response.success is True
        assert response.message == "Operation successful"
        assert response.data == {}
        assert response.error_code is None
        assert response.renderer is None

    def test_to_dict_excludes_defaults(self) -> None:
        """Test that to_dict returns only fields that differ from their default values."""
        response = Response(success=True, message="Test dict")
        result = response.to_dict()

        assert "success" in result
        assert "message" in result
        assert "data" in result
        assert "error_code" not in result

    def test_to_json_removes_non_serializable_fields(self) -> None:
        """Test that to_json excludes the renderer and returns serializable data."""
        from pyclifer.core.output.renderer import BaseRenderer

        response = Response(
            success=False,
            message="An error occurred",
            error_code=404,
            renderer=BaseRenderer(),
        )

        result = response.to_json()

        assert result["success"] is False
        assert result["message"] == "An error occurred"
        assert result["error_code"] == 404
        assert "renderer" not in result

    def test_serialize_data_with_nested_objects(self) -> None:
        """Test that objects with a to_dict method are properly serialized inside data."""
        mock_object = MockDataModel()
        response = Response(
            success=True,
            message="Data fetch success",
            data={"user": mock_object, "status": "active"},
        )

        result = response.to_json()

        assert "data" in result
        assert result["data"]["status"] == "active"
        assert result["data"]["user"] == {"mock_key": "mock_value"}

    def test_renderer_field_present(self) -> None:
        """renderer field is present on Response and defaults to None."""
        response = Response(success=True, message="ok")
        assert response.renderer is None

    def test_renderer_excluded_from_to_json(self) -> None:
        """renderer is excluded from to_json() output."""
        renderer = BaseRenderer()
        response = Response(success=True, message="ok", renderer=renderer)
        result = response.to_json()
        assert "renderer" not in result

    def test_non_serializable_fields_contains_renderer(self) -> None:
        """NON_SERIALIZABLE_FIELDS constant includes 'renderer'."""
        assert "renderer" in NON_SERIALIZABLE_FIELDS

    def test_serialize_data_with_non_dict_data_is_noop(self) -> None:
        """_serialize_data skips serialization when data is not a dict (192→exit)."""
        response = Response(success=True, message="ok", data=["a", "b"])
        response._serialize_data()
        assert response.data == ["a", "b"]

    def test_serialize_data_with_base_model_value(self) -> None:
        """_serialize_data calls to_dict() on BaseModel values in the data dict."""

        class _Item(BaseModel):
            id: int
            name: str

        item = _Item(id=1, name="test")
        response = Response(success=True, message="ok", data={"item": item})
        result = response.to_json()
        assert result["data"]["item"] == {"id": 1, "name": "test"}


class TestResponseFromStream:
    """Test suite for Response.from_stream."""

    def test_stores_generator_without_consuming(self) -> None:
        """from_stream stores the generator without consuming it."""
        calls: list[str] = []

        def _gen():
            calls.append("consumed")
            yield OperationResult.ok("a")

        renderer = BaseRenderer()
        Response.from_stream(_gen(), renderer=renderer)
        assert calls == []

    def test_stream_in_data(self) -> None:
        """from_stream stores the generator under data['stream']."""
        renderer = BaseRenderer()
        gen = iter([OperationResult.ok("a")])
        response = Response.from_stream(gen, renderer=renderer)
        assert "stream" in response.data

    def test_renderer_attached(self) -> None:
        """from_stream attaches the renderer to the response."""
        renderer = BaseRenderer()
        gen = iter([OperationResult.ok("a")])
        response = Response.from_stream(gen, renderer=renderer)
        assert response.renderer is renderer

    def test_message_blank_at_construction(self) -> None:
        """from_stream leaves message empty until the stream is consumed."""
        response = Response.from_stream(iter([OperationResult.ok("a")]), renderer=BaseRenderer())
        assert response.message == ""

    def test_results_not_in_data_at_construction(self) -> None:
        """from_stream does not pre-populate data['results']."""
        response = Response.from_stream(iter([OperationResult.ok("a")]), renderer=BaseRenderer())
        assert "results" not in response.data

    def test_renderer_excluded_from_stream_to_json(self) -> None:
        """renderer is excluded from to_json() on a stream-based Response."""
        response = Response.from_stream(iter([OperationResult.ok("a")]), renderer=BaseRenderer())
        list(response.data.pop("stream"))
        response.data["results"] = []
        assert "renderer" not in response.to_json()


class TestMaterialiseStream:
    """Test suite for OutputFormatMixin._materialise_stream."""

    def _make_context(self) -> OutputFormatMixin:
        ctx = OutputFormatMixin()
        ctx.console = MagicMock()  # type: ignore[attr-defined]
        return ctx

    def test_replaces_stream_with_results(self) -> None:
        """_materialise_stream replaces data['stream'] with data['results']."""
        renderer = BaseRenderer()
        gen = iter([OperationResult.ok("a"), OperationResult.ok("b")])
        response = Response.from_stream(gen, renderer=renderer)
        OutputFormatMixin._materialise_stream(response)
        assert "stream" not in response.data
        assert "results" in response.data
        assert len(response.data["results"]) == 2

    def test_success_true_when_all_ok(self) -> None:
        """_materialise_stream sets success=True and error_code=0 when all results succeeded."""
        renderer = BaseRenderer()
        gen = iter([OperationResult.ok("a"), OperationResult.ok("b")])
        response = Response.from_stream(gen, renderer=renderer)
        OutputFormatMixin._materialise_stream(response)
        assert response.success is True
        assert response.error_code == 0

    def test_error_code_zero_on_success(self) -> None:
        """_materialise_stream sets error_code=0 when all results succeeded."""
        gen = iter([OperationResult.ok("a"), OperationResult.ok("b")])
        response = Response.from_stream(gen, renderer=BaseRenderer())
        OutputFormatMixin._materialise_stream(response)
        assert response.error_code == 0

    def test_success_false_when_any_failed(self) -> None:
        """_materialise_stream sets success=False when any result failed."""
        renderer = BaseRenderer()
        gen = iter([OperationResult.ok("a"), OperationResult.error("b", "boom")])
        response = Response.from_stream(gen, renderer=renderer)
        OutputFormatMixin._materialise_stream(response)
        assert response.success is False

    def test_error_code_from_first_failure(self) -> None:
        """_materialise_stream sets error_code from the first failed result."""
        renderer = BaseRenderer()
        gen = iter(
            [
                OperationResult.error("a", "err", error_code=3),
                OperationResult.error("b", "err", error_code=5),
            ]
        )
        response = Response.from_stream(gen, renderer=renderer)
        OutputFormatMixin._materialise_stream(response)
        assert response.error_code == 3

    def test_message_from_renderer_on_success(self) -> None:
        """_materialise_stream sets message from renderer.get_success_message on success."""

        class _MsgRenderer(BaseRenderer):
            success_message = "stream done"

        renderer = _MsgRenderer()
        gen = iter([OperationResult.ok("a")])
        response = Response.from_stream(gen, renderer=renderer)
        OutputFormatMixin._materialise_stream(response)
        assert response.message == "stream done"

    def test_message_from_renderer_on_failure(self) -> None:
        """_materialise_stream sets message from renderer.get_failure_message on failure."""

        class _MsgRenderer(BaseRenderer):
            failure_message = "stream failed"

        renderer = _MsgRenderer()
        gen = iter([OperationResult.error("a", "boom")])
        response = Response.from_stream(gen, renderer=renderer)
        OutputFormatMixin._materialise_stream(response)
        assert response.message == "stream failed"


class TestPaginatedResponse:
    """Test suite for PaginatedResponse."""

    def test_to_dict_includes_pagination_block(self) -> None:
        """to_dict includes a 'pagination' key with page, limit, and total."""
        response = PaginatedResponse(success=True, message="ok", page=2, limit=10, total=42)
        result = response.to_dict()
        assert result["pagination"] == {"page": 2, "limit": 10, "total": 42}

    def test_to_dict_total_none_is_serialized(self) -> None:
        """to_dict includes total=None when total is not known."""
        response = PaginatedResponse(success=True, message="ok")
        result = response.to_dict()
        assert result["pagination"]["total"] is None

    def test_default_values(self) -> None:
        """PaginatedResponse defaults are page=1, limit=20, total=None."""
        response = PaginatedResponse(success=True, message="ok")
        assert response.page == 1
        assert response.limit == 20
        assert response.total is None

    def test_inherits_response_fields(self) -> None:
        """PaginatedResponse carries all base Response fields."""
        response = PaginatedResponse(success=False, message="error", data={"x": 1}, error_code=3)
        result = response.to_dict()
        assert result["success"] is False
        assert result["message"] == "error"
        assert result["error_code"] == 3

    def test_from_results_returns_paginated_response(self) -> None:
        """from_results can be called on PaginatedResponse."""
        results = [OperationResult.ok("a")]
        response = PaginatedResponse.from_results(results, message="done")
        assert isinstance(response, Response)
        assert response.success is True
