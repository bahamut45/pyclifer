# Context Options Visible in Subcommand Help — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `context=True` options declared on `@app_group` visible in subcommand `--help` output in a dedicated panel, with per-option opt-out and a configurable panel name.

**Architecture:** Three layers of change. (1) `PycliferOption` gains `show_in_subcommand_help: bool = True`; `GroupConfig` gains `context_options_panel: str`. (2) `GroupDecorator._apply_click_group` stores the panel name on the group instance; `@option` forwards the new flag. (3) `GlobalOptionsMixin` gains `_get_context_option_display_copy` + `_propagate_context_options` and calls them from `add_command`. Display copies carry `expose_value=False`, `required=False`, `context=False`, and `rich_help_panel` so they appear in help but never affect callbacks or validation. The panel is absent when no qualifying option exists.

**Tech Stack:** Python 3.10+, click-extra, rich-click, pytest

---

## File Map

| Action  | Path                                        | What changes                                                         |
|---------|---------------------------------------------|----------------------------------------------------------------------|
| Modify  | `src/pyclifer/core/classes.py`              | `PycliferOption.__init__` + `GroupConfig.context_options_panel`      |
| Modify  | `src/pyclifer/core/decorators.py`           | `@option` forwards `show_in_subcommand_help`; `_apply_click_group` stores `_context_options_panel` |
| Modify  | `src/pyclifer/core/mixins/cli.py`           | `CONTEXT_OPTIONS_PANEL` constant + two new methods + updated `add_command` |
| Modify  | `tests/core/test_classes.py`               | Tests for `show_in_subcommand_help` + `context_options_panel`        |
| Create  | `tests/core/mixins/test_cli.py`            | All mixin tests                                                      |
| Modify  | `tests/core/test_decorators.py`            | Test `show_in_subcommand_help` forwarding through `@option`          |

---

### Task 1: `PycliferOption.show_in_subcommand_help` + `GroupConfig.context_options_panel`

**Files:**
- Modify: `src/pyclifer/core/classes.py`
- Modify: `tests/core/test_classes.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/core/test_classes.py`:

```python
# ---------------------------------------------------------------------------
# PycliferOption — show_in_subcommand_help attribute
# ---------------------------------------------------------------------------


class TestPycliferOptionShowInSubcommandHelp:
    """PycliferOption stores show_in_subcommand_help correctly."""

    def test_show_in_subcommand_help_defaults_to_true(self):
        """show_in_subcommand_help defaults to True when not passed."""
        opt = PycliferOption(["--host"])
        assert opt.show_in_subcommand_help is True

    def test_show_in_subcommand_help_false_is_stored(self):
        """show_in_subcommand_help=False is stored on the instance."""
        opt = PycliferOption(["--host"], show_in_subcommand_help=False)
        assert opt.show_in_subcommand_help is False

    def test_show_in_subcommand_help_independent_from_context(self):
        """show_in_subcommand_help and context are independent attributes."""
        opt = PycliferOption(["--host"], context=True, show_in_subcommand_help=False)
        assert opt.context is True
        assert opt.show_in_subcommand_help is False


# ---------------------------------------------------------------------------
# GroupConfig — context_options_panel attribute
# ---------------------------------------------------------------------------


class TestGroupConfigContextOptionsPanel:
    """GroupConfig stores context_options_panel correctly."""

    def test_context_options_panel_has_default(self):
        """context_options_panel has a non-empty default string."""
        cfg = GroupConfig()
        assert isinstance(cfg.context_options_panel, str)
        assert len(cfg.context_options_panel) > 0

    def test_context_options_panel_custom_value(self):
        """context_options_panel accepts a custom string."""
        cfg = GroupConfig(context_options_panel="Connection")
        assert cfg.context_options_panel == "Connection"
```

- [ ] **Step 2: Run to verify they fail**

```bash
python -m pytest tests/core/test_classes.py::TestPycliferOptionShowInSubcommandHelp tests/core/test_classes.py::TestGroupConfigContextOptionsPanel -v
```

Expected: `AttributeError` — attributes do not exist yet.

- [ ] **Step 3: Implement in `classes.py`**

In `PycliferOption.__init__`, add `show_in_subcommand_help: bool = True`:

```python
    def __init__(
        self,
        *args: Any,
        is_global: bool = False,
        context: bool = False,
        show_in_subcommand_help: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize the option.

        Args:
            *args: Positional arguments for click.Option.
            is_global: If True, this option will be propagated to subcommands.
            context: If True, this option feeds ctx.obj construction and is
                accepted at any position in the command chain.
            show_in_subcommand_help: If True and context=True, this option is
                shown in subcommand --help under a dedicated panel.
            **kwargs: Keyword arguments for click.Option.
        """
        self.is_global = is_global
        self.context = context
        self.show_in_subcommand_help = show_in_subcommand_help
        super().__init__(*args, **kwargs)
```

In `GroupConfig` (after `context_factory`), add:

```python
    # Context options help panel
    context_options_panel: str = "Context Options (anywhere-passable)"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/core/test_classes.py::TestPycliferOptionShowInSubcommandHelp tests/core/test_classes.py::TestGroupConfigContextOptionsPanel -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pyclifer/core/classes.py tests/core/test_classes.py
git commit -m "✨ feat(classes): add show_in_subcommand_help to PycliferOption and context_options_panel to GroupConfig"
```

---

### Task 2: Forward `show_in_subcommand_help` through `@option` + store panel on group

**Files:**
- Modify: `src/pyclifer/core/decorators.py`
- Modify: `tests/core/test_decorators.py`

- [ ] **Step 6: Write failing tests**

Append to `tests/core/test_decorators.py`:

```python
class TestOptionShowInSubcommandHelp:
    """@option forwards show_in_subcommand_help to PycliferOption."""

    def test_show_in_subcommand_help_defaults_to_true(self):
        """show_in_subcommand_help defaults to True on the resulting param."""
        import click

        @option("--host", context=True)
        @click.command()
        def cmd(host):
            pass

        param = next(p for p in cmd.params if p.name == "host")
        assert getattr(param, "show_in_subcommand_help", None) is True

    def test_show_in_subcommand_help_false_forwarded(self):
        """show_in_subcommand_help=False is forwarded to the underlying PycliferOption."""
        import click

        @option("--host", context=True, show_in_subcommand_help=False)
        @click.command()
        def cmd(host):
            pass

        param = next(p for p in cmd.params if p.name == "host")
        assert getattr(param, "show_in_subcommand_help", None) is False


class TestGroupDecoratorContextOptionsPanel:
    """GroupDecorator stores context_options_panel on the created group."""

    def test_default_panel_name_stored_on_group(self):
        """Group gets _context_options_panel equal to GroupConfig default."""
        from pyclifer import app_group

        @app_group()
        def myapp():
            pass

        assert hasattr(myapp, "_context_options_panel")
        assert len(myapp._context_options_panel) > 0

    def test_custom_panel_name_stored_on_group(self):
        """Custom context_options_panel value is stored on the group."""
        from pyclifer import app_group

        @app_group(context_options_panel="Connection")
        def myapp():
            pass

        assert myapp._context_options_panel == "Connection"
```

- [ ] **Step 7: Run to verify they fail**

```bash
python -m pytest tests/core/test_decorators.py::TestOptionShowInSubcommandHelp tests/core/test_decorators.py::TestGroupDecoratorContextOptionsPanel -v
```

Expected: `AttributeError` — `show_in_subcommand_help` not forwarded, `_context_options_panel` not stored.

- [ ] **Step 8: Update `@option` in `decorators.py`**

Current signature (line ~626):
```python
def option(
    *param_decls: str,
    is_global: bool = False,
    context: bool = False,
    show_envvar: bool = True,
    store_in_meta: bool = False,
    **kwargs: Any,
) -> Callable[[Callable], Callable]:
```

Replace with:
```python
def option(
    *param_decls: str,
    is_global: bool = False,
    context: bool = False,
    show_in_subcommand_help: bool = True,
    show_envvar: bool = True,
    store_in_meta: bool = False,
    **kwargs: Any,
) -> Callable[[Callable], Callable]:
    """Create a Click option with global propagation support.

    Ensures a consistent environment variable display and allows options
    to be marked as global to be available on all subcommands.

    Args:
        *param_decls: Parameter declarations for the option.
        is_global: If True, the option is propagated to all subcommands.
        context: If True, the option feeds ctx.obj construction and is accepted
            at any position in the command chain.
        show_in_subcommand_help: If True and context=True, this option is shown
            in subcommand --help under a dedicated panel.
        show_envvar: Show environment variables in the help output.
        store_in_meta: If True, stores the option value in ctx.meta automatically.
        **kwargs: Additional arguments passed to click_extra.option().

    Returns:
        Option decorator function.
    """
```

In the body, where `context` is forwarded (line ~657), also forward `show_in_subcommand_help`:

```python
    # Only forward context/show_in_subcommand_help to classes that declare the attribute.
    if isinstance(cls, type) and issubclass(cls, PycliferOption):
        kwargs["context"] = context
        kwargs["show_in_subcommand_help"] = show_in_subcommand_help
```

- [ ] **Step 9: Update `_apply_click_group` in `GroupDecorator`**

Current (line ~146):
```python
    def _apply_click_group(self, f: Callable) -> click_extra.Group:
        """Apply the final Click group decorator using the custom PycliferGroup class."""
        if self.config.use_rich_help:
            self.click_kwargs["cls"] = PycliferRichGroup
            group_decorator = rich_group_decorator
        else:
            self.click_kwargs["cls"] = PycliferExtraGroup
            group_decorator = click_extra.group

        if self.config.name:
            self.click_kwargs["name"] = self.config.name
        return group_decorator(**self.click_kwargs)(f)
```

Replace the last line:
```python
        if self.config.name:
            self.click_kwargs["name"] = self.config.name
        result = group_decorator(**self.click_kwargs)(f)
        result._context_options_panel = self.config.context_options_panel
        return result
```

- [ ] **Step 10: Run tests**

```bash
python -m pytest tests/core/test_decorators.py::TestOptionShowInSubcommandHelp tests/core/test_decorators.py::TestGroupDecoratorContextOptionsPanel -v
```

Expected: all 4 tests PASS.

- [ ] **Step 11: Commit**

```bash
git add src/pyclifer/core/decorators.py tests/core/test_decorators.py
git commit -m "✨ feat(decorators): forward show_in_subcommand_help and store context_options_panel on group"
```

---

### Task 3: `_get_context_option_display_copy` in `GlobalOptionsMixin`

**Files:**
- Modify: `src/pyclifer/core/mixins/cli.py`
- Create: `tests/core/mixins/test_cli.py`

- [ ] **Step 12: Write failing tests**

Create `tests/core/mixins/test_cli.py`:

```python
"""Tests for GlobalOptionsMixin — context option display propagation."""

import click_extra

from pyclifer.core.classes import PycliferOption
from pyclifer.core.mixins.cli import CONTEXT_OPTIONS_PANEL, GlobalOptionsMixin


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Group(GlobalOptionsMixin, click_extra.Group):
    pass


def _make_context_opt(name: str = "--host", **kwargs) -> PycliferOption:
    return PycliferOption([name], context=True, **kwargs)


# ---------------------------------------------------------------------------
# _get_context_option_display_copy
# ---------------------------------------------------------------------------


class TestGetContextOptionDisplayCopy:
    """_get_context_option_display_copy returns a correctly configured display copy."""

    def test_expose_value_is_false(self):
        """Display copy has expose_value=False so it is not injected into callback kwargs."""
        opt = _make_context_opt()
        result = GlobalOptionsMixin._get_context_option_display_copy(opt, CONTEXT_OPTIONS_PANEL)
        assert result.expose_value is False

    def test_required_is_false(self):
        """Display copy has required=False so subcommand does not fail if option absent."""
        opt = _make_context_opt(required=True)
        result = GlobalOptionsMixin._get_context_option_display_copy(opt, CONTEXT_OPTIONS_PANEL)
        assert result.required is False

    def test_rich_help_panel_set_to_given_name(self):
        """Display copy has rich_help_panel equal to the given panel_name."""
        opt = _make_context_opt()
        result = GlobalOptionsMixin._get_context_option_display_copy(opt, "My Panel")
        assert result.rich_help_panel == "My Panel"

    def test_context_attr_is_false(self):
        """Display copy has context=False so prescan ignores it on subcommands."""
        opt = _make_context_opt()
        result = GlobalOptionsMixin._get_context_option_display_copy(opt, CONTEXT_OPTIONS_PANEL)
        assert result.context is False

    def test_name_preserved(self):
        """Display copy retains the same param name as the original."""
        opt = _make_context_opt("--pool")
        result = GlobalOptionsMixin._get_context_option_display_copy(opt, CONTEXT_OPTIONS_PANEL)
        assert result.name == "pool"

    def test_original_is_not_mutated(self):
        """Original option attributes are unchanged after creating a display copy."""
        opt = _make_context_opt(required=True)
        GlobalOptionsMixin._get_context_option_display_copy(opt, CONTEXT_OPTIONS_PANEL)
        assert opt.required is True
        assert opt.expose_value is True
        assert opt.context is True
```

- [ ] **Step 13: Run to verify they fail**

```bash
python -m pytest tests/core/mixins/test_cli.py::TestGetContextOptionDisplayCopy -v
```

Expected: `ImportError` — `CONTEXT_OPTIONS_PANEL` and `_get_context_option_display_copy` do not exist yet.

- [ ] **Step 14: Implement in `cli.py`**

Add `import copy` and the constant at the top of `src/pyclifer/core/mixins/cli.py`:

```python
"""CLI-related mixins for Click options and groups."""

import copy
from typing import Any

import click_extra

from pyclifer.core.callbacks import get_meta_storing_callback

CONTEXT_OPTIONS_PANEL = "Context Options (anywhere-passable)"
```

Add this static method inside `GlobalOptionsMixin`, before `_propagate_global_options`:

```python
    @staticmethod
    def _get_context_option_display_copy(
        opt: click_extra.Parameter, panel_name: str
    ) -> click_extra.Parameter:
        """Create a display-only copy of a context option for subcommand help panels.

        The copy is configured so it appears in a dedicated help panel but is
        never parsed into callback kwargs and never blocks execution when absent.

        Args:
            opt: The original context option to copy.
            panel_name: The rich_help_panel label to set on the copy.

        Returns:
            A shallow copy with expose_value=False, required=False,
            context=False, and rich_help_panel set to panel_name.
        """
        display = copy.copy(opt)
        display.expose_value = False
        display.required = False
        if hasattr(display, "context"):
            display.context = False
        display.rich_help_panel = panel_name
        return display
```

- [ ] **Step 15: Run tests**

```bash
python -m pytest tests/core/mixins/test_cli.py::TestGetContextOptionDisplayCopy -v
```

Expected: all 6 tests PASS.

- [ ] **Step 16: Commit**

```bash
git add src/pyclifer/core/mixins/cli.py tests/core/mixins/test_cli.py
git commit -m "✨ feat(mixins): add CONTEXT_OPTIONS_PANEL and _get_context_option_display_copy"
```

---

### Task 4: `_propagate_context_options` + updated `add_command`

**Files:**
- Modify: `src/pyclifer/core/mixins/cli.py`
- Modify: `tests/core/mixins/test_cli.py`

- [ ] **Step 17: Write failing tests**

Append to `tests/core/mixins/test_cli.py`:

```python
# ---------------------------------------------------------------------------
# _propagate_context_options
# ---------------------------------------------------------------------------


class TestPropagateContextOptions:
    """_propagate_context_options injects display copies into subcommands."""

    def test_display_copy_added_to_direct_subcommand(self):
        """A context option is added to a subcommand that has no such param yet."""
        group = _Group(name="root")
        opt = _make_context_opt("--host")

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        group._propagate_context_options(sub, [opt], CONTEXT_OPTIONS_PANEL)

        assert any(p.name == "host" for p in sub.params)

    def test_display_copy_has_correct_attributes(self):
        """The injected copy has expose_value=False, required=False, context=False."""
        group = _Group(name="root")
        opt = _make_context_opt("--host", required=True)

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        group._propagate_context_options(sub, [opt], CONTEXT_OPTIONS_PANEL)

        injected = next(p for p in sub.params if p.name == "host")
        assert injected.expose_value is False
        assert injected.required is False
        assert injected.context is False
        assert injected.rich_help_panel == CONTEXT_OPTIONS_PANEL

    def test_custom_panel_name_used(self):
        """The panel_name argument is forwarded to the display copy."""
        group = _Group(name="root")
        opt = _make_context_opt("--host")

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        group._propagate_context_options(sub, [opt], "Custom Panel")

        injected = next(p for p in sub.params if p.name == "host")
        assert injected.rich_help_panel == "Custom Panel"

    def test_existing_param_not_duplicated(self):
        """If subcommand already defines the same param name, it is not duplicated."""
        group = _Group(name="root")
        opt = _make_context_opt("--host")

        existing = click_extra.Option(["--host"])
        sub = click_extra.Command("sub", callback=lambda: None, params=[existing])
        group._propagate_context_options(sub, [opt], CONTEXT_OPTIONS_PANEL)

        host_params = [p for p in sub.params if p.name == "host"]
        assert len(host_params) == 1

    def test_recursive_into_nested_subcommand(self):
        """Context options propagate recursively into commands nested inside a group."""
        group = _Group(name="root")
        opt = _make_context_opt("--host")

        leaf = click_extra.Command("leaf", callback=lambda: None, params=[])
        middle = click_extra.Group("middle")
        middle.add_command(leaf)

        group._propagate_context_options(middle, [opt], CONTEXT_OPTIONS_PANEL)

        assert any(p.name == "host" for p in leaf.params)

    def test_command_without_params_attr_skipped_gracefully(self):
        """Commands without a params attribute do not raise."""
        group = _Group(name="root")
        opt = _make_context_opt("--host")

        class _Bare:
            commands = None

        group._propagate_context_options(_Bare(), [opt], CONTEXT_OPTIONS_PANEL)  # must not raise


# ---------------------------------------------------------------------------
# add_command — context option propagation through the public API
# ---------------------------------------------------------------------------


class TestAddCommandContextPropagation:
    """add_command propagates context=True, show_in_subcommand_help=True options."""

    def test_context_option_added_on_add_command(self):
        """add_command injects display copies of qualifying context options."""
        group = _Group(name="root")
        group.params = [_make_context_opt("--host")]
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        group.add_command(sub)

        assert any(p.name == "host" for p in sub.params)

    def test_show_in_subcommand_help_false_skipped(self):
        """Options with show_in_subcommand_help=False are not propagated."""
        group = _Group(name="root")
        group.params = [_make_context_opt("--token", show_in_subcommand_help=False)]
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        group.add_command(sub)

        assert not any(p.name == "token" for p in sub.params)

    def test_context_and_is_global_true_not_double_injected(self):
        """context=True + is_global=True: _propagate_global_options adds it first;
        _propagate_context_options skips it because name already exists."""
        group = _Group(name="root")
        group.params = [PycliferOption(["--resource"], context=True, is_global=True)]
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        group.add_command(sub)

        resource_params = [p for p in sub.params if p.name == "resource"]
        assert len(resource_params) == 1

    def test_no_context_options_leaves_subcommand_unchanged(self):
        """When root has no qualifying context options, subcommand params are not modified."""
        group = _Group(name="root")
        group.params = [PycliferOption(["--verbose"])]
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        original_count = len(sub.params)
        group.add_command(sub)

        assert len(sub.params) == original_count

    def test_panel_name_from_context_options_panel_attr(self):
        """add_command uses _context_options_panel from the group instance."""
        group = _Group(name="root")
        group.params = [_make_context_opt("--host")]
        group._context_options_panel = "Connection"

        sub = click_extra.Command("sub", callback=lambda: None, params=[])
        group.add_command(sub)

        injected = next(p for p in sub.params if p.name == "host")
        assert injected.rich_help_panel == "Connection"
```

- [ ] **Step 18: Run to verify they fail**

```bash
python -m pytest tests/core/mixins/test_cli.py::TestPropagateContextOptions tests/core/mixins/test_cli.py::TestAddCommandContextPropagation -v
```

Expected: `AttributeError` — `_propagate_context_options` does not exist yet.

- [ ] **Step 19: Implement `_propagate_context_options` and update `add_command`**

Add `_propagate_context_options` after `_propagate_global_options` in `GlobalOptionsMixin`:

```python
    def _propagate_context_options(
        self,
        cmd: click_extra.Command,
        context_options: list[click_extra.Parameter],
        panel_name: str,
    ) -> None:
        """Recursively inject display-only copies of context options into a command tree.

        Each copy is configured so it renders in the dedicated help panel but
        never interferes with argument parsing or callback signatures.

        Args:
            cmd: Root of the command tree to receive the display copies.
            context_options: Original context options from the root group.
            panel_name: Label for the rich_help_panel on each display copy.
        """
        if hasattr(cmd, "params"):
            existing_names = {p.name for p in cmd.params}
            for opt in context_options:
                if opt.name not in existing_names:
                    cmd.params.append(self._get_context_option_display_copy(opt, panel_name))

        if hasattr(cmd, "commands") and cmd.commands:
            for subcommand in cmd.commands.values():
                self._propagate_context_options(subcommand, context_options, panel_name)
```

Replace `add_command` with:

```python
    def add_command(self, cmd: click_extra.Command, name: str | None = None, **kwargs: Any) -> None:
        """Register a subcommand and inject global and context options.

        Args:
            cmd: The command to add.
            name: The name to register the command with.
            **kwargs: Additional arguments passed to the parent method.
        """
        # 1. Find global options attached to this group
        global_options = [
            param for param in getattr(self, "params", []) if getattr(param, "is_global", False)
        ]

        # 2. Inject them recursively into the subcommand and all its descendants
        if global_options:
            self._propagate_global_options(cmd, global_options)

        # 3. Find context=True (non-global) options marked for subcommand help
        context_options = [
            param
            for param in getattr(self, "params", [])
            if getattr(param, "context", False)
            and not getattr(param, "is_global", False)
            and getattr(param, "show_in_subcommand_help", True)
        ]
        if context_options:
            panel_name = getattr(self, "_context_options_panel", CONTEXT_OPTIONS_PANEL)
            self._propagate_context_options(cmd, context_options, panel_name)

        super().add_command(cmd, name, **kwargs)  # type: ignore
```

- [ ] **Step 20: Run all mixin tests**

```bash
python -m pytest tests/core/mixins/test_cli.py -v
```

Expected: all tests PASS.

- [ ] **Step 21: Commit**

```bash
git add src/pyclifer/core/mixins/cli.py tests/core/mixins/test_cli.py
git commit -m "✨ feat(mixins): propagate context options as display-only copies in subcommand help"
```

---

### Task 5: Integration test — help output contains the panel

**Files:**
- Modify: `tests/core/mixins/test_cli.py`

- [ ] **Step 22: Append the integration test class**

```python
# ---------------------------------------------------------------------------
# Integration — help text contains the context options panel
# ---------------------------------------------------------------------------


class TestContextOptionsInHelpText:
    """End-to-end: context options appear in subcommand --help output."""

    def test_context_options_appear_in_subcommand_help(self):
        """Subcommand --help output lists context=True options in the panel."""
        from click.testing import CliRunner

        group = _Group(
            name="myapp",
            params=[
                _make_context_opt("--host", help="Array hostname."),
                _make_context_opt("--pool", help="Storage pool name."),
            ],
        )
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        @click_extra.command("status")
        def status_cmd():
            """Show status."""

        group.add_command(status_cmd)

        runner = CliRunner()
        result = runner.invoke(group, ["status", "--help"])

        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--pool" in result.output
        assert CONTEXT_OPTIONS_PANEL in result.output

    def test_hidden_context_option_absent_from_subcommand_help(self):
        """Options with show_in_subcommand_help=False do not appear in subcommand help."""
        from click.testing import CliRunner

        group = _Group(
            name="myapp",
            params=[
                _make_context_opt("--host"),
                _make_context_opt("--token", show_in_subcommand_help=False),
            ],
        )
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        @click_extra.command("ping")
        def ping_cmd():
            """Ping."""

        group.add_command(ping_cmd)

        runner = CliRunner()
        result = runner.invoke(group, ["ping", "--help"])

        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--token" not in result.output

    def test_panel_absent_when_all_options_hidden(self):
        """Panel section is absent when all context options have show_in_subcommand_help=False."""
        from click.testing import CliRunner

        group = _Group(
            name="myapp",
            params=[_make_context_opt("--token", show_in_subcommand_help=False)],
        )
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        @click_extra.command("ping")
        def ping_cmd():
            """Ping."""

        group.add_command(ping_cmd)

        runner = CliRunner()
        result = runner.invoke(group, ["ping", "--help"])

        assert result.exit_code == 0
        assert CONTEXT_OPTIONS_PANEL not in result.output

    def test_subcommand_does_not_error_without_required_context_option(self):
        """Subcommand runs without error when a required context option is not re-provided."""
        from click.testing import CliRunner

        group = _Group(
            name="myapp",
            params=[_make_context_opt("--host", required=True)],
        )
        group._context_options_panel = CONTEXT_OPTIONS_PANEL

        @click_extra.command("ping")
        def ping_cmd():
            """Ping."""

        group.add_command(ping_cmd)

        runner = CliRunner()
        # --host provided at root level, not repeated before subcommand
        result = runner.invoke(group, ["--host", "10.0.0.1", "ping"])
        assert result.exit_code == 0
```

- [ ] **Step 23: Run to verify integration tests pass**

```bash
python -m pytest tests/core/mixins/test_cli.py::TestContextOptionsInHelpText -v
```

Expected: all 4 PASS (implementation is already in place from Task 4).

---

### Task 6: Full suite + lint + final commit

- [ ] **Step 24: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all existing tests still PASS — zero regressions.

- [ ] **Step 25: Lint and format**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

Fix any reported issues. Re-run until clean.

- [ ] **Step 26: Final commit**

```bash
git add src/pyclifer/core/classes.py src/pyclifer/core/decorators.py src/pyclifer/core/mixins/cli.py tests/core/test_classes.py tests/core/test_decorators.py tests/core/mixins/test_cli.py
git commit -m "✨ feat: show context=True options in subcommand help panel (closes #3)

- PycliferOption gains show_in_subcommand_help=True for per-option opt-out
- GroupConfig gains context_options_panel for custom panel label
- @option forwards show_in_subcommand_help to PycliferOption
- GroupDecorator stores _context_options_panel on group instance
- GlobalOptionsMixin._get_context_option_display_copy creates display-only copies
- GlobalOptionsMixin._propagate_context_options injects copies recursively
- add_command filters by show_in_subcommand_help, reads panel name from group
- panel absent when no qualifying option exists"
```

---

## Self-Review

**Spec coverage (issue #3):**
- ✅ `context=True` options appear in subcommand `--help` → Tasks 4 + 5
- ✅ Dedicated panel with configurable name → Tasks 1, 2, 4
- ✅ Per-option opt-out via `show_in_subcommand_help=False` → Tasks 1, 2, 4, 5
- ✅ Panel absent when no qualifying options → Task 5 (`test_panel_absent_when_all_options_hidden`)
- ✅ Display copies do not affect callbacks (`expose_value=False`, `required=False`) → Tasks 3, 4, 5
- ✅ Recursive propagation into nested subgroups → Task 4 (`test_recursive_into_nested_subcommand`)
- ✅ `is_global=True` not double-injected → Task 4 (`test_context_and_is_global_true_not_double_injected`)

**Placeholder scan:** None found — all steps contain actual code.

**Type consistency:**
- `_get_context_option_display_copy(opt, panel_name)` — consistent across Tasks 3, 4
- `_propagate_context_options(cmd, context_options, panel_name)` — consistent across Tasks 4, 5
- `CONTEXT_OPTIONS_PANEL` — imported from `pyclifer.core.mixins.cli` in all test tasks
- `show_in_subcommand_help` — attribute name consistent across `PycliferOption`, `@option`, filter in `add_command`
- `context_options_panel` — `GroupConfig` field name consistent with `_apply_click_group` store and test assertions