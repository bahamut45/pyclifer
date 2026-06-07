# Output

## ExitCode

Named exit codes used as both the classification value in structured output (JSON, YAML) and
the actual OS exit code (`$?`). Values are POSIX-safe (0-127).

::: pyclifer.ExitCode

### Built-in codes

| Code | Name               | Rationale                                              |
|------|--------------------|--------------------------------------------------------|
| 0    | `SUCCESS`          | POSIX standard — implicit default on success           |
| 1    | `ERROR`            | POSIX standard — unhandled exceptions                  |
| 2    | `ALREADY_EXISTS`   | Resource already exists (scaffolding, idempotent ops)  |
| 3    | `NOT_FOUND`        | Resource not found                                     |
| 4    | `PERMISSION_DENIED`| Insufficient permissions                               |
| 5    | `INVALID_INPUT`    | Bad user input                                         |

### Safe value ranges for project codes

| Range   | Reserved for                              |
|---------|-------------------------------------------|
| 0-5     | pyclifer framework codes                    |
| 6-125   | Application-specific codes — use this     |
| 126+    | Shell-reserved (not executable, not found, signals) |

### Extending ExitCode

Define a subclass in your project and register it with `@app_group`:

```python
# my_project/core/constants.py
from pyclifer import ExitCode as _Base

class ExitCode(_Base):
    QUOTA_EXCEEDED = 10
    RATE_LIMITED = 11
```

```python
# my_project/cli.py
from pyclifer import app_group
from my_project.core.constants import ExitCode

@app_group(exit_codes_class=ExitCode)
def cli(): ...
```

The framework validates that all project-specific values fall in 6-125 at decoration time
and stores the class in `ctx.meta["pyclifer.exit_codes_class"]`. When a command returns a
`Response(success=False, error_code=ExitCode.QUOTA_EXCEEDED)`, pyclifer calls `ctx.exit(10)`
so that `$?` reflects the failure in shell scripts.

For base codes, `from pyclifer import ExitCode` is always sufficient. Only import from
`constants.py` in files that reference project-specific codes.

---

## OperationResult

The atomic result type returned by interface methods. Carries success state, an item
identifier, a message, optional data payload, and an error code.

::: pyclifer.OperationResult

---

## Response

The standard return type for all pyclifer commands. Carries success state, a human-readable
message, optional structured data, and an error code.

::: pyclifer.Response

---

## PaginatedResponse

Extends `Response` with pagination metadata (`page`, `limit`, `total`). Includes a
`pagination` block in JSON and YAML output automatically.

::: pyclifer.PaginatedResponse

---

## CliTable

Wrapper around Rich `Table` for consistent tabular output.

::: pyclifer.CliTable

---

## CliTableColumn

Column definition for `CliTable`.

::: pyclifer.CliTableColumn

---

## ExceptionTable

Renders an exception as a Rich table. Used internally by the response formatter but
available for direct use in error handlers.

::: pyclifer.ExceptionTable

---

## Output formats

| Format  | Output                                              | Filterable |
|---------|-----------------------------------------------------|------------|
| `table` | Rich table — **default format**                     | no         |
| `rich`  | Live / panels / markdown                            | no         |
| `text`  | Plain text: `response.message` only                 | no         |
| `json`  | Syntax-highlighted JSON — always valid JSON         | yes        |
| `yaml`  | Syntax-highlighted YAML — always valid YAML         | yes        |
| `raw`   | Compact JSON, no highlighting — machine-readable    | yes        |

`table` is the default format.

`--output-filter` accepts a **dotted key path** (`results.0.id`, `article.title`, `message`).
Numeric segments are treated as list indices. Resolution: `data["data"]` first, then top-level.

- **`raw`** — prints the extracted value as-is. `running`, not `"running"`. Best for scripting.
- **`json`** — re-serializes the extracted value as valid JSON. Always outputs valid JSON.
- **`yaml`** — re-serializes the extracted value as valid YAML. Always outputs valid YAML.

---

## BaseRenderer

Declarative base class for all pyclifer output renderers. Subclass and set class
attributes (`fields`, `columns`, `rich_title`, `success_message`, `failure_message`)
to control every output format without overriding methods.

Key hooks:

- `text(response)` — returns `response.message` as plain text (used by `--output-format text`)
- `raw(response)` — returns a serialized dict for machine-readable output (used by `--output-format raw`)
- `serialize(response)` — returns a JSON-serializable dict (used by `json`, `yaml`, and `raw`)

::: pyclifer.BaseRenderer

---

## ResponseRenderer

Protocol that all renderer implementations must satisfy. Implement this Protocol
directly only when inheriting `BaseRenderer` is not appropriate.

::: pyclifer.ResponseRenderer