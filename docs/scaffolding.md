# Project Scaffolding

pyclifer ships a built-in `project` command that generates Django-inspired project structures so
you can skip the boilerplate and start writing business logic immediately.

```bash
pyclifer project --help
pyclifer project add --help
```

## Creating a new project

```bash
pyclifer project init my-project
```

This creates a fully wired `my-project/` directory with a `src/` layout, a test suite, a
`pyproject.toml`, and a `.gitignore`.

**Options**

| Option | Default | Description |
|---|---|---|
| `--package-manager` | `uv` | Toolchain to target — `uv` or `poetry` |
| `--integrations` | _(none)_ | Comma-separated integrations to scaffold in one shot |

```bash
# Target poetry instead of uv
pyclifer project init my-project --package-manager poetry

# Generate a project and immediately scaffold two integrations
pyclifer project init my-project --integrations github,slack
```

### Generated structure

```
my-project/
├── pyproject.toml              # build system, scripts, bumpversion config
├── README.md
├── .gitignore
├── src/my_project/
│   ├── __init__.py
│   ├── cli.py                  # @app_group entry point, wires all app exports
│   ├── core/
│   │   ├── context.py          # MyProjectContext(BaseContext) + pass_cli_context
│   │   ├── constants.py
│   │   ├── options.py
│   │   └── integrations/
│   │       └── __init__.py
│   └── apps/
│       └── __init__.py         # exports = [] — add_app appends or extends here
└── tests/
    ├── __init__.py
    └── conftest.py
```

The generated `cli.py` wires app exports dynamically so each new app you add is picked up
automatically:

```python
from pyclifer import app_group, pass_context
from .core.context import MyProjectContext
from .apps import groups

@app_group()
@pass_context
def app(ctx):
    """MyProject CLI."""
    ctx.obj = MyProjectContext()

for group in groups:
    app.add_command(group)
```

## Adding an app

An _app_ is a self-contained feature area with its own commands, interfaces, models, and tables.
By default it creates a Click group, giving you `my-project app command`. Use `--no-group` when
you want commands to appear directly on the root CLI instead.

**Options**

| Option | Default | Description |
|---|---|---|
| `--no-group` | off | Skip the `@group` wrapper — expose commands directly on the root app |
| `--with-core` | off | Generate a `core/` directory with `context.py`, `constants.py`, and `options.py` |

### Grouped app (default)

```bash
# Run from the project root
pyclifer project add app users
```

**What gets created**

```
src/my_project/apps/users/
├── __init__.py         # @group() decorator + add_command loop
├── interfaces.py       # UserInterface + UserRenderer stubs
├── models.py
├── tables.py
└── commands/
    └── __init__.py     # commands = []
```

**What gets wired**

`apps/__init__.py` is updated automatically — the import is injected and the list expanded inline:

```python
from .users import users
groups = [users]
```

Result: `my-project users list`, `my-project users create`, …

### Grouped app with its own context (--with-core)

Use `--with-core` when the app needs to carry its own state — a shared client, a config
object, or anything that commands should access via `ctx`.

```bash
pyclifer project add app repos --with-core
```

**What gets created**

```
src/my_project/apps/repos/
├── __init__.py         # @group() + @pass_repos_context
├── interfaces.py       # RepoInterface (ctx: ReposContext) + RepoRenderer
├── models.py
├── tables.py
├── commands/
│   └── __init__.py
└── core/
    ├── __init__.py
    ├── context.py      # ReposContext(BaseContext) + pass_repos_context
    ├── constants.py
    └── options.py
```

`context.py` gives you a typed context and a pass decorator ready to use:

```python
from pyclifer import BaseContext, make_pass_decorator

class ReposContext(BaseContext):
    """Application context for Repos."""

pass_repos_context = make_pass_decorator(ReposContext, ensure=True)
```

Commands in this app receive the typed context automatically:

```python
@command()
@pass_repos_context
def list(ctx) -> Response:
    ...
```

And the interface gains a typed `ctx` annotation:

```python
class RepoInterface(BaseInterface):
    ctx: ReposContext  # type narrowing — full autocompletion on ctx
```

### Flat app — commands without a group layer

Use `--no-group` when you want commands to appear directly on the root CLI
(`my-project status`, not `my-project health status`). The internal structure under
`apps/health/` is identical — only the `__init__.py` and the wiring differ.
`--with-core` has no effect when combined with `--no-group`.

```bash
pyclifer project add app health --no-group
```

**What gets created**

```
src/my_project/apps/health/
├── __init__.py         # imports commands — no @group decorator
├── interfaces.py       # HealthInterface + HealthRenderer stubs
├── models.py
├── tables.py
└── commands/
    └── __init__.py     # commands = []
```

**What gets wired**

`apps/__init__.py` gets an `extend` call appended:

```python
from .health import commands as health_commands
groups.extend(health_commands)
```

Result: `my-project status`, `my-project ping`, … — no intermediate group level.

**Adding commands to a flat app works exactly the same way:**

```bash
pyclifer project add command status ping --app health
```

### Mixing grouped and flat apps

Both styles coexist freely. `cli.py` calls `add_command()` on every item in `exports`,
whether it is a Click `Group` (grouped app) or a Click `Command` (flat app):

```python
# apps/__init__.py after adding both:
from .users import users                              # grouped
groups = [users]

from .health import commands as health_commands       # flat
groups.extend(health_commands)
```

```
my-project users list      # grouped app
my-project users create
my-project status          # flat app
my-project ping
```

## Adding a command

A _command_ belongs to an existing app (grouped or flat). It gets its own file and is
immediately reachable on the CLI. Pass one or more names to create several commands in one call.

```bash
# Single command
pyclifer project add command list --app users

# Multiple commands at once
pyclifer project add command list get create --app users
```

**Options**

| Option | Required | Description |
|---|---|---|
| `NAMES…` | yes | One or more command names to create |
| `--app` | yes | App that owns the commands |

**What gets created**

```
src/my_project/apps/users/commands/list.py
```

```python
from pyclifer import command, Response
from ....core.context import pass_cli_context
from ..interfaces import UserInterface

@command()
@pass_cli_context
def list(ctx) -> Response:
    """List description."""
    return UserInterface(ctx).respond("list")
```

**What gets wired**

`apps/users/commands/__init__.py` is updated automatically:

```python
from .list import list
commands.append(list)
```

## Adding an integration

An _integration_ wraps an external library or service and is attached to the application
context so every command can access it via `ctx`.

```bash
# Single-file integration
pyclifer project add integration github

# Package integration (client + helpers + models)
pyclifer project add integration github --package
```

**Options**

| Option | Default | Description |
|---|---|---|
| `--package` | off | Generate a package with `client.py`, `helpers.py`, and `models.py` |

**Single-file layout**

```
src/my_project/core/integrations/github.py
```

```python
class GithubIntegration:
    """Integration for Github."""

    def __init__(self):
        pass
```

**Package layout**

```
src/my_project/core/integrations/github/
├── __init__.py     # exposes GithubIntegration, wires GithubClient
├── client.py       # GithubClient stub
├── helpers.py
└── models.py
```

**What gets wired**

`core/context.py` is updated in two places — an import is injected after the existing imports,
and `__init__` gets the instance assigned:

```python
from .integrations.github import GithubIntegration   # ← injected

class MyProjectContext(BaseContext):
    def __init__(self):
        super().__init__()
        self.github = GithubIntegration()             # ← injected
```

Every command with a typed context can then reach the integration via `ctx.github`.

## Name conventions

All scaffolding commands accept names in either `kebab-case` or `snake_case`. pyclifer derives
the other variants automatically:

| Input | `name_snake` | `name_pascal` |
|---|---|---|
| `my-project` | `my_project` | `MyProject` |
| `user_profile` | `user_profile` | `UserProfile` |
| `github` | `github` | `Github` |

## Error handling

- **Directory already exists** (`init`): exits with code 2 rather than overwriting.
- **App not found** (`add command`): suggests running `add app` first.
- **File already exists** (any command): exits with code 2; no file is touched.
- **`src/` not found** (`add app`, `add command`, `add integration`): reports that the
  current directory is not a pyclifer project root.

## Typical workflow

### Grouped app (simple)

```bash
# 1. Bootstrap
pyclifer project init my-project
cd my-project
uv sync --extra dev

# 2. Add a feature area
pyclifer project add app users

# 3. Add commands to it
pyclifer project add command list get create --app users

# 4. Wrap an external service
pyclifer project add integration github --package

# 5. Run the CLI
uv run my-project --help
uv run my-project users list
```

### Grouped app with its own context

```bash
# 1. Bootstrap
pyclifer project init my-project
cd my-project
uv sync --extra dev

# 2. Add an app that carries its own state (repos client, config, …)
pyclifer project add app repos --with-core

# 3. Add commands — they automatically receive ReposContext
pyclifer project add command list show create --app repos

# 4. Wire your state into ReposContext (edit core/context.py)
#    then access it from any command via ctx.<your_attr>

# 5. Run the CLI
uv run my-project repos list
```

### Flat app

```bash
# 1. Bootstrap
pyclifer project init deploy-tool
cd deploy-tool
uv sync --extra dev

# 2. Add a flat app — commands appear directly on the root
pyclifer project add app deploy --no-group

# 3. Add commands
pyclifer project add command up down status --app deploy

# 4. Run the CLI — no group level
uv run deploy-tool up
uv run deploy-tool status
```
