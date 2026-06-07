<p align="center">
  <img src="https://raw.githubusercontent.com/bahamut45/pyclifer/main/docs/assets/logo.png" alt="pyclifer logo" width="200">
</p>

# pyclifer

[![PyPI](https://img.shields.io/pypi/v/pyclifer)](https://pypi.org/project/pyclifer/)
[![codecov](https://codecov.io/gh/bahamut45/pyclifer/graph/badge.svg)](https://codecov.io/gh/bahamut45/pyclifer)

**PY**thon **C**ommand **L**ine **I**nterface **F**ram**E**wo**R**k — a decorator-driven CLI framework built on
[click-extra](https://github.com/kdeldycke/click-extra) and [rich-click](https://github.com/ewels/rich-click).

pyclifer provides four decorators (`@app_group`, `@group`, `@command`, `@option`) that give
your CLI applications automatic configuration management, environment variable binding,
Rich-enhanced logging, global option propagation, and standardized output formatting —
with zero boilerplate.

## Installation

```bash
pip install pyclifer
```

Requires Python 3.10+.

## Development

Requires [Task](https://taskfile.dev/#/installation).

```bash
task install       # install dev + docs dependencies
pre-commit install # activate git hooks (ruff check + format on every commit)
```

```bash
task check         # lint + test
task test          # run test suite
task tox           # run tests across Python 3.10–3.13
```

```bash
task release:patch # bump patch version, commit, tag and push
task release:minor
task release:major
```

Run `task --list` to see all available tasks.

## Quick Start

```python
"""CLI application using pyclifer."""
from pyclifer import app_group, command, option, Response


@app_group(handle_response=True)
def main():
    """My CLI application."""
    pass


@main.command()
@option("--name", "-n", default="World", help="Your name")
def hello(name: str) -> Response:
    """Say hello."""
    return Response(success=True, message=f"Hello {name}!")


if __name__ == "__main__":
    main()
```

```bash
$ python app.py --help
 Usage: app.py [OPTIONS] COMMAND [ARGS]...

 My CLI application.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│     --version                                    Show the version and exit.  │
│     --log-file       FILE                        Path to the log file (with  │
│                                                  daily automatic rotation).  │
│                                                  [env var: MYAPP_LOG_FILE]   │
│ -v  --verbosity      LEVEL                       Either TRACE, DEBUG, INFO,  │
│                                                  WARNING, ERROR, CRITICAL.   │
│                                                  [env var: MYAPP_VERBOSITY]  │
│                                                  [default: WARNING]          │
│ -C  --config         CONFIG_PATH                 Configuration file          │
│                                                  location. Supports glob     │
│                                                  patterns and remote URLs.   │
│                                                  [env var: MYAPP_CONFIG]     │
│                                                  [default:                   │
│                                                  /etc/myapp/*.{toml,yaml,    │
│                                                  yml,json,ini,xml},          │
│                                                  ~/.config/myapp/*.{toml,    │
│                                                  yaml,yml,json,ini,xml}]     │
│ -o  --output-format  [json|yaml|table|rich|raw]  Specify the output format   │
│                                                  for the command. [env var:  │
│                                                  MYAPP_OUTPUT_FORMAT]        │
│                                                  [default: table]            │
│ -h  --help                                       Show this message and exit. │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ hello                       Say hello.                                       │
╰──────────────────────────────────────────────────────────────────────────────╯

$ python app.py hello --name Alice
Hello Alice!

$ python app.py hello --help
 Usage: app.py hello [OPTIONS]

 Say hello.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ -n  --name           TEXT                        Your name [env var:         │
│                                                  MYAPP_HELLO_NAME] [default: │
│                                                  World]                      │
│ -v  --verbosity      LEVEL                       Either TRACE, DEBUG, INFO,  │
│                                                  WARNING, ERROR, CRITICAL.   │
│                                                  [env var:                   │
│                                                  MYAPP_HELLO_VERBOSITY]      │
│                                                  [default: WARNING]          │
│ -o  --output-format  [json|yaml|table|rich|raw]  Specify the output format   │
│                                                  for the command. [env var:  │
│                                                  MYAPP_HELLO_OUTPUT_FORMAT]  │
│                                                  [default: table]            │
│ -h  --help                                       Show this message and exit. │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Features

- **Decorator-driven** — four decorators (`@app_group`, `@group`, `@command`, `@option`) cover the full CLI surface
- **Autoconfiguration** — TOML/YAML/JSON/XML config files with Linux path conventions (`/etc/<app>/`, `~/.config/<app>/`)
- **Environment variables** — automatic prefix-based binding for every option
- **Rich logging** — colored output, custom `TRACE` level, secret masking, rotating log files
- **Structured output** — `Response` + `OperationResult` with JSON/YAML/Table/Rich/Raw formatters via `--output-format`
- **Renderer system** — declarative `BaseRenderer` controls all output formats from a single class; streaming generators drive a Live Rich display via `rich_on_item` hooks
- **Service layer** — `BaseInterface.respond()` auto-detects list vs generator, picks the right renderer, and builds the `Response` — commands stay thin
- **Global options** — options marked `is_global=True` propagate automatically to all subcommands
- **Pagination** — built-in `PaginatedResponse` with page/limit/total in JSON and YAML output
- **Project scaffolding** — `pyclifer project init / add app / add command / add integration` generates a ready-to-use project structure

## Documentation

Full documentation at **[bahamut45.github.io/pyclifer](https://bahamut45.github.io/pyclifer/)**.

## License

MIT — see [LICENSE](LICENSE).