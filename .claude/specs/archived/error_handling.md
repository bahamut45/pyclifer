# Error handling — framework contract

## Design decision

The framework imposes a strict separation of responsibilities:

- **Interface** (service layer): executes actions, returns `OperationResult`. Never raises for
  expected business failures (file exists, not found, invalid input). Exceptions are reserved
  for programming errors (missing template, corrupt state, broken invariant).
- **Renderer** (output layer): declares how every output format (JSON, YAML, table, rich) looks
  for a given command. Owns success/failure messages.
- **Command** (view layer): three lines — instantiate interface, call `respond()`, return.
  No try/except, no business logic, no renderer knowledge.

This mirrors Django's MTV pattern: interface = Model/Service, renderer = Template/Serializer,
command = View. It is the enforced contract for all pyclifer projects.

## Core types (framework-level, `pyclifer.core`)

### `OperationResult`

Single operation outcome returned by an interface method:

```python
@dataclass
class OperationResult:
    success: bool
    item: str                       # human-readable identifier (file path, name, …)
    data: Any = None
    message: str = ""
    error_code: int = 0

    @classmethod
    def ok(cls, item: str, data: Any = None) -> "OperationResult": ...

    @classmethod
    def error(cls, item: str, message: str, error_code: int = 1) -> "OperationResult": ...
```

### `Response.from_results()`

Aggregates a list of `OperationResult` into a `Response`:
- `success=True` only if all results succeeded
- `error_code` from the first failed result (or 0)
- `data["results"]` carries the full list for rendering

```python
@classmethod
def from_results(
    cls,
    results: list[OperationResult],
    message: str = "",
    success_message: str = "",
    failure_message: str = "",
    renderer: BaseRenderer | None = None,
) -> "Response": ...
```

## The contract in practice

> This section shows the **current implementation** (pre-migration). The target pattern
> after migration is shown in the "Interface/renderer liaison" section.

```python
# Interface — returns OperationResult, never raises for business errors
class ScaffoldingInterface:
    def create_file(self, dest: Path, tmpl: str, ns: dict) -> OperationResult:
        if dest.exists():
            return OperationResult.error(str(dest), f"'{dest}' already exists.", error_code=2)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(self._render(tmpl, ns))
        return OperationResult.ok(str(dest))

    def init_project(self, name: str) -> list[OperationResult]:
        return [self.create_file(dest, tmpl, ns) for dest, tmpl in files]
```

```python
# Command — current pattern (pre-migration)
@command()
@argument("name")
@pass_context
def init(ctx, name: str) -> Response:
    """Create a new pyclifer project skeleton."""
    results = ScaffoldingInterface(ctx).init_project(name)
    return Response.from_results(results, message=f"Project '{name}' created.", table=ScaffoldingTable)
```

## Boundary rule

| Situation                                  | Interface does          |
|--------------------------------------------|-------------------------|
| File already exists                        | `OperationResult.error` |
| Target directory not found                 | `OperationResult.error` |
| Invalid input (bad name, unknown option)   | `OperationResult.error` |
| Template file missing (framework bug)      | raise `RuntimeError`    |
| Jinja2 render failure (corrupt template)   | raise `RuntimeError`    |
| `src/` absent (not a pyclifer project)       | raise `RuntimeError`    |

## Last resort handler (framework-level)

Any exception that escapes the interface and command layers is caught by the framework in
`returns_response`. The two outputs are strictly independent:

- **stdout** — always a properly formatted `Response`, respecting `--output-format`
- **stderr** — traceback via `_log.log(level, ..., exc_info=True)`, level controlled by the
  developer via `@app_group(unhandled_exception_log_level=...)`

```python
except Exception as e:
    _log.log(unhandled_exception_log_level, "Unhandled exception in '%s'", f.__name__, exc_info=True)
    result = Response(success=False, message=str(e), error_code=1)
```

### `unhandled_exception_log_level` on `@app_group`

The log level for unhandled exceptions is configurable per application:

```python
@app_group(
    handle_response=True,
    unhandled_exception_log_level="error",  # default — traceback visible without -v
)

@app_group(
    handle_response=True,
    unhandled_exception_log_level="debug",  # traceback only with --log-level debug/trace
)
```

Default is `"error"` — safe behaviour, the traceback is always visible so nothing is silently
swallowed. The level is stored in `ctx.meta` alongside `pyclifer.output_format` and resolved
inside `returns_response` at call time.

## `OperationResult.data` — domain facts, not rendering hints

`data` carries structured domain facts about the operation — what was returned by the source
(API, filesystem, DB). It is included in JSON/YAML output. Rendering callbacks read it to
build their display.

```python
# Filesystem operation — action is a domain fact
OperationResult.ok(str(path), message="created", data={"action": "created"})

# API CRUD — domain object is the payload
OperationResult.ok("article-123", message="created",
                   data={"id": 123, "title": "Django tips", "action": "created"})
```

`message` carries the human-readable description of what happened. It must always be filled
by the interface — an empty message is a missing fact.

## Future — unified renderer (steps 1–7, 11–12 implemented; steps 8–10, 13 pending)

The current `callback_table_output` / `callback_rich_output` pattern on `Response` requires
the developer to register two separate callbacks, and JSON/YAML serialization is entirely
generic with no per-command control. The replacement is a single `BaseRenderer` class that
is the source of truth for **all** output formats of a command.

### Design principles

- **Declarative first** — class attributes drive the common case; method overrides handle
  the rest. Same philosophy as Django generic views and DRF `ModelSerializer`.
- **Maximum choice for rich** — `rich` output covers two distinct UX patterns (static panels
  and live dynamic displays) that require different hooks. Both are first-class.
- **Framework drives execution** — the renderer never iterates data sources or drives I/O.
  It only declares how to display data the framework hands it.

### `BaseRenderer` — full surface

`BaseRenderer` lives in `core/output/renderer.py` and exposes all available hooks:

```python
class BaseRenderer:
    # --- declarative attributes ---
    fields: list[str] = []                    # JSON + YAML output fields
    columns: list[str | CliTableColumn] = []  # table columns
    rich_title: str = ""                      # default rich panel title

    # --- hooks: data formatting (return a value, framework prints it) ---
    def get_fields(self) -> list[str]: ...
    def get_columns(self) -> list[CliTableColumn]: ...
    def serialize(self, response: Response) -> dict: ...     # JSON + YAML
    def table(self, response: Response) -> CliTable: ...
    def raw(self, response: Response) -> str: ...

    # --- hooks: static rich display (panels, rules, markdown, tables) ---
    def rich(self, response: Response, console: Console) -> None:
        console.print(Panel(response.message))  # sensible default

    # --- hooks: streaming rich display (Live, Progress, spinners) ---
    def rich_setup(self) -> RenderableType:
        return Panel("Working…")               # initial Live layout

    def rich_on_item(self, result: OperationResult, all_so_far: list) -> None:
        pass                                   # mutate self._progress etc. here

    def rich_summary(self, response: Response, console: Console) -> None:
        self.rich(response, console)           # defaults to static display
```

`rich()` and the streaming hooks are **imperative and return nothing** — they call
`console.print()` or mutate Rich objects directly. All other hooks return a value
that the framework prints.

**Implementation note — class-level lists:** `fields` and `columns` are declared as
`ClassVar[list]` on `BaseRenderer`. Subclasses override them as plain class attributes
(not instance attributes), which is safe because they are never mutated at runtime —
only read. The `get_fields()` and `get_columns()` hooks always copy before returning
so callers cannot accidentally mutate the class-level list.

### Three levels of customisation

```python
# Level 1 — pure declarative (most commands)
class ArticleListRenderer(BaseRenderer):
    fields = ["id", "title", "status", "created_at"]
    columns = ["id", "title", "status"]
    rich_title = "Articles"

# Level 2 — override one hook for specific behaviour
class ArticleDetailRenderer(BaseRenderer):
    fields = ["id", "title", "status", "body", "author"]
    columns = ["id", "title", "status", "body", "author"]

    def rich(self, response: Response, console: Console) -> None:
        console.print(Rule(response.message))
        console.print(Markdown(response.data.get("body", "")))

# Level 3 — streaming live display (scaffolding, long-running operations)
class ScaffoldingRenderer(BaseRenderer):
    columns = ["file", "action"]
    fields = ["file", "action", "success"]

    def rich_setup(self) -> RenderableType:
        self._progress = Progress(SpinnerColumn(), TextColumn("{task.description}"))
        self._task = self._progress.add_task("Scaffolding…")
        return Panel(self._progress)

    def rich_on_item(self, result: OperationResult, all_so_far: list) -> None:
        self._progress.update(self._task, description=result.item)

    def rich_summary(self, response: Response, console: Console) -> None:
        icon = "[green]✓[/]" if response.success else "[red]✗[/]"
        console.print(Panel(f"{icon} {response.message}"))
```

### Impact on Response

`callback_table_output` and `callback_rich_output` are removed. `renderer` replaces them
as an instance field — instances carry per-command configuration (columns, fields):

```python
@dataclass
class Response:
    ...
    renderer: BaseRenderer | None = None
```

`from_results()` accepts `renderer` instead of `table`. `from_stream()` is a new
constructor for streaming responses — it stores the generator without materialising it.

`from_stream()` takes only `stream` + `renderer` — no messages. Messages are always
owned by the renderer via `get_success_message()`/`get_failure_message()`. When messages
are dynamic (include a project name, pk, etc.), the renderer is instantiated with that
context:

```python
# batch — interface returns a list, messages on the renderer class
return Response.from_results(
    results,
    renderer=ArticleListRenderer(),
)

# stream — renderer carries dynamic context, no messages on from_stream()
return Response.from_stream(
    interface.init_project(name),
    renderer=ScaffoldingRenderer(name=name),
)
```

`from_stream()` signature:

```python
@classmethod
def from_stream(
    cls,
    stream: Iterator[OperationResult],
    renderer: BaseRenderer,          # required — a stream without a renderer has no contract
) -> "Response": ...
```

`NON_SERIALIZABLE_FIELDS` is updated to exclude `renderer`.

### Impact on OutputFormatMixin

The framework detects the response type and drives the correct path. The renderer
never touches the stream — the framework iterates it and calls renderer hooks.

#### Streaming path

For `rich`, the framework manages the `Live` context and calls the renderer hooks.
For all other formats, the stream is materialised first, then `success`, `error_code`,
and `message` are re-evaluated before dispatch — `from_stream()` leaves them blank
because they can only be computed after the stream is consumed:

```python
def _materialise_stream(self, response: Response) -> None:
    """Consume the generator, then re-evaluate success/message on the Response."""
    items = list(response.data.pop("stream"))
    failed = [r for r in items if not r.success]
    response.success = not bool(failed)
    response.error_code = failed[0].error_code if failed else None
    response.message = (
        response.renderer.get_success_message(items) if not failed
        else response.renderer.get_failure_message(items)
    )
    response.data["results"] = items
```

Full dispatch logic:

```python
if isinstance(result, Response) and result.renderer:
    if "stream" in result.data:
        if output_format == "rich":
            renderable = result.renderer.rich_setup()
            items = []
            with Live(renderable, console=self.console):
                for item in result.data.pop("stream"):
                    items.append(item)
                    result.renderer.rich_on_item(item, items)
            result.data["results"] = items
            result.renderer.rich_summary(result, self.console)
        else:
            self._materialise_stream(result)
            # fall through to batch dispatch below

    if "stream" not in result.data:
        dispatch = {
            "json":  lambda: result.renderer.serialize(result),
            "yaml":  lambda: result.renderer.serialize(result),
            "table": lambda: self.console.print(result.renderer.table(result)),
            "rich":  lambda: result.renderer.rich(result, self.console),
            "raw":   lambda: self.console.print(result.renderer.raw(result)),
        }
        output_format = getattr(self, "output_format", None)
        dispatch.get(output_format, dispatch["raw"])()
```

When `renderer` is `None`, the current generic fallback is preserved for backward
compatibility during the migration period.

### ResponseRenderer Protocol

Defined alongside `BaseRenderer` for type-checking. Advanced users who need a fully
custom renderer can implement the Protocol without inheriting `BaseRenderer`.
Must include the message methods since `_materialise_stream()` calls them directly
on `response.renderer`:

```python
class ResponseRenderer(Protocol):
    def serialize(self, response: Response) -> dict: ...
    def table(self, response: Response) -> Any: ...
    def raw(self, response: Response) -> str: ...
    def rich(self, response: Response, console: Console) -> None: ...
    def rich_setup(self) -> Any: ...
    def rich_on_item(self, result: OperationResult, all_so_far: list) -> None: ...
    def rich_summary(self, response: Response, console: Console) -> None: ...
    def get_success_message(self, results: list) -> str: ...
    def get_failure_message(self, results: list) -> str: ...
```

### Interface/renderer liaison — `respond()`

Currently the command wires interface and renderer manually:

```python
return Response.from_stream(interface.init_project(name), renderer=ScaffoldingRenderer())
```

The target is a command as thin as a Django CBV — it calls the interface and returns,
with no knowledge of renderers, message strings, or stream vs batch detection.

#### `BaseInterface` and `respond()`

`BaseInterface` lives in `core/interfaces/base.py`. It stores `ctx` at construction time
(interfaces need it for API clients, DB connections, etc.) and provides `respond()`:

```python
class BaseInterface:
    renderers: dict[str, type[BaseRenderer]] = {}
    renderer_class: type[BaseRenderer] = BaseRenderer  # fallback

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def respond(self, method_name: str, *args, **kwargs) -> Response:
        method = getattr(self, method_name)   # AttributeError = programming error, not caught
        renderer = self.renderers.get(method_name, self.renderer_class)()
        result = method(*args, **kwargs)

        if inspect.isgenerator(result):
            return Response.from_stream(result, renderer=renderer)
        return Response.from_results(
            result,
            success_message=renderer.get_success_message(result),
            failure_message=renderer.get_failure_message(result),
            renderer=renderer,
        )
```

`respond()` auto-detects list vs generator and picks `from_results()` vs `from_stream()`
accordingly — the command never needs to know.

`method_name` must match a method on the interface exactly. An `AttributeError` is
intentionally not caught — a wrong name is a programming error, not a business failure.

#### Message ownership moves to the renderer

Success and failure messages are declared on the renderer — they belong to the output
layer, not the command or interface:

```python
class BaseRenderer:
    success_message: str = ""
    failure_message: str = ""

    def get_success_message(self, results: list) -> str:
        return self.success_message or f"{len(results)} operation(s) completed."

    def get_failure_message(self, results: list) -> str:
        failed = [r for r in results if not r.success]
        return self.failure_message or f"{len(failed)}/{len(results)} operation(s) failed."
```

#### Full example — interface to command

```python
# renderers.py
class ArticleListRenderer(BaseRenderer):
    fields = ["id", "title", "status", "created_at"]
    columns = ["id", "title", "status"]
    success_message = "Articles fetched."

class ArticleCreateRenderer(BaseRenderer):
    fields = ["id", "title", "action"]
    columns = ["id", "title", "action"]
    success_message = "Article created."
    failure_message = "Article creation failed."

# interfaces.py
class ArticleInterface(BaseInterface):
    renderers = {
        "list":   ArticleListRenderer,
        "create": ArticleCreateRenderer,
    }

    def list(self) -> list[OperationResult]:
        items = self._api.get_articles()
        return [OperationResult.ok(a["id"], data=a) for a in items]

    def create(self, title: str, body: str) -> list[OperationResult]:
        ...

# commands/list.py
@command()
@pass_context
def list_articles(ctx) -> Response:
    return ArticleInterface(ctx).respond("list")

# commands/create.py
@command()
@argument("title")
@pass_context
def create_article(ctx, title: str) -> Response:
    return ArticleInterface(ctx).respond("create", title=title, body="")
```

The command is three lines. The renderer owns the output contract. The interface owns
the business logic. Each layer is independently testable and replaceable.

### Migration path

This is a breaking change to `Response`. Delivery order:

1. ✅ **`core/output/renderer.py`** — `ResponseRenderer` Protocol and `BaseRenderer`
   with all hooks and declarative attributes.

2. ✅ **`core/interfaces/base.py`** — `BaseInterface` with `__init__(ctx)` and `respond()`.
   `core/interfaces/__init__.py` re-exporting `BaseInterface`.

3. ✅ **`core/output/responses.py`** — `renderer` field on `Response`; `renderer` parameter
   in `from_results()`; `from_stream()`; `NON_SERIALIZABLE_FIELDS` updated.

4. ✅ **`core/mixins/output.py`** — `_materialise_stream()` (static); two-path dispatch
   (batch + stream) in `print_result_based_on_format()`.

5. ✅ **`apps/project/`** — `ScaffoldingInterface` extends `BaseInterface`; generators;
   `ScaffoldingRenderer` in `renderers.py`; commands use `Response.from_stream()`.

6. ✅ **`tests/core/test_renderer.py`** — `BaseRenderer`: declarative attributes,
   `get_columns()`, `get_fields()`, `serialize()`, `table()`, `rich()`, streaming hooks.

7. ✅ **`tests/core/test_interfaces.py`** — `BaseInterface`: init, `respond()` list/generator,
   renderer selection, fallback, `AttributeError` on unknown method.

8. ✅ **`tests/core/test_output.py`** — add tests for `Response` additions:
   - `renderer` field present and excluded from `to_json()`
   - `from_stream()` stores generator without consuming it, attaches renderer
   - `_materialise_stream()` re-evaluates `success`, `message`, `error_code` after
     consumption, using `renderer.get_success_message()` / `get_failure_message()`

9. ✅ **`tests/core/mixins/test_output.py`** — dispatch tests for `OutputFormatMixin`:
   - batch path with renderer: json, yaml, table, rich, raw, text
   - streaming path rich: `Live` context, `rich_on_item` called per item, `rich_summary`
   - streaming path non-rich: `_materialise_stream` called, then batch dispatch
   - fallback when `renderer=None`: `BaseRenderer()` used as fallback

10. ✅ **`apps/project/templates/`** — update the generated project templates
    (`app_interfaces.py.jinja2`, `command.py.jinja2`)
    to demonstrate the `BaseInterface` + renderer pattern so scaffolded projects inherit
    the contract out of the box.

11. ✅ **`pyclifer/__init__.py`** — `BaseRenderer`, `ResponseRenderer`, `BaseInterface`
    added to `__all__`.

12. ✅ **Docs** — `api/interfaces.md` created; registered in `mkdocs.yml nav`;
    `api/output.md` updated with `OperationResult`, `BaseRenderer`, `ResponseRenderer`.

13. ✅ **Remove** `callback_table_output` / `callback_rich_output` from `Response` —
    fields, `to_table()`, `to_rich()`, and `table` param of `from_results()` deleted;
    `NON_SERIALIZABLE_FIELDS` updated; all related tests cleaned up.

## Visibility in the framework

Public API exported from `pyclifer.__init__` with `__all__`:

| Symbol              | Where defined                 |
|---------------------|-------------------------------|
| `OperationResult`   | `core/output/responses.py`    |
| `Response`          | `core/output/responses.py`    |
| `BaseRenderer`      | `core/output/renderer.py`     |
| `ResponseRenderer`  | `core/output/renderer.py`     |
| `BaseInterface`     | `core/interfaces/base.py`     |

The scaffolding documentation and generated project templates must demonstrate the full
`BaseInterface` + renderer pattern so developers inherit the contract naturally.