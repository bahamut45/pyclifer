"""Unit tests for BaseInterface."""

import pytest

from pyclifer import OperationResult
from pyclifer.core.interfaces import BaseInterface
from pyclifer.core.output.renderer import BaseRenderer
from pyclifer.core.output.responses import Response

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _DummyRenderer(BaseRenderer):
    """Test renderer with fixed success/failure messages."""

    success_message = "all good"
    failure_message = "some failed"


class _OtherRenderer(BaseRenderer):
    """Alternate test renderer."""

    success_message = "other"


def _ok(item: str = "item") -> OperationResult:
    return OperationResult.ok(item)


def _err(item: str = "item") -> OperationResult:
    return OperationResult.error(item, "boom")


# ---------------------------------------------------------------------------
# Interface stubs
# ---------------------------------------------------------------------------


class _FetchOkIface(BaseInterface):
    """Stub returning a single successful result."""

    @staticmethod
    def fetch() -> list[OperationResult]:
        """Return one successful result."""
        return [_ok()]


class _FetchTwoOkIface(BaseInterface):
    """Stub returning two successful results."""

    @staticmethod
    def fetch() -> list[OperationResult]:
        """Return two successful results."""
        return [_ok("a"), _ok("b")]


class _FetchMixedIface(BaseInterface):
    """Stub returning one success and one failure."""

    @staticmethod
    def fetch() -> list[OperationResult]:
        """Return one success and one failure."""
        return [_ok("a"), _err("b")]


class _FetchSingleItemIface(BaseInterface):
    """Stub returning a single result with item='x'."""

    @staticmethod
    def fetch() -> list[OperationResult]:
        """Return one result with item='x'."""
        return [_ok("x")]


class _DummyFetchIface(BaseInterface):
    """Stub using _DummyRenderer for fetch."""

    renderers = {"fetch": _DummyRenderer}

    @staticmethod
    def fetch() -> list[OperationResult]:
        """Return one successful result."""
        return [_ok()]


class _DummyFetchFailIface(BaseInterface):
    """Stub using _DummyRenderer and returning a failed result."""

    renderers = {"fetch": _DummyRenderer}

    @staticmethod
    def fetch() -> list[OperationResult]:
        """Return one failed result."""
        return [_err()]


class _DummyClassIface(BaseInterface):
    """Stub with renderer_class set to _DummyRenderer."""

    renderer_class = _DummyRenderer

    @staticmethod
    def fetch() -> list[OperationResult]:
        """Return one successful result."""
        return [_ok()]


class _OtherRendererIface(BaseInterface):
    """Stub with _DummyRenderer as default class and _OtherRenderer for fetch."""

    renderer_class = _DummyRenderer
    renderers = {"fetch": _OtherRenderer}

    @staticmethod
    def fetch() -> list[OperationResult]:
        """Return one successful result."""
        return [_ok()]


class _DummyGenerateIface(BaseInterface):
    """Stub with a generate() generator using _DummyRenderer."""

    renderers = {"generate": _DummyRenderer}

    @staticmethod
    def generate():
        """Yield two successful results."""
        yield _ok("a")
        yield _ok("b")


# ---------------------------------------------------------------------------
# TestBaseInterfaceInit
# ---------------------------------------------------------------------------


class TestBaseInterfaceInit:
    def test_stores_ctx(self) -> None:
        ctx = object()
        iface = BaseInterface(ctx)
        assert iface.ctx is ctx

    def test_ctx_none(self) -> None:
        iface = BaseInterface(None)
        assert iface.ctx is None


# ---------------------------------------------------------------------------
# TestRespondWithListMethod
# ---------------------------------------------------------------------------


class TestRespondWithListMethod:
    def test_returns_response(self) -> None:
        response = _FetchOkIface(None).respond("fetch")
        assert isinstance(response, Response)

    def test_success_when_all_results_ok(self) -> None:
        response = _FetchTwoOkIface(None).respond("fetch")
        assert response.success is True

    def test_failure_when_any_result_fails(self) -> None:
        response = _FetchMixedIface(None).respond("fetch")
        assert response.success is False

    def test_results_stored_in_data(self) -> None:
        response = _FetchSingleItemIface(None).respond("fetch")
        assert len(response.data["results"]) == 1
        assert response.data["results"][0].item == "x"

    def test_args_forwarded_to_method(self) -> None:
        class Iface(BaseInterface):
            """Stub with a parametric fetch method."""

            @staticmethod
            def fetch(name: str) -> list[OperationResult]:
                """Return one result using name as item."""
                return [_ok(name)]

        response = Iface(None).respond("fetch", "hello")
        assert response.data["results"][0].item == "hello"

    def test_kwargs_forwarded_to_method(self) -> None:
        class Iface(BaseInterface):
            """Stub with a keyword-parametric fetch method."""

            @staticmethod
            def fetch(name: str = "") -> list[OperationResult]:
                """Return one result using name as item."""
                return [_ok(name)]

        response = Iface(None).respond("fetch", name="world")
        assert response.data["results"][0].item == "world"


# ---------------------------------------------------------------------------
# TestRespondWithGeneratorMethod
# ---------------------------------------------------------------------------


class TestRespondWithGeneratorMethod:
    def test_returns_response_with_stream(self) -> None:
        response = _DummyGenerateIface(None).respond("generate")
        assert isinstance(response, Response)
        assert "stream" in response.data

    def test_stream_not_consumed(self) -> None:
        calls: list[str] = []

        class Iface(BaseInterface):
            """Stub whose generate() records calls to verify lazy evaluation."""

            renderers = {"generate": _DummyRenderer}

            @staticmethod
            def generate():
                """Record the call and yield one result."""
                calls.append("called")
                yield _ok("x")

        Iface(None).respond("generate")
        assert calls == []

    def test_renderer_attached(self) -> None:
        response = _DummyGenerateIface(None).respond("generate")
        assert isinstance(response.renderer, _DummyRenderer)


# ---------------------------------------------------------------------------
# TestRespondRendererSelection
# ---------------------------------------------------------------------------


class TestRespondRendererSelection:
    def test_uses_renderer_from_renderers_dict(self) -> None:
        response = _DummyFetchIface(None).respond("fetch")
        assert isinstance(response.renderer, _DummyRenderer)

    def test_falls_back_to_renderer_class(self) -> None:
        response = _DummyClassIface(None).respond("fetch")
        assert isinstance(response.renderer, _DummyRenderer)

    def test_renderer_class_default_is_base_renderer(self) -> None:
        response = _FetchOkIface(None).respond("fetch")
        assert type(response.renderer) is BaseRenderer

    def test_renderers_dict_overrides_renderer_class(self) -> None:
        response = _OtherRendererIface(None).respond("fetch")
        assert isinstance(response.renderer, _OtherRenderer)


# ---------------------------------------------------------------------------
# TestRespondMessages
# ---------------------------------------------------------------------------


class TestRespondMessages:
    def test_success_message_from_renderer(self) -> None:
        response = _DummyFetchIface(None).respond("fetch")
        assert response.message == "all good"

    def test_failure_message_from_renderer(self) -> None:
        response = _DummyFetchFailIface(None).respond("fetch")
        assert response.message == "some failed"


# ---------------------------------------------------------------------------
# TestRespondInvalidMethod
# ---------------------------------------------------------------------------


class TestRespondInvalidMethod:
    def test_raises_attribute_error_for_unknown_method(self) -> None:
        iface = BaseInterface(None)
        with pytest.raises(AttributeError):
            iface.respond("nonexistent")
