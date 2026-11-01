# Decorators

The four main decorators are the public surface of pyclifer. They wrap Click objects with
framework features: automatic configuration, global option propagation, Rich logging, and
standardized response handling.

## app_group

Entry point decorator. Creates the root CLI group with all framework features enabled.

Key parameters:

- `context_factory` — callable that receives all `context=True` option values as keyword
  arguments and returns the `ctx.obj` instance. Enables declarative context construction
  without a manual `ctx.obj =` assignment in the group callback.
- `context_options_panel` — label for the help section that lists `context=True` options
  in subcommand `--help` output. Defaults to `"Context Options (anywhere-passable)"`.
  Set to any string to customise the heading.
- `auto_envvar_prefix` — uppercase prefix for automatic environment variable binding.
  With `auto_envvar_prefix="MYAPP"`, `--database-url` reads `MYAPP_DATABASE_URL`.
- `rich_help_config` — `RichHelpConfiguration` instance (or dict) forwarded to rich-click.
  Lets you customise colours, column widths, and panel styles in `--help` output.
- `use_rich_help` — set to `False` to disable rich-click rendering and use plain Click help.
  Defaults to `True`.
- `on` — mapping of lifecycle event names to lists of handler functions, for example
  `on={"config.loaded": [check_config]}`. Keys are framework event names or `Event` objects; a plain
  string that is not a framework event raises `ValueError` at decoration time. See the
  [Lifecycle events](../how-to/lifecycle-events.md) guide. `group` accepts it too.

::: pyclifer.app_group

---

## group

Creates a subgroup that inherits global options from its parent.

::: pyclifer.group

---

## command

Creates a CLI command. Use inside a group or app_group.

Key parameter:

- `handle_response=False` — when `True`, wraps the command with `returns_response` so any
  `Response` returned by the function is printed automatically. Equivalent to stacking
  `@returns_response` manually.

::: pyclifer.command

---

## option

Extends Click options with environment variable binding and optional global/context propagation.

- `is_global=True` — propagates this option to all subcommands (see `GlobalOptionsMixin`).
- `context=True` — marks this option as a *context option*: its value feeds `context_factory`
  and is accepted at any position in the command chain (see *Anywhere-passable options*).
  By default it also appears in subcommand `--help` under the *Context Options* panel.
- `show_in_subcommand_help=True` — when `context=True`, controls whether the option is
  shown in subcommand help. Set to `False` to hide it from subcommand help while keeping
  the anywhere-passable behaviour intact.
- `store_in_meta=False` — when `True`, stores the option value in `ctx.meta` automatically
  (key: `"pyclifer.<option-name>"`). The option is not exposed as a function parameter.
  Used internally by `pagination_options` for `--page` and `--limit`.

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
