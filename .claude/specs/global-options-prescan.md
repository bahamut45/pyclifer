# Spec: Anywhere-passable options and declarative context construction

Options marked `context=True` or `is_global=True` on the root group must be
accepted at **any position** in the command chain. Options marked `context=True`
feed `ctx.obj` construction, which can be fully delegated to pyclifer via a new
`context_factory` parameter on `@app_group`.

Closes [#1](https://github.com/bahamut45/pyclifer/issues/1).

---

## Context

### Problem 1 — root-only options locked to root position

Options declared on `@app_group` that feed `ctx.obj` (e.g. `--host`,
`--username`, `--password`) are only parseable *before* the first subcommand
name. Placing them after causes a Click error:

```bash
myapp items list --host prod    # ✗  "No such option: --host" at items list level
myapp --host prod items list    # ✓  works today
```

These options are not propagated to subcommands (not `is_global=True`) so Click
rejects them at any sublevel.

### Problem 2 — `is_global=True` values don't reach the root callback

`GlobalOptionsMixin` already injects `is_global=True` options into every
subcommand's param list. But Click runs the root callback *before* parsing
subcommands, so values placed after a subcommand name are not available when
`ctx.obj` is built:

```bash
myapp items list --resource acme   # ✗  app() already ran, resource=None
myapp --resource acme items list   # ✓  works today
```

### Problem 3 — ctx.obj construction is always manual

Every root callback must manually build `ctx.obj`. There is no declarative
alternative.

---

## Goal

1. Introduce `context=True` on `@option` — marks an option as an
   anywhere-passable context-construction input, not propagated to subcommands.
2. Extend `is_global=True` — values are now pre-scanned so they reach the root
   callback regardless of where they appear in the command chain.
3. Add `context_factory` on `@app_group` — a callable pyclifer invokes with all
   `context=True` option values to build `ctx.obj` automatically.

---

## New API

### `@option(..., context=True)`

```python
@option("--host",     required=True, context=True)
@option("--username", required=True, context=True)
@option("--resource", required=True, context=True, is_global=True)
```

- `context=True` alone: option is root-only (not injected into subcommands),
  tokens placed after the subcommand boundary are extracted and consumed before
  Click's normal parse.
- `context=True, is_global=True`: option is also injected into subcommands
  (visible in their `--help`); tokens are not consumed because the subcommand
  legitimately owns them.

### `@app_group(context_factory=...)`

```python
@app_group(context_factory=AppContext)
@option("--host",     required=True, context=True)
@option("--resource", required=True, context=True, is_global=True)
def app():
    pass   # ctx.obj built automatically by pyclifer
```

`context_factory` is called with all `context=True` option values as kwargs
(matched by param name). `ctx.obj` is set in the post-call of
`_patch_make_context`, before `invoke` runs the root callback.

Without `context_factory` the user can still mark options `context=True` for
the anywhere-passable behaviour and build `ctx.obj` manually in the callback.

---

## Behaviour matrix

| Combo | Propagated to subcommands | Tokens consumed | Reaches root callback | Fed to `context_factory` |
|---|---|---|---|---|
| `context=True` | No | Yes (after boundary) | Via `default_map` | Yes (if set) |
| `is_global=True` | Yes | No | Via `default_map` | No |
| `context=True, is_global=True` | Yes | No | Via `default_map` | Yes (if set) |
| *(default)* | No | No | Direct Click parse only | No |

---

## Design

### New attributes

**`PycliferOption`** (`core/classes.py`):
```python
class PycliferOption(click_extra.Option):
    def __init__(self, *param_decls, is_global: bool = False, context: bool = False, **attrs):
        self.is_global = is_global
        self.context = context
        super().__init__(*param_decls, **attrs)
```

**`GroupConfig`** (`core/classes.py`):
```python
@dataclass
class GroupConfig:
    ...
    context_factory: Callable[..., Any] | None = None
```

**`@option` and `@app_group` decorators** (`core/decorators.py`): surface
`context` and `context_factory` kwargs and forward them.

---

### `_patch_make_context` — two pre-call passes + one post-call

```python
def custom_make_context(info_name, args, parent=None, **extra):
    # --- pre-call ---

    # Pass 1 — context=True, is_global=False: extract and consume after boundary
    if parent is None and args:
        context_only_params = [
            p for p in f.params
            if getattr(p, "context", False) and not getattr(p, "is_global", False)
        ]
        if context_only_params:
            boundary = _find_subcommand_boundary(args, f)
            before, after = args[:boundary], args[boundary:]
            if after:
                found, after_remainder = _extract_params(after, context_only_params)
                if found:
                    default_map = extra.get("default_map") or {}
                    for name, value in found.items():
                        default_map.setdefault(name, value)
                    extra["default_map"] = default_map
                    args = before + after_remainder

    # Pass 2 — is_global=True (includes context=True, is_global=True): extract, no consume
    if parent is None and args:
        global_params = [
            p for p in f.params if getattr(p, "is_global", False)
        ]
        if global_params:
            found, _ = _extract_params(args, global_params)
            if found:
                default_map = extra.get("default_map") or {}
                for name, value in found.items():
                    default_map.setdefault(name, value)
                extra["default_map"] = default_map

    # Concern 1 — dynamic auto_envvar_prefix (unchanged)
    ...

    # Concern 2 — early verbosity pre-call (unchanged)
    ...

    # --- call ---
    ctx = original_make_context(info_name, args, parent=parent, **extra)

    # --- post-call ---

    # Concern 3 — framework meta injection (unchanged)
    ...

    # Concern 4 — context_factory
    if parent is None and self.config.context_factory is not None:
        context_values = {
            p.name: ctx.params[p.name]
            for p in f.params
            if getattr(p, "context", False) and p.name in ctx.params
        }
        ctx.obj = self.config.context_factory(**context_values)

    return ctx
```

### `_find_subcommand_boundary(args, f)`

Static helper. Returns the index of the first token in `args` that matches a
registered subcommand name (`f.commands.keys()`). Returns `len(args)` if none
found (no subcommand in args, so no boundary — scan is a no-op).

### `_extract_params(args, params)`

Static helper. Builds a temporary `_OptionParser` (Click internal, wrapped in
`try/except` for forward-compatibility) with `allow_interspersed_args=True`
over the given params. Returns `(opts_dict, remainder_list)`. On any exception,
returns `({}, args)` so the CLI never breaks due to pre-scan failure.

---

## Priority chain

For `context=True` (non-global) options:

1. Explicit token before subcommand boundary → Click direct parse (highest)
2. Pre-scanned token after subcommand boundary → `default_map`
3. Environment variable → Click env resolution
4. Config file value → `default_map` already set by `CustomConfigOption`
5. Declared `default=` → lowest

`default_map.setdefault` ensures a pre-scanned value never overrides a value
already in `default_map` (e.g. from config file loaded earlier).

---

## Files

| File | Change |
|------|--------|
| `src/pyclifer/core/classes.py` | `PycliferOption`: add `context` attr; `GroupConfig`: add `context_factory` |
| `src/pyclifer/core/decorators.py` | `@option`: surface `context` kwarg; `@app_group`: surface `context_factory`; `GroupDecorator`: add Pass 1, Pass 2, post-call concern 4, `_find_subcommand_boundary`, `_extract_params` |
| `src/pyclifer/apps/project/templates/` | Update `cli.py` and `core/context.py` to use `context=True` / `context_factory` pattern |
| `docs/api/classes.md` | Document `context` on `PycliferOption`, `context_factory` on `GroupConfig` |
| `docs/api/decorators.md` | Document `context` kwarg on `@option`, `context_factory` on `@app_group` |
| `docs/` | New how-to guide: *Context construction and anywhere-passable options* |
| `tests/core/test_decorators.py` | New test classes (see below) |
| `tests/core/test_classes.py` | `context` and `context_factory` attribute tests |

---

## Test coverage requirements

### `TestFindSubcommandBoundary`
- no subcommand in args → returns `len(args)`
- subcommand name at index 0 → returns 0
- subcommand name after options → returns correct index
- token that looks like a subcommand but is an option value → not treated as boundary
- group with no registered commands → returns `len(args)`

### `TestExtractParams`
- `--option VALUE` → `{"option": "VALUE"}`
- `--option=VALUE` → `{"option": "VALUE"}`
- `-s VALUE` short form → `{"option": "VALUE"}`
- flag (`is_flag=True`) → `{"flag": True}`
- option absent → not in result dict
- only first occurrence recorded (setdefault semantics)
- `_OptionParser` exception → returns `({}, args)` unchanged
- empty args → `({}, [])`
- empty params → `({}, args)`

### `TestContextTrueNonGlobal` (Pass 1)
- token after subcommand boundary extracted, consumed from args
- token before boundary left for Click direct parse (not consumed)
- `required=True` option after boundary does not raise `MissingParameter`
- same option at root AND after boundary → root-level value wins
- `context_factory` not set → root callback still receives value

### `TestIsGlobalPrescan` (Pass 2)
- token at any position extracted, injected into `default_map`
- tokens NOT consumed (subcommand still sees them)
- root callback receives value from `default_map`
- env var overrides pre-scanned `default_map` value (env > default_map)
- no-op when no `is_global=True` params on group

### `TestContextTrueIsGlobalCombo`
- propagated to subcommand by `GlobalOptionsMixin`
- pre-scanned (not consumed) for root `default_map`
- fed to `context_factory` when set

### `TestContextFactory`
- `ctx.obj` set before root callback invoked
- `ctx.obj` built from `context=True` param values
- `context_factory` not called when `context_factory=None`
- `ctx.obj` set at root level only (`parent is None`)
- all `context=True` values (non-global + global) passed to `context_factory`
- exception in `context_factory` propagates normally

### Scaffolding
- `pyclifer project init` generated `cli.py` uses `context_factory` pattern
- generated `core/context.py` reflects new pattern

### Regression
- all existing tests pass unchanged

---

## Implementation order

1. Feature branch: `git checkout -b feat/anywhere-passable-options`
2. `PycliferOption` — add `context` attr; `GroupConfig` — add `context_factory`
3. Surface `context` in `@option` and `context_factory` in `@app_group`
4. Write failing integration tests (Pass 1, Pass 2, `context_factory`)
5. Write `_find_subcommand_boundary` + unit tests (pass)
6. Write `_extract_params` + unit tests (pass)
7. Add Pass 1 + Pass 2 blocks in `custom_make_context` (Pass 1/2 integration tests now pass)
8. Add post-call concern 4 (`context_factory`) — `context_factory` tests now pass
9. Update scaffolding templates
10. Update docs (`classes.md`, `decorators.md`, new how-to guide)
11. `ruff check` + `ruff format`
12. Full test suite green
13. One commit per logical group (classes, decorators core, scaffolding, docs)

---

## Out of scope

- Options without `context=True` or `is_global=True` — behaviour unchanged
- `store_in_meta=True` + `expose_value=False` options (e.g. `--verbosity`,
  `--output-format`) — already work at any level via their eager callbacks
- Multi-root-group CLIs — `parent is None` guard limits all changes to root
- `context_factory` receiving non-`context=True` option values