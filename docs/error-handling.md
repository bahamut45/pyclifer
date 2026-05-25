# Error Handling

pyclif enforces a strict separation between the service layer (interface) and the view layer
(command). This makes error handling consistent, testable, and free of boilerplate.

## The contract

| Layer | Tool | Responsibility |
|-------|------|----------------|
| **Interface** | `BaseInterface` subclass | Executes actions. Returns `list[OperationResult]` or `Iterator[OperationResult]`. Never raises for expected business failures. |
| **Command** | `@command()` function | Thin view. Calls `interface.respond()`, returns a `Response`. No try/except. |

Exceptions are reserved for programming errors: missing templates, corrupt state, broken
invariants. The last resort handler catches anything that escapes and formats it as a clean
`Response` — stdout is always properly formatted regardless of the error.

## OperationResult

`OperationResult` is the unit of work returned by an interface method. Use the class methods
to construct success or failure outcomes:

```python
from pyclif import OperationResult

# Success
result = OperationResult.ok("src/my_app/cli.py", data={"action": "created"})

# Failure — normalised error code
result = OperationResult.error(
    "src/my_app/cli.py",
    message="File already exists.",
    error_code=2,
)
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `success` | `bool` | Whether the action succeeded |
| `item` | `str` | Human-readable identifier (file path, resource name, …) |
| `data` | `Any` | Optional payload (e.g. `{"action": "created"}`) |
| `message` | `str` | Human-readable description of the outcome |
| `error_code` | `int` | Non-zero on failure |

## Writing an interface

Interface methods return `list[OperationResult]` or `Iterator[OperationResult]` — they never
raise for expected failures:

```python
from collections.abc import Iterator
from pyclif import BaseInterface, OperationResult


class MyInterface(BaseInterface):
    def create_resource(self, name: str) -> list[OperationResult]:
        if self._exists(name):
            return [OperationResult.error(name, f"'{name}' already exists.", error_code=2)]
        self._write(name)
        return [OperationResult.ok(name, data={"action": "created"})]

    def bulk_create(self, names: list[str]) -> list[OperationResult]:
        return [self.create_resource(name)[0] for name in names]

    def stream_files(self, paths: list[str]) -> Iterator[OperationResult]:
        """Generator variant — results are yielded one by one for live output."""
        for path in paths:
            yield self._process_file(path)
```

The interface decides whether to stop on the first failure (return early) or continue
collecting results across all items.

## Writing a command

### Using BaseInterface.respond() — recommended

`BaseInterface.respond()` is the standard way to call an interface method from a command. It
auto-detects whether the method returns a list or a generator, selects the renderer declared
in `renderers`, and builds the `Response` automatically:

```python
from pyclif import command, argument, pass_context, Response

from .interfaces import MyInterface


@command()
@argument("name")
@pass_context
def create(ctx, name: str) -> Response:
    """Create a resource."""
    return MyInterface(ctx).respond("create_resource", name)
```

The renderer is declared once on the interface class:

```python
from pyclif import BaseInterface, BaseRenderer, OperationResult


class MyRenderer(BaseRenderer):
    fields = ["item", "action", "success"]
    columns = ["item", "action"]
    rich_title = "Resources"
    success_message = "Resource created."
    failure_message = "Resource creation failed."


class MyInterface(BaseInterface):
    renderers = {
        "create_resource": MyRenderer,
        "bulk_create": MyRenderer,
    }

    def create_resource(self, name: str) -> list[OperationResult]:
        if self._exists(name):
            return [OperationResult.error(name, f"'{name}' already exists.", error_code=2)]
        self._write(name)
        return [OperationResult.ok(name, data={"action": "created"})]
```

### Using Response.from_results() directly

For cases where you need full control over the message or renderer at call time, call
`from_results()` manually:

```python
from pyclif import Response, argument, command, pass_context

from .interfaces import MyInterface
from .renderers import MyRenderer


@command()
@argument("name")
@pass_context
def create(ctx, name: str) -> Response:
    """Create a resource."""
    results = MyInterface(ctx).create_resource(name)
    return Response.from_results(
        results,
        success_message=f"'{name}' created.",
        failure_message=f"Failed to create '{name}'.",
        renderer=MyRenderer(),
    )
```

## Response.from_results()

Aggregates a list of `OperationResult` into a single `Response`:

```python
from pyclif import Response

results = interface.do_something()
response = Response.from_results(
    results,
    success_message="Operation completed.",
    failure_message="Operation failed.",
    renderer=MyRenderer(),
)
```

- `success=True` only if **all** results succeeded
- `error_code` is taken from the first failed result (None if all passed)
- `data["results"]` carries the full list for table rendering

**Message selection** — in order of precedence:
1. `message` — fixed, used regardless of outcome
2. `success_message` / `failure_message` — selected based on outcome
3. Auto-generated summary (`"N operation(s) completed."` / `"N/M operation(s) failed."`)

## Boundary rule

| Situation | Interface does |
|-----------|----------------|
| Resource already exists | `OperationResult.error` |
| Target not found | `OperationResult.error` |
| Invalid input | `OperationResult.error` |
| Missing required file (framework bug) | `raise RuntimeError` |
| Corrupt template / broken invariant | `raise RuntimeError` |

## Last resort handler

Any exception that escapes the interface and command is caught by the framework before output
is produced. The two streams are always independent:

- **stdout** — a properly formatted `Response(success=False, message=str(e))`, respecting
  `--output-format` (JSON, table, rich, raw)
- **stderr** — traceback via the logging system, visible at the configured verbosity level

The log level for unhandled exceptions is set on `@app_group`:

```python
from pyclif import app_group

@app_group(
    unhandled_exception_log_level="error",   # default — always visible
)
def main():
    """My CLI."""

# Quieter — traceback only with --log-level debug or --log-level trace
@app_group(
    unhandled_exception_log_level="debug",
)
def main():
    """My CLI."""
```

The default is `"error"` so that nothing is silently swallowed in production. Use `"debug"`
when you want clean output for end users and full traces only for developers.