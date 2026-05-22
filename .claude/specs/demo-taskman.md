# Demo CLI — `pyclif demo`

`pyclif demo` est une sous-app fictive de gestion de tâches livrée dans `pyclif` qui
exerce chaque fonctionnalité du framework dans une application unique et exécutable.
Elle suit le même layout Django-inspired que génère `pyclif project init`, ce qui en
fait aussi une référence d'implémentation vivante.

## Objectifs

- Chaque symbole public de pyclif utilisé au moins une fois dans du code réel.
- Aucune magie ni raccourci — la démo doit ressembler exactement à un projet utilisateur.
- Navigable comme documentation : les lecteurs peuvent sauter d'une fonctionnalité dans
  les docs à son usage concret dans la démo.

## Approche de construction — scaffolding first

La démo est construite **en utilisant les commandes de scaffolding de pyclif lui-même**
autant que possible. L'objectif est double : produire le code de la démo ET auditer le
scaffolding en conditions réelles pour identifier ce qui manque ou ce qui doit être
amélioré.

### Processus cible — ✅ COMPLÉTÉ

```bash
# Depuis la racine du projet pyclif

# 1. Groupe racine de la démo  ✅
pyclif project add app demo

# 2. Sous-groupes tasks et users  ✅
pyclif project add group tasks --app demo
pyclif project add group users --app demo

# 3. Commandes tasks  ✅
pyclif project add command list add show complete delete sync --app demo.tasks

# 4. Commandes users  ✅
pyclif project add command list whoami --app demo.users
```

### Ce qu'on attend du scaffolding

Chaque commande `add app` / `add group` / `add command` doit générer :

- le squelette de fichier au bon endroit (`apps/demo/apps/tasks/commands/list.py`, etc.)
- les imports pyclif corrects
- la décoration `@group` / `@command` / `@pass_cli_context` en place
- le câblage automatique dans le `__init__.py` du groupe parent

### Journal des écarts

Écarts observés pendant l'implémentation — chaque entrée devient une issue dans
`apps/project/`.

```
✅ CORRIGÉ  apps/__init__.py utilisait `groups` mais le wiring appendait `exports`
            → templates et _wire_app_grouped alignés sur `groups`

✅ CORRIGÉ  `add command` syntaxe 3-args inexistante (`demo tasks list`)
            → implémenté `add group NAME --app APP` + syntaxe `add command NAME --app APP`

✅ CORRIGÉ  `add command --app APP` ne résolvait APP que dans apps/ racine.
            → `_resolve_app_dir` + notation pointée `--app demo.tasks` implémentés.

✅ CORRIGÉ  `add command` n'acceptait qu'un seul nom à la fois.
            → `nargs=-1` sur l'argument `names` ; `add_commands()` dans l'interface.

✅ CORRIGÉ  template `command.py.jinja2` référençait `{{ name_pascal }}Interface`
            (ex. `ListInterface`) au lieu de l'interface de l'app parente.
            → renommé en `{{ app_pascal }}Interface` ; `app_pascal` injecté dans le namespace.

✅ CORRIGÉ  `interfaces.py` généré sans `OperationResult` dans les imports.
            → `_wire_interface_method` injecte l'import si absent ; template mis à jour.

✅ CORRIGÉ  `def list(self)` dans `interfaces.py` shadowing le builtin `list` dans les
            annotations de retour → `TypeError` à l'import.
            → `from __future__ import annotations` ajouté au template et aux fichiers existants.

✅ CORRIGÉ  `commands/__init__.py` généré avec un en-tête commentaire au lieu d'une
            docstring module, provoquant des violations ruff I001.
            → template mis à jour avec `"""Commands for the {{ name_pascal }} app."""`.

✅ CORRIGÉ  `_wire_list_var` n'ajoutait pas de ligne vide entre le premier import injecté
            et `commands = [...]`, provoquant des violations ruff.
            → branche `else` corrigée pour utiliser `\n\n` avant l'assignation.

- [ ] `add app` ne génère pas `core/` (context.py, constants.py, options.py, storage.py)
      → la démo doit créer ce répertoire manuellement.
      Fix : `add app` pourrait accepter `--with-core` pour générer le squelette core/.

- [ ] aucune commande pour scaffolder `renderers.py` → à créer manuellement.
      Fix : `add renderer NAME --app APP` à spec-er.
```

## Câblage dans la CLI pyclif

La démo s'enregistre comme sous-groupe de `pyclif` exactement comme `pyclif project`,
sans aucune modification de `pyproject.toml` :

```python
# src/pyclif/apps/__init__.py
from .project import project
from .demo import demo

groups = [project, demo]
```

Après `uv sync --extra dev`, `pyclif demo --help` est disponible.

Les données sont persistées dans `~/.config/pyclif/demo.json` (créé automatiquement au
premier lancement).

---

## Arbre de commandes

`--config`, `--verbosity` et `--output-format` sont hérités du groupe racine `pyclif`
et ne sont pas redéclarés dans `demo`.

```
pyclif [--config FILE] [--verbosity LEVEL] [--output-format FMT]
└── demo [--project NAME]
    ├── tasks
    │   ├── list    [--status] [--priority] [--page] [--page-size] [--output-filter]
    │   ├── add     --title TEXT [--description TEXT] [--priority] [--due DATE]
    │   │           [--tags TEXT] [--assignee TEXT]
    │   ├── show    TASK_ID
    │   ├── complete TASK_ID
    │   ├── delete  TASK_ID [--yes]
    │   └── sync    [--source URL]
    └── users
        ├── list    [--output-filter]
        └── whoami
```

`--project` est une **global option** (`is_global=True`) — définie une seule fois sur
le groupe `demo` et automatiquement propagée à chaque sous-commande.

---

## Matrice de couverture des fonctionnalités

| Fonctionnalité pyclif | Où elle est exercée |
|---|---|
| `@group` | groupe racine `demo` + subgroups `tasks/` et `users/` |
| `@command` | chaque commande feuille |
| `@option` | options de chaque commande |
| `is_global=True` option propagation | `--project` dans `core/options.py` |
| `handle_response=True` auto-wrapping | hérité du groupe `pyclif` parent — observé sans être redéclaré |
| `returns_response` | utilisé directement dans `show` |
| `output_filter_option` | `tasks list`, `users list` |
| `pagination_options` | `tasks list` |
| `BaseModel` (Pydantic) | `Task`, `User` |
| `BaseInterface` + `respond()` | `TaskInterface`, `UserInterface` |
| `OperationResult.ok()` | `add`, `complete` |
| `OperationResult.error()` | `delete` (id inexistant) |
| `Response.from_results()` | `list`, `add`, `complete`, `delete` |
| `Response.from_stream()` | `sync` |
| `PaginatedResponse` | `tasks list` |
| `BaseRenderer` (déclaratif) | `TaskListRenderer`, `TaskDetailRenderer` |
| `ResponseRenderer` Protocol | `UserWhoamiRenderer` |
| `CliTable` + `CliTableColumn` | sortie table dans les renderers list |
| `RichHelpersMixin` — panel | `tasks show` |
| `RichHelpersMixin` — rule | résumé de `tasks sync` |
| `RichHelpersMixin` — spinner / status | progression live de `tasks sync` |
| `RichHelpersMixin` — confirm prompt | `tasks delete` (sans `--yes`) |
| `get_logger()` + niveau TRACE | `TaskInterface`, `UserInterface` |
| `SecretsMasker` | URL `--source` avec credentials embarquées dans `sync` |
| Sous-classe `BaseContext` | `DemoContext` |
| `make_pass_decorator` | `pass_demo_context` dans `core/context.py` |

---

## Structure de fichiers

```
src/pyclif/apps/demo/
├── __init__.py                 # @group "demo" + câblage add_command (miroir de apps/project/)
├── core/
│   ├── __init__.py
│   ├── context.py              # DemoContext(BaseContext) + pass_demo_context
│   ├── constants.py            # enums Priority, Status / listes Choice
│   ├── options.py              # définition de l'option globale --project
│   └── storage.py              # helper lecture/écriture JSON
└── apps/
    ├── __init__.py
    ├── tasks/
    │   ├── __init__.py
    │   ├── models.py           # Task(BaseModel)
    │   ├── interfaces.py       # TaskInterface(BaseInterface)
    │   ├── renderers.py        # TaskListRenderer, TaskDetailRenderer, TaskSyncRenderer
    │   └── commands/
    │       ├── __init__.py
    │       ├── list.py
    │       ├── add.py
    │       ├── show.py
    │       ├── complete.py
    │       ├── delete.py
    │       └── sync.py
    └── users/
        ├── __init__.py
        ├── models.py           # User(BaseModel)
        ├── interfaces.py       # UserInterface(BaseInterface)
        ├── renderers.py        # UserListRenderer, UserWhoamiRenderer
        └── commands/
            ├── __init__.py
            ├── list.py
            └── whoami.py
```

---

## Modèles de domaine

### `Task` (`tasks/models.py`)

```python
class Task(BaseModel):
    id: str                          # UUID4, généré à la création
    title: str
    description: str = ""
    priority: str = "medium"         # "low" | "medium" | "high"
    status: str = "open"             # "open" | "in_progress" | "done"
    due_date: datetime.date | None = None
    tags: list[str] = []
    assignee: str = ""
    created_at: datetime.datetime
```

`pydantic.field_validator` sur `priority` et `status` enforce les valeurs autorisées et
lève `ValueError` avec un message lisible que Click remonte proprement.

### `User` (`users/models.py`)

```python
class User(BaseModel):
    username: str
    email: str
    role: str = "member"             # "admin" | "member"
    created_at: datetime.datetime
```

---

## Storage (`core/storage.py`)

Helper minimal qui lit/écrit `~/.config/pyclif/demo.json`. Volontairement simple pour
ne pas distraire des patterns pyclif.

```python
class Storage:
    def load(self) -> dict          # {"tasks": [...], "users": [...]}
    def save(self, data: dict) -> None
    def get_tasks(self) -> list[Task]
    def get_users(self) -> list[User]
    def get_task(self, task_id: str) -> Task | None
    def upsert_task(self, task: Task) -> None
    def delete_task(self, task_id: str) -> bool   # False si non trouvé
```

---

## Groupe racine (`__init__.py`)

Miroir exact du pattern `apps/project/__init__.py` — `@group()` et non `@app_group` :

```python
# src/pyclif/apps/demo/__init__.py
from pyclif import group
from .core.options import project_option
from .core.context import pass_demo_context
from .apps.tasks import tasks_group
from .apps.users import users_group


@group()
@project_option
@pass_demo_context
def demo(ctx, project):
    """Demo task manager — reference implementation of all pyclif features."""
    ctx.meta["project"] = project


demo.add_command(tasks_group)
demo.add_command(users_group)
```

`handle_response`, `--config`, `--verbosity` et `--output-format` sont portés par le
groupe `pyclif` parent — `demo` n'a pas besoin de les redéclarer.

---

## Option globale (`core/options.py`)

```python
project_option = option(
    "--project",
    default="default",
    help="Project namespace to operate in.",
    is_global=True,
    show_envvar=True,
)
```

Déclarée une fois ; `GlobalOptionsMixin` la propage à chaque sous-commande
automatiquement. Les commandes la récupèrent via `ctx.meta["project"]`.

---

## Contexte (`core/context.py`)

```python
class DemoContext(BaseContext):
    """Contexte étendu portant l'instance Storage active."""

    @property
    def storage(self) -> Storage:
        if "storage" not in self.meta:
            self.meta["storage"] = Storage()
        return self.meta["storage"]

pass_demo_context = make_pass_decorator(DemoContext, ensure=True)
```

Chaque commande reçoit un `DemoContext` via `@pass_demo_context`. `ctx.storage` donne
un accès lazy au backend JSON sans singleton ni état global.

---

## Constantes (`core/constants.py`)

```python
PRIORITIES = ["low", "medium", "high"]
STATUSES   = ["open", "in_progress", "done"]

PRIORITY_CHOICE = Choice(PRIORITIES)
STATUS_CHOICE   = Choice(STATUSES)
```

---

## Interfaces

### `TaskInterface` (`tasks/interfaces.py`)

```python
class TaskInterface(BaseInterface):
    renderers = {
        "list_tasks":    TaskListRenderer,
        "add_task":      TaskAddRenderer,
        "show_task":     TaskDetailRenderer,
        "complete_task": TaskCompleteRenderer,
        "delete_task":   TaskDeleteRenderer,
        "sync_tasks":    TaskSyncRenderer,
    }

    def list_tasks(self, status, priority, page, page_size) -> list[OperationResult]: ...
    def add_task(self, title, description, priority, due_date, tags, assignee) -> list[OperationResult]: ...
    def show_task(self, task_id) -> list[OperationResult]: ...
    def complete_task(self, task_id) -> list[OperationResult]: ...
    def delete_task(self, task_id) -> list[OperationResult]: ...
    def sync_tasks(self, source) -> Iterator[OperationResult]: ...   # générateur
```

`sync_tasks` est la seule méthode **générateur** — elle yield un `OperationResult` par
tâche fakée après un court sleep, ce qui fait router `respond()` via
`Response.from_stream()`.

L'URL `source` peut contenir des credentials embarquées
(`https://user:s3cr3t@remote.example.com`). Avant le log, `TaskInterface` passe l'URL
dans `SecretsMasker` :

```python
logger.debug("Syncing from %s", self._mask(source))
```

### `UserInterface` (`users/interfaces.py`)

```python
class UserInterface(BaseInterface):
    renderers = {
        "list_users": UserListRenderer,
        "whoami":     UserWhoamiRenderer,
    }

    def list_users(self) -> list[OperationResult]: ...
    def whoami(self) -> list[OperationResult]: ...
```

`whoami` lit l'utilisateur Unix courant depuis `os.getenv("USER")` et le wrappe dans
un `User` avec role `admin` — suffisant pour montrer `UserWhoamiRenderer`.

---

## Renderers

### `TaskListRenderer`

```python
class TaskListRenderer(BaseRenderer):
    fields      = ["id", "title", "priority", "status", "due_date", "assignee"]
    columns     = ["id", "title", "priority", "status", "due_date", "assignee"]
    rich_title  = "Tasks"
    success_message = "Tasks retrieved successfully."
    model_class = Task
```

Retourné par `tasks list`. Supporte tous les output formats (json/yaml/table/rich/raw).

`PaginatedResponse` est construit par la commande directement après `respond()` :

```python
response = iface.respond("list_tasks", ...)
return PaginatedResponse(
    **dataclasses.asdict(response),
    page=page, limit=page_size, total=total,
)
```

### `TaskDetailRenderer`

Override `rich()` pour afficher un `Panel` Rich avec les champs de la tâche formatés
en liste de définitions + badge de statut coloré. Démontre un output Rich custom
au-delà du panel par défaut.

### `TaskSyncRenderer`

Override les hooks streaming :

```python
class TaskSyncRenderer(BaseRenderer):
    rich_title = "Syncing tasks"

    def rich_setup(self) -> Progress:
        self._progress = Progress(...)
        self._task_bar = self._progress.add_task("Syncing…", total=None)
        return self._progress

    def rich_on_item(self, result, all_so_far):
        self._progress.advance(self._task_bar)

    def rich_summary(self, response, console):
        console.rule("[bold green]Sync complete")
        console.print(f"{len(response.data['results'])} tasks imported.")
```

Démontre `Response.from_stream()` + le cycle de vie complet du streaming Rich.

### `UserWhoamiRenderer`

Implémente le **Protocol** `ResponseRenderer` directement (sans héritage `BaseRenderer`)
pour montrer que le chemin Protocol fonctionne :

```python
class UserWhoamiRenderer:
    def serialize(self, response): ...
    def table(self, response): ...
    def text(self, response): ...
    def raw(self, response): ...
    def rich(self, response, console): ...
    def rich_setup(self): ...
    def rich_on_item(self, result, all_so_far): ...
    def rich_summary(self, response, console): ...
    def get_success_message(self, results): ...
    def get_failure_message(self, results): ...
```

---

## Spécifications des commandes

### `tasks list`

**Démontre :** `pagination_options`, `output_filter_option`, `PaginatedResponse`,
`TaskListRenderer`, types `@option` variés.

```python
@tasks_group.command("list")
@pagination_options()
@output_filter_option()
@option("--status",   type=STATUS_CHOICE,   default=None)
@option("--priority", type=PRIORITY_CHOICE, default=None)
@pass_demo_context
def list_tasks(ctx, page, page_size, output_filter, status, priority): ...
```

Retourne un `PaginatedResponse` → la sortie JSON/YAML inclut un bloc `pagination`.

---

### `tasks add`

**Démontre :** types `@option` variés dont `DateTime`, parsing liste pour `--tags`,
`OperationResult.ok()`.

```python
@tasks_group.command("add")
@option("--title",       required=True)
@option("--description", default="")
@option("--priority",    type=PRIORITY_CHOICE, default="medium")
@option("--due",         type=DateTime(formats=["%Y-%m-%d"]), default=None)
@option("--tags",        default="", help="Comma-separated list of tags.")
@option("--assignee",    default="")
@pass_demo_context
def add_task(ctx, title, description, priority, due, tags, assignee): ...
```

`tags` est splitté sur les virgules avant d'être passé à `TaskInterface.add_task()`.

---

### `tasks show`

**Démontre :** `TaskDetailRenderer` avec `rich()` custom (Panel Rich avec champs
formatés), gestion d'un résultat `error_code=404`.

```python
@tasks_group.command("show")
@argument("task_id")
@pass_demo_context
def show_task(ctx, task_id): ...
```

Si la tâche n'est pas trouvée, l'interface retourne `OperationResult.error()` avec
`error_code=404` et le framework affiche le message d'échec.

---

### `tasks complete`

**Démontre :** branchement `OperationResult.ok()` / `.error()`, renderer minimal.

```python
@tasks_group.command("complete")
@argument("task_id")
@pass_demo_context
def complete_task(ctx, task_id): ...
```

Passe `task.status = "done"` et sauvegarde. Retourne une erreur si la tâche est déjà
terminée ou inexistante.

---

### `tasks delete`

**Démontre :** prompt de confirmation interactif `RichHelpersMixin`, `OperationResult.error()`
pour une ressource manquante, bypass `--yes`.

```python
@tasks_group.command("delete")
@argument("task_id")
@option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation.")
@pass_demo_context
def delete_task(ctx, task_id, yes): ...
```

Sans `--yes`, appelle `ctx.confirm(f"Delete task {task_id}?", abort=True)`.

---

### `tasks sync`

**Démontre :** `Response.from_stream()`, hooks streaming `TaskSyncRenderer`,
`SecretsMasker` sur l'URL `--source`, rule Rich.

```python
@tasks_group.command("sync")
@option(
    "--source",
    default="https://remote.example.com/tasks",
    help="URL of the remote task source. Supports embedded credentials.",
)
@pass_demo_context
def sync_tasks(ctx, source): ...
```

Le générateur dans `TaskInterface.sync_tasks()` yield un `OperationResult` toutes les
`0.1 s` (simulé avec `time.sleep`), créant un effet de progression live visible dans
le terminal.

---

### `users list`

**Démontre :** `UserListRenderer` avec colonnes déclaratives `BaseRenderer`,
`output_filter_option`.

---

### `users whoami`

**Démontre :** `UserWhoamiRenderer` implémentant le Protocol `ResponseRenderer`,
Panel Rich avec les infos de l'utilisateur courant.

---

## Tests

Les tests vivent dans `tests/apps/demo/` et reflètent la structure source. Cibles de
couverture :

| Fichier | Ce qui est testé |
|---|---|
| `core/storage.py` | round-trip lecture/écriture, création si fichier absent |
| `tasks/models.py` | rejet par le validateur de priority/status invalides |
| `tasks/interfaces.py` | chaque méthode ; `Storage` mocké ; générateur stream |
| `tasks/renderers.py` | `serialize()`, `table()`, `rich()`, hooks streaming |
| `tasks/commands/*.py` | invocation CLI via `CliRunner` ; chemins succès et erreur |
| `users/` | même structure que tasks |

Tous les tests utilisent `click.testing.CliRunner` avec `mix_stderr=False`.
`Storage` est patché au niveau de l'interface pour que les tests ne touchent jamais
le filesystem.