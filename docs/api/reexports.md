# Re-exports and Constants

pyclifer re-exports a set of `click_extra` names so that a command file needs one import line,
`from pyclifer import ...`, and no direct dependency on Click. They are the same objects as in
`click_extra` (`pyclifer.prompt is click_extra.prompt`): their behaviour is the one described in the
[Click documentation](https://click.palletsprojects.com/).

## Parameter types

| Name | What it is |
|---|---|
| `BOOL`, `INT`, `FLOAT`, `STRING`, `UUID` | Click's built-in parameter types, used as `type=INT` in `@option` |
| `IntRange`, `FloatRange` | Integer and float types bounded by `min` and `max` |
| `Choice`, `DateTime` | A fixed set of values, and a date and time parsed from given formats |
| `Tuple` | A parameter made of several values with their own types |
| `ClickPath` | Click's `Path` type, renamed so it does not hide `pathlib.Path` |

## Console helpers

| Name | What it is |
|---|---|
| `prompt`, `confirm` | Ask the user for a value, or for a yes or no answer |
| `secho` | Print a message with colour and style |
| `unstyle` | Remove ANSI styling from a text |
| `get_current_context` | The active Click context, from anywhere inside a running command |
| `pass_obj` | Pass `ctx.obj` to a command, whatever its type. `pass_cli_context` looks for an object of your context class instead |

## Option decorators

| Name | What it is |
|---|---|
| `confirmation_option` | Ask for confirmation before the command runs |
| `password_option` | Ask for a password with hidden input |
| `version_option` | Add `--version`. `@app_group` already adds it unless `add_version_option=False` |

## Constants

| Name | What it is |
|---|---|
| `__app_name__` | The name of the package, `"pyclifer"` |
| `__version__` | The installed version of pyclifer, kept in sync by `bumpversion` |
