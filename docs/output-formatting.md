# Output Formatting and Responses

pyclifer provides a built-in system to standardize and format CLI output. It supports JSON, YAML,
interactive tables, Rich text, plain text, and raw values — all driven by `BaseContext`, the
`Response` dataclass, and `BaseRenderer`.

## Core Concepts

The output system is built around four parts:

1. **`BaseContext`** — Combines `OutputFormatMixin` and `RichHelpersMixin`. All commands receive
   it as their Click context and use it to dispatch output.
2. **`Response`** — A standardized dataclass for structuring command results. Carries `success`,
   `message`, `data`, `error_code`, and an optional `renderer`.
3. **`BaseRenderer`** — Controls how a `Response` is displayed for every output format. Subclass
   it and set class attributes; the framework calls the right method based on `--output-format`.
4. **Mixins** — `OutputFormatMixin` handles format dispatch; `RichHelpersMixin` provides Rich
   console helpers.

## Automatic Output Format Option

`@app_group` and `@group` automatically add `--output-format` / `-o` to the CLI. It is propagated
globally to all subcommands. The selected format is stored in `ctx.meta['pyclifer.output_format']`
and read automatically by `BaseContext` — you do not need to declare an `output_format` parameter
in your functions.

## Automatic Response Dispatch

pyclifer provides three complementary mechanisms to print a `Response` automatically when a command
returns one, without manually calling `ctx.print_result_based_on_format(response)`.

### Level 1 — App-wide (default)

Response handling is **on by default** for `@app_group`. Every command that returns a
`Response` is automatically dispatched to the output formatter. Disable per-command with
`handle_response=False`, or app-wide with `@app_group(handle_response=False)`.

```python
from pyclifer import app_group, option, Response
import click


@app_group()
@click.pass_context
def app(ctx):
    """My CLI."""
    pass


@app.command()
@option("--name", default="world")
@click.pass_context
def hello(ctx, name):
    """Greet someone."""
    return Response(success=True, message=f"Hello {name}!", data={"name": name})
```

Per-command opt-out:

```python
@app.command(handle_response=False)
@click.pass_context
def raw_cmd(ctx):
    """This command manages its own output."""
    click.echo("custom output")
```

### Level 2 — Standalone command: `@command(handle_response=True)`

```python
from pyclifer import command, option, Response
import click


@command(handle_response=True)
@option("--name", default="world")
@click.pass_context
def hello(ctx, name):
    """Greet someone."""
    return Response(success=True, message=f"Hello {name}!", data={"name": name})


app.add_command(hello)
```

### Level 3 — Explicit decorator: `@returns_response`

```python
from pyclifer import returns_response, Response
import click


@app.command()
@returns_response
@click.pass_context
def hello(ctx):
    """Greet someone."""
    return Response(success=True, message="Hello!", data={})
```

### Output Format Resolution

All three mechanisms read the format from `ctx.meta['pyclifer.output_format']`, set by
`--output-format`. Explicit values (command-line or environment variable) always take precedence.

```bash
myapp --output-format json hello --name Alice   # JSON output
myapp -o yaml hello                             # YAML output
```

## Filtering Output — `@output_filter_option()`

Add `@output_filter_option()` to expose `--output-filter` / `-f`. Works with `raw`, `json`,
and `yaml`. Accepts a **dotted key path** — single keys and nested traversal both work.

```python
from pyclifer import app_group, output_filter_option, Response
import click


@app_group()
@click.pass_context
def app(ctx):
    """My CLI."""
    pass


@app.command()
@output_filter_option()
@click.pass_context
def list_articles(ctx):
    """List articles."""
    return Response(
        success=True,
        message="2 articles retrieved",
        data={
            "results": [
                {"id": 1, "title": "Hello pyclifer", "author": "Alice"},
                {"id": 2, "title": "Advanced usage", "author": "Bob"},
            ]
        },
    )
```

Resolution order: `data["data"]` first, then top-level response fields (`success`, `message`,
`error_code`). Numeric path segments are treated as list indices. Negative indices are
supported — `results.-1.id` points to the last element.

The output format determines how the extracted value is printed:

```bash
# raw: value as-is — best for shell scripting and piping
myapp -o raw list-articles -f results           # [{"id": 1, ...}, {"id": 2, ...}]
myapp -o raw list-articles -f results.0.title   # Hello pyclifer
myapp -o raw list-articles -f results.-1.title  # Advanced usage  (last element)
myapp -o raw list-articles -f message           # 2 articles retrieved

# json: value re-serialized as valid JSON
myapp -o json list-articles -f results.0        # {"id": 1, "title": "Hello pyclifer", ...}
myapp -o json list-articles -f results.0.id     # 1

# yaml: value re-serialized as valid YAML
myapp -o yaml list-articles -f results.0.title  # 'Hello pyclifer'\n
```

### Invalid filter paths

When the path cannot be resolved, pyclifer prints an error in the **active output format**
with the available keys at the last valid node, then exits with code 2.

With `-o json`:

```bash
myapp -o json list-articles -f results.0.nonexistent
```

```json
{
  "success": false,
  "message": "filter path 'results.0.nonexistent' not found in response.",
  "error_code": 2,
  "data": {
    "results": [
      {"available_keys": ["author", "id", "title"]}
    ]
  }
}
```

Exit code is always `2` regardless of format.

## The Response Object

`Response` carries the result of a command: success state, a message, optional structured data,
and a renderer that controls the output for every format.

```python
from pyclifer import Response

# Minimal response — uses BaseRenderer defaults for all formats
response = Response(
    success=True,
    message="Operation completed successfully",
    data={"id": 1, "status": "active"},
)
```

Attach a `BaseRenderer` subclass to control table columns, JSON fields, and Rich display:

```python
from pyclifer import Response, BaseRenderer


class ArticleRenderer(BaseRenderer):
    fields = ["id", "title", "author"]   # included in JSON / YAML / raw
    columns = ["id", "title", "author"]  # shown in the table
    rich_title = "Articles"


response = Response(
    success=True,
    message="Articles retrieved",
    data={"results": [...]},
    renderer=ArticleRenderer(),
)
```

In practice, renderers are attached by `BaseInterface.respond()` automatically — you rarely
need to set `renderer=` by hand. See [Error Handling](error-handling.md) and
[Interfaces](api/interfaces.md) for the full pattern.

## Supported Formats

| Format  | Renderer method called          | Description                                     | Filterable |
|---------|---------------------------------|-------------------------------------------------|------------|
| `table` | `renderer.table()`              | Rich table — **default format**                 | no         |
| `rich`  | `renderer.rich()` / Live hooks  | Rich panels / live display                      | no         |
| `text`  | `renderer.text()`               | Plain text — `response.message` only            | no         |
| `json`  | `renderer.serialize()`          | Syntax-highlighted JSON — always valid JSON     | yes        |
| `yaml`  | `renderer.serialize()`          | Syntax-highlighted YAML — always valid YAML     | yes        |
| `raw`   | `renderer.raw()`                | Compact JSON, no highlighting — machine-readable| yes        |

`table` is the default format.

`--output-filter` accepts a single key (checks `data` sub-dict first, then top-level fields).
Its behaviour differs by format:

- **`raw --output-filter key`** — prints the raw extracted value as-is. `running`, not `"running"`.
  Use this for shell scripts where the value feeds another command.
- **`json --output-filter key`** — re-serializes the extracted value as valid JSON.
  Output is always valid JSON: `"running"`, `42`, or `{"id": 1}`.
- **`yaml --output-filter key`** — re-serializes the extracted value as valid YAML.
  Output is always valid YAML.

```bash
myapp status --output-format raw -f status    # running          (raw string)
myapp status --output-format json -f status   # "running"        (valid JSON string)
myapp status --output-format yaml -f status   # 'running'\n      (valid YAML)
myapp status --output-format json -f data     # {"status": "running", ...}  (valid JSON object)
```

## Using BaseRenderer

`BaseRenderer` is the single source of truth for all output formats. Subclass it and set
class attributes — the framework calls the right method automatically based on `--output-format`.

### Declarative renderer

```python
from pyclifer import BaseRenderer


class ArticleRenderer(BaseRenderer):
    # Fields included in JSON / YAML / raw serialization
    fields = ["id", "title", "author", "published"]

    # Columns shown in the table (defaults to fields when empty)
    columns = ["id", "title", "author"]

    # Panel title used by the default rich() display
    rich_title = "Articles"

    # Static success / failure messages (optional — see below)
    success_message = "Articles retrieved."
    failure_message = "Failed to retrieve articles."
```

`serialize()` builds a dict from the `fields` list. Every row always carries `item` (from
`OperationResult.item`), and `success` + `error_code` by default (`include_row_meta=True`).
For failed results, model fields are set to `null` so the consumer knows which resource failed.
`table()` uses `columns` to build a `CliTable`, with failed rows highlighted in red by default.
Both are auto-called by the framework.

#### `failure_message` — resolution order

`get_failure_message()` uses the first rule that matches:

1. **Static `failure_message` attribute** — set on the class; always wins when present.
2. **Single failed result** — when the batch has exactly one result and it failed,
   `results[0].message` is used directly. This means renderers for single-result commands
   (add, delete, show) get the per-resource error message for free without overriding anything.
3. **Count string** — `"N/M operation(s) failed."` for mixed or multi-failure batches.

Omitting `failure_message` is safe for any renderer whose command returns a single result —
the interface-layer message propagates automatically.

#### `include_row_meta` — per-row metadata in serialized output

`include_row_meta = True` (default) injects `success` and `error_code` into every row of
`serialize()` output. This lets consumers of JSON/YAML distinguish failed rows from
successful rows with empty data:

```json
{
  "success": false,
  "message": "1/2 operation(s) failed.",
  "error_code": 3,
  "data": {
    "results": [
      {"item": "pool_01", "success": true,  "error_code": 0,  "total": 1000, "used": 400},
      {"item": "pool_02", "success": false, "error_code": 3,  "total": null, "used": null}
    ]
  }
}
```

Set `include_row_meta = False` for read-only commands that never produce failures (e.g., a
task list) to keep the output clean:

```python
class TaskListRenderer(BaseRenderer):
    fields = ["id", "title", "status"]
    include_row_meta = False  # suppress success/error_code from every row
```

#### `_serialize_result` — per-row serialization hook

Override `_serialize_result()` to customize how a single `OperationResult` is serialized,
without replacing the batch logic in `serialize()`:

```python
class StorageRenderer(BaseRenderer):
    fields = ["total", "used", "available"]

    def _serialize_result(self, r, fields):
        row = super()._serialize_result(r, fields)
        if r.success and r.data:
            row["utilization"] = round(r.data.get("used", 0) / r.data.get("total", 1) * 100, 1)
        return row
```

`item`, `success`, and `error_code` are injected by the base implementation after your
field extraction runs, so they are always authoritative — do not set them yourself.

#### `_row_style` — per-row table style hook

`_row_style()` controls the Rich style applied to each row in the table. The default marks
failed rows red:

```python
def _row_style(self, result: OperationResult) -> str | None:
    return "red" if not result.success else None
```

Override it to use different styles — for example, to colour rows by status:

```python
_STATUS_STYLE = {"done": "dim", "in_progress": "yellow", "blocked": "red bold"}

class TaskListRenderer(BaseRenderer):
    def _row_style(self, result: OperationResult) -> str | None:
        if not result.success:
            return "red"
        status = result.data.get("status") if isinstance(result.data, dict) else None
        return _STATUS_STYLE.get(status)
```

Return `None` for the default table style (alternating `none`/`dim` rows).

### Overriding individual methods

Override only what the declarative attributes cannot express:

```python
from rich.console import Console
from rich.table import Table as RichTable
from pyclifer import BaseRenderer, Response


class UserRenderer(BaseRenderer):
    fields = ["username", "email", "active"]
    columns = ["username", "email", "active"]

    def rich(self, response: Response, console: Console) -> None:
        """Colour active / inactive rows."""
        table = RichTable(title="Users")
        table.add_column("Username")
        table.add_column("Email")
        table.add_column("Active")
        for result in response.data.get("results", []):
            d = result.data or {}
            color = "green" if d.get("active") else "red"
            table.add_row(
                d.get("username", ""),
                d.get("email", ""),
                f"[{color}]{'yes' if d.get('active') else 'no'}[/{color}]",
            )
        console.print(table)
```

### Streaming support

For long-running operations that yield results one by one, override the Live context hooks.
The framework uses a `rich.live.Live` context during streaming; `rich_on_item()` is called after
each `OperationResult` arrives, and `rich_summary()` is called once the generator is exhausted.

```python
from rich.progress import Progress, SpinnerColumn, TextColumn
from pyclifer import BaseRenderer, Response, OperationResult


class DeployRenderer(BaseRenderer):
    fields = ["item", "success"]
    columns = ["item", "success"]
    success_message = "Deployment complete."
    failure_message = "Deployment failed."

    def rich_setup(self):
        """Create the Progress bar shown inside the Live context."""
        self._progress = Progress(SpinnerColumn(), TextColumn("{task.description}"))
        self._task = self._progress.add_task("Deploying…")
        return self._progress

    def rich_on_item(self, result: OperationResult, all_so_far: list) -> None:
        """Update the progress bar after each result."""
        icon = "✓" if result.success else "✗"
        self._progress.update(self._task, description=f"{icon} {result.item}")

    def rich_summary(self, response: Response, console) -> None:
        """Print a summary panel after the Live context closes."""
        status = "Success" if response.success else "Failed"
        console.print(f"[bold]{status}[/bold]: {response.message}")
```

Use `Response.from_stream()` in the command to wire a generator to this renderer:

```python
from pyclifer import Response, command, pass_context


@command()
@pass_context
def deploy(ctx) -> Response:
    """Deploy the application."""
    return Response.from_stream(
        MyInterface(ctx).deploy(),
        renderer=DeployRenderer(),
    )
```

## Unhandled Exceptions

Any exception that escapes a command is caught by the framework before output is produced.
You do not need `try`/`except` in your commands for expected failures — use
`OperationResult.error()` in the interface layer instead (see [Error Handling](error-handling.md)).

For truly unexpected exceptions (programming errors, broken invariants), the framework:

- Prints a formatted `Response(success=False, message=str(e))` to **stdout**, respecting
  `--output-format` (JSON, table, rich, raw…)
- Logs the traceback to **stderr** at the configured log level

The log level is configured on `@app_group`:

```python
@app_group(
    handle_response=True,
    unhandled_exception_log_level="error",  # default — traceback always visible
)
def main():
    """My CLI."""

# Use "debug" for clean end-user output; full traces only with --log-level debug
@app_group(
    handle_response=True,
    unhandled_exception_log_level="debug",
)
def main():
    """My CLI."""
```

## BaseContext and Mixins

Commands can print a `Response` manually by calling `ctx.print_result_based_on_format()`:

```python
import click
from pyclifer import app_group, BaseContext, Response


@app_group()
@click.pass_context
def cli(ctx):
    """CLI with output management."""
    pass


@cli.command()
@click.pass_context
def get_users(ctx):
    """List users."""
    response = Response(
        success=True,
        message="Users retrieved",
        data={"results": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]},
    )
    ctx.obj.print_result_based_on_format(response)
```

In practice you rarely call this directly — `handle_response=True` or `@returns_response` handle
it automatically.

## Rich Helpers

`RichHelpersMixin` (included in `BaseContext`) gives easy access to Rich console interactions:

```python
@cli.command()
@click.pass_context
def interactive_command(ctx):
    """Interactive command."""
    ctx.obj.rich_panel("Welcome to interactive mode!", title="Hello")

    name = ctx.obj.ask_user("What is your name?", default="User")

    with ctx.obj.show_status("Processing..."):
        import time
        time.sleep(2)
```

## Table Utilities

pyclifer provides built-in table components used internally by `BaseRenderer.table()`. You can
also construct them directly for custom renderers:

- **`CliTable`**: Pre-styled Rich table for structured data.
- **`CliTableColumn`**: Column descriptor with header, style, and justify options.
- **`ExceptionTable`**: Specialized table for displaying formatted exception details.

```python
from pyclifer import CliTable, CliTableColumn

fields = {
    "id": CliTableColumn(header="ID", justify="right"),
    "name": CliTableColumn(header="Name"),
    "active": CliTableColumn(header="Active"),
}

table = CliTable(fields=fields, rows=[
    {"id": 1, "name": "Alice", "active": True},
    {"id": 2, "name": "Bob", "active": False},
])
```

## Paginated Commands — `pagination_options()` and `PaginatedResponse`

For commands that list resources, `pagination_options()` injects `--page` / `-p` and
`--limit` / `-l` in a single decorator. Values are stored in `ctx.meta` and read by the
command without being passed as function arguments.

```python
from pyclifer import app_group, command, pagination_options, PaginatedResponse, pass_context


@app_group()
@pass_context
def app(ctx):
    """My CLI."""


@app.command()
@pagination_options(default_limit=50, max_limit=200)
@pass_context
def list_articles(ctx):
    """List articles."""
    page = ctx.meta["pyclifer.page"]
    limit = ctx.meta["pyclifer.limit"]
    results, total = ArticleService.list(page=page, limit=limit)
    return PaginatedResponse(
        success=True,
        message=f"{len(results)} articles retrieved.",
        data={"results": results},
        page=page,
        limit=limit,
        total=total,
    )
```

```bash
myapp list-articles --page 2 --limit 25
myapp list-articles -p 2 -l 25
```

`PaginatedResponse` extends `Response` with a `pagination` block in JSON and YAML output:

```json
{
  "success": true,
  "message": "25 articles retrieved.",
  "pagination": {"page": 2, "limit": 25, "total": 142},
  "data": {"results": [...]}
}
```

When `total` is unknown (`total=None`), it is serialized as `null`. The `table`, `rich`, and
`text` formats are unaffected — `PaginatedResponse` behaves identically to `Response` for
those formats.

`pagination_options()` parameters:

| Parameter       | Default | Description                                    |
|-----------------|---------|------------------------------------------------|
| `default_limit` | `20`    | Default value for `--limit`                    |
| `max_limit`     | `100`   | Maximum value enforced by `IntRange`           |

## See Also

- [Getting Started](getting-started.md)
- [Error Handling](error-handling.md)
- [Examples](examples.md)
- [Configuration Management](configuration.md)
- [API — Output](api/output.md)
- [API — Interfaces](api/interfaces.md)