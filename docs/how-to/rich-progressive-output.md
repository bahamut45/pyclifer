# Rich Progressive Output

Stream results to the terminal as they arrive — with a live spinner or progress bar during
execution and a summary panel on completion.

The pattern is identical to [Response Patterns](response-patterns.md) with two differences:
the interface method `yield`s instead of returning a list, and the renderer implements three
Live hooks.

## Try it first

```bash
pyclifer demo tasks sync
pyclifer demo tasks sync -o json
pyclifer demo tasks sync -o table
```

The `rich` format (default) shows a live progress bar. The `json` and `table` formats buffer
all results and render once the stream is complete.

Source: [`tasks/interfaces.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/apps/tasks/interfaces.py),
[`tasks/renderers.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/apps/tasks/renderers.py),
[`tasks/commands/sync.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/apps/tasks/commands/sync.py)

## How it works

```
interface.sync_tasks()   →  yields OperationResult one at a time
renderer.rich_setup()    →  returns the Live renderable (Progress, Table, …)
renderer.rich_on_item()  →  called after each result; update the renderable
renderer.rich_summary()  →  called once the stream closes; print final output
command                  →  identical to the non-streaming case
```

`respond()` auto-detects that the interface method returns a generator and switches to
`Response.from_stream()` — the command call site does not change.

## The interface

Return type changes from `list[OperationResult]` to `Iterator[OperationResult]`, and `return`
becomes `yield`:

```python
# tasks/interfaces.py
import time
from collections.abc import Iterator
from pyclifer import BaseInterface, OperationResult


class TaskInterface(BaseInterface):
    renderers = {
        "sync_tasks": TaskSyncRenderer,
    }

    def sync_tasks(self, source: str = "https://remote.example.com/tasks") -> Iterator[OperationResult]:
        """Fetch tasks from a remote source, yielding one result per task."""
        for item in fetch_remote(source):   # any iterable — HTTP stream, DB cursor, …
            time.sleep(0.1)                 # simulate network latency
            yield OperationResult.ok(item=item.id, data=item, message=f"Synced: {item.title}")
```

The interface method does not need to know anything about the renderer or the Live context.
It just yields results as they become available.

## The renderer

Implement three hooks on `BaseRenderer`:

```python
# tasks/renderers.py
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from pyclifer import BaseRenderer


class TaskSyncRenderer(BaseRenderer):
    fields = ["id", "title", "success"]
    columns = ["id", "title", "success"]
    success_message = "Sync completed."
    failure_message = "Sync failed."

    def rich_setup(self):
        """Return the renderable that the Live context will display.

        Called once before the stream starts. Return any Rich renderable:
        Progress, Table, Layout, …
        """
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
        )
        self._progress = progress
        self._task_bar = progress.add_task("Syncing…", total=None)
        return self._progress

    def rich_on_item(self, result, all_so_far: list) -> None:
        """Update the renderable after each OperationResult arrives.

        Args:
            result: The latest OperationResult from the stream.
            all_so_far: Every result received up to and including this one.
        """
        self._progress.advance(self._task_bar)

    def rich_summary(self, response, console) -> None:
        """Print the final output after the stream closes and Live exits.

        Args:
            response: The fully materialized Response with all results.
            console: The Rich console — use it to print panels, rules, tables.
        """
        console.rule("[bold green]Sync complete")
        console.print(f"{len(response.data.get('results', []))} tasks imported.")
```

`rich_setup()` is the only required hook — if you omit `rich_on_item()` or `rich_summary()`,
the framework uses no-op defaults.

## The command

Identical to a non-streaming command:

```python
# tasks/commands/sync.py
from pyclifer import Response, command, option
from ..context import pass_my_context
from ..interfaces import TaskInterface


@command()
@option("--source", default="https://remote.example.com/tasks", help="Remote URL.")
@pass_my_context
def sync(ctx, source: str) -> Response:
    """Sync tasks from a remote source."""
    return TaskInterface(ctx).respond("sync_tasks", source=source)
```

`respond()` detects that `sync_tasks` returns a generator and calls
`Response.from_stream()` automatically. No change needed at the call site.

## Non-Rich formats

Streaming is only visual — the `json`, `yaml`, `table`, and `raw` formats buffer all results
and render once the stream is exhausted. The same command works correctly with every format:

```bash
pyclifer demo tasks sync -o json    # waits for all results, then prints JSON
pyclifer demo tasks sync -o table   # waits for all results, then prints table
pyclifer demo tasks sync -o rich    # live progress bar while streaming
```

## Spinner variant

For operations where the total count is unknown upfront, a spinner is simpler than a progress
bar. The scaffolding renderer uses this pattern:

```python
from rich.progress import Progress, SpinnerColumn, TextColumn
from pyclifer import BaseRenderer


class SpinnerRenderer(BaseRenderer):
    def rich_setup(self):
        progress = Progress(SpinnerColumn(), TextColumn("{task.description}"))
        self._progress = progress
        self._task = progress.add_task("Processing…")
        return self._progress

    def rich_on_item(self, result, all_so_far: list) -> None:
        icon = "✓" if result.success else "✗"
        self._progress.update(self._task, description=f"{icon}  {result.item}")
```

Real example: [`project/renderers.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/project/renderers.py)
(`ScaffoldingRenderer` — used by `pyclifer project init` and `pyclifer project add`).

## Using `Response.from_stream()` directly

When the stream is assembled in the command itself rather than in a single interface method
(for example, chaining multiple generators), call `Response.from_stream()` directly instead
of going through `respond()`:

```python
@command()
@argument("name")
@pass_my_context
def init(ctx, name: str) -> Response:
    """Create a new project."""
    def _stream():
        yield from ScaffoldingInterface(ctx).init_project(name)
        yield from ScaffoldingInterface(ctx).add_integration("github")

    return Response.from_stream(_stream(), renderer=ScaffoldingRenderer(name=name))
```

Real example: [`project/commands/init.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/project/commands/init.py)

## See also

- [Response Patterns](response-patterns.md) — the non-streaming baseline
- [Output Formatting](../output-formatting.md) — full `BaseRenderer` API and Live hook reference
- [API — Interfaces](../api/interfaces.md) — `respond()` and `from_stream()` internals