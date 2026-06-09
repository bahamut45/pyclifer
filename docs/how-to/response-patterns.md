# Response Patterns

A pyclifer command is always four layers: a **model** that holds data, an **interface** that
executes business logic and returns `OperationResult` objects, a **renderer** that controls
display, and a **command** that wires them together and returns a `Response`.

This guide shows the minimum code for each variant of that pattern.

## Try it first

The `pyclifer demo tasks` app is a working implementation of this pattern. Run it to see the
output before reading the code:

```bash
# single-item command (add)
pyclifer demo tasks add --title "Fix login bug" --priority high

# collection command (list)
pyclifer demo tasks list

# same data, different formats
pyclifer demo tasks list -o json
pyclifer demo tasks list -o yaml
pyclifer demo tasks list -o table
```

Source: [`src/pyclifer/apps/demo/apps/tasks/`](https://github.com/bahamut45/pyclifer/tree/main/src/pyclifer/apps/demo/apps/tasks)

## The four layers at a glance

```
model       → defines the data shape
interface   → executes logic, returns list[OperationResult]
renderer    → controls table columns, JSON fields, Rich output
command     → calls interface.respond(), returns Response
```

`BaseInterface.respond()` is the glue: it calls the interface method, collects the results,
builds the `Response`, and attaches the renderer — the command just returns what `respond()`
gives back.

## Single-item command

The simplest case: a command that creates or retrieves one resource.

**Model** — a dataclass ([`tasks/models.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/apps/tasks/models.py)):

```python
# tasks/models.py
import datetime
from dataclasses import dataclass, field


@dataclass
class Task:
    id: str
    title: str
    status: str = "open"
    priority: str = "medium"
    due_date: datetime.date | None = None
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
```

**Renderer** — set class attributes, override nothing ([`tasks/renderers.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/apps/tasks/renderers.py)):

```python
# tasks/renderers.py
from pyclifer import BaseRenderer
from .models import Task


class TaskAddRenderer(BaseRenderer):
    model_class = Task
    fields = ["id", "title", "priority", "status"]
    columns = ["id", "title", "priority", "status"]
    success_message = "Task added successfully."
    failure_message = "Failed to add task."
```

`fields` drives JSON/YAML/raw serialization. `columns` drives the table. Both default to all
dataclass fields when left empty — set them explicitly to control ordering and visibility.
`failure_message` is optional for single-result commands: when omitted, the `OperationResult.message`
set in the interface propagates automatically (see [Error Handling](error-handling.md)).

**Interface** — returns `list[OperationResult]` ([`tasks/interfaces.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/apps/tasks/interfaces.py)):

```python
# tasks/interfaces.py
import uuid
import datetime
from pyclifer import BaseInterface, OperationResult
from .models import Task
from .renderers import TaskAddRenderer


class TaskInterface(BaseInterface):
    renderers = {
        "add_task": TaskAddRenderer,
    }

    def add_task(self, title: str, priority: str = "medium") -> list[OperationResult]:
        """Create and persist a new task."""
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            priority=priority,
            created_at=datetime.datetime.now(),
        )
        # persist task...
        return [OperationResult.ok(item=task.id, message=f"Task '{title}' created.", data=task)]
```

The `renderers` dict maps method names to renderer classes. `respond()` looks up the renderer
automatically by method name.

**Command** — calls `respond()` and returns the result ([`tasks/commands/add.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/apps/tasks/commands/add.py)):

```python
# tasks/commands/add.py
from pyclifer import Response, command, option
from ..context import pass_my_context
from ..interfaces import TaskInterface


@command()
@option("--title", required=True, help="Task title.")
@option("--priority", default="medium", help="Task priority.")
@pass_my_context
def add(ctx, title: str, priority: str) -> Response:
    """Add a new task."""
    return TaskInterface(ctx).respond("add_task", title=title, priority=priority)
```

`respond()` builds a `Response` from the `OperationResult` list, attaches `TaskAddRenderer`,
and determines `success` from whether all results succeeded. The command returns it; pyclifer
prints it in the format requested by `--output-format`.

## Collection command

For commands that return multiple items, the pattern is identical — the interface returns a
longer list and the renderer declares more columns.

**Interface** — one `OperationResult` per item:

```python
class TaskInterface(BaseInterface):
    renderers = {
        "add_task": TaskAddRenderer,
        "list_tasks": TaskListRenderer,
    }

    def list_tasks(self, status: str | None = None) -> list[OperationResult]:
        """Return all tasks, optionally filtered by status."""
        tasks = self._storage.get_tasks()
        if status:
            tasks = [t for t in tasks if t.status == status]
        return [OperationResult.ok(item=t.id, data=t) for t in tasks]
```

**Command** — no change to the call site:

```python
@command()
@option("--status", default=None, help="Filter by status.")
@pass_my_context
def list(ctx, status: str | None) -> Response:
    """List all tasks."""
    return TaskInterface(ctx).respond("list_tasks", status=status)
```

The table formatter iterates `response.data["results"]` and renders one row per result.
JSON and YAML output follow the same structure.

## Attaching context

`BaseInterface.__init__` receives `ctx` and stores it as `self.ctx`. If your interface needs
application-specific helpers (storage, HTTP clients, config), put them on your `BaseContext`
subclass and access them via `self.ctx`:

```python
# core/context.py
from pyclifer import BaseContext, make_pass_decorator


class MyContext(BaseContext):
    def __init__(self):
        super().__init__()
        self.storage = InMemoryStorage()


pass_my_context = make_pass_decorator(MyContext)
```

```python
# tasks/interfaces.py
class TaskInterface(BaseInterface):
    ctx: MyContext  # typed for IDE completion

    def list_tasks(self) -> list[OperationResult]:
        tasks = self.ctx.storage.get_tasks()  # access context helpers
        ...
```

## Quick reference

| Pattern | Interface return type | Command return |
|---|---|---|
| Single item | `list[OperationResult]` (one item) | `interface.respond("method")` |
| Collection | `list[OperationResult]` (many items) | `interface.respond("method")` |
| Streaming | `Iterator[OperationResult]` | `Response.from_stream(...)` |

The streaming variant is covered in [Rich Progressive Output](rich-progressive-output.md).

## See also

- [Error Handling](error-handling.md) — returning failures from the interface layer
- [Output Formatting](../output-formatting.md) — full `BaseRenderer` API reference
- [API — Interfaces](../api/interfaces.md) — `BaseInterface` and `respond()` internals
- Real-world examples in the demo app: [`tasks/interfaces.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/apps/tasks/interfaces.py), [`tasks/renderers.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/apps/tasks/renderers.py), [`tasks/commands/`](https://github.com/bahamut45/pyclifer/tree/main/src/pyclifer/apps/demo/apps/tasks/commands)
