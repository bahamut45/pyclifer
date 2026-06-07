# Demo App

pyclifer ships a built-in demo application — a fully working task manager CLI that exercises
every framework feature. Run it right after installation to see pyclifer in action, then read
the walkthrough below to understand how it is built.

The demo covers:

- Multi-format output (`table`, `json`, `yaml`, `raw`, `rich`)
- Streaming results with a live progress bar
- Error handling via `OperationResult`
- Custom context, persistent JSON storage, filtered listings, pagination

Data is persisted in `~/.config/pyclifer/demo.json`.

## Part 1 — CLI Tour

### Explore the demo group

```bash
pyclifer demo --help
```

You will see two sub-groups (`tasks` and `users`) and the global options inherited from
`@app_group`: `-o` / `--output-format`, `-v` / `--verbosity`, `--config`.

### Create tasks

```bash
pyclifer demo tasks add --title "Fix login bug" --priority high
```

A Rich panel titled **Task added** appears with the new task id and a success message.
Add a few more tasks to work with:

```bash
pyclifer demo tasks add --title "Write docs" --priority low \
    --assignee alice --tags "docs,chore"
pyclifer demo tasks add --title "Deploy to staging" --priority medium \
    --due 2026-06-30
```

### List tasks

```bash
pyclifer demo tasks list
```

Output: a Rich table with columns `id`, `title`, `priority`, `status`, `due_date`, `assignee`.
This is the default `table` format set by the renderer.

Switch to JSON for machine-readable output:

```bash
pyclifer demo tasks list -o json
```

```json
{
  "success": true,
  "message": "Tasks retrieved successfully.",
  "data": {
    "results": [
      {
        "id": "3f2a…",
        "title": "Fix login bug",
        "priority": "high",
        "status": "open",
        "due_date": null,
        "assignee": ""
      }
    ]
  },
  "page": 1,
  "limit": 20,
  "total": 3
}
```

Filter by status or priority:

```bash
pyclifer demo tasks list --priority high
pyclifer demo tasks list --status open --priority high
```

### Show a task

Copy an id from the list output:

```bash
pyclifer demo tasks show <task-id>
```

A Rich detail panel appears with every field and a colored status/priority badge.

### Error handling

Complete a task, then try again:

```bash
pyclifer demo tasks complete <task-id>
# ✔ Task 'Fix login bug' marked as done.

pyclifer demo tasks complete <task-id>
# ✘ Task '…' is already done.
```

Fetch a non-existent id in JSON to inspect the error structure:

```bash
pyclifer demo tasks show "bad-id" -o json
```

```json
{
  "success": false,
  "message": "Task 'bad-id' not found.",
  "data": {},
  "error_code": 4
}
```

`error_code: 4` maps to `ExitCode.NOT_FOUND`. The process exits with code 1.

### Streaming sync

```bash
pyclifer demo tasks sync
```

A live progress bar animates as 8 tasks are imported one by one. When the stream closes,
a green rule prints the total count.

Switch to JSON to consume the same operation in a script:

```bash
pyclifer demo tasks sync -o json
```

The output is silent until all results are collected, then a single JSON object is printed
with all 8 tasks in `data.results`.

### Users sub-group

```bash
pyclifer demo users list
```

Three seed users (`alice`, `bob`, `carol`) appear in a Rich table on the first call.

```bash
pyclifer demo users whoami
```

A Rich panel titled **Logged in as \<your-unix-user\>** shows your auto-created profile.

## Part 2 — Code Walkthrough

The demo app lives in `src/pyclifer/apps/demo/`. It follows the exact same structure that
`pyclifer project init` generates for your own projects.

```
apps/demo/
├── __init__.py             # @group entry point, wires sub-groups and commands
├── core/
│   ├── context.py          # DemoContext — extends BaseContext with a storage property
│   ├── constants.py        # PRIORITY_CHOICE, STATUS_CHOICE Click types
│   ├── options.py          # --project global option
│   └── storage.py          # JSON file backend at ~/.config/pyclifer/demo.json
├── apps/
│   ├── tasks/
│   │   ├── models.py       # Task dataclass (Pydantic BaseModel)
│   │   ├── renderers.py    # TaskListRenderer, TaskDetailRenderer, TaskSyncRenderer…
│   │   ├── interfaces.py   # TaskInterface — business logic, yields/returns OperationResult
│   │   └── commands/       # one file per command (add, list, show, complete, delete, sync)
│   └── users/
│       ├── models.py       # User dataclass
│       ├── interfaces.py   # UserInterface + renderers
│       └── commands/       # list, whoami
├── interfaces.py           # top-level DemoInterface (unused in tour, available to extend)
├── models.py               # top-level shared models
└── tables.py               # top-level shared table helpers
```

### Layer 1 — Model

Source: [`apps/tasks/models.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/apps/tasks/models.py)

```python
class Task(BaseModel):
    id: str
    title: str
    description: str = ""
    priority: str = "medium"
    status: str = "open"
    due_date: datetime.date | None = None
    tags: list[str] = []
    assignee: str = ""
    created_at: datetime.datetime
```

`BaseModel` is pyclifer's re-export of `pydantic.BaseModel`. Pydantic validators on
`priority` and `status` reject values outside the allowed sets at construction time.

!!! tip "In your project"
    Run `pyclifer project init my-app` and `pyclifer project add app tasks` — the generated
    `apps/tasks/models.py` has the same shape, ready to fill with your own fields.

### Layer 2 — Renderer

Source: [`apps/tasks/renderers.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/apps/tasks/renderers.py)

Every output format (table, JSON, YAML, Rich, raw) is controlled from one class —
no formatting logic lives in commands or interfaces.

**Declarative renderer** — set class attributes, override nothing:

```python
class TaskListRenderer(BaseRenderer):
    model_class = Task
    fields = ["id", "title", "priority", "status", "due_date", "assignee"]
    columns = ["id", "title", "priority", "status", "due_date", "assignee"]
    rich_title = "Tasks"
    success_message = "Tasks retrieved successfully."
    failure_message = "Failed to retrieve tasks."
```

- `fields` — keys included in JSON / YAML / raw output
- `columns` — columns shown in the Rich table
- `rich_title` — panel / table title

**Streaming renderer** — three hooks drive the live progress bar in `sync`:

```python
class TaskSyncRenderer(BaseRenderer):
    def rich_setup(self) -> Any:
        # called once before the stream starts — return the Rich renderable for Live()
        progress = Progress(SpinnerColumn(), TextColumn("…"), BarColumn(), MofNCompleteColumn())
        self._progress = progress
        self._task_bar = progress.add_task("Syncing…", total=None)
        return self._progress

    def rich_on_item(self, result: OperationResult, all_so_far: list) -> None:
        # called after each yielded result — advance the bar
        self._progress.advance(self._task_bar)

    def rich_summary(self, response: Response, console: Console) -> None:
        # called once after the stream closes — print a summary
        results = response.data.get("results", [])
        console.rule("[bold green]Sync complete")
        console.print(f"{len(results)} tasks imported.")
```

When `-o json` is passed, none of these hooks are called — the framework waits for all
results and serialises them directly. The renderer stays format-agnostic.

!!! tip "In your project"
    See [Rich Progressive Output](how-to/rich-progressive-output.md) for the full guide on
    building streaming commands with live renderers.

### Layer 3 — Interface

Source: [`apps/tasks/interfaces.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/apps/tasks/interfaces.py)

The interface owns all business logic. It maps method names to renderers and returns
`OperationResult` objects — never strings, never HTTP responses.

```python
class TaskInterface(BaseInterface):
    ctx: DemoContext

    renderers = {
        "list_tasks": TaskListRenderer,
        "add_task": TaskAddRenderer,
        "show_task": TaskDetailRenderer,
        "complete_task": TaskCompleteRenderer,
        "delete_task": TaskDeleteRenderer,
        "sync_tasks": TaskSyncRenderer,
    }

    def list_tasks(
        self, status: str | None = None, priority: str | None = None
    ) -> list[OperationResult]:
        tasks = self.ctx.storage.get_tasks()
        if status:
            tasks = [t for t in tasks if t.status == status]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        return [OperationResult.ok(item=t.id, data=t) for t in tasks]

    def sync_tasks(self, source: str = "…") -> Iterator[OperationResult]:
        # yields one result per task — drives the streaming renderer
        for title in _FAKE_SYNC_TITLES:
            time.sleep(0.1)
            task = Task(id=str(uuid.uuid4()), title=title, created_at=datetime.datetime.now())
            self.ctx.storage.upsert_task(task)
            yield OperationResult.ok(item=task.id, data=task, message=f"Synced: {title}")
```

**Error path** — return `OperationResult.error()` with an `ExitCode`:

```python
    def show_task(self, task_id: str = "") -> list[OperationResult]:
        task = self.ctx.storage.get_task(task_id)
        if task is None:
            return [
                OperationResult.error(
                    item=task_id,
                    message=f"Task '{task_id}' not found.",
                    error_code=ExitCode.NOT_FOUND,
                )
            ]
        return [OperationResult.ok(item=task.id, data=task)]
```

`ExitCode.NOT_FOUND` is 4. The framework serialises this into `"error_code": 4` in JSON
and exits with code 1.

!!! tip "In your project"
    See [Response Patterns](how-to/response-patterns.md) for the full interface + renderer
    wiring, and [Error Handling](how-to/error-handling.md) for the complete error recipe.

### Layer 4 — Command

Source: [`apps/tasks/commands/add.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/apps/tasks/commands/add.py)

Commands are thin wiring. They declare options, call `respond()`, and return the result.
No formatting, no business logic.

```python
@command()
@option("--title", required=True, help="Task title.")
@option("--description", default="", help="Task description.")
@option("--priority", type=PRIORITY_CHOICE, default="medium", help="Task priority.")
@option("--due", type=DateTime(formats=["%Y-%m-%d"]), default=None, help="Due date (YYYY-MM-DD).")
@option("--tags", default="", help="Comma-separated list of tags.")
@option("--assignee", default="", help="Assignee username.")
@pass_demo_context
def add(ctx, title, description, priority, due, tags, assignee) -> Response:
    """Add a new task."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    return TaskInterface(ctx).respond(
        "add_task",
        title=title,
        description=description,
        priority=priority,
        due_date=due.date() if due else None,
        tags=tag_list,
        assignee=assignee,
    )
```

`respond("add_task", …)` looks up `renderers["add_task"]`, calls `add_task(…)`, wraps the
results in a `Response`, and returns it. The `@app_group(handle_response=True)` decorator
intercepts that `Response` and dispatches it to the right formatter.

Commands that use an `@argument` instead of `--option` (e.g. `show`, `complete`) are even
shorter:

```python
@command()
@argument("task_id")
@pass_demo_context
def show(ctx, task_id) -> Response:
    """Show details of a specific task."""
    return TaskInterface(ctx).respond("show_task", task_id=task_id)
```

!!! tip "In your project"
    Run `pyclifer project add command list --app tasks` to generate a pre-wired command stub
    following this exact pattern.

### Layer 5 — Core (context + storage)

Source: [`core/context.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/core/context.py),
[`core/storage.py`](https://github.com/bahamut45/pyclifer/blob/main/src/pyclifer/apps/demo/core/storage.py)

`DemoContext` extends `BaseContext` with a single addition — a lazily initialised `Storage`
property:

```python
class DemoContext(BaseContext):
    def __init__(self) -> None:
        super().__init__()
        self._storage: Storage | None = None

    @property
    def storage(self) -> Storage:
        if self._storage is None:
            self._storage = Storage()
        return self._storage

pass_demo_context = make_pass_decorator(DemoContext, ensure=True)
```

`make_pass_decorator` is pyclifer's typed equivalent of `click.make_pass_decorator`. The
`ensure=True` flag creates a fresh context if none exists, so commands always get a valid
`DemoContext` even when invoked in isolation.

`Storage` reads and writes a single JSON file:

```python
DATA_PATH = pathlib.Path.home() / ".config" / "pyclifer" / "demo.json"

class Storage:
    def upsert_task(self, task: Task) -> None:
        data = self.load()
        tasks = data.get("tasks", [])
        task_dict = task.model_dump(mode="json")
        for i, raw in enumerate(tasks):
            if raw["id"] == task.id:
                tasks[i] = task_dict
                break
        else:
            tasks.append(task_dict)
        data["tasks"] = tasks
        self.save(data)
```

In a real project you would replace `Storage` with a client for your actual backend
(database, API, cloud service). The interface layer never touches storage directly —
only through `ctx.storage` — so swapping the backend requires changing one file.

!!! tip "In your project"
    `pyclifer project init my-app` generates `core/context.py` with the same `BaseContext`
    extension pattern. Add your own service clients as properties there.

---

## Next steps

- Browse the full source: [`src/pyclifer/apps/demo/`](https://github.com/bahamut45/pyclifer/tree/main/src/pyclifer/apps/demo)
- Build the same structure for your own project: [Scaffolding](scaffolding.md)
- Deep-dive on output formats: [Choosing an Output Format](how-to/output-format.md)
- Streaming in detail: [Rich Progressive Output](how-to/rich-progressive-output.md)
- Error handling patterns: [Error Handling](how-to/error-handling.md)
