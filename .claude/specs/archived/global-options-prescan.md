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

## ✅ Goal

1. ✅ Introduce `context=True` on `@option` — marks an option as an
   anywhere-passable context-construction input, not propagated to subcommands.
2. ✅ Extend `is_global=True` — values are now pre-scanned so they reach the root
   callback regardless of where they appear in the command chain.
3. ✅ Add `context_factory` on `@app_group` — a callable pyclifer invokes with all
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
| `context=True` | No | Yes (after boundary) | Via token reorder → direct CLI parse | Yes (if set) |
| `is_global=True` | Yes | No | Via token copy → direct CLI parse | No |
| `context=True, is_global=True` | Yes | No | Via token copy → direct CLI parse | Yes (if set) |
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

    # Pass 1 — context=True, is_global=False: extract and reorder before boundary
    #
    # Tokens are MOVED before the subcommand boundary so Click parses them directly.
    # This gives them full CLI-parse priority (above env vars).
    # Placement: consumed_tokens + before + after_remainder ensures that if the same
    # option appears both before and after the boundary, the pre-boundary value wins
    # (Click takes the last occurrence; pre-boundary comes last in the reordered list).
    if parent is None and args:
        context_only_params = [
            p for p in f.params
            if getattr(p, "context", False) and not getattr(p, "is_global", False)
        ]
        if context_only_params:
            boundary = _find_subcommand_boundary(args, f)
            before, after = args[:boundary], args[boundary:]
            if after:
                _, consumed_tokens, after_remainder = _extract_params(after, context_only_params)
                if consumed_tokens:
                    args = consumed_tokens + before + after_remainder

    # Pass 2 — is_global=True (includes context=True, is_global=True): copy before boundary
    #
    # Tokens are COPIED before the subcommand boundary (not consumed — subcommand still
    # owns its copy). Same reordering mechanic as Pass 1, but after_remainder = after
    # (unchanged). Placement consumed_tokens_after + before + after ensures:
    #   - pre-boundary explicit arg wins (comes last, Click takes last occurrence)
    #   - env var does NOT override (direct CLI parse beats env var)
    #   - subcommand still sees its tokens intact
    if parent is None and args:
        global_params = [
            p for p in f.params if getattr(p, "is_global", False)
        ]
        if global_params:
            boundary = _find_subcommand_boundary(args, f)
            before, after = args[:boundary], args[boundary:]
            if after:
                _, consumed_tokens_after, _ = _extract_params(after, global_params)
                if consumed_tokens_after:
                    args = consumed_tokens_after + before + after

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

Static helper. Returns the index of the first token in `args` that is a
registered subcommand name (`f.commands.keys()`), correctly skipping tokens
that are option values. Returns `len(args)` if none found.

Algorithm (linear scan):

```
i = 0
option_value_counts: dict[str, int]  ← built from f.params: decl → nargs (0 for flags)

while i < len(args):
    token = args[i]
    if token == "--":           # argument terminator — no boundary after this
        return len(args)
    if token starts with "-":
        if "=" in token:        # --key=val form — inline value, no next token consumed
            i += 1
        else:
            nargs = option_value_counts.get(token, None)
            if nargs is None or nargs == -1:   # unknown or variadic — treat as flag
                i += 1
            else:
                i += 1 + nargs  # skip option + its value token(s)
    else:
        if token in f.commands:
            return i
        i += 1                  # positional arg that is not a subcommand

return len(args)
```

`option_value_counts` maps every declared form (`--host`, `-h`, etc.) of each
param in `f.params` to `0` (flag or `is_flag=True`) or `param.nargs`
(default 1).

`f.params` is always complete at scan time — it includes user-declared options,
pyclifer-injected options, and click-extra options (all added during group
`__init__`, before `make_context` is ever called). "Unknown option" at root
level therefore means an invalid invocation; Click rejects it regardless, so
the scan result is irrelevant in that case.

`nargs=-1` (variadic) is not supported for context/global options — document
as out of scope.

### `_extract_params(args, params)`

Static helper. Linear scan over `args`; does **not** use Click internals.
Returns `(opts_dict, consumed_tokens, remainder)`:

- `opts_dict`: `{param.name: value}` — first occurrence per param (for
  `default_map` injection in Pass 2).
- `consumed_tokens`: flat list of raw token strings that were matched and
  consumed (option + value tokens), in order encountered (for reordering in
  Pass 1).
- `remainder`: tokens not matched.

Handles `--key=val` (inline) and `--key val` / `-k val` forms.
Stops at `--` (argument terminator); everything from `--` onwards goes to
`remainder` unchanged.
`nargs > 1`: consume `nargs` successive value tokens; inline `=` form not
supported for `nargs > 1` (treat as unmatched).
`nargs=-1` (variadic): param is skipped entirely — not extracted, not consumed,
goes to `remainder`. Variadic options can only be used in canonical position
(before the subcommand boundary).
Empty `args` or empty `params` → `({}, [], args)`.

---

## Priority chain

### `context=True` (non-global) — Pass 1 token reordering

Click resolution order after reordering:

1. Token before subcommand boundary → Click direct parse, placed last → wins over reordered token
2. Token after subcommand boundary → moved before boundary by Pass 1 → Click direct parse, env var does NOT override
3. Environment variable → Click env resolution
4. Config file value → `default_map` (set by `CustomConfigOption`)
5. Declared `default=` → lowest

No `default_map` manipulation in Pass 1. Reordering (`consumed_tokens +
before + after_remainder`) ensures the pre-boundary explicit arg always wins
over a post-boundary one (Click takes the last occurrence; `before` appears
after `consumed_tokens` in the reordered list).

### `is_global=True` — Pass 2 token copy

Same priority chain as Pass 1 — both passes use the same `consumed_tokens +
before + after` reordering. Pass 2 differs only in that `after` is kept intact
(tokens copied, not consumed), so the subcommand still parses its own copy.

1. Token before subcommand boundary → Click direct parse, placed last → wins
2. Token after subcommand boundary → copied before boundary by Pass 2 → Click direct parse, env var does NOT override
3. Environment variable → Click env resolution
4. Config file value → `default_map` (set by `CustomConfigOption`)
5. Declared `default=` → lowest

---

## Known Limitations

### `nargs=-1` (variadic) — canonical position only

```python
# Allowed, but pre-scan does not apply:
@option("--tags", nargs=-1, context=True)
@option("--tags", nargs=-1, is_global=True)
```

```bash
myapp --tags python cli items list   # ✓ Click handles normally — before boundary
myapp items list --tags python cli   # ✗ pre-scan cannot help
```

Root cause: Click groups set `allow_interspersed_args=False`. A `nargs=-1`
option at root level consumes all remaining tokens greedily — including the
subcommand name. Even if pre-scan copied/moved `["--tags", "python", "cli"]`
before the boundary, the reconstructed args would be
`["--tags", "python", "cli", "items", "list"]` and Click would consume
`items` as a tag value, making the subcommand unreachable.

Pre-scan behaviour: `_extract_params` and `_find_subcommand_boundary` skip
params with `nargs=-1` silently (treat as `nargs=0` for boundary detection,
omit from extraction). These options work normally when placed before the
subcommand boundary. Document in the how-to guide.

### `--` argument terminator

```bash
myapp -- items list --host prod
#        ^^^^^^^^^^^^^^^^^^^^^ treated as positional args by POSIX convention
#        --host prod is a string argument, not an option
```

Pre-scan stops at `--` and leaves everything after it untouched. This is
correct: `items` here is not a subcommand invocation, it is a positional
argument value passed to `myapp`. If the user writes `myapp items list -- --host prod`,
the `--` is after the boundary — the subcommand receives it normally.

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
- token that looks like a subcommand but is an option value (`--output items list` where `items` is a subcommand) → not treated as boundary
- `--key=val` form before subcommand → value is inline, subcommand index unchanged
- option with `nargs=2` before subcommand → skips both value tokens, finds subcommand at correct index
- `--` before subcommand name → returns `len(args)` (no boundary)
- group with no registered commands → returns `len(args)`

### `TestExtractParams`
- `--option VALUE` → `opts={"option": "VALUE"}`, `consumed=["--option", "VALUE"]`
- `--option=VALUE` → `opts={"option": "VALUE"}`, `consumed=["--option=VALUE"]`
- `-s VALUE` short form → `opts={"option": "VALUE"}`, `consumed=["-s", "VALUE"]`
- flag (`is_flag=True`) → `opts={"flag": True}`, `consumed=["--flag"]`
- option absent → not in opts dict, not in consumed
- only first occurrence in opts dict (setdefault semantics); all occurrences in consumed
- `nargs=2` option → consumes two value tokens
- `--` in args → everything from `--` onward in remainder, extraction stops
- empty args → `({}, [], [])`
- empty params → `({}, [], args)`

### `TestContextTrueNonGlobal` (Pass 1)
- token after subcommand boundary moved before boundary, received by root callback
- token before boundary left in place; both before and reordered token present → pre-boundary value wins (last in list)
- `required=True` option after boundary does not raise `MissingParameter`
- env var set AND token after boundary → token wins (direct CLI parse beats env var after reordering)
- `context_factory` not set → root callback still receives value via direct parse

### `TestIsGlobalPrescan` (Pass 2)
- token after boundary copied before boundary, received by root callback
- tokens NOT consumed — subcommand still sees its own copy in the original position
- token before boundary left in place; both before and copied token present → pre-boundary value wins (last in list)
- env var set AND token after boundary → token wins (direct CLI parse beats env var after copy)
- no-op when no `is_global=True` params on group
- no-op when no post-boundary tokens found (all global tokens already before boundary)

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
- absent optional `context=True` param → `context_factory` receives `None` for that kwarg
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