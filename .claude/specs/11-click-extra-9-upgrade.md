# Mise à jour click-extra 7.20.1 → 9.x

**Objectif :** Lever la contrainte `click-extra>=7.20.1,<8.0.0` vers `>=9.5.1,<10.0.0`. Deux
changements de click-extra touchent pyclifer :

1. **Renommages (8.0.0)** : le préfixe `Extra` disparaît (`ExtraGroup` → `Group`,
   `ExtraFormatter` → `Formatter`, `ExtraStreamHandler` → `StreamHandler`, `extraBasicConfig` →
   `basicConfig`). pyclifer utilise directement ces 4 symboles.
2. **Tri alphabétique des fichiers de config (9.x)** : `ConfigOption.search_and_read_file()` trie
   désormais (`sorted(...)`) les fichiers trouvés par un même motif. Or
   `CustomConfigOption.default_pattern()` assemble `/etc/<cli>/*.ext|~/.config/<cli>/*.ext` en un
   seul motif séparé par `|` : le tri écrase l'ordre de priorité voulu (système avant utilisateur).

Tout le reste de l'API consommée par pyclifer est inchangé.

**Vérification préalable (déjà faite manuellement) :** worktree jetable + venv isolé (Python
3.13), click-extra **9.5.1** (Click 8.5.0) réellement installé.

- Avec les 4 renommages seuls : 665 tests passent, 1 échoue
  (`test_custom_config_option.py::TestCustomConfigOptionMultiPathSearch::test_etc_takes_priority_over_user_config` :
  renvoie `user` au lieu de `system`).
- Avec les 4 renommages + le correctif de l'ordre de recherche (Décision 2) : 666 tests passent,
  y compris avec `-W error::DeprecationWarning -W error::PendingDeprecationWarning`, et
  `pyclifer --help` s'affiche correctement.

Ce spec formalise ces changements avec TDD et les valide sur 3.10–3.13 via `tox`.

**Cas d'usage cible :** aucun changement de comportement observable pour les utilisateurs de
pyclifer — mise à jour de dépendance transparente. L'ordre de priorité des fichiers de config
(système avant utilisateur) est conservé.

**Stack :** deux dépendances directes déclarées explicitement (`boltons`, `extra-platforms`),
déjà présentes de façon transitive via click-extra.

---

## Design

### Décision 1 — Renommages 1:1, pas d'abstraction de compatibilité

Les 4 symboles renommés sont importés depuis `click_extra`/`click_extra.logging` à un seul
endroit chacun (`classes.py`, `log/formatters.py`, `log/handlers.py`, `log/config.py`). Pas besoin
d'alias de compatibilité ni de détection de version à l'exécution : pyclifer ne supporte qu'une
seule version de click-extra à la fois (bornée dans `pyproject.toml`), donc on renomme
directement, sans branche conditionnelle.

### Décision 2 — `CustomConfigOption` cherche chaque sous-motif séparément

`CustomConfigOption` surcharge `search_and_read_file(pattern)` : elle découpe le motif sur `|`
et appelle `super().search_and_read_file(sous_motif)` pour chaque sous-motif, dans l'ordre. Le
tri de click-extra ne s'applique alors qu'à l'intérieur d'un même répertoire, et l'ordre de
priorité défini par `default_pattern()` est préservé.

- Un sous-motif sans fichier (`FileNotFoundError`) est ignoré ; si aucun sous-motif ne trouve de
  fichier, la méthode relève `FileNotFoundError(f"No file found matching {pattern}")`, comme
  click-extra.
- La signature suit celle de click-extra 9 : triplets `(location, content, media_type)`.

Alternative écartée : changer `default_pattern()` pour ne plus utiliser `|`. `read_and_parse_conf`
et `--validate-config` attendent un motif unique ; la surcharge est plus locale et ne change pas
le contrat de `default_pattern()`.

### Décision 3 — Les classes publiques pyclifer gardent leur nom

`RichExtraFormatter`, `RichExtraStreamHandler`, `PycliferExtraGroup` ne changent pas de nom — seule
la classe de base importée de click-extra change. Aucun impact sur l'API publique de pyclifer, pas
de bump majeur de version nécessaire pour ce changement.

### Décision 4 — Déclarer `boltons` et `extra-platforms`

`core/classes.py` importe `boltons.iterutils` et `extra_platforms.is_linux` directement. Ces
paquets n'arrivent aujourd'hui que par transitivité via click-extra. Ils sont déclarés dans
`pyproject.toml` avec les mêmes planchers que click-extra 9.5.1 (`boltons>=26.2`,
`extra-platforms>=13.4`) pour ne pas dépendre d'un détail d'implémentation de click-extra.

### Décision 5 — Points confirmés sans risque

- `click_extra.version_option(**version_kw)` avec `version=...` : reste valide.
- `from click_extra.config import ConfigOption` : `ConfigOption` reste exporté.
- `PycliferOption`, `CustomConfigOption`, `PycliferVerbosityOption` : click-extra 9.3.0 rend
  keyword-only tous les arguments après `param_decls` ; la suite de tests complète passe sans
  changement de ces classes.
- `--show-params` → `--params` (8.5.0) et les metavars d'aide modifiés (9.1.0, 9.2.0) : aucune
  référence dans `src/`, `docs/` ni `tests/`.

### Décision 6 — Étendre la matrice `tox` avant de fusionner

L'audit manuel n'a couvert que Python 3.13. Avant de fusionner, `tox` doit passer sur 3.10, 3.11,
3.12 et 3.13 (click-extra 9.5.1 supporte Python >=3.10).

---

## Fichiers à modifier

| Fichier                                   | Changement                                                           |
|-------------------------------------------|----------------------------------------------------------------------|
| `pyproject.toml`                          | `click-extra>=9.5.1,<10.0.0` + `boltons>=26.2` + `extra-platforms>=13.4` |
| `src/pyclifer/core/classes.py`            | `click_extra.ExtraGroup` → `click_extra.Group` ; surcharge `search_and_read_file` |
| `src/pyclifer/core/log/formatters.py`     | `ExtraFormatter` → `Formatter` (import + base class)                 |
| `src/pyclifer/core/log/handlers.py`       | `ExtraStreamHandler` → `StreamHandler` (import + base class)         |
| `src/pyclifer/core/log/config.py`         | `extraBasicConfig` → `basicConfig` (import + appel + docstring)      |
| `tests/core/log/test_rich_logging.py`     | Cibles `@patch(...)` : `extraBasicConfig` → `basicConfig`            |
| `tests/core/options/test_custom_config_option.py` | Tests de la surcharge `search_and_read_file`                |
| `docs/api/classes.md`, `docs/configuration.md` | Mentionner l'ordre de priorité garanti si la page le décrit    |

---

## Tâche 1 : Créer la branche et bumper les contraintes

- [ ] **Étape 1 : Créer la branche**

```bash
git checkout -b feat/click-extra-9-upgrade
```

- [ ] **Étape 2 : `pyproject.toml`**

```toml
dependencies = [
    "click-extra>=9.5.1,<10.0.0",
    "boltons>=26.2",
    "extra-platforms>=13.4",
    ...
]
```

- [ ] **Étape 3 : Synchroniser l'environnement**

```bash
uv sync --extra dev --extra docs
python -c "from importlib.metadata import version; print(version('click-extra'))"  # 9.5.1 ou plus
```

---

## Tâche 2 : Constater l'échec (tests existants cassés par la montée de version)

- [ ] **Étape 1 : Lancer la suite sans toucher au code**

```bash
python -m pytest tests/ -v
```

Attendu : `AttributeError: module 'click_extra' has no attribute 'ExtraGroup'` à la collection
(import de `pyclifer.core.classes`), qui bloque toute la suite.

---

## Tâche 3 : Renommer `ExtraGroup` → `Group`

**Fichier :** `src/pyclifer/core/classes.py`

- [ ] **Étape 1 :**

```python
class PycliferExtraGroup(HandleResponseMixin, GlobalOptionsMixin, click_extra.Group):
```

---

## Tâche 4 : Renommer `ExtraFormatter` → `Formatter`

**Fichier :** `src/pyclifer/core/log/formatters.py`

- [ ] **Étape 1 :** attention à ne remplacer que le symbole de click-extra, pas
  `RichExtraFormatter` (utiliser des bornes de mots, ex. `\bExtraFormatter\b`).

```python
from click_extra.logging import Formatter


class RichExtraFormatter(Formatter):
    """Enhanced Formatter with Rich text capabilities and TRACE level support.

    Extends click-extra's Formatter to support Rich markup and custom TRACE level
    while preserving a click-extra's colorization system.
    """
```

---

## Tâche 5 : Renommer `ExtraStreamHandler` → `StreamHandler`

**Fichier :** `src/pyclifer/core/log/handlers.py`

- [ ] **Étape 1 :** même précaution (`\bExtraStreamHandler\b`).

```python
from click_extra.logging import StreamHandler


class RichExtraStreamHandler(StreamHandler):
    """Enhanced StreamHandler with Rich support and built-in security filtering.

    Extends click-extra's StreamHandler to use Rich for beautiful logging
    while maintaining compatibility with click.echo() and color support.
    Automatically includes SecretsMasker for sensitive data protection.
    """
```

---

## Tâche 6 : Renommer `extraBasicConfig` → `basicConfig`

**Fichier :** `src/pyclifer/core/log/config.py`

- [ ] **Étape 1 : Import**

```python
from click_extra.logging import basicConfig
```

- [ ] **Étape 2 : Appel** (dans `configure_rich_logging`)

```python
        basicConfig(
            stream_handler_class=RichExtraStreamHandler,
            formatter_class=RichExtraFormatter,
            force=True,
        )
```

- [ ] **Étape 3 : Docstring** — remplacer "Global configuration via extraBasicConfig"
  par "Global configuration via basicConfig".

---

## Tâche 7 : Mettre à jour les cibles de mock dans les tests

**Fichier :** `tests/core/log/test_rich_logging.py`

- [ ] **Étape 1 :** remplacer toutes les occurrences de `pyclifer.core.log.config.extraBasicConfig`
  (décorateurs `@patch` et `patch(...)`) par `pyclifer.core.log.config.basicConfig`, et les
  mentions dans les docstrings de test.

- [ ] **Étape 2 : Constater l'échec restant**

```bash
python -m pytest tests/ -v
```

Attendu : un seul échec,
`TestCustomConfigOptionMultiPathSearch::test_etc_takes_priority_over_user_config`
(`assert 'user' == 'system'`). Il documente la régression d'ordre (Décision 2).

---

## Tâche 8 : Préserver l'ordre de priorité des fichiers de config (TDD)

**Fichiers :** `tests/core/options/test_custom_config_option.py`, `src/pyclifer/core/classes.py`

- [ ] **Étape 1 : Tests (rouge)** — `test_etc_takes_priority_over_user_config` existe déjà et
  échoue. Ajouter :
  - `test_search_skips_subpattern_without_match` : `/etc` vide, fichier utilisateur présent →
    le fichier utilisateur est renvoyé (couvre le `continue` sur `FileNotFoundError`).
  - `test_search_raises_when_no_subpattern_matches` : aucun fichier nulle part →
    `pytest.raises(FileNotFoundError, match="No file found matching")`.
  - `test_search_yields_triples_in_pattern_order` : les résultats sont des triplets
    `(location, content, media_type)` dans l'ordre des sous-motifs.

- [ ] **Étape 2 : Implémentation (vert)** — dans `CustomConfigOption`, avant
  `_get_extension_pattern` :

```python
    def search_and_read_file(self, pattern: str) -> Iterator[tuple[Path | URL, str, str | None]]:
        """Search each pipe-separated sub-pattern in order to preserve priority.

        click-extra sorts the matches of a single pattern alphabetically, which would
        override the priority order built by default_pattern (system before user).
        Searching sub-patterns one at a time keeps that order.

        Args:
            pattern: Pipe-separated glob patterns, or a single pattern or URL.

        Yields:
            Triples of location, raw content and media type, in sub-pattern order.

        Raises:
            FileNotFoundError: When no sub-pattern matches any file.
        """
        found = False
        for sub_pattern in pattern.split("|"):
            try:
                for result in super().search_and_read_file(sub_pattern):
                    found = True
                    yield result
            except FileNotFoundError:
                continue
        if not found:
            raise FileNotFoundError(f"No file found matching {pattern}")
```

  Imports : `Iterator` depuis `collections.abc`, `URL` depuis `boltons.urlutils` (placés selon
  l'ordre d'imports défini dans `.claude/CLAUDE.md`).

- [ ] **Étape 3 : Confirmer le succès**

```bash
python -m pytest tests/ -v
```

Attendu : tous les tests passent.

---

## Tâche 9 : Vérification complète multi-version

- [ ] **Étape 1 : Suite complète + coverage**

```bash
python -m pytest tests/ -v
python -m pytest tests/ -q -W error::DeprecationWarning -W error::PendingDeprecationWarning
```

Attendu : 100% de couverture de branches maintenu sur les modules touchés.

- [ ] **Étape 2 : Lint**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

- [ ] **Étape 3 : Matrice complète 3.10–3.13**

```bash
tox
```

Si un échec apparaît sur une version précise de Python, l'investiguer avant de continuer.

- [ ] **Étape 4 : Documentation**

```bash
mkdocs build --strict
```

Vérifier que `docs/` ne référence pas les noms `Extra*`/`extraBasicConfig` de click-extra, et
compléter la page de configuration si elle décrit l'ordre de recherche des fichiers.

---

## Tâche 10 : Commit

```bash
git add pyproject.toml uv.lock src/ tests/ docs/ .claude/specs/11-click-extra-9-upgrade.md
git commit -m "$(cat <<'EOF'
♻️ refactor(deps): upgrade click-extra to 9.x

- click-extra 8.0.0 drops the Extra prefix from several internal classes;
  pyclifer imports 4 of them directly (ExtraGroup, ExtraFormatter,
  ExtraStreamHandler, extraBasicConfig) — renamed to their 9.x equivalents
- click-extra now sorts matches of a single config pattern alphabetically,
  which broke the system-before-user priority; CustomConfigOption searches
  each pipe-separated sub-pattern in order to keep it
- declare boltons and extra-platforms, imported directly by core/classes.py
- bump dependency floor to click-extra>=9.5.1,<10.0.0
EOF
)"
```

Obtenir la validation utilisateur avant de fusionner dans `main`, puis supprimer la branche.
