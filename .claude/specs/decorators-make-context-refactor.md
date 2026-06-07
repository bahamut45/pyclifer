# Spec: `GroupDecorator` — composite `make_context` patch

Refactor the three sequential `make_context` monkey-patches in `GroupDecorator`
into a single composite wrapper. No behaviour change.

---

## Context

`GroupDecorator.__call__` currently patches `f.make_context` three times in
sequence via three separate methods:

1. `_inject_dynamic_envvar` — pre-call: derives `auto_envvar_prefix` from CLI name
2. `_inject_early_verbosity` — pre-call + post-call: extracts verbosity level before
   Click parses args, applies it after the context is built
3. `_configure_handle_response` — post-call: stores `unhandled_exception_log_level`
   and `exit_codes_class` in `ctx.meta`

Each method captures `original_make_context = f.make_context` and replaces it with
a new closure, so the patches chain implicitly. The full behaviour of `make_context`
is invisible without reading all three methods.

---

## Goal

Replace the three patches with a single `_patch_make_context(f)` method that applies
all three concerns in one wrapper. The docstring structure (`pre-call / call / post-call`)
makes execution order explicit. Each concern is guarded by the same config flag as before.

---

## Design

```python
def _patch_make_context(self, f: click_extra.Group) -> None:
    """Patch make_context once with all framework hooks applied in order.

    Three concerns are composed here — each guarded by its config flag:
    1. Dynamic auto_envvar_prefix (pre-call): derive prefix from CLI name when not set.
    2. Early verbosity (pre-call + post-call): extract level before Click parses args,
       apply it after the context is built.
    3. Framework meta injection (post-call): store log level and exit codes in ctx.meta
       so returns_response can read them without a GroupConfig reference.
    """
    original_make_context = f.make_context
    level = self.config.unhandled_exception_log_level       # capture before closure
    exit_codes_cls = self.config.exit_codes_class           # capture before closure

    @functools.wraps(original_make_context)
    def custom_make_context(info_name, args, parent=None, **extra):
        # --- pre-call ---
        if self.config.auto_envvar_prefix is None and parent is None and info_name:
            derived_prefix = info_name.upper().replace("-", "_").replace(" ", "_")
            extra.setdefault("auto_envvar_prefix", derived_prefix)

        level_name = None
        if self.config.add_verbosity_option and parent is None and args:
            level_name = self._extract_early_verbosity(args)

        # --- call ---
        ctx = original_make_context(info_name, args, parent=parent, **extra)

        # --- post-call ---
        if self.config.add_verbosity_option and parent is None and level_name:
            from .log.config import PYCLIFER_LOG_LEVELS

            if level_name in PYCLIFER_LOG_LEVELS:
                for param in ctx.command.params:  # pragma: no branch
                    if param.name == "verbosity" and hasattr(param, "set_level"):
                        param.set_level(ctx, param, level_name)
                        break

        if parent is None:
            ctx.meta.setdefault("pyclifer.unhandled_exception_log_level", level)
            ctx.meta.setdefault("pyclifer.exit_codes_class", exit_codes_cls)

        return ctx

    f.make_context = custom_make_context
```

`_configure_handle_response` becomes `_configure_handle_response(f)` with only the
`validate_exit_codes_class` call and the `handle_response_by_default` flag — no
`make_context` patch inside it.

`_inject_dynamic_envvar` and `_inject_early_verbosity` are deleted.

`__call__` replaces the three calls with one:

```python
# Before
f = self._inject_dynamic_envvar(f)
f = self._inject_early_verbosity(f)
self._configure_handle_response(f)

# After
self._patch_make_context(f)
self._configure_handle_response(f)
```

---

## Files

| File | Change |
|------|--------|
| `src/pyclifer/core/decorators.py` | Add `_patch_make_context`, update `_configure_handle_response`, delete `_inject_dynamic_envvar` and `_inject_early_verbosity`, update `__call__` |
| `tests/core/test_decorators.py` | Add/update tests per concern (see below) |

---

## Test coverage requirements

Each concern must be tested **independently** via the composite wrapper — regression
protection against future edits silently disabling one concern.

### Concern 1 — Dynamic envvar prefix
- `auto_envvar_prefix` is derived from CLI name when `config.auto_envvar_prefix is None`
- `auto_envvar_prefix` is NOT overridden when explicitly set
- prefix derivation: hyphens and spaces become underscores, uppercase

### Concern 2 — Early verbosity
- verbosity extracted pre-parse and applied to context
- no-op when `add_verbosity_option=False`
- no-op when no args supplied
- unknown level in `PYCLIFER_LOG_LEVELS` is silently skipped

### Concern 3 — Framework meta injection
- `pyclifer.unhandled_exception_log_level` stored in `ctx.meta` at root
- `pyclifer.exit_codes_class` stored in `ctx.meta` at root
- neither key is set on sub-context (`parent is not None`)
- `setdefault` semantics: pre-existing value not overwritten

### Integration
- all three concerns active simultaneously (default `app_group` config)
- existing tests in `test_decorators.py` and `test_returns_response.py` must all pass

---

## Implementation order

1. Write failing tests for each concern (they pass today — verify they still map to
   the right behaviour after the refactor)
2. Add `_patch_make_context`
3. Strip `make_context` patch from `_configure_handle_response`
4. Delete `_inject_dynamic_envvar` and `_inject_early_verbosity`
5. Update `__call__`
6. Run full suite — all 529+ tests must pass
7. One commit per step 2–5, or a single atomic commit — your choice

---

## Out of scope

- Changing any config flags or their defaults
- Changing the behaviour of `_extract_early_verbosity`
- Touching `_apply_rich_help`, `_configure_context`, `_apply_automatic_options`