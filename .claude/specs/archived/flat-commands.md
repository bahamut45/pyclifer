# Flat commands — apps sans couche group intermédiaire

## Problème

Le scaffolding génère toujours un `@group` intermédiaire, ce qui impose `mon-app app command`.
Pour certains domaines, le groupe n'apporte rien — les commandes sont mieux exposées directement
à la racine (`mon-app command`) tout en conservant la structure `apps/<app>/` qui organise le code.

Le **cœur du framework supporte déjà** cette topologie : `GlobalOptionsMixin`, `HandleResponseMixin`
et `returns_response` fonctionnent à n'importe quel niveau. La lacune est uniquement dans le
scaffolding.

## Décision de design

### La structure `apps/` ne change pas

Un app reste organisé dans `apps/<app>/` avec ses `commands/`, `interfaces.py`, `renderers.py`,
etc. La seule différence : son `__init__.py` expose soit un `@group` (comportement actuel), soit
ses commandes directement (nouveau).

```
apps/
  articles/             ← app groupé (inchangé)
    __init__.py         # définit @group articles
    commands/
      list.py
      create.py
    interfaces.py
  status/               ← app plat (nouveau)
    __init__.py         # pas de @group — exporte les commandes directement
    commands/
      check.py
    interfaces.py
```

### `apps/__init__.py` — liste unifiée `exports`

La liste actuelle `groups` est renommée `exports`. Elle peut contenir des instances `Group`
(app groupé) ou des instances `Command` (app plat). `cli.py` appelle `add_command()` sur
chaque élément — Click gère les deux de la même façon.

```python
# apps/__init__.py
from .articles import articles    # Group  → mon-app articles list
from .status import check         # Command → mon-app check

exports = [articles, check]
```

### App groupé — inchangé

```python
# apps/articles/__init__.py
from .commands import commands

@group()
def articles():
    """Article management."""

for cmd in commands:
    articles.add_command(cmd)
```

### App plat — sans @group

```python
# apps/status/__init__.py
from .commands import commands

# Pas de @group. Les commandes s'enregistrent directement sur l'app_group via exports.
```

Et `commands/__init__.py` exporte la liste habituelle :

```python
from .check import check

commands = [check]
```

`apps/__init__.py` importe et aplatit :

```python
from .articles import articles
from .status import commands as status_commands

exports = [articles, *status_commands]
```

### `cli.py` — câblage unifié

```python
from .apps import exports

@app_group(handle_response=True)
@click.pass_context
def app(ctx):
    """{{ name_pascal }} CLI."""
    ctx.obj = {{ name_pascal }}Context()

for item in exports:
    app.add_command(item)
```

Un seul `add_command()` quelle que soit la forme — pas de branchement dans `cli.py`.

## Scaffolding — changements

### `pyclif project add app` — nouveau flag `--no-group`

```bash
# Comportement actuel (inchangé)
pyclif project add app articles

# Nouveau : app plat, commandes sur le root
pyclif project add app status --no-group
```

Avec `--no-group`, le scaffolding génère :
- `apps/status/__init__.py` sans `@group`, exportant `commands` directement
- Le `apps/__init__.py` est mis à jour pour aplatir les commandes dans `exports`

### Nouveaux templates

| Template                              | Usage                                              |
|---------------------------------------|----------------------------------------------------|
| `app_init_flat.py.jinja2`            | `apps/<app>/__init__.py` sans @group               |
| `project_apps_init_flat.py.jinja2`   | `apps/__init__.py` avec import aplati              |

Le template `app_init.py.jinja2` (avec @group) reste inchangé.

### `pyclif project add command` — inchangé

`add command --app <name>` fonctionne pareil, que l'app soit groupée ou plate. Le
`commands/__init__.py` de l'app est toujours mis à jour de la même façon.

### Migration `groups` → `exports` dans `apps/__init__.py`

Le template `project_apps_init.py.jinja2` passe de `groups = [...]` à `exports = [...]`.
Le template `project_cli.py.jinja2` passe de `from .apps import groups` à
`from .apps import exports`.

Les projets existants qui importent `groups` dans `cli.py` doivent renommer manuellement —
changement de nommage simple, pas de logique à modifier.

## Ce qui ne change pas

- `core/decorators.py`, `core/classes.py`, tous les `core/mixins/` — zéro modification
- Les quatre décorateurs — zéro modification
- La propagation des options globales — fonctionne déjà à tout niveau
- La gestion des réponses — fonctionne déjà à tout niveau
- `pyclif project add command --app <name>` — comportement inchangé
- `pyclif project add app` sans `--no-group` — comportement inchangé
- La structure interne d'un app (`commands/`, `interfaces.py`, `renderers.py`) — inchangée