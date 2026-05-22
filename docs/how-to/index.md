# How-to Guides

Task-oriented recipes for common pyclif patterns. Each guide shows the minimum code needed to
accomplish a specific goal — start here when you know what you want to build.

For conceptual explanations and full API reference, see the [User Guide](../output-formatting.md)
and [API Reference](../api/decorators.md).

## Guides

### [Response Patterns](response-patterns.md)

Wire together a model, interface, renderer, and command in the simplest possible form. This is
the foundational pattern every pyclif app follows — read this first.

### [Rich Progressive Output](rich-progressive-output.md)

Stream results to the terminal as they arrive, with live spinners, progress bars, and a summary
panel on completion. Covers the full chain: an interface that yields `OperationResult` objects,
a renderer with Live hooks, and the `Response.from_stream()` wiring in the command.

### [Multi-integration Commands](multi-integration-commands.md)

Build a command that coordinates two or more interfaces — for example, creating a user and
immediately assigning it a role. Shows how to inject multiple interfaces via context, aggregate
their results, and handle partial failures cleanly.

### [Error Handling](error-handling.md)

Two recipes side by side: errors in the interface layer via `OperationResult.error()` (the
standard pattern), and direct `Response(success=False, error_code=...)` for lightweight commands
that do not use an interface.

### [Choosing an Output Format](output-format.md)

A practical decision guide: which `--output-format` value to use depending on whether the
consumer is a human, a shell script, a CI pipeline, or an interactive terminal session.