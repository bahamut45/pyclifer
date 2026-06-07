"""Renderer protocol and base class for all pyclifer output formats."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from pyclifer.core.models import BaseModel

    from .responses import OperationResult, Response
    from .tables import CliTable, CliTableColumn


class ResponseRenderer(Protocol):  # pragma: no cover
    """Protocol for renderer implementations.

    Renderers are the single source of truth for all output formats of a command.
    Implement this Protocol directly only when inheriting BaseRenderer is not
    appropriate. All methods called by the framework must be present.
    """

    def serialize(self, response: Response) -> dict:
        """Return a JSON-serializable dict for the response."""
        ...

    def table(self, response: Response) -> CliTable:
        """Build a CliTable from the response results."""
        ...

    def text(self, response: Response) -> str:
        """Return the response message as plain text."""
        ...

    def raw(self, response: Response) -> dict:
        """Return a serialized dict for machine-readable output."""
        ...

    def rich(self, response: Response, console: Console) -> None:
        """Print a static Rich display (panels, markdown, tables) to the console."""
        ...

    def rich_setup(self) -> Any:
        """Return the initial Rich renderable for the Live context."""
        ...

    def rich_on_item(self, result: OperationResult, all_so_far: list) -> None:
        """Update the Live renderable after each streamed item."""
        ...

    def rich_summary(self, response: Response, console: Console) -> None:
        """Print a summary after the Live context closes."""
        ...

    def get_success_message(self, results: list) -> str:
        """Return the success message for a completed batch."""
        ...

    def get_failure_message(self, results: list) -> str:
        """Return the failure message for a partially or fully failed batch."""
        ...


class BaseRenderer:
    """Declarative base class for pyclifer output renderers.

    Subclass and declare class attributes to control every output format.
    Override individual hooks for custom behavior. Override the full method
    only as a last resort.

    Class attributes:
        fields: Field names included in JSON/YAML serialization. Empty means
            all fields via the standard Response.to_json() fallback.
        columns: Column names for table output. Falls back to fields when empty.
        rich_title: Panel title used by the default rich() and table() display.
        success_message: Static success message returned by get_success_message().
        failure_message: Static failure message returned by get_failure_message().
        datetime_format: strftime format for datetime values in table output.
        date_format: strftime format for date values in table output.

    Implementation note — class-level lists: fields and columns are ClassVar.
    Subclasses override them as plain class attributes (never mutated at runtime).
    get_fields() and get_columns() always return a copy, so callers cannot
    accidentally mutate the class-level list.
    """

    fields: ClassVar[list[str]] = []
    columns: ClassVar[list[str]] = []
    rich_title: ClassVar[str] = ""
    success_message: ClassVar[str] = ""
    failure_message: ClassVar[str] = ""
    model_class: ClassVar[type[BaseModel] | None] = None
    datetime_format: ClassVar[str] = "%Y-%m-%d %H:%M"
    date_format: ClassVar[str] = "%Y-%m-%d"

    def get_fields(self) -> list[str]:
        """Return the effective field list.

        Resolution order: explicit fields declaration, then model_class.field_names(),
        then empty list.

        Returns:
            Field name strings in declaration order.
        """
        if self.fields:
            return list(self.fields)
        if self.model_class is not None:
            return self.model_class.field_names()
        return []

    def get_columns(self) -> list[str]:
        """Return a copy of the declared columns list, falling back to fields."""
        return list(self.columns) or list(self.fields)

    def _result_to_row(self, result: OperationResult, columns: list[str]) -> dict:
        """Extract a row dict from an OperationResult for the given column names.

        Checks result.data first (domain payload), then falls back to top-level
        OperationResult attributes (item, success, message, error_code).
        If result.data is a BaseModel, it is serialized via to_dict() before lookup.

        Args:
            result: The operation result to extract data from.
            columns: Column names to extract.

        Returns:
            Dict mapping each column name to its value.
        """
        data = result.data
        if hasattr(data, "to_dict") and callable(data.to_dict):
            data = data.to_dict()
        row = {}
        for col in columns:
            if isinstance(data, dict) and col in data:
                row[col] = data[col]
            else:
                row[col] = getattr(result, col, None)
        return row

    def serialize(self, response: Response) -> dict:
        """Return a JSON-serializable dict filtered to self.fields.

        When fields are empty, delegates to response.to_json() for full
        serialization with standard exclusions.

        Args:
            response: The command response to serialize.

        Returns:
            Dict suitable for JSON/YAML output.
        """
        fields = self.get_fields()
        if not fields:
            return response.to_json()

        results = response.data.get("results", [])
        serialized = []
        for r in results:
            data = r.data
            if hasattr(data, "to_dict") and callable(data.to_dict):
                data = data.to_dict()
            row = {
                f: data.get(f) if isinstance(data, dict) and f in data else getattr(r, f, None)
                for f in fields
            }
            serialized.append(row)
        return {
            "success": response.success,
            "message": response.message,
            "error_code": response.error_code,
            "data": {"results": serialized},
        }

    def table(self, response: Response) -> CliTable:
        """Build a CliTable from response.data["results"] using self.columns.

        Args:
            response: The command response carrying the result list.

        Returns:
            A CliTable instance is ready for console.print().
        """
        # Lazy import — renderer.py and tables.py are in the same package;
        # importing at module level would create a circular dependency via
        # responses.py (which imports BaseRenderer for its renderer field).
        from .tables import CliTable, CliTableColumn  # noqa: PLC0415

        cols = self.get_columns()
        fields_dict: dict[str, CliTableColumn] = {
            col: CliTableColumn(header=col.replace("_", " ").title()) for col in cols
        }
        results = response.data.get("results", [])
        rows = [self._result_to_row(r, cols) for r in results]
        title = self.rich_title or response.message or None
        return CliTable(
            fields=fields_dict,
            rows=rows,
            table_style={"title": title} if title else None,
            datetime_format=self.datetime_format,
            date_format=self.date_format,
        )

    # noinspection PyMethodMayBeStatic
    def text(self, response: Response) -> str:
        """Return the response message as plain text.

        Args:
            response: The command response.

        Returns:
            The response message string.
        """
        return response.message

    def raw(self, response: Response) -> dict:
        """Return a serialized dict for machine-readable output.

        Defaults to serialize() output. Override for a custom raw representation.

        Args:
            response: The command response.

        Returns:
            Serialized dict suitable for compact JSON output.
        """
        return self.serialize(response)

    @staticmethod
    def _detail_grid() -> Table:
        """Return a two-column key-value grid for detail panels.

        Returns:
            A Table configured as a key-value grid with a bold-cyan label column.
        """
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold cyan", no_wrap=True)
        grid.add_column()
        return grid

    def _first_result(self, response: Response, console: Console) -> OperationResult | None:
        """Return the first successful result, printing an error panel when absent.

        Args:
            response: The command response to inspect.
            console: The Rich console to print an error panel to on failure.

        Returns:
            The first OperationResult, or None when results are empty or the first
            result is a failure.
        """
        results = response.data.get("results", [])
        if not results or not results[0].success:
            console.print(Panel(response.message, title=self.rich_title or None))
            return None
        return results[0]

    def rich(self, response: Response, console: Console) -> None:
        """Display a panel with the response message.

        Override for panels, rules, markdown, or any static Rich display.

        Args:
            response: The command response to display.
            console: The Rich console to print to.
        """
        title = self.rich_title or None
        console.print(Panel(response.message, title=title))

    def rich_setup(self) -> Any:
        """Return the initial renderable for the Live context.

        Called once before iteration starts. Override to create and store
        stateful Rich objects (Progress, Layout, etc.) as instance attributes
        so rich_on_item() can mutate them.

        Returns:
            A Rich renderable to wrap in Live().
        """
        return Panel("Working…")

    def rich_on_item(self, result: OperationResult, all_so_far: list) -> None:
        """Called after each streamed item inside the Live context.

        Override to mutate the Rich objects created in rich_setup().

        Args:
            result: The latest OperationResult.
            all_so_far: All results received so far, including a result.
        """

    def rich_summary(self, response: Response, console: Console) -> None:
        """Called after all items are processed and the Live context is closed.

        Defaults to the static rich() display. Override for a custom summary.

        Args:
            response: The fully materialized response with all results.
            console: The Rich console to print to.
        """
        self.rich(response, console)

    def get_success_message(self, results: list) -> str:
        """Return the success message for a completed batch.

        Args:
            results: All OperationResult items from the batch.

        Returns:
            Human-readable success message.
        """
        return self.success_message or f"{len(results)} operation(s) completed successfully."

    def get_failure_message(self, results: list) -> str:
        """Return the failure message for a partially or fully failed batch.

        Args:
            results: All OperationResult items from the batch.

        Returns:
            Human-readable failure message with failure count.
        """
        if self.failure_message:
            return self.failure_message
        failed = sum(1 for r in results if not r.success)
        return f"{failed}/{len(results)} operation(s) failed."
