# Scaffolding — `add command` dans un sous-groupe imbriqué

Étend `pyclifer project add command` pour cibler un sous-groupe imbriqué
(`apps/<app>/apps/<group>/commands/`) en plus des apps de premier niveau.

## Problème actuel

`add command NAME --app APP` résout toujours `APP` dans `src/<pkg>/apps/APP/`.
Pour les sous-groupes créés par `add group`, le chemin est
`apps/<parent>/apps/<group>/` — introuvable avec la syntaxe actuelle.

```bash
pyclifer project add group tasks --app demo        # crée apps/demo/apps/tasks/
pyclifer project add command list --app tasks      # ❌ cherche apps/tasks/ (inexistant)
```

## Solution — chemin pointé

Étendre `--app` pour accepter une notation pointée `parent.group` :

```bash
pyclifer project add command list --app demo.tasks   # ✅ résout apps/demo/apps/tasks/
```

La résolution est récursive : `a.b.c` → `apps/a/apps/b/apps/c/`.

---

## Comportement attendu

```bash
# Commandes tasks
pyclifer project add command list     --app demo.tasks
pyclifer project add command add      --app demo.tasks
pyclifer project add command show     --app demo.tasks
pyclifer project add command complete --app demo.tasks
pyclifer project add command delete   --app demo.tasks
pyclifer project add command sync     --app demo.tasks

# Commandes users
pyclifer project add command list     --app demo.users
pyclifer project add command whoami   --app demo.users
```

Chaque commande génère les mêmes fichiers et câblages qu'aujourd'hui, au bon chemin.

---

## Résolution du chemin

Fonction `_resolve_app_dir(app_path: str) -> Path` :

```python
def _resolve_app_dir(self, app_path: str) -> Path:
    """Resolve a dotted app path to an absolute directory.

    "tasks"       → src/<pkg>/apps/tasks/
    "demo.tasks"  → src/<pkg>/apps/demo/apps/tasks/
    "a.b.c"       → src/<pkg>/apps/a/apps/b/apps/c/
    """
    pkg = self._detect_package()
    parts = app_path.split(".")
    path = self._root / "src" / pkg / "apps" / parts[0]
    for part in parts[1:]:
        path = path / "apps" / part
    return path
```

`add_command` utilise `_resolve_app_dir` à la place de la construction manuelle actuelle.
Le nom de l'app (pour les messages d'erreur et le câblage dans `__init__.py`) reste
la dernière partie du chemin pointé.

---

## Cas d'erreur

| Situation | Comportement |
|---|---|
| Chemin inexistant à n'importe quel niveau | `OperationResult.error` : "App 'X' not found at …" |
| Commande déjà existante | `OperationResult.error` `error_code=2` (inchangé) |

---

## Implémentation

### Fichiers à modifier

- `interfaces.py` — ajouter `_resolve_app_dir`, remplacer la construction de
  `commands_dir` dans `add_command` par `_resolve_app_dir(app) / "commands"`
- `commands/add/command.py` — help text de `--app` mis à jour pour documenter
  la notation pointée

### Rétrocompatibilité

`add command NAME --app tasks` (sans point) continue de fonctionner —
`_resolve_app_dir("tasks")` → `apps/tasks/` comme avant.

---

## Tests

Ajouter dans `tests/apps/project/test_interfaces.py` — classe `TestAddCommandNested` :

| Test | Ce qui est vérifié |
|---|---|
| `test_creates_command_in_nested_group` | `add_command("list", "demo.tasks")` crée `apps/demo/apps/tasks/commands/list.py` |
| `test_wires_command_in_nested_group` | `commands/__init__.py` du sous-groupe reçoit l'import |
| `test_three_levels_deep` | `a.b.c` résout `apps/a/apps/b/apps/c/` |
| `test_simple_app_unchanged` | `--app tasks` (sans point) fonctionne toujours |
| `test_error_intermediate_not_found` | `--app demo.unknown` → erreur si `unknown` inexistant |