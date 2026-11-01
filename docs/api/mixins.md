# Mixins

Feature mixins used internally by pyclifer's group and context classes. Exposed publicly
for advanced subclassing.

## EventsMixin

Lets a group attach handlers to named lifecycle events with `on()` and call them with `emit()`.
Handlers run in registration order, a plain string that is not a framework event raises
`ValueError` from both `on()` and `emit()`, and an exception raised by a handler propagates. See the
[Lifecycle events](../how-to/lifecycle-events.md) guide.

::: pyclifer.EventsMixin

### Event

A named lifecycle event. It is a string, so it compares equal to its name. The framework defines its
own events; plugins and applications create theirs with `Event("myplugin.ready")`, which needs no
registration.

::: pyclifer.Event

---

## GlobalOptionsMixin

Propagates options from a parent group to all child commands and subgroups at registration time.

- Options marked `is_global=True` are added as real subcommand parameters — visible in help
  and forwarded to each callback.
- **A group takes a propagated option only if it wants it.** The callback of a subgroup receives a
  propagated global option when it declares the parameter (or `**kwargs`); `def ops():` works and
  simply does not see it. An option the group declares itself is always passed, and a leaf command
  must accept every global option, since it is forwarded to its callback.
- **A global option is parsed where it is written.** `myapp --region eu leaf` gives `eu` to the
  group that declares the option, not to `leaf`, which parses its own copy and keeps its default.
  Write `myapp leaf --region eu` for the subcommand to receive it. This holds for a
  `required=True` option too: `myapp --token T leaf` fails with a missing option on `leaf`, while
  `myapp leaf --token T` works.
- Options marked `context=True` (non-global) with `show_in_subcommand_help=True` are injected
  as display-only copies into subcommand help under a dedicated *Context Options* panel.
  These copies have `expose_value=False` and `required=False` so they never interfere with
  subcommand argument parsing or callbacks. They reach commands at any depth, whatever the order
  in which groups and commands are registered. The panel title is drawn by the Rich help; with
  `use_rich_help=False` the option is listed with the other options of the command.

::: pyclifer.GlobalOptionsMixin

---

## HandleResponseMixin

Auto-wraps commands added via `command()` or `add_command()` with `returns_response`
by default (opt out with `handle_response=False`).
`handle_response` has three values, on a command as well as on a group:

| Value | Meaning |
|-------|---------|
| `None` (default) | Inherit. A command takes its group's setting; a group takes its parent's once attached. |
| `True` | Enable. |
| `False` | Opt out. A group set to `False` protects its whole sub-tree from a parent that handles responses. |

Whichever of the sub-group and the application is declared first, a command with no explicit choice
is wrapped as soon as its group is attached to an application that handles responses.

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