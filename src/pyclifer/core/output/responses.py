"""Response and OperationResult classes."""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator
from operator import attrgetter
from typing import TYPE_CHECKING, Any

from .exit_codes import ExitCode

if TYPE_CHECKING:
    from .renderer import BaseRenderer

NON_SERIALIZABLE_FIELDS = ["renderer"]


@dataclasses.dataclass
class OperationResult:
    """Outcome of a single interface action.

    Interface methods return this instead of rising for expected business
    failures. Exceptions are reserved for programming errors (broken invariant,
    missing template, corrupt state).

    Attributes:
        success: Whether the action succeeded.
        item: Human-readable identifier (file path, resource name, …).
        data: Optional payload attached to the result.
        message: Human-readable description of the outcome.
        error_code: Non-zero on failure.
    """

    success: bool
    item: str
    data: Any = None
    message: str = ""
    error_code: int = 0

    @classmethod
    def ok(cls, item: str, message: str = "", data: Any = None) -> OperationResult:
        """Create a successful result.

        Args:
            item: Human-readable identifier for the operated resource.
            message: Human-readable description of what happened.
            data: Optional domain payload.

        Returns:
            A successful OperationResult with error_code 0.
        """
        return cls(success=True, item=item, message=message, data=data)

    @classmethod
    def error(cls, item: str, message: str, error_code: int = ExitCode.ERROR) -> OperationResult:
        """Create a failed result.

        Args:
            item: Human-readable identifier for the operated resource.
            message: Description of the failure.
            error_code: Exit code for this failure (default 1).

        Returns:
            A failed OperationResult with the given error_code.
        """
        return cls(success=False, item=item, message=message, error_code=error_code)


@dataclasses.dataclass
class Response:
    """Represents a CLI command response with structured output support.

    Attributes:
        success: Indicates whether the response is successful.
        message: The message associated with the response.
        data: Additional data associated with the response.
        error_code: The error code associated with the response.
        renderer: Renderer controlling all output formats for this response.
    """

    success: bool
    message: str
    data: Any = dataclasses.field(default_factory=dict)
    error_code: int | None = None
    renderer: BaseRenderer | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the object.

        Only includes fields whose values differ from their defaults.

        Returns:
            Dictionary mapping attributes names to their values.
        """
        return dict(
            (f.name, attrgetter(f.name)(self))
            for f in dataclasses.fields(self)
            if attrgetter(f.name)(self) != f.default
        )

    def to_json(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary of the response.

        Non-serializable fields (callbacks) are excluded from the output.

        Returns:
            Dictionary containing the serializable attributes.
        """
        self._serialize_data()
        data = self.to_dict()
        for field in NON_SERIALIZABLE_FIELDS:
            data.pop(field, None)
        return data

    @classmethod
    def from_results(
        cls,
        results: list[OperationResult],
        message: str = "",
        success_message: str = "",
        failure_message: str = "",
        renderer: BaseRenderer | None = None,
    ) -> Response:
        """Build a Response from a list of OperationResult.

        Aggregates a batch of interface results into a single Response.
        success is True only if every result succeeded. error_code is taken
        from the first failed result, or 0 if all passed.

        Args:
            results: Outcomes returned by the interface layer.
            message: Fixed message used regardless of the outcome. When omitted,
                success_message / failure_message are used, or a default
                summary is generated from the result counts.
            success_message: Message used when all results succeeded.
            failure_message: Message used when at least one result failed.
            renderer: Renderer instance controlling all output formats.

        Returns:
            An aggregated Response reflecting the overall outcome.
        """
        failed = [r for r in results if not r.success]
        success = not failed
        error_code = failed[0].error_code if failed else 0

        if not message:
            if success:
                message = success_message or f"{len(results)} operation(s) completed successfully."
            else:
                message = failure_message or f"{len(failed)}/{len(results)} operation(s) failed."

        return cls(
            success=success,
            message=message,
            data={"results": results},
            error_code=error_code if not success else 0,
            renderer=renderer,
        )

    @classmethod
    def from_stream(
        cls,
        stream: Iterator[OperationResult],
        renderer: BaseRenderer,
    ) -> Response:
        """Build a Response from a generator of OperationResult.

        The generator is stored without being consumed. The framework
        materializes it at dispatch time: for rich output the Live context
        drives iteration via renderer hooks; for all other formats
        OutputFormatMixin calls _materialise_stream() before dispatch.

        success, message, and error_code are left blank — they are
        re-evaluated by the framework after the stream is consumed, using
        renderer.get_success_message() / get_failure_message().

        Args:
            stream: Generator yielding OperationResult items one by one.
            renderer: Renderer instance — required, a stream with no renderer
                has no output contract.

        Returns:
            An incomplete Response carrying the stream and renderer.
        """
        return cls(
            success=True,
            message="",
            data={"stream": stream},
            renderer=renderer,
        )

    def _serialize_data(self):
        """Serialize dict values that expose a to_dict method in place."""
        if isinstance(self.data, dict):
            serialized_dict = {}
            for key, value in self.data.items():
                if callable(getattr(value, "to_dict", None)):
                    serialized_dict[key] = value.to_dict()
                else:
                    serialized_dict[key] = value
            self.data = serialized_dict


@dataclasses.dataclass
class PaginatedResponse(Response):
    """Response carrying pagination metadata in its serialized output.

    Extends Response with page, limit, and total fields that are included
    as a 'pagination' block in JSON and YAML output.

    Attributes:
        page: Current page number (1-indexed).
        limit: Number of results per page.
        total: Total number of results across all pages, or None if unknown.
    """

    page: int = 1
    limit: int = 20
    total: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Include a 'pagination' block in the serialized output.

        Returns:
            Dictionary with all Response fields plus a 'pagination' block.
        """
        base = super().to_dict()
        base["pagination"] = {"page": self.page, "limit": self.limit, "total": self.total}
        return base
