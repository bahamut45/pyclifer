# Demo App

pyclifer ships a built-in demo application — a fully working task manager CLI that exercises
every framework feature. Run it right after installation to see pyclifer in action, then read
the walkthrough below to understand how it is built.

The demo covers:

- Multi-format output (`table`, `json`, `yaml`, `raw`, `rich`)
- Streaming results with a live progress bar
- Error handling via `OperationResult`
- Custom context, persistent JSON storage, filtered listings, pagination

Data is persisted in `~/.config/pyclifer/demo.json`.

## Part 1 — CLI Tour

### Explore the demo group

```bash
pyclifer demo --help
```

You will see two sub-groups (`tasks` and `users`) and the global options inherited from
`@app_group`: `-o` / `--output-format`, `-v` / `--verbosity`, `--config`.

### Create tasks

```bash
pyclifer demo tasks add --title "Fix login bug" --priority high
```

A Rich panel titled **Task added** appears with the new task id and a success message.
Add a few more tasks to work with:

```bash
pyclifer demo tasks add --title "Write docs" --priority low \
    --assignee alice --tags "docs,chore"
pyclifer demo tasks add --title "Deploy to staging" --priority medium \
    --due 2026-06-30
```

### List tasks

```bash
pyclifer demo tasks list
```

Output: a Rich table with columns `id`, `title`, `priority`, `status`, `due_date`, `assignee`.
This is the default `table` format set by the renderer.

Switch to JSON for machine-readable output:

```bash
pyclifer demo tasks list -o json
```

```json
{
  "success": true,
  "message": "Tasks retrieved successfully.",
  "data": {
    "results": [
      {
        "id": "3f2a…",
        "title": "Fix login bug",
        "priority": "high",
        "status": "open",
        "due_date": null,
        "assignee": ""
      }
    ]
  },
  "page": 1,
  "limit": 20,
  "total": 3
}
```

Filter by status or priority:

```bash
pyclifer demo tasks list --priority high
pyclifer demo tasks list --status open --priority high
```

## Part 2 — Code Walkthrough

<!-- walkthrough sections go here -->
