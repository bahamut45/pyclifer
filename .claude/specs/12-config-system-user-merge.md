# Fusion des configs système et utilisateur (utilisateur prioritaire)

**Prérequis :** la spec `11-click-extra-9-upgrade.md` est fusionnée (ce spec s'appuie sur
`ConfigOption.read_and_parse_all_conf` et sur le triplet `(location, content, media_type)` de
click-extra 9.x, ainsi que sur la surcharge `search_and_read_file` de la spec 11).

**Objectif :** Quand un fichier de config existe à la fois dans `/etc/<cli>/` et dans
`~/.config/<cli>/`, les deux sont lus et fusionnés en profondeur, et la valeur de l'utilisateur
gagne en cas de conflit. Un administrateur fixe des valeurs par défaut pour tous, chaque
utilisateur peut les surcharger, et `--config` explicite reste prioritaire sur tout.

**Constat (mesuré sur `main`, click-extra 7.20.1) :** CLI de test `mytestcli`, vrai faux `/etc` et
vrai `~/.config` (espace de noms isolé, voir Annexe).

| Scénario                   | Résultat actuel                                                              |
|----------------------------|------------------------------------------------------------------------------|
| A. aucun fichier           | valeurs par défaut                                                           |
| B. système seul            | valeurs système                                                              |
| C. utilisateur seul        | valeurs utilisateur                                                          |
| **D. système + utilisateur** | **`source=system`, `only_user=none`** : le fichier utilisateur est ignoré en entier |
| E. `--config` explicite    | valeurs du fichier explicite                                                 |

`docs/configuration.md` (« Files found later override values from earlier files, so users can
override system defaults ») contredit le comportement D. Le test existant
`test_etc_takes_priority_over_user_config` valide le comportement actuel, pas la documentation.

**Cas d'usage cible :** `/etc/myapp/config.toml` fixe `timeout = 60` et `database-url = ...` ;
`~/.config/myapp/config.toml` fixe `timeout = 10`. Résultat : `timeout = 10` (utilisateur) et
`database-url` hérité du système.

**Stack :** `deepmerge` déclaré comme dépendance directe (déjà présent via click-extra).

---

## Design

### Décision 1 — Fusion profonde, ordre de priorité utilisateur > système

Priorité décroissante : `--config` explicite > `~/.config/<cli>/` > `/etc/<cli>/`. Les tables sont
fusionnées récursivement (deepmerge `always_merger`) ; en cas de conflit sur une clé, la couche de
priorité la plus haute gagne. Les listes sont concaténées (comportement par défaut de
`always_merger`) : à documenter dans `docs/configuration.md`.

### Décision 2 — Ne pas utiliser l'option `cascade` de click-extra

Mesuré avec click-extra 9.5.1 et `cascade=True` : les deux fichiers sont lus et posés comme couches
d'un `ChainMap`, mais la fusion n'est faite qu'au premier niveau. Pour une sous-commande
(`[mytestcli.hello]`), Click lit la section de la couche utilisateur seule : les clés du système
sont perdues (`only_system=none`). `cascade` ne donne donc pas le comportement voulu.

### Décision 3 — Surcharger `read_and_parse_conf` dans `CustomConfigOption`

`CustomConfigOption.read_and_parse_conf(pattern)` :

1. appelle `self.read_and_parse_all_conf(pattern)` : fichiers parsés dans l'ordre de découverte,
   priorité la plus haute en premier (la surcharge `search_and_read_file` de la spec 11 garantit
   que cet ordre est celui des sous-motifs) ;
2. fusionne les couches de la plus basse à la plus haute priorité ;
3. renvoie `(location_de_la_couche_prioritaire, conf_fusionnée)` — la même forme qu'avant, donc
   aucun changement pour le reste de click-extra ;
4. sans couche (aucun fichier, ou fichiers vides), délègue à `super().read_and_parse_conf` pour
   conserver ses erreurs (`FileNotFoundError`, fichier vide).

### Décision 4 — `default_pattern()` met la plus haute priorité en premier

`default_pattern()` produit `~/.config/<cli>/*.ext|/etc/<cli>/*.ext` (utilisateur avant système).
La docstring documente que l'ordre des sous-motifs est l'ordre de priorité décroissante.

### Décision 5 — `--config` explicite inchangé

Un `--config` explicite épingle une source unique (comportement click-extra, non modifié ici).

### Décision 6 — Changement de comportement assumé

Un utilisateur qui avait un fichier `~/.config/<cli>/` jusque-là ignoré (parce que `/etc` existait)
verra ses valeurs désormais appliquées. À signaler dans le changelog et la note de version
(version 0.x : bump mineur).

### Limites connues

- Une erreur de validation stricte est attribuée au fichier de plus haute priorité, pas au fichier
  fautif exact (la fusion est faite avant la validation).
- `ctx.meta` expose la configuration fusionnée.

---

## Fichiers à modifier

| Fichier                                           | Changement                                                  |
|---------------------------------------------------|-------------------------------------------------------------|
| `pyproject.toml`                                  | ajouter `deepmerge>=1.0.1`                                  |
| `src/pyclifer/core/classes.py`                    | `read_and_parse_conf` ; ordre de `default_pattern`          |
| `tests/core/options/test_custom_config_option.py` | remplacer le test de priorité, ajouter les tests de fusion  |
| `docs/configuration.md`                           | section « Configuration Search Order » et exemples          |
| `docs/api/classes.md`                             | docstring de `CustomConfigOption` (rendue par mkdocstrings) |

---

## Tâche 1 : Branche

- [ ] `git checkout -b feat/config-system-user-merge`

## Tâche 2 : Tests (rouge)

**Fichier :** `tests/core/options/test_custom_config_option.py`

- [ ] **Étape 1 :** remplacer `test_etc_takes_priority_over_user_config` par
  `test_user_overrides_system_on_conflict` : `/etc` fixe `source = 'system'`, l'utilisateur
  `source = 'user'` → `source == 'user'`.
- [ ] **Étape 2 :** ajouter
  - `test_keys_from_both_files_are_merged` : une clé propre à chaque fichier est présente
    dans le résultat.
  - `test_nested_tables_are_deep_merged` : `[app.hello]` définit `a` côté système et `b` côté
    utilisateur → `a` et `b` présents, pas seulement la table utilisateur.
  - `test_returns_highest_priority_location` : le chemin renvoyé est celui du fichier utilisateur.
  - `test_single_file_is_returned_unchanged` : un seul fichier → contenu inchangé.
  - `test_no_file_raises_file_not_found` : `pytest.raises(FileNotFoundError, match="No file found")`.
  - `test_empty_files_delegate_to_parent` : fichiers vides → comportement du parent (couvre la
    branche de délégation).
  - `test_default_pattern_lists_user_before_system` : l'ordre des sous-motifs.
- [ ] **Étape 3 :** `python -m pytest tests/core/options/ -v` → les nouveaux tests échouent.

## Tâche 3 : Implémentation (vert)

**Fichier :** `src/pyclifer/core/classes.py`

- [ ] **Étape 1 : `default_pattern`** : `"|".join(reversed(all_patterns))` en mettant à jour la
  docstring (« highest priority first »).
- [ ] **Étape 2 : surcharge**

```python
    def read_and_parse_conf(
        self, pattern: str
    ) -> tuple[Path | URL | None, dict[str, Any] | None]:
        """Read every matching file and deep-merge them, highest priority winning.

        Files are discovered in sub-pattern order (user before system), so the first
        layer has the highest priority. Layers are merged from lowest to highest priority.

        Args:
            pattern: Pipe-separated glob patterns, or a single pattern or URL.

        Returns:
            The location of the highest priority file and the merged configuration.

        Raises:
            FileNotFoundError: When no file matches the pattern.
        """
        # Deferred import: keeps deepmerge off the startup path of every CLI.
        from deepmerge import always_merger

        layers = list(self.read_and_parse_all_conf(pattern))
        if not layers:
            return super().read_and_parse_conf(pattern)
        merged: dict[str, Any] = {}
        for _location, conf in reversed(layers):
            merged = always_merger.merge(merged, conf)
        return layers[0][0], merged
```

- [ ] **Étape 3 :** `python -m pytest tests/ -v` → tout passe, couverture de branches à 100 %.

## Tâche 4 : Vérification de bout en bout

- [ ] Rejouer l'Annexe. Résultat attendu : A défauts ; B système ; C utilisateur ;
  **D `source=user only_system=yes only_user=yes`** ; E explicite.

Vérifié sur un prototype jetable (click-extra 9.5.1) : D donne exactement
`source=user only_system=yes only_user=yes`.

## Tâche 5 : Documentation

- [ ] `docs/configuration.md` : réécrire « Configuration Search Order » (priorité décroissante
  `--config` > utilisateur > système, fusion profonde, listes concaténées) et ajouter l'exemple
  `timeout` / `database-url` du cas d'usage.
- [ ] `mkdocs build --strict`.

## Tâche 6 : Lint, tox et commit

```bash
ruff check src/ tests/ && ruff format src/ tests/
tox
git add pyproject.toml uv.lock src/ tests/ docs/ .claude/specs/12-config-system-user-merge.md
git commit  # ✨ feat(config): merge system and user config files, user wins
```

Obtenir la validation utilisateur avant de fusionner dans `main`, puis supprimer la branche.
Archiver la spec dans `.claude/specs/archived/` une fois toutes les tâches cochées `✅`.

---

## Annexe — Test de bout en bout (sans root)

Un espace de noms utilisateur remplace `/etc` par un tmpfs privé ; rien n'est modifié sur le
système. Le script de la CLI doit s'appeler exactement comme `name=` (`info_name` détermine les
dossiers cherchés : `/etc/<info_name>/` et `~/.config/<info_name>/`).

`mytestcli` (fichier sans extension) :

```python
from pyclifer import app_group, option


@app_group(name="mytestcli")
def cli():
    """Test app."""


@cli.command()
@option("--source", default="none")
@option("--only-system", default="none")
@option("--only-user", default="none")
def hello(source, only_system, only_user):
    """Print resolved values."""
    print(f"source={source} only_system={only_system} only_user={only_user}")


if __name__ == "__main__":
    cli()
```

`run.sh`, lancé avec `unshare -Urm ./run.sh <python> <mytestcli> <dossier-de-travail>` :

```bash
#!/bin/bash
PY=$1; APP=$2; D=$3
mount -t tmpfs tmpfs /etc || exit 1
export HOME=$D/home XDG_CONFIG_HOME=$D/home/.config
run() { echo "== $1"; (cd $D && $PY $APP "${@:2}" hello 2>&1 | tail -3); }
mkdir -p /etc/mytestcli $HOME/.config/mytestcli
run "A: aucun fichier"
printf '[mytestcli.hello]\nsource="system"\nonly_system="yes"\n' > /etc/mytestcli/config.toml
run "B: systeme seul"
rm /etc/mytestcli/config.toml
printf '[mytestcli.hello]\nsource="user"\nonly_user="yes"\n' > $HOME/.config/mytestcli/config.toml
run "C: utilisateur seul"
printf '[mytestcli.hello]\nsource="system"\nonly_system="yes"\n' > /etc/mytestcli/config.toml
run "D: systeme + utilisateur"
printf '[mytestcli.hello]\nsource="explicit"\n' > $D/explicit.toml
run "E: --config explicite" --config $D/explicit.toml
```
