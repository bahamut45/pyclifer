# Error Handling

Two recipes depending on where the failure originates: in the interface layer (the standard
pattern) or directly in the command (for lightweight cases without an interface).

For the full conceptual explanation of the interface/command contract, see
[Error Handling — User Guide](../error-handling.md).

## Try it

```bash
# not-found error — error_code 404 in the output
pyclif demo tasks show "nonexistent-id"
pyclif demo tasks show "nonexistent-id" -o json

# already-done error — no error_code, just success=false
pyclif demo tasks complete <an-already-done-task-id>
```

## Recipe 1 — Interface layer (standard pattern)

The interface returns `OperationResult.error()` for expected business failures. The command
has no error handling code — it just calls `respond()` and returns.

### Resource not found

```python
# tasks/interfaces.py
def show_task(self, task_id: str) -> list[OperationResult]:
    task = self.ctx.storage.get_task(task_id)
    if task is None:
        return [OperationResult.error(
            item=task_id,
            message=f"Task '{task_id}' not found.",
            error_code=404,
        )]
    return [OperationResult.ok(item=task.id, data=task)]
```

```python
# tasks/commands/show.py
@command()
@argument("task_id")
@pass_my_context
def show(ctx, task_id: str) -> Response:
    """Show details of a specific task."""
    return TaskInterface(ctx).respond("show_task", task_id=task_id)
```

Source: [`tasks/interfaces.py`](https://github.com/bahamut45/pyclif/blob/main/src/pyclif/apps/demo/apps/tasks/interfaces.py)

### Resource already in desired state

When the failure is a business rule rather than a missing resource, omit `error_code`:

```python
def complete_task(self, task_id: str) -> list[OperationResult]:
    task = self.ctx.storage.get_task(task_id)
    if task is None:
        return [OperationResult.error(item=task_id, message=f"Task '{task_id}' not found.", error_code=404)]
    if task.status == "done":
        return [OperationResult.error(item=task_id, message=f"Task '{task_id}' is already done.")]
    task.status = "done"
    self.ctx.storage.upsert_task(task)
    return [OperationResult.ok(item=task_id, message=f"Task '{task.title}' marked as done.")]
```

### Stop on first failure vs collect all

Return early to stop on the first failure:

```python
def create_files(self, paths: list[str]) -> list[OperationResult]:
    results = []
    for path in paths:
        if Path(path).exists():
            return [OperationResult.error(path, f"'{path}' already exists.", error_code=2)]
        results.append(self._write(path))
    return results
```

Remove the early return to collect all failures instead:

```python
def create_files(self, paths: list[str]) -> list[OperationResult]:
    results = []
    for path in paths:
        if Path(path).exists():
            results.append(OperationResult.error(path, f"'{path}' already exists.", error_code=2))
        else:
            results.append(self._write(path))
    return results
```

## Recipe 2 — Command layer (no interface)

For lightweight commands that do a quick check and don't need an interface, build
`Response(success=False, ...)` directly:

```python
# commands/ping.py
import httpx
from pyclif import Response, command, option
from ..context import pass_my_context


@command()
@option("--url", required=True, help="URL to check.")
@pass_my_context
def ping(ctx, url: str) -> Response:
    """Check that a URL is reachable."""
    try:
        r = httpx.get(url, timeout=5)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return Response(
            success=False,
            message=f"{url} returned HTTP {exc.response.status_code}.",
            error_code=exc.response.status_code,
        )
    except httpx.RequestError as exc:
        return Response(success=False, message=f"Could not reach {url}: {exc}", error_code=1)
    return Response(success=True, message=f"{url} is reachable.")
```

Use this pattern when:
- There is no domain model or interface to go through
- The check is a single operation that either works or doesn't
- The command is a utility that doesn't fit the interface pattern

## Error codes

`error_code` appears in machine-readable output (`-o json`, `-o yaml`, `-o raw`) and is
useful for scripts that need to distinguish between failure reasons:

```bash
code=$(pyclif demo tasks show "bad-id" -o json | jq .error_code)
# code=404 → not found, code=2 → conflict, code=1 → generic failure
```

`error_code` does **not** set the process exit code. The process always exits `0` unless you
raise `SystemExit` explicitly or the framework's `--output-filter` path encounters a bad path
(exits `2`). To set a process exit code on failure:

```python
response = TaskInterface(ctx).respond("show_task", task_id=task_id)
if not response.success:
    raise SystemExit(response.error_code or 1)
return response
```

## Decision table

| Situation | Pattern |
|---|---|
| Resource not found | `OperationResult.error(item, message, error_code=404)` in interface |
| Resource already exists | `OperationResult.error(item, message, error_code=2)` in interface |
| Business rule violated | `OperationResult.error(item, message)` in interface (no error_code) |
| Bulk operation, collect all failures | return full list from interface, no early return |
| Bulk operation, stop on first failure | return early from interface on first failure |
| No interface, quick check | `Response(success=False, message=..., error_code=...)` in command |
| Programming error / broken invariant | `raise RuntimeError(...)` — framework catches and formats |

## See also

- [Error Handling — User Guide](../error-handling.md) — contract, boundary rules, last-resort handler
- [Response Patterns](response-patterns.md) — the full interface → command wiring
- [Multi-integration Commands](multi-integration-commands.md) — combining results from multiple interfaces
- [`tasks/interfaces.py`](https://github.com/bahamut45/pyclif/blob/main/src/pyclif/apps/demo/apps/tasks/interfaces.py) — real-world examples of every error pattern above