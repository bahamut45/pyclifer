# Demo Page Design

**Date:** 2026-06-07
**Status:** Approved

## Goal

Create `docs/demo.md` — a standalone documentation page for new users discovering pyclifer.
The page teaches via two ordered parts: CLI tour first, code walkthrough second.

## Audience

Someone discovering pyclifer for the first time. Not a reference page — a guided introduction.

## Navigation placement

In `mkdocs.yml` nav, between `Examples` and `How-to Guides`:

```yaml
- Examples: examples.md
- Demo App: demo.md          # ← new
- How-to Guides:
    ...
```

## Structure

### Part 1 — CLI Tour

Prerequisites: `pip install pyclifer` only.

Sequence of commands (each with bash block + expected output description + one-line explanation):

1. `pyclifer demo --help` — discover the group and its subgroups
2. `pyclifer demo tasks add --title "Fix login bug" --priority high` — create a task, Rich panel output
3. `pyclifer demo tasks list` — table output (default format)
4. `pyclifer demo tasks list -o json` — same data, machine-readable format
5. `pyclifer demo tasks list --status pending --priority high` — filtering
6. `pyclifer demo tasks show <id>` — single task, Rich detail panel with colored badge
7. `pyclifer demo tasks complete <id>` then same command again — demonstrates error handling (already done)
8. `pyclifer demo tasks sync` — live Rich progress bar while streaming
9. `pyclifer demo tasks sync -o json` — same operation, waits for all results then prints JSON
10. `pyclifer demo users whoami` + `pyclifer demo users list` — second sub-group

### Part 2 — Code Walkthrough

Order: bottom-up (data → renderer → interface → command → core).
Each layer: real code snippet from source + GitHub link + "Dans ton projet" callout (1-2 lines).

Layers:
1. **Structure** — file tree of `apps/demo/`, one-line description per folder
2. **Model** (`apps/tasks/models.py`) — `Task` dataclass with Pydantic validators
3. **Renderer** (`apps/tasks/renderers.py`) — `TaskListRenderer` (declarative fields/columns) + `TaskSyncRenderer` (streaming hooks `rich_setup` / `rich_on_item` / `rich_summary`)
4. **Interface** (`apps/tasks/interfaces.py`) — `TaskInterface`, `list_tasks` (returns `list[OperationResult]`), `sync_tasks` (yields `Iterator[OperationResult]`), error path in `show_task` / `complete_task`
5. **Command** (`apps/tasks/commands/list.py` + `add.py`) — minimal wiring via `respond()`, `@pass_demo_context`, `PaginatedResponse`
6. **Core** (`core/context.py` + `core/storage.py`) — `DemoContext` extending `BaseContext`, `Storage` JSON backend at `~/.config/pyclifer/demo.json`

## Snippets to include

Selected real code extracts (not invented):

- `TaskListRenderer` — `fields`, `columns`, `rich_title`, `success_message`
- `TaskSyncRenderer.rich_setup` + `rich_on_item` + `rich_summary`
- `TaskInterface.list_tasks` return signature
- `TaskInterface.sync_tasks` yield signature
- `TaskInterface.show_task` error path (`OperationResult.error` with `ExitCode.NOT_FOUND`)
- `add` command — full function (short enough, shows full pattern)
- `DemoContext` — `storage` property
- `Storage` — `DATA_PATH` constant + `upsert_task` signature

## Callout pattern

Each code layer ends with an admonition block:

```markdown
!!! tip "Dans ton projet"
    ...
```

Kept to 1-2 lines, pointing to the relevant scaffolding command or concept.

## Out of scope

- `users` app walkthrough (same pattern as tasks — link to source only)
- `commands/__init__.py` wiring details
- `core/options.py` and `core/constants.py` (supporting detail, not primary pattern)
- Full output rendering (covered in how-to guides)