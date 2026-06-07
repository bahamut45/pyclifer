"""Output formatting mixin for CLI contexts."""

import json
import traceback
from typing import Any

import yaml
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax

from pyclifer.core.output.exit_codes import ExitCode
from pyclifer.core.output.renderer import BaseRenderer
from pyclifer.core.output.responses import OperationResult, Response


class _FallbackEncoder(json.JSONEncoder):
    """JSON encoder that degrades gracefully for non-serializable objects.

    Resolution order for each value that the default encoder cannot handle:
    1. `to_dict()` — pyclifer / domain objects that expose a serialization method.
    2. `__dict__` — generic Python instances.
    3. `str()` — last resort; preserves readability without crashing.
    """

    def default(self, obj: Any) -> Any:
        """Encode non-serializable objects using available introspection methods."""
        if callable(getattr(obj, "to_dict", None)):
            return obj.to_dict()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)


class _ExceptionRenderer(BaseRenderer):
    """Internal renderer for unhandled exceptions.

    Renders error details across all output formats. Not part of the public API.
    """

    fields = ["available_keys"]

    def table(self, response: Response) -> Any:
        """Build an ExceptionTable from the first result's error data."""
        # Lazy import — tables.py would create a circular import at module level
        # because tables.py → output → renderer → responses → renderer.
        from pyclifer.core.output.tables import ExceptionTable  # noqa: PLC0415

        result = response.data["results"][0]
        tb = result.data.get("traceback", "") if isinstance(result.data, dict) else ""
        return ExceptionTable({"error_code": result.item, "message": result.message, "data": tb})

    def rich(self, response: Response, console: Any) -> None:
        """Display the error message in a red panel.

        Args:
            response: The error response.
            console: The Rich console to print to.
        """
        console.print(Panel(response.message, title="Error", style="red"))


class OutputFormatMixin:
    """Provide methods for printing error messages and results based on a specified format.

    This mixin expects the inheriting class to have 'console' and 'output_format' attributes.
    Every result must be a Response with a renderer attached.
    """

    def print_error_based_on_format(self, exception: Exception) -> None:
        """Format and print an unhandled exception as a structured Response.

        Creates a single-result Response from the exception and dispatches
        it through the normal renderer path using _ExceptionRenderer.

        Args:
            exception: The exception to display.
        """
        result = OperationResult(
            success=False,
            item=type(exception).__name__,
            message=str(exception),
            error_code=ExitCode.ERROR,
            data={"traceback": traceback.format_exc()},
        )
        response = Response.from_results(
            [result], message=str(exception), renderer=_ExceptionRenderer()
        )
        self.print_result_based_on_format(response)

    @staticmethod
    def _materialise_stream(response: Response) -> None:
        """Consume a streaming Response generator and re-evaluate its fields.

        Replaces data["stream"] with data["results"], then re-computes
        success, error_code, and message from the materialized list using
        the renderer's message methods.

        Args:
            response: A Response carrying a generator in data["stream"].
        """
        assert response.renderer is not None, "_materialise_stream requires a renderer"
        items = list(response.data.pop("stream"))
        failed = [r for r in items if not r.success]
        response.success = not bool(failed)
        response.error_code = failed[0].error_code if failed else None
        response.message = (
            response.renderer.get_success_message(items)
            if not failed
            else response.renderer.get_failure_message(items)
        )
        response.data["results"] = items

    def print_result_based_on_format(self, result: Response, options: dict | None = None) -> None:
        """Print a Response using its renderer.

        Streaming responses (data["stream"] present) are handled via the Live
        context for rich output, or materialized first for all other formats.

        Args:
            result: The Response to print. Must have a renderer attached.
            options: Optional dict with the filter_value key for --output-filter support.

        Raises:
            RuntimeError: When result.renderer is None — a programming error.
        """
        renderer: BaseRenderer = result.renderer or BaseRenderer()
        result.renderer = renderer

        opts: dict = options or {}
        output_format: str | None = getattr(self, "output_format", None)

        if "stream" in result.data:
            if output_format == "rich":
                renderable = renderer.rich_setup()
                items: list = []
                with Live(renderable, console=self.console):  # type: ignore[attr-defined]
                    for item in result.data.pop("stream"):
                        items.append(item)
                        renderer.rich_on_item(item, items)
                result.data["results"] = items
                renderer.rich_summary(result, self.console)  # type: ignore[attr-defined]
                return
            self._materialise_stream(result)
        filter_key: str | None = opts.get("filter_value")

        def _json() -> None:
            serialized = renderer.serialize(result)
            if filter_key:
                self._print_json(self._apply_output_filter(serialized, filter_key))
            else:
                self._print_json(serialized)

        def _yaml() -> None:
            serialized = renderer.serialize(result)
            if filter_key:
                self._print_yaml(self._apply_output_filter(serialized, filter_key))
            else:
                self._print_yaml(serialized)

        dispatch: dict[str, Any] = {
            "json": _json,
            "yaml": _yaml,
            "table": lambda: self.console.print(renderer.table(result)),  # type: ignore[attr-defined]
            "rich": lambda: renderer.rich(result, self.console),  # type: ignore[attr-defined]
            "raw": lambda: self._print_raw_dict(renderer.raw(result), filter_key),
            "text": lambda: self.console.print(renderer.text(result)),  # type: ignore[attr-defined]
        }
        dispatch.get(output_format or "table", dispatch["table"])()

    @staticmethod
    def _resolve_filter_path(data: dict, path: str) -> tuple[Any, bool]:
        """Traverse a dotted path in a nested dict or list.

        Args:
            data: The dict to traverse.
            path: Dotted path — numeric segments are treated as list indices,
                  negative indices are supported (e.g. 'results.-1.id').

        Returns:
            A tuple of (resolved value, found). If the path does not exist,
            found is False and value is None.
        """
        segments = path.split(".")
        node: Any = data
        for segment in segments:
            if isinstance(node, list):
                if not segment.lstrip("-").isdigit():
                    return None, False
                idx = int(segment)
                if idx >= len(node) or idx < -len(node):
                    return None, False
                node = node[idx]
            elif isinstance(node, dict):
                if segment not in node:
                    return None, False
                node = node[segment]
            else:
                return None, False
        return node, True

    def _apply_output_filter(self, serialized: dict, filter_path: str) -> Any:
        """Resolve a dotted filter path in a serialized response, or exit with an error.

        Traverses data["data"] first (the structured payload), then falls back
        to the top-level dict. On failure, prints an error Response and raises
        SystemExit(2).

        Args:
            serialized: Serialized response dict.
            filter_path: Dotted path to resolve (e.g. "results.0.id").

        Returns:
            The resolved value.

        Raises:
            SystemExit: With code 2 when the path cannot be resolved.
        """
        sub = serialized.get("data")
        if isinstance(sub, dict):
            value, found = self._resolve_filter_path(sub, filter_path)
            if found:
                return value

        value, found = self._resolve_filter_path(serialized, filter_path)
        if found:
            return value

        available_keys = sorted(sub.keys() if isinstance(sub, dict) else serialized.keys())
        message = f"filter path '{filter_path}' not found in response."
        err_result = OperationResult(
            success=False,
            item="output-filter",
            message=message,
            error_code=ExitCode.INVALID_INPUT,
            data={"available_keys": available_keys},
        )
        error_response = Response.from_results(
            [err_result], message=message, renderer=_ExceptionRenderer()
        )
        self.print_result_based_on_format(error_response)
        raise SystemExit(2)

    def _print_raw_dict(self, data: dict, filter_key: str | None) -> None:
        """Print a serialized dict as compact JSON, or extract and print a raw value.

        When filter_key is set, the extracted value is printed as-is with no
        re-serialization — suitable for shell scripting and piping.
        When filter_key is None, prints the full dict as compact JSON without
        syntax highlighting.

        Args:
            data: Serialized response dict from renderer.raw().
            filter_key: Key to extract, or None to print the full dict.
        """
        if filter_key:
            self.console.print(self._apply_output_filter(data, filter_key), soft_wrap=True)  # type: ignore[attr-defined]
        else:
            self.console.print(json.dumps(data, cls=_FallbackEncoder), soft_wrap=True)  # type: ignore[attr-defined]

    def _print_json(self, data: Any) -> None:
        """Print a value as syntax-highlighted JSON.

        Accepts any JSON-serializable value — dict, list, str, int, etc.
        Used for both full-response output and filtered single-value output.

        Args:
            data: Value to serialize and display as JSON.
        """
        self.console.print_json(json.dumps(data, cls=_FallbackEncoder))  # type: ignore[attr-defined]

    def _print_yaml(self, data: Any) -> None:
        """Print a value as syntax-highlighted YAML.

        Accepts any YAML-serializable value — dict, list, str, int, etc.
        Used for both full-response output and filtered single-value output.

        Args:
            data: Value to serialize and display as YAML.
        """
        yaml_content = yaml.dump(data, allow_unicode=True, indent=2, sort_keys=False)
        self.console.print(  # type: ignore[attr-defined]
            Syntax(yaml_content, "yaml", theme="ansi_dark"), soft_wrap=True
        )
