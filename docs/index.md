<p align="center">
  <img src="assets/logo.png" alt="pyclifer logo" width="200">
</p>

# Documentation

Welcome to the comprehensive documentation for pyclifer, a decorator-driven CLI framework that provides powerful
decorators for building Python CLI applications with automatic configuration management, environment variable support,
Rich-enhanced logging, and standardized output formatting.

## Overview

pyclifer is built on top of `click-extra` and `rich-click` and exposes four main decorators from `pyclifer.core`:

- `@app_group` — Create the main CLI application group with all features enabled.
- `@group` — Create command subgroups.
- `@command` — Create CLI commands.
- `@option` — Create CLI options with environment variable binding and global propagation support.

## Quick Navigation

### Getting Started

- [**Getting Started**](getting-started.md) — Installation, requirements, and your first CLI application
- [**Examples**](examples.md) — Complete examples and usage patterns

### Configuration & Usage

- [**Configuration Management**](configuration.md) — Configuration files, environment variables, and the
  `CustomConfigOption` system
- [**Rich Logging**](logging.md) — Colored logging with Rich formatting, TRACE level, and secrets filtering
- [**Output Formatting**](output-formatting.md) — `BaseContext`, `Response`, `BaseRenderer`, and dynamic
  formatting (JSON, YAML, Tables, Rich, Text, Raw)
- [**Error Handling**](error-handling.md) — `OperationResult`, `BaseInterface`, and the service/command
  layer contract
- [**Development and Testing**](development.md) — Development setup, testing, and contribution guidelines

## Quick Example

```python
from pyclifer import app_group, command, option


@app_group()
def main():
    """My CLI application."""
    pass


@main.command()
@option("--name", "-n", help="Your name")
def hello(name):
    """Say hello."""
    print(f"Hello {name or 'World'}!")


if __name__ == "__main__":
    main()
```

## Key Features

### Automatic Configuration

- **Configuration files**: TOML, YAML, JSON support
- **Multiple locations**: System-wide (`/etc/<app>/`) and user-specific (`~/.config/<app>/`)
- **Environment variables**: Automatic prefix-based mapping
- **Precedence**: CLI args → env vars → config files → defaults

### Rich CLI Options

- **Automatic help**: Generated from docstrings with environment variable display
- **Rich logging**: Colored output with Rich formatting and enhanced tracebacks
- **Advanced verbosity**: Built-in `-v`, `-vv`, `-vvv` with custom TRACE level
- **Security filtering**: Automatic masking of sensitive data in logs
- **File logging**: Time-based rotating log files via `--log-file`
- **Version option**: Automatic `--version` support
- **Consistent behavior**: Standardized option handling across all commands

### Standardized Output

- **Dynamic format**: JSON, YAML, Tables, Rich text, plain text, or raw values via `--output-format`
- **Response model**: Standardize results and errors with the `Response` dataclass
- **Renderer model**: `BaseRenderer` controls every output format from a single subclass
- **Error handling**: `OperationResult` + `BaseInterface` keep commands free of try/except boilerplate
- **Context helpers**: Rich-powered prompts, panels, status spinners via `BaseContext`

### Seamless Integration

- **Click compatibility**: Full compatibility with the Click ecosystem
- **Linux conventions**: Follows standard Linux configuration paths
- **Testing support**: Built-in support for CLI testing with pytest

## Project Information

- **Author**: Nicolas JOUBERT (njoubert45@gmail.com)
- **Repository**: https://github.com/bahamut45/pyclifer
- **Issues**: https://github.com/bahamut45/pyclifer/issues
- **License**: MIT License
- **Python**: Requires Python 3.10+
