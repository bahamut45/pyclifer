# Choosing an Output Format

`--output-format` (or `-o`) controls how every command renders its result. The right choice
depends on who — or what — is consuming the output.

For the full API reference (renderers, dispatch mechanics, `--output-filter`), see
[Output Formatting — User Guide](../output-formatting.md).

## Quick reference

| Consumer | Format | Why |
|---|---|---|
| Human at terminal | `table` (default) | Aligned columns, readable at a glance |
| Human, detail view | `rich` | Colors, panels, live streaming output |
| Shell script / `jq` | `raw` | Single-line compact JSON, no highlighting |
| Specific field in a script | `raw -f <key>` | Extracts one value as plain text |
| Pretty-printed JSON | `json` | Syntax-highlighted, indented — for reading |
| YAML consumer / config | `yaml` | Syntax-highlighted YAML |
| One-line log message | `text` | Prints `response.message` only |

## table — the default

Best for humans scanning results interactively. Columns are defined by the renderer.

```bash
pyclif demo tasks list
pyclif demo tasks list -o table   # explicit, same result
```

```
                                     Tasks
╭─────────────────┬───────────────┬──────────┬────────┬──────────┬──────────╮
│ Id              │ Title         │ Priority │ Status │ Due Date │ Assignee │
├─────────────────┼───────────────┼──────────┼────────┼──────────┼──────────┤
│ a2506054-1216-… │ Test task     │ high     │ open   │ N/A      │          │
╰─────────────────┴───────────────┴──────────┴────────┴──────────┴──────────╯
```

## rich — detailed human output

Use for detail views, streaming operations, or when the renderer overrides `rich()` to display
panels, grids, or progress bars.

```bash
pyclif demo tasks show <task-id> -o rich
pyclif demo tasks sync -o rich        # live progress bar while streaming
```

`rich` is the only format that displays live output during streaming. Every other format
buffers all results first.

## raw — shell scripting and piping

Single-line compact JSON — no indentation, no syntax highlighting. Use when the output feeds
another command.

```bash
pyclif demo tasks list -o raw
```

```
{"success": true, "message": "Tasks retrieved successfully.", "error_code": null, "data": {"results": [{"id": "a2506054…", "title": "Test task", ...}]}}
```

Pipe to `jq` to extract values:

```bash
# without -o raw (table output) — jq sees nothing useful
$ pyclif demo tasks list | jq '.data.results[].title'
parse error (Invalid numeric literal at EOF on line 1)

# with -o raw — jq gets valid JSON
$ pyclif demo tasks list -o raw | jq -r '.data.results[].title'
Test task
Fix login bug
E2E test
Show test
Rich test
```

Check command success in a script:

```bash
output=$(pyclif demo tasks show "$id" -o raw)
if [ "$(echo "$output" | jq -r .success)" = "false" ]; then
    echo "Error: $(echo "$output" | jq -r .message)" >&2
    exit 1
fi
task_title=$(echo "$output" | jq -r '.data.results[0].title')
```

### Extracting a single value with `-f`

`-f` (or `--output-filter`) extracts one field and prints it as plain text — no JSON, no
quotes. Useful when the value feeds directly into a shell variable or another command.

```bash
# without -f — you get the full JSON and must parse it
$ pyclif demo tasks list -o raw | jq -r '.data.results[0].title'
Test task

# with -f — plain value, no parsing needed
$ pyclif demo tasks list -o raw -f results.0.title
Test task

# capture into a variable in one step
title=$(pyclif demo tasks list -o raw -f results.0.title)

# pipe the id directly to another command
pyclif demo tasks list -o raw -f results.0.id | xargs pyclif demo tasks show
```

Nested paths use dot notation. Numeric segments are list indices; negative indices count from
the end (`results.-1.id` = last item).

## json — pretty-printed JSON for reading

Indented and syntax-highlighted. Same data as `raw` but formatted for human inspection.
Still valid JSON — tools like `jq` parse it correctly.

```bash
pyclif demo tasks list -o json
```

```json
{
  "success": true,
  "message": "Tasks retrieved successfully.",
  "error_code": null,
  "data": {
    "results": [
      {
        "id": "a2506054-1216-4a30-9e2d-dd0f0207561b",
        "title": "Test task",
        "priority": "high",
        "status": "open",
        "due_date": null,
        "assignee": ""
      }
    ]
  }
}
```

```bash
# jq works on json too, but raw is faster in scripts (no indentation overhead)
pyclif demo tasks list -o json | jq -r '.data.results[].title'
```

## yaml — YAML consumers and config generation

Use when the output feeds a YAML-aware tool or when you want a structured human-readable
format without JSON punctuation.

```bash
pyclif demo tasks list -o yaml
pyclif demo tasks list -o yaml > tasks-snapshot.yml
```

```yaml
success: true
message: Tasks retrieved successfully.
error_code: null
data:
  results:
    - id: a2506054-1216-4a30-9e2d-dd0f0207561b
      title: Test task
      priority: high
      status: open
```

## text — one-line message

Prints `response.message` only. Use for simple status lines in logs or wrapper scripts where
structured data is not needed.

```bash
pyclif demo tasks add --title "Fix bug" -o text
# Task 'Fix bug' created.

pyclif demo tasks list -o text
# Tasks retrieved successfully.
```

## Setting a default format

Set the output format via environment variable to avoid passing `-o` on every call. The
variable name follows the pattern `<APP_PREFIX>_OUTPUT_FORMAT`:

```bash
# all commands use JSON in this shell session
export PYCLIF_DEMO_OUTPUT_FORMAT=json
pyclif demo tasks list          # outputs JSON without -o json
pyclif demo tasks add --title …  # also outputs JSON
```

Or set a permanent default in a config file:

```toml
# ~/.config/myapp/config.toml
output-format = "raw"
```

## See also

- [Output Formatting — User Guide](../output-formatting.md) — renderer API, dispatch mechanics, filter path reference
- [Response Patterns](response-patterns.md) — how `fields` and `columns` control what each format includes