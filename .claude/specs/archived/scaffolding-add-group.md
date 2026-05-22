# Scaffolding — `pyclif project add group`

Ajoute la commande `pyclif project add group NAME --app APP` au scaffolding,
permettant de créer un sous-groupe `@group` imbriqué à l'intérieur d'un app existant.

## Motivation

`add app` crée un groupe de premier niveau (`apps/NAME/`).
`add command` crée une commande feuille (`apps/APP/commands/NAME.py`).
Il manque un niveau intermédiaire pour les CLIs à trois niveaux :

```
mycli
└── demo          ← add app demo
    ├── tasks     ← add group tasks --app demo   (manquant)
    │   └── list  ← add command list --app tasks
    └── users     ← add group users --app demo   (manquant)
        └── whoami
```

Ce pattern couvre les cas réels : CLIs cloud (`aws ec2 instances list`),
admin SaaS (`admin tenants users list`), DevOps (`platform k8s pods describe`).

---

## Commande

```
pyclif project add group NAME --app APP
```

- `NAME` : nom du sous-groupe (snake_case ou kebab-case).
- `--app APP` : app parent existant (doit être dans `src/<pkg>/apps/APP/`).

`--app` est cohérent avec `add command --app APP` — même sémantique "à l'intérieur de".

---

## Fichiers générés

```
src/<pkg>/apps/<app>/
├── __init__.py                ← modifié  (import + subgroups = [...] mis à jour)
└── apps/
    ├── __init__.py            ← créé si absent  (package marker vide)
    └── <name>/
        ├── __init__.py        ← créé  (template : app_init.py.jinja2)
        ├── interfaces.py      ← créé  (template : app_interfaces.py.jinja2)
        ├── models.py          ← créé  (template : app_models.py.jinja2)
        ├── tables.py          ← créé  (template : app_tables.py.jinja2)
        └── commands/
            └── __init__.py   ← créé  (template : app_commands_init.py.jinja2)
```

Aucun nouveau template n'est nécessaire — les templates existants sont réutilisés.

---

## Pattern de câblage — déclaratif (miroir du top-level)

Le câblage est **identique au pattern `groups = [...]`** du top-level `apps/__init__.py`.
Le template `app_init.py.jinja2` est modifié pour inclure `subgroups = []` et sa boucle.

### Template `app_init.py.jinja2` — après modification

```python
from pyclif import group
from .commands import commands

subgroups = []


@group()
def {{ name_snake }}():
    """{{ name_pascal }} group."""


for grp in subgroups:
    {{ name_snake }}.add_command(grp)

for cmd in commands:
    {{ name_snake }}.add_command(cmd)
```

### État du parent après `add group tasks --app demo`

```python
from pyclif import group
from .apps.tasks import tasks
from .commands import commands

subgroups = [tasks]


@group()
def demo():
    """Demo group."""


for grp in subgroups:
    demo.add_command(grp)

for cmd in commands:
    demo.add_command(cmd)
```

### Après un second `add group users --app demo`

```python
from pyclif import group
from .apps.tasks import tasks
from .apps.users import users
from .commands import commands

subgroups = [tasks, users]


@group()
def demo():
    """Demo group."""


for grp in subgroups:
    demo.add_command(grp)

for cmd in commands:
    demo.add_command(cmd)
```

### Logique de câblage dans `_wire_subgroup`

Exactement la même mécanique que `_wire_app_grouped` :

1. **Insertion de l'import** — insérer `from .apps.<name> import <name>` après le
   dernier bloc `from .` existant.
2. **Expansion de `subgroups = [...]`** — regex `r"subgroups\s*=\s*\[(.*?)]"`,
   même helper `_expand` que pour `groups`.

---

## Cas d'erreur

| Situation | Comportement |
|---|---|
| `--app APP` inexistant | `OperationResult.error` : "App 'APP' not found. Run `add app APP` first." |
| Sous-groupe `NAME` déjà existant | `OperationResult.error` : "Group 'NAME' already exists at …" `error_code=2` |
| `apps/<app>/__init__.py` absent | `OperationResult.error` : "File '…/__init__.py' not found." |
| `apps/<app>/__init__.py` sans sentinel `subgroups = [` | `OperationResult.error` : "No `subgroups = [` found in …/__init__.py — is it a grouped app?" |

---

## Implémentation

### 1. Modifier `app_init.py.jinja2`

Ajouter `subgroups = []` et la boucle (voir ci-dessus).

### 2. Ajouter `add_group` dans `interfaces.py`

```python
def add_group(self, name: str, app: str) -> Iterator[OperationResult]:
    """Create a subgroup skeleton inside an existing app's apps/ directory."""
```

Logique :
1. Vérifier que `apps/<app>/` existe — sinon erreur.
2. Vérifier que `apps/<app>/apps/<name>/` n'existe pas — sinon erreur `error_code=2`.
3. Créer `apps/<app>/apps/__init__.py` si absent (fichier vide).
4. Générer les 5 fichiers du sous-groupe avec les templates existants.
5. Appeler `_wire_subgroup(name_snake, app)`.

Enregistrer dans `renderers` : `"add_group": ScaffoldingRenderer`.

### 3. Ajouter `_wire_subgroup` dans `interfaces.py`

```python
def _wire_subgroup(self, name_snake: str, app: str) -> Iterator[OperationResult]:
    """Insert import and expand subgroups list in the parent app's __init__.py."""
```

Logique (miroir de `_wire_app_grouped`) :
1. Lire `apps/<app>/__init__.py`.
2. Insérer `from .apps.<name> import <name>` après le dernier bloc `from .`.
3. Regex-expand `subgroups = [...]` pour y ajouter `<name>`.
4. Écrire et yielder `OperationResult.ok`.

### 4. Nouveau fichier de commande

`src/pyclif/apps/project/commands/add/group.py` :

```python
@command()
@argument("name")
@option("--app", "app", required=True, help="App that owns this group.")
@pass_context
def group(ctx, name: str, app: str) -> Response:
    """Add a subgroup to an existing app."""
    return ScaffoldingInterface(ctx).respond("add_group", name, app)
```

### 5. Câblage dans `commands/add/__init__.py`

Ajouter `from .group import group` et `commands.append(group)`.

---

## Tests

Fichier : `tests/apps/project/commands/add/test_group.py`

| Test | Ce qui est vérifié |
|---|---|
| `test_creates_subgroup_files` | Les 5 fichiers sont créés aux bons chemins |
| `test_creates_apps_package_if_absent` | `apps/<app>/apps/__init__.py` créé si absent |
| `test_does_not_overwrite_apps_package` | Pas d'erreur si `apps/__init__.py` existe déjà |
| `test_wires_import_in_parent_init` | `from .apps.tasks import tasks` inséré |
| `test_expands_subgroups_list` | `subgroups = []` → `subgroups = [tasks]` |
| `test_second_group_expands_correctly` | `subgroups = [tasks]` → `subgroups = [tasks, users]` |
| `test_error_app_not_found` | Erreur si `--app` inexistant |
| `test_error_group_already_exists` | Erreur `error_code=2` si sous-groupe déjà là |
| `test_error_parent_init_missing` | Erreur si `__init__.py` du parent absent |
| `test_error_no_subgroups_sentinel` | Erreur si `subgroups = [` absent du parent |

Tous les tests utilisent `tmp_path` et ne touchent pas le filesystem réel.