# Lifecycle events

pyclifer groups emit named *lifecycle events*. You attach a function to an event, and the
framework calls it at that point of the run. It is the one extension mechanism of the framework:
you declare your app with `@app_group`, and you extend it with handlers.

## Attach a handler

Declare handlers with the `on=` argument of `@app_group` (or `@group`). It maps an event name to a
list of functions:

```python
from pyclifer import app_group


def check_config(ctx) -> None:
    """Run once the configuration is resolved."""
    ...


@app_group(on={"config.loaded": [check_config]})
def cli():
    """My CLI."""
```

Or attach a handler after the group exists, with `on()`. It works as a decorator, which is the
form a plugin uses:

```python
@cli.on("config.loaded")
def another_handler(ctx) -> None:
    ...
```

A handler receives the Click context of the group that owns it. For `@app_group` this is the root
context, so `ctx.command_path` is the name of your CLI.

## Rules

- Handlers run in the order they were attached, and each group keeps its own handlers.
- An exception raised by a handler is never swallowed: it propagates.
- A plain string that is not a framework event raises `ValueError`, both when you attach a handler
  and when you emit, and the message lists the valid names, so a typo never goes unnoticed.

```python
@app_group(on={"config.laoded": [check_config]})  # ValueError: Unknown event 'config.laoded'...
def cli(): ...
```

To use an event of your own, create an [`Event`](#define-your-own-events) instead of a string.

## Available events

| Event           | Emitted                                                   |
|-----------------|-----------------------------------------------------------|
| `config.loaded` | Once, after the configuration file resolution is over.    |

### `config.loaded`

Use it to validate the configuration, or to react to the file that was found. The path of the
loaded file is in `ctx.meta`; it is `None` when no file was found:

```python
from click_extra.context import CONF_SOURCE


def show_source(ctx) -> None:
    print(ctx.meta.get(CONF_SOURCE))
```

click-extra also stores the parsed content of the file under `CONF_FULL` in the same place.

When the event is emitted:

| Command line                           | `config.loaded`        |
|----------------------------------------|------------------------|
| `myapp hello`, with or without a file  | once                   |
| `myapp` alone (bare call)              | once                   |
| `myapp unknown-command`                | once, before the error |
| `myapp --help`, `myapp --version`      | not emitted            |
| `myapp hello --help`                   | not emitted            |
| `myapp --config file.toml --help`      | once                   |

The last row comes from the order of processing: `--config` is handled before `--help`, so the
configuration is already resolved when the help is shown.

## Define your own events

A plugin, or your application, can expose its own extension points. Create an `Event` once, in a
module that others can import, and emit it where it belongs:

```python
# myplugin/events.py
from pyclifer import Event

READY = Event("myplugin.ready")
```

```python
# in a command of the app, or of a plugin
import click

from myplugin.events import READY


@cli.command()
@click.pass_context
def run(ctx):
    """Do the work, then tell the handlers."""
    ctx.find_root().command.emit(READY, ctx)
```

Anyone can then attach a handler, with the same `on=` argument or `on()` method as for the framework
events:

```python
from myplugin.events import READY


@app_group(on={READY: [my_handler]})
def cli(): ...
```

- An `Event` needs no registration, so the order in which plugins are loaded does not matter.
- `Event` is a string: `READY == "myplugin.ready"`. Only an `Event` object is accepted for your own
  names, by `on()` as well as by `emit()`; a plain string must be a framework event. A typo in the
  name of an imported `Event` becomes an import error.
- Prefix the name with your plugin, as in `myplugin.ready`. Because an `Event` is a string, an
  `Event("config.loaded")` is equal to the framework event and would share its handlers.
- Handlers belong to a group, so a handler attached to one group is not called for another.
- `emit()` returns the values the handlers returned, in the order they ran.

## Report an error from a handler

Raise a Click error to stop the run with a clear message:

```python
import click_extra


def check_config(ctx) -> None:
    if not ctx.meta.get(CONF_SOURCE):
        raise click_extra.UsageError("No configuration found, run `myapp config init`.")
```

The message is printed once and the exit code is 2. Prefer `UsageError`: a plain `ClickException`
exits with code 1 on a normal call, but with code 2 on a bare call, where the help screen sets the
exit code. The same holds for a bare call: click-extra
swallows errors raised while it reads the configuration for default subcommands, so pyclifer keeps
the error and reports it before the help screen.

With a structured output format (`json` or `yaml`) and `handle_response=True`, the error is answered
on stdout with the usual schema (`success: false`, the message, `error_type: "usage_error"`).

## Learn more

- [`EventsMixin`](../api/mixins.md#eventsmixin) is the mixin that gives a group `on()` and `emit()`.
- [`app_group`](../api/decorators.md#app_group) lists the `on` parameter.
