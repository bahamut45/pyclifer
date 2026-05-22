# Output formats — redesign

## Problem

The `raw` format has inconsistent semantics between the two dispatch paths:

- **Legacy path** (`_print_raw`): serializes the response to a JSON dict, then optionally
  extracts a key via `--output-filter`. Machine-readable, filterable.
- **Renderer path** (`renderer.raw()`): returns `response.message` as plain text.
  Not filterable, not machine-readable.

Additionally, `--output-filter` is only wired to the `raw` format in the legacy path. Users
who want to extract a specific field from JSON or YAML output cannot do so.

## Design decision

### Rename `raw` → `text`, introduce `raw` with its original semantics

| Format  | Output                                           | Filterable |
|---------|--------------------------------------------------|------------|
| `json`  | Syntax-highlighted JSON (current)                | yes        |
| `yaml`  | Syntax-highlighted YAML (current)                | yes        |
| `table` | Rich table (current)                             | no         |
| `rich`  | Live / panels / markdown (current)               | no         |
| `raw`   | Flat JSON, no highlighting — machine-readable    | yes        |
| `text`  | Plain text: `response.message` only (new)        | no         |

- **`raw`** is the machine-readable format. No syntax highlighting. Single-line or compact.
  Supports `--output-filter` to extract a dotted-path value. This matches the original
  legacy behaviour and CLI conventions (`--output-format raw | jq .`).
- **`text`** is the new plain-text format. Returns `response.message` as-is. No filtering.
  Useful for scripting where only the human summary is needed.
- The **default format** (when `--output-format` is not set) remains `table` — unchanged
  from the current behaviour. `text` and `raw` are explicitly opt-in.

### `--output-filter` semantics differ by format

`--output-filter` accepts a single key. Resolution order:
1. Look inside `data` sub-dict for the key.
2. Fall back to top-level response fields (`success`, `message`, `error_code`).

Dotted paths beyond one level are a future extension — for now a single key is sufficient.

**`raw --output-filter path`** — prints the extracted value as-is, without re-serialization.
Suitable for shell scripts where `running` is preferable to `"running"`.

**`json --output-filter path`** — extracts the value and re-serializes it as valid JSON.
Output is always valid JSON: `"running"`, `42`, or `{"id": 1}`.

**`yaml --output-filter path`** — extracts the value and re-serializes it as valid YAML.
Output is always valid YAML.

### Filter path traversal

`--output-filter` accepts a **dotted key path**. Each segment is resolved in order;
numeric segments are treated as list indices.

Resolution order:
1. Traverse starting from `data["data"]` (the structured payload).
2. If not found, traverse from the top-level response dict.

```bash
# Single key
myapp articles -f message                  # top-level message field
myapp articles -f results                  # data["data"]["results"] list

# Dotted path into a nested dict
myapp article get --id 1 -f article.title  # data["data"]["article"]["title"]

# Dotted path with list index
myapp articles -f results.0.id             # first result's id
myapp articles -f results.1.title          # second result's title
```

## Impact on `BaseRenderer`

### Rename `raw()` → `text()`

```python
class BaseRenderer:
    # noinspection PyMethodMayBeStatic
    def text(self, response: Response) -> str:
        """Return the response message as plain text."""
        return response.message

    def raw(self, response: Response) -> dict:
        """Return a serialized dict for machine-readable output.

        Defaults to serialize() output. Override for a custom raw representation.
        """
        return self.serialize(response)
```

`raw()` now returns a `dict` (the serialized response), not a `str`. The framework
applies the filter and prints it. `text()` returns a `str` — no filter, no processing.

### `ResponseRenderer` Protocol updated accordingly

```python
class ResponseRenderer(Protocol):
    def text(self, response: Response) -> str: ...
    def raw(self, response: Response) -> dict: ...
    # serialize, table, rich, rich_setup, rich_on_item, rich_summary,
    # get_success_message, get_failure_message — unchanged
```

## Impact on `OutputFormatMixin`

### `print_result_based_on_format` — renderer dispatch

```python
renderer_dispatch: dict[str, Any] = {
    "json":  lambda: self._print_json(renderer.serialize(result), {}),
    "yaml":  lambda: self._print_yaml(renderer.serialize(result), {}),
    "table": lambda: self.console.print(renderer.table(result)),
    "rich":  lambda: renderer.rich(result, self.console),
    "raw":   lambda: self._print_raw_dict(renderer.raw(result), filter_key),
    "text":  lambda: self.console.print(renderer.text(result)),
}
```

`filter_key` is read from `ctx.meta` (same mechanism as current `output_filter_option`).
`_print_raw_dict(data, key)` applies the filter and prints the result.

### `_print_raw_dict(data, filter_key)` — new helper

```python
@staticmethod
def _print_raw_dict(data: dict, filter_key: str | None) -> str | Any:
    """Extract filter_key from a serialized dict, or return the full dict."""
    if not filter_key:
        return data
    # check data sub-dict first, then top-level
    sub = data.get("data")
    if isinstance(sub, dict) and filter_key in sub:
        return sub[filter_key]
    return data.get(filter_key)
```

### `--output-filter` applies to `json` and `yaml` too

Both formats call `renderer.serialize()` first, then apply the filter before printing.
When a filter is active, the output is the raw extracted value (no highlighting).

### Default format fallback

The fallback when `output_format` is `None` or unrecognised remains `table`.
The `text` entry is added alongside `raw` but is not the default:

```python
renderer_dispatch.get(output_format or "table", renderer_dispatch["table"])()
```

## Impact on `output_filter_option`

No structural change — the option still stores `filter_value` in `ctx.meta`. The dispatch
layer reads it and passes it to `_print_raw_dict`. The option help text is updated to
reflect that it now works with `json`, `yaml`, and `raw`.

## Migration path

1. **`core/output/renderer.py`** — rename `raw()` → `text()`, add new `raw() -> dict`.
   Update `ResponseRenderer` Protocol.

2. **`core/mixins/output.py`** — add `_print_raw_dict()`, update `renderer_dispatch` with
   new `raw` and `text` entries, read `filter_key` from `ctx.meta` in the renderer path,
   apply filter to `json` and `yaml` when filter is active.

3. **`apps/project/renderers.py`** — rename `raw()` override if present (none currently).

4. **Tests** — update `tests/core/test_renderer.py` for renamed `text()` and new `raw()`;
   add dispatch tests for filter on `json`/`yaml`/`raw`, default-format fallback.

5. **Docs** — update `api/output.md` and `api/interfaces.md` for the new format table and
   `text()`/`raw()` signatures.

## What does NOT change

- `serialize()` — unchanged, used by `json`, `yaml`, and the new `raw`.
- `table()`, `rich()`, streaming hooks — unchanged.
- `from_stream()` / `from_results()` / `_materialise_stream()` — unchanged.
- `BaseInterface.respond()` — unchanged.
- Legacy dispatch path (when `renderer=None`) — preserved for backward compatibility.