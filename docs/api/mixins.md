# Mixins

Feature mixins used internally by pyclif's group and context classes. Exposed publicly
for advanced subclassing.

## GlobalOptionsMixin

Propagates options marked `is_global=True` from a parent group to all child commands
and subgroups at invocation time.

::: pyclif.GlobalOptionsMixin

---

## HandleResponseMixin

Auto-wraps commands added via `command()` or `add_command()` with `returns_response`
by default (opt out with `handle_response=False`).

::: pyclif.HandleResponseMixin

---

## OutputFormatMixin

Dispatches `Response` objects to the appropriate formatter (JSON / YAML / Table / Rich / Raw)
based on `--output-format` stored in `ctx.meta`.

::: pyclif.OutputFormatMixin

---

## RichHelpersMixin

Rich console helpers available on the context: panels, rules, status spinners, prompts.

::: pyclif.RichHelpersMixin