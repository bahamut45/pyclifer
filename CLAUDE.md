# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Code style rules (type hints, docstrings, naming, decorator order, tests) are in [`.claude/CLAUDE.md`](.claude/CLAUDE.md).

## Project Overview

pyclif (PYthon Command Line Interface Framework) is a decorator-driven CLI framework built on
top of `click-extra` and `rich-click`. It provides four main decorators (`@app_group`, `@group`,
`@command`, `@option`) that give CLI applications automatic configuration management, environment
variable binding, Rich-enhanced logging, global option propagation, and standardized output
formatting.

pyclif also ships a built-in project scaffolding tool (`pyclif project`) that generates
Django-inspired project structures for CLI applications.

## Context

pyclif is a migration and clean rewrite of `recia-cli` (private GitLab project). All the core
framework logic has been ported over with the following improvements:

- Clean public API exposed exclusively through `pyclif.__init__` with `__all__`
- `core/` internals are never imported directly by users — always via `from pyclif import ...`
- Built-in scaffolding CLI (`pyclif project init / add app / add command / add integration`)
- Framework dogfoods its own pattern — scaffolding lives in `src/pyclif/apps/project/`

## Working Style

Before modifying any file, state in one or two sentences:
- **What** you are about to write or change (the substance, not just "update X")
- **Why** — what problem it solves or what behaviour it enables

Do this even for small edits. Skip it only when the change was explicitly dictated by the
user (e.g., "replace line 12 with …") and there is nothing non-obvious to explain.

## Spec lifecycle

Specs live in `.claude/specs/`. When a spec is fully implemented, move it to
`.claude/specs/archived/` immediately — do not ask for confirmation.

As each item is completed, prefix its heading with `✅` in the spec file.
When all items are marked, archive the spec.

When a spec file is created, commit it immediately before any implementation:
`📝 docs(specs): add <spec-name> spec`

Implementation process per spec item:

1. Create a feature branch: `git checkout -b feat/<item-slug>`
2. Apply TDD: write a failing test first, watch it fail, then write minimal code to pass
3. Run `ruff check` and `ruff format` before committing
4. Run `python -m pytest tests/ -v` and confirm all tests pass
5. Stage code, tests, **and** the spec file (with `✅` prefix on the item heading) together
6. Commit everything in one commit using the format defined in `.claude/CLAUDE.md` → "Commit message format"
7. Get user validation before merging
8. Merge into `main` and delete the feature branch

## Commands

```bash
# Install dev dependencies
uv sync --extra dev,docs

# Run all tests
python -m pytest tests/ -v

# Run a single test
python -m pytest tests/core/test_decorators.py::TestReturnsResponse::test_response_is_printed -v

# Run tests across all supported Python versions (3.10–3.13)
tox
tox -e py310

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/
```

## Architecture

### Public API

All public symbols are exposed through `src/pyclif/__init__.py` with `__all__`.
Users always import from `pyclif` directly — never from `pyclif.core.*`:

```python
from pyclif import app_group, group, command, option
from pyclif import BaseContext, Response, get_logger
```

### Core Design Patterns

- **Decorator-driven**: Four decorators in `src/pyclif/core/decorators.py` wrap Click objects
  with framework features. `@app_group` is the main entry point; `@group` and `@command` add
  subgroups/commands; `@option` extends Click options with env var binding and global propagation.
- **Mixin composition**: Features are split across reusable mixins (`src/pyclif/core/mixins/`)
  and composed into core classes. This keeps the feature surface modular.
- **Context-based output dispatch**: `BaseContext` (context.py) combines `RichHelpersMixin` +
  `OutputFormatMixin`. All output goes through `ctx.print_result_based_on_format()`, which
  dispatches to JSON/YAML/Table/Rich/Raw formatters based on the `--output-format` flag stored
  in `ctx.meta`.
- **Global option propagation**: Options marked `is_global=True` via `PyclifOption` are
  automatically propagated from parent groups to all subcommands via `GlobalOptionsMixin`.
- **Automatic response handling**: `handle_response=True` on `@app_group` automatically wraps
  all commands (including those added via `add_command()` and nested subgroups) with
  `returns_response`, which intercepts `Response` return values and prints them.

### Key Modules

| Module                     | Responsibility                                                                            |
|----------------------------|-------------------------------------------------------------------------------------------|
| `core/decorators.py`       | The four public decorators + `GroupDecorator` class + `returns_response`                  |
| `core/classes.py`          | `PyclifOption`, `PyclifExtraGroup`/`PyclifRichGroup`, `CustomConfigOption`, `GroupConfig` |
| `core/context.py`          | `BaseContext` — composites RichHelpersMixin + OutputFormatMixin                           |
| `core/mixins/cli.py`       | `GlobalOptionsMixin`, `StoreInMetaMixin`                                                  |
| `core/mixins/response.py`  | `HandleResponseMixin` — auto-wraps commands via `command()` and `add_command()`           |
| `core/mixins/output.py`    | `OutputFormatMixin` — dispatches to JSON/YAML/Table/Rich/Raw, `_FallbackEncoder` for JSON |
| `core/mixins/rich.py`      | `RichHelpersMixin` — Rich console helpers: panels, rules, status spinners, prompts        |
| `core/output/responses.py` | `Response` dataclass: `(success, message, data, error_code)` + table/rich callbacks       |
| `core/output/tables.py`    | `CliTable`, `CliTableColumn`, `ExceptionTable`                                            |
| `core/log/`            | Rich-enhanced logging, custom `TRACE` level (5), `SecretsMasker`, `get_logger()` factory  |
| `apps/project/`            | Scaffolding CLI — `pyclif project init / add app / add command / add integration`         |

### Internal structure

```
src/pyclif/
├── __init__.py             # public API — __all__ + re-exports from core/
├── cli.py                  # pyclif CLI entry point (dogfoods apps/ pattern)
├── core/                   # framework internals — never imported directly by users
│   ├── decorators.py
│   ├── classes.py
│   ├── context.py
│   ├── callbacks.py
│   ├── mixins/
│   │   ├── cli.py
│   │   ├── output.py
│   │   ├── response.py
│   │   └── rich.py
│   ├── output/
│   │   ├── responses.py
│   │   └── tables.py
│   └── log/
└── apps/
    └── project/            # scaffolding app
        ├── __init__.py
        ├── interfaces.py
        ├── templates/
        └── commands/
            ├── init.py
            ├── add_app.py
            ├── add_command.py
            └── add_integration.py
```

### Generated project structure

Projects generated by `pyclif project init` follow this convention:

```
my-project/
├── pyproject.toml
├── src/my_project/
│   ├── __init__.py
│   ├── cli.py                  # @app_group + add_command wiring
│   ├── core/
│   │   ├── context.py          # class MyContext(BaseContext) + pass_cli_context
│   │   ├── constants.py
│   │   ├── options.py
│   │   └── integrations/       # external lib wrappers
│   └── apps/
│       └── <app>/
│           ├── __init__.py
│           ├── interfaces.py
│           ├── models.py
│           ├── tables.py
│           └── commands/
│               └── <command>.py
└── tests/
```

See `docs/scaffolding.md` for the full scaffolding specification.

### Configuration Cascade

CLI args → environment variables → config files (TOML/YAML/JSON/XML) → defaults.
`CustomConfigOption` searches standard Linux locations (`/etc/<cli>/`, `~/.config/<cli>/`, etc.).

### Output Flow

Commands return a `Response` object. When `handle_response=True` is set on `@app_group`,
`returns_response` intercepts the return value and dispatches to the appropriate formatter
via `BaseContext.print_result_based_on_format()`. JSON output uses `_FallbackEncoder` to
handle non-serializable domain objects gracefully.

## Testing Structure

Tests mirror the `src/` layout under `tests/`. The `tox` configuration in `pyproject.toml`
runs the suite against Python 3.10, 3.11, 3.12, and 3.13 using `tox-uv`.

## Versioning

Managed with `bumpversion`. Version is synced across `pyproject.toml`, `README.md`, and
`src/pyclif/__init__.py`. Commits follow conventional commits with emoji prefixes
(e.g., `✨ feat`, `🐛 fix`, `♻️ refactor`).