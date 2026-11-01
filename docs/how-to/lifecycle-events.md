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
- An unknown event name raises `ValueError` as soon as you attach the handler, and the message lists
  the valid names, so a typo never goes unnoticed.

```python
@app_group(on={"config.laoded": [check_config]})  # ValueError: Unknown event 'config.laoded'...
def cli(): ...
```

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

## Report an error from a handler

Raise a Click error to stop the run with a clear message:

```python
import click_extra


def check_config(ctx) -> None:
    if not ctx.meta.get(CONF_SOURCE):
        raise click_extra.UsageError("No configuration found, run `myapp config init`.")
```

The message is printed once and the exit code is 2. The same holds for a bare call: click-extra
swallows errors raised while it reads the configuration for default subcommands, so pyclifer keeps
the error and reports it before the help screen.

With a structured output format (`json` or `yaml`) and `handle_response=True`, the error is answered
on stdout with the usual schema (`success: false`, the message, `error_type: "usage_error"`).

## Learn more

- [`EventsMixin`](../api/mixins.md#eventsmixin) is the mixin that gives a group `on()` and `emit()`.
- [`app_group`](../api/decorators.md#app_group) lists the `on` parameter.
