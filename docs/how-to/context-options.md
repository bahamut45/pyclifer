# Context construction and anywhere-passable options

By default, you wire a context object by assigning `ctx.obj` manually in the
root group callback:

```python
@app_group()
@click.pass_context
def app(ctx):
    ctx.obj = MyContext(host=ctx.params.get("host"))
```

pyclifer offers a declarative alternative through two features that work together:

- `context=True` on `@option` — marks the option as a *context option*
- `context_factory=` on `@app_group` — callable that receives context option values
  and returns the `ctx.obj` instance

## Basic usage

```python
from pyclifer import app_group, option
from myapp.core.context import MyContext

@app_group(context_factory=MyContext)
@option("--host", required=True, context=True)
@option("--token", required=True, context=True)
def app():
    """My CLI."""
```

When the CLI starts, pyclifer collects the values of all `context=True` options
and calls `MyContext(host=..., token=...)`. The result is stored as `ctx.obj`
before the root callback runs — no manual assignment needed.

Your context class must accept those keyword arguments:

```python
class MyContext(BaseContext):
    def __init__(self, host: str = "localhost", token: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.client = MyClient(host=host, token=token)
```

## Anywhere-passable placement

Context options (and global options marked `is_global=True`) are *anywhere-passable*:
they are accepted at any position in the command chain, including after a subcommand name.

All of the following are equivalent:

```bash
# canonical position — before the subcommand
myapp --host api.example.com --token secret items list

# after the subcommand
myapp items list --host api.example.com --token secret

# mixed
myapp --host api.example.com items list --token secret
```

This is useful when users want to keep connection options close to the command
that uses them without breaking the `context_factory` contract.

### Priority

Anywhere-passable placement does **not** change option priority. The standard
Click cascade still applies:

```
CLI arg > environment variable > config file (default_map) > default=
```

If the same option appears both before and after the subcommand boundary,
the value closest to the option definition (canonical position) wins.

## Difference between `context=True` and `is_global=True`

| Feature | `context=True` | `is_global=True` |
|---------|---------------|------------------|
| Accepted anywhere in chain | Yes | Yes |
| Forwarded to subcommand params | No | Yes |
| Passed to `context_factory` | Yes | No |

Use `context=True` for options that feed `ctx.obj` construction (connection
credentials, environment name, etc.). Use `is_global=True` for cross-cutting
options that each subcommand also receives directly (e.g. `--dry-run`).

An option can carry both flags if you need both behaviours.

## Known limitations

### `nargs=-1` options must stay in canonical position

Click does not allow `nargs=-1` on options (only on arguments). If you define
a multi-value option with a fixed `nargs` greater than 1, it must appear before
the subcommand boundary:

```bash
# nargs=2 option — works anywhere
myapp items list --coords 10 20

# Correct: values travel as a unit
myapp items list --coords 10 20
```

A variadic list of values (e.g. `--tags a b c`) requires a Click `Argument`
with `nargs=-1`, which is not an option and therefore cannot be marked
`context=True` or `is_global=True`. Use `--tag` with `multiple=True` instead:

```python
@option("--tag", multiple=True, context=True)
```

### `--` terminator

A bare `--` in the argument list stops option scanning. Any `context=True` or
`is_global=True` tokens after `--` are treated as positional arguments by
Click and are not pre-scanned. Place context options before `--` when using
this terminator.