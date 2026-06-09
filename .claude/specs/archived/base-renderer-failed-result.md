# BaseRenderer — first-class handling of failed OperationResult

Fixes three gaps reported in issue #2 and adds two framework-level extensibility items
identified during analysis. All gaps share the same root cause: `BaseRenderer` has no
concept of a *failed* `OperationResult`, forcing every renderer to override boilerplate.

---

## ✅ Item 1 — `get_failure_message` must propagate single-result failure message

### Problem

`get_failure_message` returns either the static `failure_message` class attribute or a
count string (`"1/2 operation(s) failed."`). When a command returns exactly one result
that failed, the natural message is `results[0].message`, but there is no way to reach
it without overriding the method.

### Subtle coupling with `BaseInterface.respond()`

`BaseInterface.respond()` calls **both** `get_success_message` and `get_failure_message`
unconditionally before delegating to `Response.from_results()`, which then picks only one:

```python
return Response.from_results(
    result,
    success_message=renderer.get_success_message(result),
    failure_message=renderer.get_failure_message(result),   # always computed
    renderer=renderer,
)
```

This means `get_failure_message` can be called with a list whose single item *succeeded*.
The guard must therefore be `len(results) == 1 and not results[0].success` — not just
`len(results) == 1` — to avoid returning a success message as the failure message (even
though `Response.from_results` would never use it in that case).

### Change in `BaseRenderer.get_failure_message` (`core/output/renderer.py`)

```python
def get_failure_message(self, results: list) -> str:
    if self.failure_message:
        return self.failure_message
    if len(results) == 1 and not results[0].success:
        return results[0].message
    failed = sum(1 for r in results if not r.success)
    return f"{failed}/{len(results)} operation(s) failed."
```

Resolution order:
1. Static `failure_message` class attribute — explicit always wins
2. Single failed result — `results[0].message` (only when `not results[0].success`)
3. Multi-result batch — count string

### TDD sequence (`tests/core/test_renderer.py`, class `TestGetFailureMessage`)

**RED 1** — single failed result returns its own message:
```python
def test_single_failed_result_returns_result_message(self) -> None:
    result = OperationResult.error("px-store", "Storage pool not found.")
    assert BaseRenderer().get_failure_message([result]) == "Storage pool not found."
```
Expected failure: `AssertionError: assert "1/1 operation(s) failed." == "Storage pool not found."`

**GREEN 1** — add the guard before the count string:
```python
if len(results) == 1 and not results[0].success:
    return results[0].message
```

**RED 2** — successful single result must NOT use its message (guard check):
```python
def test_single_successful_result_falls_through_to_count(self) -> None:
    result = OperationResult.ok("px-store")
    assert BaseRenderer().get_failure_message([result]) == "0/1 operation(s) failed."
```
Expected failure: `AssertionError: assert "Storage pool created." == "0/1 operation(s) failed."` if the
guard was `len(results) == 1` without the `not results[0].success` check. With GREEN 1 this test already
passes — run it to confirm the guard is correct, then move on.

**RED 3** — static `failure_message` wins over single-result message:
```python
def test_static_failure_message_takes_precedence(self) -> None:
    result = OperationResult.error("px-store", "Storage pool not found.")
    assert _FullRenderer().get_failure_message([result]) == "Something failed."
```
Expected failure: `AssertionError: assert "Something failed." == "Storage pool not found."` if the
static check were placed after the single-result check. With GREEN 1 (static check first) this passes
immediately — confirms the resolution order is correct.

---

## ✅ Item 2 — `serialize` must preserve `item` and model fields for failed results

### Problem

For a failed result, `result.data` is `None`. The current `serialize` tries to call
`.get(f)` on `None` (via the `isinstance(data, dict)` branch), or produces all-`null`
model fields with no `item` identifier — the consumer cannot tell *which* resource failed.

### Change — introduce `_serialize_result` hook

Rather than inlining the fix directly in `serialize()`, extract a per-row hook. This
preserves `serialize()` as a stable entry point and gives subclasses a clean override
point for row-level customization without replacing batch logic.

```python
def _serialize_result(self, r: OperationResult, fields: list[str]) -> dict:
    """Serialize one OperationResult into a row dict.

    Always includes item, success, and error_code when include_row_meta is True.
    For failed results, model fields are set to None; data extraction is skipped.

    Args:
        r: The operation result to serialize.
        fields: The field names to include (from get_fields()).

    Returns:
        Dict representing one row in the serialized output.
    """
    if r.success:
        data = r.data
        if hasattr(data, "to_dict") and callable(data.to_dict):
            data = data.to_dict()
        row = {
            f: data.get(f) if isinstance(data, dict) and f in data else getattr(r, f, None)
            for f in fields
        }
    else:
        row = {f: None for f in fields}

    row["item"] = r.item
    if self.include_row_meta:
        row["success"] = r.success
        row["error_code"] = r.error_code
    return row
```

The three injected keys (`item`, `success`, `error_code`) are written *after* the field
comprehension, so they always override any field of the same name declared in `fields`.
This is intentional: `item` from `result.item` is always authoritative.

`serialize()` becomes:

```python
def serialize(self, response: Response) -> dict:
    fields = self.get_fields()
    if not fields:
        return response.to_json()

    results = response.data.get("results", [])
    serialized = [self._serialize_result(r, fields) for r in results]
    return {
        "success": response.success,
        "message": response.message,
        "error_code": response.error_code,
        "data": {"results": serialized},
    }
```

### Expected JSON for a failed single-result command

```json
{
  "success": false,
  "message": "Storage pool 'px-store' not found on the array.",
  "error_code": 3,
  "data": {
    "results": [{"item": "px-store", "success": false, "error_code": 3, "total": null, "used": null, "available": null}]
  }
}
```

### TDD sequence

**Step 1 — design `_serialize_result` for failed results**
(`tests/core/test_renderer.py`, class `TestSerializeResult`)

**RED 1** — hook does not exist yet:
```python
def test_failed_result_item_always_in_row(self) -> None:
    result = OperationResult.error("px-store", "not found", error_code=3)
    row = BaseRenderer()._serialize_result(result, ["total", "used"])
    assert row["item"] == "px-store"
```
Expected failure: `AttributeError: 'BaseRenderer' object has no attribute '_serialize_result'`

**GREEN 1** — minimal hook, failed path only:
```python
def _serialize_result(self, r, fields):
    row = {f: None for f in fields}
    row["item"] = r.item
    return row
```

**RED 2** — successful result must extract real data:
```python
def test_successful_result_extracts_fields_from_data(self) -> None:
    result = OperationResult.ok("px-store", data={"total": 1000, "used": 400})
    row = BaseRenderer()._serialize_result(result, ["total", "used"])
    assert row["total"] == 1000
    assert row["used"] == 400
    assert row["item"] == "px-store"
```
Expected failure: `AssertionError: assert None == 1000` (GREEN 1 always sets fields to None)

**GREEN 2** — add success/failure branching (full implementation).

**RED 3** — `item` declared in `fields` must still use `result.item`:
```python
def test_item_in_fields_is_overwritten_by_result_item(self) -> None:
    result = OperationResult.ok("authoritative", data={"item": "from-data", "total": 5})
    row = BaseRenderer()._serialize_result(result, ["item", "total"])
    assert row["item"] == "authoritative"
```
Expected failure: `AssertionError: assert "from-data" == "authoritative"` if the `row["item"] = r.item`
post-write is missing. With GREEN 2 (injection after comprehension) this passes.

**Step 2 — wire `_serialize_result` into `serialize()`**
(`TestSerialize`, existing class — add cases)

**RED** — failed result in a renderer with non-`item` fields produces `item` in serialized output:
```python
class _StorageRenderer(BaseRenderer):
    fields = ["total", "used"]

def test_serialize_failed_result_preserves_item(self) -> None:
    result = OperationResult.error("px-store", "not found", error_code=3)
    response = Response.from_results([result])
    serialized = _StorageRenderer().serialize(response)
    row = serialized["data"]["results"][0]
    assert row["item"] == "px-store"
    assert row["total"] is None
```
Expected failure: `KeyError: 'item'` (current `serialize` only emits declared `fields`)

**GREEN** — replace the inline comprehension in `serialize()` with `self._serialize_result(r, fields)`.

---

## ✅ Item 3 — `serialize` must carry per-row `success` and `error_code` in mixed batches

### Problem

When a batch command returns both successful and failed results, the consumer cannot
distinguish *why* a specific item failed — only that its model fields are `null`.

### Solution

Covered by `_serialize_result` and `include_row_meta` from item 2. No additional code
change needed.

### New class attribute on `BaseRenderer`

```python
include_row_meta: ClassVar[bool] = True
```

Default `True` — per-row `success` and `error_code` are emitted by default, enabling
the expected output without opt-in:

```json
{
  "success": false,
  "message": "1/2 operation(s) failed.",
  "error_code": 3,
  "data": {
    "results": [
      {"item": "pool_01", "success": true,  "error_code": 0,  "total": 1000, "used": 400, "available": 600},
      {"item": "pool_02", "success": false, "error_code": 3,  "total": null,  "used": null,  "available": null}
    ]
  }
}
```

Renderers for commands that never fail (e.g., a simple list) can set
`include_row_meta = False` to suppress the noise.

### TDD sequence (`tests/core/test_renderer.py`, class `TestSerializeResult`)

**RED 1** — row contains `success` and `error_code` by default:
```python
def test_row_contains_success_and_error_code_by_default(self) -> None:
    result = OperationResult.error("px-store", "not found", error_code=3)
    row = BaseRenderer()._serialize_result(result, ["total"])
    assert row["success"] is False
    assert row["error_code"] == 3
```
Expected failure: `KeyError: 'success'` (not injected yet in `_serialize_result`)

**GREEN 1** — add `include_row_meta` class attr and injection in `_serialize_result`:
```python
include_row_meta: ClassVar[bool] = True
# in _serialize_result, after row["item"] = r.item:
if self.include_row_meta:
    row["success"] = r.success
    row["error_code"] = r.error_code
```

**RED 2** — `include_row_meta = False` suppresses meta keys:
```python
def test_include_row_meta_false_suppresses_meta(self) -> None:
    class _NoMetaRenderer(BaseRenderer):
        include_row_meta = False

    result = OperationResult.error("px-store", "not found")
    row = _NoMetaRenderer()._serialize_result(result, ["total"])
    assert "success" not in row
    assert "error_code" not in row
```
Expected failure: `AssertionError: assert "success" not in {"item": ..., "success": False, ...}` if the
`if self.include_row_meta` guard is missing. With GREEN 1 this passes immediately — confirms opt-out works.

---

## ✅ Item 4 — `table()` visual consistency: `_row_style` hook for failed rows

### Problem (not in the original issue — identified during spec analysis)

`table()` → `_result_to_row()` already handles failed results correctly: `item` is read
via `getattr`, model fields return `None`. However, there is no visual distinction between
a failed row and a successful row with empty data. JSON/YAML output now carries
`success`/`error_code` per row; table output should signal failures visually to maintain
cross-format consistency.

### Change — `_row_style` hook

Add a method that `table()` uses to style each row, with a default that marks failed rows
in red:

```python
def _row_style(self, result: OperationResult) -> str | None:
    """Return a Rich style string for a row, or None for the default style.

    Override to customize row styles. The default marks failed rows red.

    Args:
        result: The OperationResult for the row.

    Returns:
        A Rich style string or None.
    """
    return "red" if not result.success else None
```

`table()` passes per-row styles to `CliTable`. This requires `CliTable` to accept an
optional `row_styles` list (parallel to `rows`).

### Change in `CliTable` (`core/output/tables.py`)

Add `row_styles: list[str | None] | None = None` to `CliTable`. When present, each entry
is applied as a Rich row style to the corresponding row via `table.add_row(..., style=...)`.

### Change in `BaseRenderer.table()` (`core/output/renderer.py`)

```python
def table(self, response: Response) -> CliTable:
    ...
    results = response.data.get("results", [])
    rows = [self._result_to_row(r, cols) for r in results]
    row_styles = [self._row_style(r) for r in results]
    ...
    return CliTable(
        fields=fields_dict,
        rows=rows,
        row_styles=row_styles,
        table_style={"title": title} if title else None,
        datetime_format=self.datetime_format,
        date_format=self.date_format,
    )
```

### TDD sequence

**Step 1 — `CliTable.row_styles`** (`tests/core/output/test_tables.py`, class `TestCliTable`)

**RED 1** — `CliTable` does not accept `row_styles` yet:
```python
def test_row_style_applied_to_row(self) -> None:
    table = CliTable(
        fields={"name": CliTableColumn(header="Name")},
        rows=[{"name": "ok"}, {"name": "err"}],
        row_styles=[None, "red"],
    )
    assert table.table.rows[1].style == "red"
    assert table.table.rows[0].style is None
```
Expected failure: `TypeError: __init__() got an unexpected keyword argument 'row_styles'`

**GREEN 1** — add `row_styles` param; pass `style` to `table.add_row()` in `update_rows`:
```python
def __init__(self, ..., row_styles: list[str | None] | None = None):
    ...
    self.update_rows(fields, rows, row_styles)

def update_rows(self, fields, rows, row_styles=None):
    if rows is not None:
        if isinstance(rows, dict):
            rows = [rows]
        for i, row in enumerate(rows):
            columns = self._generate_columns(fields, row)
            style = row_styles[i] if row_styles else None
            self.table.add_row(*columns, style=style)
```

**RED 2** — length mismatch raises `ValueError`:
```python
def test_row_styles_length_mismatch_raises(self) -> None:
    with pytest.raises(ValueError, match="row_styles length"):
        CliTable(
            fields={"name": CliTableColumn(header="Name")},
            rows=[{"name": "a"}, {"name": "b"}],
            row_styles=["red"],
        )
```
Expected failure: `IndexError` (no validation yet). Add the guard at the start of `update_rows`.

**Step 2 — `_row_style` hook** (`tests/core/test_renderer.py`, class `TestRowStyle`)

**RED 1** — hook does not exist:
```python
def test_row_style_returns_red_for_failed_result(self) -> None:
    result = OperationResult.error("px-store", "fail")
    assert BaseRenderer()._row_style(result) == "red"
```
Expected failure: `AttributeError: 'BaseRenderer' object has no attribute '_row_style'`

**GREEN 1** — add minimal `_row_style`:
```python
def _row_style(self, result: OperationResult) -> str | None:
    return "red" if not result.success else None
```

**RED 2** — successful result returns `None`:
```python
def test_row_style_returns_none_for_successful_result(self) -> None:
    result = OperationResult.ok("px-store")
    assert BaseRenderer()._row_style(result) is None
```
Passes immediately with GREEN 1.

**Step 3 — `table()` passes `row_styles`** (`tests/core/test_renderer.py`, class `TestTable`)

**RED** — mixed response, failed row must be styled red in the `CliTable`:
```python
def test_table_failed_row_styled_red(self) -> None:
    ok = OperationResult.ok("a")
    err = OperationResult.error("b", "fail")
    response = Response.from_results([ok, err], renderer=_FullRenderer())
    cli_table = _FullRenderer().table(response)
    assert cli_table.table.rows[0].style is None
    assert cli_table.table.rows[1].style == "red"
```
Expected failure: `AssertionError` — `table()` doesn't compute `row_styles` yet.

**GREEN** — update `table()` to build and pass `row_styles`:
```python
row_styles = [self._row_style(r) for r in results]
return CliTable(..., row_styles=row_styles)
```

---

## Documentation

### `docs/output-formatting.md`

The most affected doc — it documents `serialize()` and `failure_message` in detail.

- **`serialize()` section** (around line 288): update description to explain that every row now
  always carries `item`, and `success`/`error_code` when `include_row_meta=True`. Show the new
  JSON output for a failed single-result command and a mixed batch.
- **`failure_message` attribute** (around line 285): update the explanation to reflect the new
  resolution order: static → single failed result message → count string.
- **New section `include_row_meta`**: document the class attribute, when to set it to `False`,
  and the resulting JSON diff.
- **New section `_row_style`**: document the hook, its default (red for failures), and how to
  override for custom row styling.
- **New section `_serialize_result`**: document the per-row hook as the override point for
  custom row serialization (replaces overriding `serialize()`).

### `docs/api/output.md`

The API reference for `BaseRenderer` — driven by mkdocstrings, so doc content lives in
the source docstrings. Verify the rendered page picks up:
- New class attributes: `include_row_meta`
- New methods: `_serialize_result`, `_row_style`
- Updated `get_failure_message` docstring (new resolution order in the body)

No prose changes needed in the `.md` file itself unless the auto-rendered output is
missing or wrong.

### `docs/how-to/error-handling.md`

Add a note under the "returning failures from the interface layer" section explaining
that `BaseRenderer` now handles the single-failure case automatically — renderers no
longer need to override `get_failure_message` just to propagate the per-result message.

### `docs/how-to/response-patterns.md`

No structural change required. The `failure_message = "..."` example in `TaskAddRenderer`
remains valid — static values still take precedence. A one-line note is sufficient to
indicate that omitting `failure_message` is now safe for single-result commands.

---

## Summary of changes

| File | Change |
|------|--------|
| `src/pyclifer/core/output/renderer.py` | `include_row_meta` class attr; `get_failure_message` guard; `_serialize_result` hook; `serialize` delegates to hook; `_row_style` hook; `table()` passes `row_styles` |
| `src/pyclifer/core/output/tables.py` | `CliTable.row_styles` field; `add_row` passes style |
| `tests/core/test_renderer.py` | `TestGetFailureMessage`, `TestSerializeResult` (new); updated `TestSerialize`, `TestTable`; `TestRowStyle` (new) |
| `tests/core/output/test_tables.py` | `row_styles` test cases |

## Implementation order

1. `CliTable.row_styles` (tables.py) — leaf, no dependencies
2. `include_row_meta` + `_serialize_result` + `serialize` (renderer.py) — Items 2 & 3
3. `get_failure_message` guard fix (renderer.py) — Item 1, independent
4. `_row_style` + `table()` update (renderer.py) — Item 4, depends on CliTable change