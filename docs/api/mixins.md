# Mixins

Feature mixins used internally by pyclifer's group and context classes. Exposed publicly
for advanced subclassing.

## GlobalOptionsMixin

Propagates options from a parent group to all child commands and subgroups at registration time.

- Options marked `is_global=True` are added as real subcommand parameters — visible in help
  and forwarded to each callback.
- Options marked `context=True` (non-global) with `show_in_subcommand_help=True` are injected
  as display-only copies into subcommand help under a dedicated *Context Options* panel.
  These copies have `expose_value=False` and `required=False` so they never interfere with
  subcommand argument parsing or callbacks.

::: pyclifer.GlobalOptionsMixin

---

## HandleResponseMixin

Auto-wraps commands added via `command()` or `add_command()` with `returns_response`
by default (opt out with `handle_response=False`).

::: pyclifer.HandleResponseMixin

---

## OutputFormatMixin

Dispatches `Response` objects to the appropriate formatter (JSON / YAML / Table / Rich / Raw)
based on `--output-format` stored in `ctx.meta`.

::: pyclifer.OutputFormatMixin

---

## RichHelpersMixin

Rich console helpers available on the context: panels, rules, status spinners, prompts.

::: pyclifer.RichHelpersMixin