# Output

## OperationResult

The atomic result type returned by interface methods. Carries success state, an item
identifier, a message, optional data payload, and an error code.

::: pyclif.OperationResult

---

## Response

The standard return type for all pyclif commands. Carries success state, a human-readable
message, optional structured data, and an error code.

::: pyclif.Response

---

## PaginatedResponse

Extends `Response` with pagination metadata (`page`, `limit`, `total`). Includes a
`pagination` block in JSON and YAML output automatically.

::: pyclif.PaginatedResponse

---

## CliTable

Wrapper around Rich `Table` for consistent tabular output.

::: pyclif.CliTable

---

## CliTableColumn

Column definition for `CliTable`.

::: pyclif.CliTableColumn

---

## ExceptionTable

Renders an exception as a Rich table. Used internally by the response formatter but
available for direct use in error handlers.

::: pyclif.ExceptionTable

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

Declarative base class for all pyclif output renderers. Subclass and set class
attributes (`fields`, `columns`, `rich_title`, `success_message`, `failure_message`)
to control every output format without overriding methods.

Key hooks:

- `text(response)` — returns `response.message` as plain text (used by `--output-format text`)
- `raw(response)` — returns a serialized dict for machine-readable output (used by `--output-format raw`)
- `serialize(response)` — returns a JSON-serializable dict (used by `json`, `yaml`, and `raw`)

::: pyclif.BaseRenderer

---

## ResponseRenderer

Protocol that all renderer implementations must satisfy. Implement this Protocol
directly only when inheriting `BaseRenderer` is not appropriate.

::: pyclif.ResponseRenderer