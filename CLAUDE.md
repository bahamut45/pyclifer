# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Code style rules (type hints, docstrings, naming, decorator order, tests) are in [`.claude/CLAUDE.md`](.claude/CLAUDE.md).

## Project Overview

pyclifer (**PY**thon **C**ommand **L**ine **I**nterface **F**ram**E**wo**R**k) is a decorator-driven CLI framework built on
top of `click-extra` and `rich-click`. It provides four main decorators (`@app_group`, `@group`,
`@command`, `@option`) that give CLI applications automatic configuration management, environment
variable binding, Rich-enhanced logging, global option propagation, and standardized output
formatting.

pyclifer also ships a built-in project scaffolding tool (`pyclifer project`) that generates
Django-inspired project structures for CLI applications.

## Context

pyclifer is a migration and clean rewrite of `recia-cli` (private GitLab project). All the core
framework logic has been ported over with the following improvements:

- Clean public API exposed exclusively through `pyclifer.__init__` with `__all__`
- `core/` internals are never imported directly by users — always via `from pyclifer import ...`
- Built-in scaffolding CLI (`pyclifer project init / add app / add command / add integration`)
- Framework dogfoods its own pattern — scaffolding lives in `src/pyclifer/apps/project/`

## Working Style

Respond in **French** in all conversational messages. Keep English for all code, comments,
docstrings, commit messages, and documentation files.

Before modifying any file, state in one or two sentences:
- **What** you are about to write or change (the substance, not just "update X")
- **Why** — what problem it solves or what behaviour it enables

Do this even for small edits. Skip it only when the change was explicitly dictated by the
user (e.g., "replace line 12 with …") and there is nothing non-obvious to explain.

### Verify behaviour, never assume it

Before stating how a dependency (click, click-extra, rich-click, cloup) or existing code behaves,
and before deciding that something needs fixing or not, reproduce the use case and base the
decision on what it prints. Use a throwaway script in the scratchpad, outside the repository.

- Test the exact scenario the code will meet, plus its neighbours (bare call, `--help`, explicit
  subcommand, with and without a config file), not only the case that motivated the change.
- Specs, docs and messages state only what was measured. Mark anything untested as untested, and
  test it before implementing the item that depends on it.
- When a measurement contradicts a spec or an earlier statement, say so and correct the spec in
  the same commit.
- Measure each case in its own process. Logging is global to the process: the first console
  handler counts as "already configured", so several apps in one process leak into each other and
  a "defect" or a "pass" can be an artifact. Compare against `main` (a `git worktree` of it) to
  tell a regression from existing behaviour.
- `invoke()` and `CliRunner` capture stdout and stderr, so a `print` inside a command is lost:
  collect into a list and print after the run. The secrets filter works on key names, so a
  free-text probe proves nothing unless `mask_free_text=True`. Printing a class name hides its
  inheritance. In zsh, `for c in "a b"` does not split `$c`. Scripts importing `tests.*` need
  `PYTHONPATH=.`.

### Design principles

Decisions the maintainer has stated; follow them and raise a conflict instead of deciding silently.

- A framework raises an explicit, actionable error, never a raw `AttributeError` or `KeyError`
  from its internals. The message names the expected shape.
- The output contract holds on failure: with `--output-format json` or `yaml`, stdout stays valid
  structured output even when the failure happens while rendering, not only inside the command.
  Code that can raise after the command returns goes through the same failure `Response` handling.
- `@app_group` is the base of an application and the only place that initialises it (logging).
  `@group()` must not. Declaration order stays free: `cli.py` imports its subgroups before it
  writes `@app_group()`.
- Rich and plain help paths never behave differently.
- Breaking changes are acceptable before 1.0.
- For a design choice, give a recommendation, and compare with other CLI frameworks (Typer,
  Cement, Click) by observing them or citing their documentation, not from memory.
- Fix a defect in the same branch as soon as it is found, after the maintainer chooses between
  fixing it, documenting it, or deferring it. Each fix has a failing test first and its own commit.

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

All public symbols are exposed through `src/pyclifer/__init__.py` with `__all__`.
Users always import from `pyclifer` directly — never from `pyclifer.core.*`:

```python
from pyclifer import app_group, group, command, option
from pyclifer import BaseContext, Response, get_logger
```

### Core Design Patterns

- **Decorator-driven**: Four decorators in `src/pyclifer/core/decorators.py` wrap Click objects
  with framework features. `@app_group` is the main entry point; `@group` and `@command` add
  subgroups/commands; `@option` extends Click options with env var binding and global propagation.
- **Mixin composition**: Features are split across reusable mixins (`src/pyclifer/core/mixins/`)
  and composed into core classes. This keeps the feature surface modular.
- **Context-based output dispatch**: `BaseContext` (context.py) combines `RichHelpersMixin` +
  `OutputFormatMixin`. All output goes through `ctx.print_result_based_on_format()`, which
  dispatches to JSON/YAML/Table/Rich/Raw formatters based on the `--output-format` flag stored
  in `ctx.meta`.
- **Global option propagation**: Options marked `is_global=True` via `PycliferOption` are
  automatically propagated from parent groups to all subcommands via `GlobalOptionsMixin`.
- **Automatic response handling**: `handle_response=True` on `@app_group` automatically wraps
  all commands (including those added via `add_command()` and nested subgroups) with
  `returns_response`, which intercepts `Response` return values and prints them.

### Key Modules

| Module                     | Responsibility                                                                            |
|----------------------------|-------------------------------------------------------------------------------------------|
| `core/decorators.py`       | The four public decorators + `GroupDecorator` class + `returns_response`                  |
| `core/classes.py`          | `PycliferOption`, `PycliferExtraGroup`/`PycliferRichGroup`, `CustomConfigOption`, `GroupConfig` |
| `core/context.py`          | `BaseContext` — composites RichHelpersMixin + OutputFormatMixin                           |
| `core/mixins/cli.py`       | `GlobalOptionsMixin`, `StoreInMetaMixin`                                                  |
| `core/mixins/response.py`  | `HandleResponseMixin` — auto-wraps commands via `command()` and `add_command()`           |
| `core/mixins/output.py`    | `OutputFormatMixin` — dispatches to JSON/YAML/Table/Rich/Raw, `_FallbackEncoder` for JSON |
| `core/mixins/rich.py`      | `RichHelpersMixin` — Rich console helpers: panels, rules, status spinners, prompts        |
| `core/output/responses.py` | `Response` dataclass: `(success, message, data, error_code)` + table/rich callbacks       |
| `core/output/tables.py`    | `CliTable`, `CliTableColumn`, `ExceptionTable`                                            |
| `core/log/`            | Rich-enhanced logging, custom `TRACE` level (5), `SecretsMasker`, `get_logger()` factory  |
| `apps/project/`            | Scaffolding CLI — `pyclifer project init / add app / add command / add integration`         |

### Internal structure

```
src/pyclifer/
├── __init__.py             # public API — __all__ + re-exports from core/
├── cli.py                  # pyclifer CLI entry point (dogfoods apps/ pattern)
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

Projects generated by `pyclifer project init` follow this convention:

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

`tests/integration/` runs every pyclifer feature in a real application (spec 15). Features are
discovered by introspection (`inventory.py`: `GroupConfig` fields, option factories, `pyclifer.__all__`,
framework events) and each one must appear in `scenarios.py` as `COVERED` (a test that exercises it) or
`EXCLUDED` (a stated reason). Adding a `GroupConfig` field, option factory, public symbol or event without
declaring it there fails `test_inventory.py`. `PENDING` stays empty. Measure the behaviour in a fresh
process before writing the expectation; a defect found this way gets its own failing test and commit.
The full suite takes about 26 s without coverage (about 48 s with the default coverage options), of
which about 17 s is `tests/integration/`.

## Versioning

Managed with `bumpversion`. Version is synced across `pyproject.toml`, `README.md`, and
`src/pyclifer/__init__.py`. Commits follow conventional commits with emoji prefixes
(e.g., `✨ feat`, `🐛 fix`, `♻️ refactor`).

Releases are published to PyPI by `.github/workflows/release.yml` through GitHub Actions OIDC
(trusted publishing), with no API token. This depends on the Trusted Publisher being configured
on pypi.org for this repository, which the repository files cannot show.

### Documentation review before a bump

Before running `bumpversion` (or when the user announces a release), run the `doc-review`
skill and report its findings **before** bumping. The bump commit tags the release and
regenerates `CHANGELOG.md`, so documentation fixes must land first.

- `doc-review` is a read-only audit: list the inconsistencies found, fix nothing until the
  user agrees, and put the fixes on a dedicated branch with their own commit.
- Do not bump while documentation findings are still open, unless the user explicitly says so.
- graphify does not track documentation (only code is refreshed by its commit hook), so never
  use the knowledge graph as evidence that the docs are up to date.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
