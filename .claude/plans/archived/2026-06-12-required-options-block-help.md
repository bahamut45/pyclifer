# Required Options Block --help on Subcommands — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `app_group` defines `required=True` context options, running `--help` on any subcommand must show help instead of raising `Missing option`.

**Architecture:** Two guards added to `custom_make_context` in `_patch_make_context`. Pre-call: detect `--help`/`-h` after the subcommand boundary and inject `resilient_parsing=True` into the context kwargs so Click skips required-option validation. Post-call: skip `context_factory` when `resilient_parsing` is active (factory would receive `None` for all required options and likely blow up).

**Tech Stack:** Python 3.10+, click-extra, pyclifer `GroupDecorator._patch_make_context`

---

### Task 1: Failing tests — resilient_parsing short-circuit

**Files:**
- Modify: `tests/core/test_decorators.py`

Tests live in a new class `TestHelpShortCircuit` appended after the existing `TestContextFactoryBehavior` block (~line 1197).

- [ ] **Step 1: Write the failing tests**

Append after the last test class in `tests/core/test_decorators.py`:

```python
# ---------------------------------------------------------------------------
# Help short-circuit — required options must not block subcommand --help
# ---------------------------------------------------------------------------


class TestHelpShortCircuit:
    """required=True options on app_group must not block subcommand --help."""

    def _make_app(self, with_factory: bool = False):
        """Build a test app with required context options and a subcommand."""
        captured: dict = {}

        factory = None
        if with_factory:
            class _Ctx:
                """Context."""
                def __init__(self, host=None, **kwargs):
                    self.host = host

            factory = _Ctx

        @_minimal_app_group(context_factory=factory, invoke_without_command=True)
        @option("--host", required=True, context=True, default=None)
        @click.pass_context
        def app(ctx, host):
            """App."""
            captured["host"] = host

        @app.command()
        @click.pass_context
        def serve(ctx):
            """Serve."""

        @app.group()
        @click.pass_context
        def infra(ctx):
            """Infra."""

        @infra.command()
        @click.pass_context
        def status(ctx):
            """Status."""

        return app, captured

    def test_subcommand_help_does_not_raise_missing_option(self):
        """--help on a direct subcommand exits 0 even when required option absent."""
        app, _ = self._make_app()
        runner = CliRunner()
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0, result.output
        assert "Missing option" not in result.output

    def test_subcommand_help_short_flag_works(self):
        """-h on a direct subcommand exits 0 even when required option absent."""
        app, _ = self._make_app()
        runner = CliRunner()
        result = runner.invoke(app, ["serve", "-h"])
        assert result.exit_code == 0, result.output
        assert "Missing option" not in result.output

    def test_nested_subcommand_help_does_not_raise(self):
        """--help on a nested subcommand exits 0 even when required option absent."""
        app, _ = self._make_app()
        runner = CliRunner()
        result = runner.invoke(app, ["infra", "status", "--help"])
        assert result.exit_code == 0, result.output
        assert "Missing option" not in result.output

    def test_normal_invocation_still_validates_required(self):
        """Without --help, a missing required option still raises MissingParameter."""
        app, _ = self._make_app()
        runner = CliRunner()
        result = runner.invoke(app, ["serve"])
        assert result.exit_code != 0
        assert "Missing option '--host'" in result.output

    def test_context_factory_not_called_during_help(self):
        """context_factory is not called when resilient_parsing is active (help mode)."""
        call_count: list = []

        @_minimal_app_group(context_factory=lambda **kw: call_count.append(1) or object(),
                            invoke_without_command=True)
        @option("--host", required=True, context=True, default=None)
        @click.pass_context
        def app(ctx, host):
            """App."""

        @app.command()
        @click.pass_context
        def serve(ctx):
            """Serve."""

        runner = CliRunner()
        runner.invoke(app, ["serve", "--help"])
        assert call_count == []

    def test_help_flag_before_boundary_still_shows_root_help(self):
        """--help placed before any subcommand shows root help (no change to existing behaviour)."""
        app, _ = self._make_app()
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0, result.output
```

- [ ] **Step 2: Run to confirm tests fail**

```bash
python -m pytest tests/core/test_decorators.py::TestHelpShortCircuit -v --no-cov
```

Expected: 5–6 FAILED (exit code ≠ 0, "Missing option" in output for the help tests).

---

### Task 2: Implementation — pre-call guard in `_patch_make_context`

**Files:**
- Modify: `src/pyclifer/core/decorators.py:190-215` (pre-call section of `custom_make_context`)

The fix adds one concern to the pre-call block and one guard to the post-call block.

- [ ] **Step 1: Add Concern 0 — help short-circuit (pre-call)**

In `custom_make_context`, insert **before** "Concern 1" (line ~192):

```python
            # Concern 0 — help short-circuit: if --help/-h appears after the
            # subcommand boundary, set resilient_parsing so Click skips required
            # option validation on the root group (issue #5).
            if parent is None and args:
                boundary = GroupDecorator._find_subcommand_boundary(args, f)
                if boundary < len(args):
                    after_boundary = args[boundary:]
                    if "--help" in after_boundary or "-h" in after_boundary:
                        extra["resilient_parsing"] = True
```

- [ ] **Step 2: Guard `context_factory` against resilient_parsing (post-call)**

In the post-call section, find Concern 5 (~line 236):

```python
            # Concern 5 — context_factory: build ctx.obj from context=True param values
            if parent is None and self.config.context_factory is not None:
```

Replace the condition with:

```python
            # Concern 5 — context_factory: build ctx.obj from context=True param values.
            # Skip during resilient_parsing (help mode) — params are None and factory
            # would fail on required fields.
            if parent is None and self.config.context_factory is not None and not ctx.resilient_parsing:
```

- [ ] **Step 3: Run the new tests to confirm they pass**

```bash
python -m pytest tests/core/test_decorators.py::TestHelpShortCircuit -v --no-cov
```

Expected: all PASSED.

- [ ] **Step 4: Run the full suite to check for regressions**

```bash
python -m pytest tests/ -v --no-cov
```

Expected: all previously passing tests still pass.

- [ ] **Step 5: Lint**

```bash
ruff check src/pyclifer/core/decorators.py tests/core/test_decorators.py
ruff format src/pyclifer/core/decorators.py tests/core/test_decorators.py
```

Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add src/pyclifer/core/decorators.py tests/core/test_decorators.py
git commit -m "🐛 fix(decorators): skip required-option validation when subcommand requests --help

- required=True context options on app_group blocked --help on subcommands
- detect --help/-h after the subcommand boundary in custom_make_context and
  inject resilient_parsing=True so Click skips required-option validation
- guard context_factory (Concern 5) behind not ctx.resilient_parsing to
  avoid calling factory with None values for required options

Closes #5"
```