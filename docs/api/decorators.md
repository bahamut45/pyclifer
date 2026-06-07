# Decorators

The four main decorators are the public surface of pyclifer. They wrap Click objects with
framework features: automatic configuration, global option propagation, Rich logging, and
standardized response handling.

## app_group

Entry point decorator. Creates the root CLI group with all framework features enabled.

::: pyclifer.app_group

---

## group

Creates a subgroup that inherits global options from its parent.

::: pyclifer.group

---

## command

Creates a CLI command. Use inside a group or app_group.

::: pyclifer.command

---

## option

Extends Click options with environment variable binding and optional global propagation.

::: pyclifer.option

---

## output_filter_option

Adds `--output-format` to a command (JSON, YAML, Table, Rich, Raw).

::: pyclifer.output_filter_option

---

## returns_response

Decorator that intercepts a `Response` return value and dispatches it to the formatter.
Applied automatically for all commands under `@app_group` (on by default). Use `handle_response=False` on the group or individual commands to opt out.

::: pyclifer.returns_response

---

## pagination_options

Injects `--page` and `--limit` options into a command. Values are stored in
`ctx.meta["pyclifer.page"]` and `ctx.meta["pyclifer.limit"]` via `store_in_meta`.

::: pyclifer.pagination_options

---
