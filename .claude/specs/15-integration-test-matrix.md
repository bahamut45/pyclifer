# Tests d'intégration de tout ce que pyclifer apporte

**Contexte :** pas d'issue dédiée. La spec naît de la correction du chemin `use_rich_help=False`, que la suite
de tests ne voyait pas (voir « Constat »).

**Objectif :** Détecter les manques et les défauts de composition de pyclifer avant qu'un utilisateur les
rencontre. Chaque fonctionnalité du framework est découverte par **introspection du code**, puis exercée dans une
application réelle (construite, puis lancée), et non seulement construite.

**Dépend de :** rien. **Recommandé avant :** l'item 2 de la spec 09 (elle change les bases des groupes, donc le
chemin que cette spec protège).

**Stack :** pytest, `pyclifer.testing.invoke`. Aucune nouvelle dépendance.

---

## Constat (mesuré)

Le défaut des options dupliquées sur `app_group(use_rich_help=False)` (25 options dont des doublons, contre 5
sur le chemin Rich, puis `RuntimeError: More than one ConfigOption` à l'exécution) est resté invisible :

- le seul test de ce chemin (`tests/core/test_rich_help_formatting.py`) construit le groupe et vérifie
  `hasattr(app, "main")` : il ne lance jamais l'application ;
- ni les tests, ni l'application de démo, ni le scaffolding n'utilisaient `use_rich_help=False` ;
- la couverture de lignes était de 100 % : elle prouve que les lignes s'exécutent, pas que l'application marche.

Le défaut est un défaut de **composition** (les options de pyclifer et celles de click-extra, correctes
séparément, se doublonnent une fois assemblées). Seul un test qui assemble puis lance une application le voit.

## Inventaire de la surface (relevé par introspection, à la date de la spec)

| Source                                          | Éléments                                                                 |
|-------------------------------------------------|--------------------------------------------------------------------------|
| `dataclasses.fields(GroupConfig)`               | 26 champs (`name`, `add_*_option`, `use_rich_help`, `handle_response`, `timer`, `on`, ...) |
| Fabriques d'options de `core/decorators.py`     | `option`, `config_option`, `verbosity_option`, `log_file_option`, `output_format_option`, `output_filter_option`, `pagination_options` |
| `pyclifer.__all__`                              | 71 symboles : décorateurs, classes (contexte, réponses, rendu, mixins, groupes), journalisation, types Click |
| `core/events.EVENTS`                            | événements du framework (`config.loaded`, puis ceux des specs suivantes)  |

---

## Design

### Décision 1 — L'inventaire est découvert, jamais listé à la main

Un test d'exhaustivité parcourt `dataclasses.fields(GroupConfig)`, les fabriques d'options et `pyclifer.__all__`.
Chaque élément doit avoir **un scénario déclaré** ou figurer dans une liste d'exclusion **justifiée par un
commentaire**. Ajouter un champ, une option ou un symbole public sans scénario fait échouer la suite : les
fonctionnalités futures (specs 05, 06, 09, ...) entrent donc automatiquement dans le périmètre.

### Décision 2 — Un contrat unique pour dire qu'une application « fonctionne »

Un scénario construit une application avec une configuration donnée, puis vérifie :

- construction sans exception ni avertissement ;
- noms d'options uniques (aucun doublon) ;
- `--help` : code 0 ;
- une sous-commande qui retourne une `Response` s'exécute : code 0, sortie valide dans le format demandé ;
- une commande inconnue : code 2 ; un appel nu : l'aide, code 2 (à mesurer avant de l'affirmer) ;
- `--version`, `--config`, `--verbosity`, `--log-file`, `--output-format` présents si et seulement si leur
  drapeau `add_*_option` est actif.

### Décision 3 — Matrice bornée par combinaisons deux à deux

Axes : `use_rich_help` (oui/non), les cinq `add_*_option` (défauts de `app_group`, tous inactifs, tous actifs),
`output_format_default` (json, yaml, table, rich, raw, text), `handle_response` (oui/non), fichier de config
(aucun, explicite), `timer`, `auto_envvar_prefix`. Le produit complet est écarté au profit d'un échantillonnage
deux à deux, pour tenir sous une durée de suite raisonnable (objectif : quelques secondes).

### Décision 4 — Mesurer d'abord, ne rien supposer

Conformément au `CLAUDE.md`, l'item 3 **produit un rapport** (scénario, résultat observé) sans corriger quoi que
ce soit. Chaque défaut trouvé devient un item séparé, avec test en échec, correctif, et validation de
l'utilisateur quand le correctif change un comportement existant.

### Décision 5 — Propriétés de parité et de propagation

Au-delà des scénarios, des invariants vérifiés sur plusieurs configurations : `use_rich_help` ne change pas les
options ; un sous-groupe créé par `group()` n'a pas d'options propres ; une option `is_global=True` atteint les
sous-commandes à trois niveaux de profondeur, qu'elles soient ajoutées par `@command`, `add_command` ou ajoutées
après coup ; `context=True` alimente `context_factory`.

### Décision 6 — Hors périmètre

- Le projet généré par `pyclifer project init` (génération, installation, exécution de ses propres tests) :
  spec séparée, si l'inventaire montre un besoin.
- Performance et robustesse en charge.

---

## Fichiers à modifier

| Fichier                                    | Changement                                                        |
|--------------------------------------------|-------------------------------------------------------------------|
| `tests/integration/` (nouveau dossier)     | Tests d'intégration transverses (ne reflètent pas un module de `src/`) |
| `tests/integration/conftest.py`            | Harnais : fabrique d'application, contrat « fonctionne »          |
| `tests/integration/test_inventory.py`      | Garde-fou d'exhaustivité (décision 1)                             |
| `tests/integration/test_group_config_matrix.py` | Matrice `GroupConfig` (décisions 2 et 3)                     |
| `tests/integration/test_automatic_options.py`   | Effet réel de chaque option automatique                       |
| `tests/integration/test_propagation.py`    | Parité et propagation (décision 5)                                |
| `tests/integration/test_public_api.py`     | Chaque symbole public utilisable dans une application minimale    |
| `CLAUDE.md`                                | Section « Testing Structure » : mentionner `tests/integration/`   |
| `docs/development.md`                      | Organisation des tests d'intégration et règle d'exhaustivité      |

---

## Item 1 : Inventaire et garde-fou d'exhaustivité

Branche : `feat/integration-test-inventory`. Test d'abord : la suite échoue tant qu'un champ de `GroupConfig`,
une fabrique d'options ou un symbole de `pyclifer.__all__` n'a ni scénario ni exclusion justifiée. Le premier
état de la liste d'exclusion est volontairement vide : chaque entrée ajoutée doit porter sa raison.

## Item 2 : Harnais de scénario

Fabrique `build_app(**config)` qui crée l'application avec une commande de test, et vérificateur
`assert_healthy(app)` qui applique le contrat de la décision 2. Tests du harnais lui-même (un cas sain, un
cas avec doublon d'options volontaire, qui doit être détecté).

## Item 3 : Matrice `GroupConfig` — mesure

Test paramétré sur l'échantillon deux à deux. **Aucune correction à cet item** : le résultat est consigné dans
cette spec (tableau scénario, résultat) et chaque échec devient un item 3.x. Les cas qui échouent sont marqués
`xfail(strict=True)` avec la raison, pour que la suite reste verte et que la correction les fasse « passer »
visiblement.

## Item 4 : Options automatiques

Pour chaque `add_*_option` et `timer` : présence ; valeur par défaut ; variable d'environnement
(`auto_envvar_prefix`) ; effet réel (`--verbosity` change le niveau de journalisation, `--log-file` crée le
fichier, `--version` affiche la version, `--config` charge le fichier, `--output-format` choisit le rendu).

## Item 5 : Propagation et parité

Les invariants de la décision 5, sur les chemins Rich et non Rich.

## Item 6 : API publique

Chaque symbole de `pyclifer.__all__` est importable et utilisable dans une application minimale (les types
Click réexportés, le journaliseur, les classes de réponse et de rendu).

## Item 7+ : Défauts trouvés

Un item par défaut mesuré aux items 3 à 6 : test en échec, correctif minimal, mise à jour de la documentation,
et validation de l'utilisateur si le comportement change.

## Item final : Vérification complète et documentation

`ruff`, `pytest`, `tox` (Python 3.10 à 3.13), `mkdocs build --strict`, durée de la suite relevée, mise à jour de
`CLAUDE.md` et de `docs/development.md`. Archivage de la spec quand tous les items sont `✅`.

Procédure par item (CLAUDE.md) : branche, TDD, ruff, pytest, un commit (code, tests, docs, spec avec `✅`),
validation de l'utilisateur, fusion dans `main`, branche supprimée.
