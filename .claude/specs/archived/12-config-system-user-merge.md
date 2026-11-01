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

1. découpe le motif sur `|` et appelle `self.read_and_parse_all_conf(sous_motif)` pour chaque
   sous-motif, dans l'ordre (un sous-motif sans fichier est ignoré) ;
2. fusionne toutes les couches **dans l'ordre de lecture, la dernière gagnant** : système, puis
   utilisateur ; dans un même dossier, ordre alphabétique (`base.toml` puis `production.toml`),
   ce qui correspond à la section « Multiple Configuration Files » de la doc ;
3. renvoie `(location_de_la_dernière_couche, conf_fusionnée)` — la même forme qu'avant, donc
   aucun changement pour le reste de click-extra ;
4. sans couche (aucun fichier, ou fichiers vides), délègue à `super().read_and_parse_conf` : la
   découverte automatique ignore les fichiers vides et renvoie `(None, None)`.

### Décision 4 — `default_pattern()` inchangé

`default_pattern()` produit déjà `/etc/<cli>/*.ext|~/.config/<cli>/*.ext`, soit l'ordre de
priorité croissante. Il n'est pas modifié (le plan initial prévoyait de l'inverser avec « la
première couche gagne » ; l'ordre « la dernière gagne » est plus simple et cohérent avec la doc).

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
| `src/pyclifer/core/classes.py`                    | surcharge de `read_and_parse_conf`                          |
| `tests/core/options/test_custom_config_option.py` | remplacer le test de priorité, ajouter les tests de fusion  |
| `docs/configuration.md`                           | section « Configuration Search Order » et exemples          |

---

## ✅ Tâche 1 : Branche

- [x] `git checkout -b feat/config-system-user-merge`

## ✅ Tâche 2 : Tests (rouge)

**Fichier :** `tests/core/options/test_custom_config_option.py`

- [x] **Étape 1 :** remplacer `test_etc_takes_priority_over_user_config` par
  `test_user_overrides_system_on_conflict` : `/etc` fixe `source = 'system'`, l'utilisateur
  `source = 'user'` → `source == 'user'`.
- [x] **Étape 2 :** ajouter
  - `test_keys_from_both_files_are_merged`, `test_nested_tables_are_deep_merged` (section de
    sous-commande fusionnée clé par clé),
  - `test_returns_highest_priority_location` (le fichier utilisateur),
  - `test_single_file_is_returned_unchanged`,
  - `test_later_file_in_a_directory_overrides_earlier_one` (`base.toml` / `production.toml`),
  - `test_no_file_raises_file_not_found`,
  - `test_blank_files_are_ignored` (la découverte automatique renvoie `(None, None)`).
- [x] **Étape 3 :** `python -m pytest tests/core/options/ -v` → les nouveaux tests échouent.

## ✅ Tâche 3 : Implémentation (vert)

**Fichier :** `src/pyclifer/core/classes.py`

- [x] **Étape 1 : surcharge** (voir `CustomConfigOption.read_and_parse_conf`) : boucle sur les
  sous-motifs, `read_and_parse_all_conf` par sous-motif, fusion `deepmerge.always_merger` sur des
  copies profondes, renvoi de `(layers[-1][0], merged)`, délégation à `super()` sans couche.
  Importer `copy` et différer l'import de `deepmerge` (démarrage de la CLI).
- [x] **Étape 2 : dépendance** : `deepmerge>=1.0.1` dans `pyproject.toml`, puis `uv sync`.
- [x] **Étape 3 :** `python -m pytest tests/ -v` → tout passe, couverture de branches à 100 %.

## ✅ Tâche 4 : Vérification de bout en bout

- [x] Rejouer l'Annexe. Résultat attendu : A défauts ; B système ; C utilisateur ;
  **D `source=user only_system=yes only_user=yes`** ; E explicite.

Vérifié sur le code réel (click-extra 9.5.1) : D donne exactement
`source=user only_system=yes only_user=yes`.

## ✅ Tâche 5 : Documentation

- [x] `docs/configuration.md` : réécrire « Configuration Search Order » (priorité décroissante
  `--config` > utilisateur > système, fusion profonde, listes concaténées) et ajouter l'exemple
  `timeout` / `database-url` du cas d'usage.
- [x] `mkdocs build --strict`.

## ✅ Tâche 6 : Lint, tox et commit

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
