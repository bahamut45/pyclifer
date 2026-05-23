<p align="center">
  <img src="https://raw.githubusercontent.com/bahamut45/pyclif/main/docs/assets/logo.png" alt="pyclif logo" width="200">
</p>

# pyclif

![version](https://img.shields.io/badge/version-0.1.2-green)
[![codecov](https://codecov.io/gh/bahamut45/pyclif/graph/badge.svg)](https://codecov.io/gh/bahamut45/pyclif)

**PYthon Command Line Interface Framework** — a decorator-driven CLI framework built on
[click-extra](https://github.com/kdeldycke/click-extra) and [rich-click](https://github.com/ewels/rich-click).

pyclif provides four decorators (`@app_group`, `@group`, `@command`, `@option`) that give
your CLI applications automatic configuration management, environment variable binding,
Rich-enhanced logging, global option propagation, and standardized output formatting —
with zero boilerplate.

## Installation

> **Note:** PyPI release is pending ([pypi/support#10302](https://github.com/pypi/support/issues/10302)). In the meantime, install directly from GitHub:

```bash
# pip
pip install git+https://github.com/bahamut45/pyclif.git

# uv
uv add git+https://github.com/bahamut45/pyclif.git

# poetry
poetry add git+https://github.com/bahamut45/pyclif.git
```

Requires Python 3.10+.

## Contributing

```bash
uv sync --dev
pre-commit install
```

`pre-commit install` activates the git hooks (ruff check + format) that run automatically on every commit.

## Quick Start

```python
"""CLI application using pyclif."""
from pyclif import app_group, command, option, Response


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

- **Decorator-driven** — four decorators cover the full CLI surface
- **Autoconfiguration** — TOML/YAML/JSON config files with Linux path conventions (`/etc/<app>/`, `~/.config/<app>/`)
- **Environment variables** — automatic prefix-based binding for every option
- **Rich logging** — colored output, custom `TRACE` level, secret masking, rotating log files
- **Standardized output** — `Response` dataclass with JSON/YAML/Table/Rich/Raw formatters via `--output-format`
- **Global options** — options marked `is_global=True` propagate automatically to all subcommands
- **Project scaffolding** — `pyclif project init` generates a ready-to-use project structure

## Documentation

Full documentation at **[bahamut45.github.io/pyclif](https://bahamut45.github.io/pyclif/)**.

## License

MIT — see [LICENSE](LICENSE).