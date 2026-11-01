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
Chaque élément doit être déclaré dans `tests/integration/scenarios.py`, dans **une seule** de trois catégories :
`COVERED` (nom du test qui l'exerce, vérifié), `EXCLUDED` (**raison obligatoire**) ou `PENDING` (temporaire :
l'item de la spec qui écrira le scénario). Chaque item retire ses entrées de `PENDING` ; un dernier test, marqué
`xfail(strict=True)` tant qu'il en reste, échoue quand la liste est vide et force à retirer le marqueur. Ajouter un champ, une option ou un symbole public sans scénario fait échouer la suite : les
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

### Décision 3 — Matrice : produit complet des axes principaux, un champ à la fois pour le reste

Axes croisés en produit complet (48 configurations) : `use_rich_help` (oui/non), options automatiques
(défauts de `app_group` ou toutes inactives), `output_format_default` (json, yaml, table, rich, raw, text),
`handle_response` (oui/non). Tous les autres champs, `timer` compris, sont variés **un à la fois** sur les deux
chemins d'aide. Le plan initial prévoyait un échantillonnage deux à deux ; il est écarté : à ce volume le
produit complet est plus simple et plus complet. Mesuré : la construction d'une application coûte moins d'une
milliseconde, ce sont les invocations (4 à 17 ms, surtout le rendu Rich) qui font la durée.

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
| `tests/integration/harness.py`             | Harnais : `build_app`, `BuiltApp`, `assert_healthy` (contrat « fonctionne ») |
| `tests/integration/conftest.py`            | Isolation de l'environnement (HOME et XDG_CONFIG_HOME temporaires) |
| `tests/integration/test_harness.py`        | Tests du harnais lui-même                                         |
| `tests/integration/inventory.py`           | Découverte de l'inventaire par introspection                      |
| `tests/integration/scenarios.py`           | `COVERED`, `EXCLUDED`, `PENDING`                                  |
| `tests/integration/test_inventory.py`      | Garde-fou d'exhaustivité (décision 1)                             |
| `tests/integration/test_group_config_matrix.py` | Matrice `GroupConfig` (décisions 2 et 3)                     |
| `tests/integration/test_automatic_options.py`   | Effet réel de chaque option automatique                       |
| `tests/integration/test_propagation.py`    | Parité et propagation (décision 5)                                |
| `tests/integration/test_public_api.py`     | Chaque symbole public utilisable dans une application minimale    |
| `CLAUDE.md`                                | Section « Testing Structure » : mentionner `tests/integration/`   |
| `docs/development.md`                      | Organisation des tests d'intégration et règle d'exhaustivité      |

---

## ✅ Item 1 : Inventaire et garde-fou d'exhaustivité

Branche : `feat/integration-test-inventory`. Tests d'abord (`tests/integration/test_inventory.py`) : la
découverte trouve les champs de `GroupConfig`, les fabriques d'options, les symboles publics (sans les noms
`__dunder__`, qui sont des métadonnées) et les événements ; le garde-fou échoue pour une fonctionnalité non
déclarée, une entrée obsolète, un doublon, une exclusion sans raison, une référence `COVERED` qui ne pointe
vers aucun test.

Écart avec le premier jet de la spec : la liste d'exclusion ne pouvait pas démarrer vide avec une suite verte.
La catégorie temporaire `PENDING` a été ajoutée (décision 1). État initial mesuré : **103 fonctionnalités**
= 1 `COVERED` (`event.config.loaded`, déjà testé par `TestCustomConfigOptionConfigLoadedEvent`) + 102 `PENDING`
(10 à l'item 3, 20 à l'item 4, 8 à l'item 5, 64 à l'item 6). Contrôle par mutation : un champ ajouté sans
scénario et une fonctionnalité supprimée sont tous deux détectés, avec leur nom.

## ✅ Item 2 : Harnais de scénario

`tests/integration/harness.py` : `build_app(**config)` construit une `app_group` nommée `cli` avec une
commande `hello` qui retourne une `Response`, en enregistrant les avertissements émis pendant la construction ;
`assert_healthy(built)` applique le contrat de la décision 2. Un fixture `autouse` isole HOME et
XDG_CONFIG_HOME, pour qu'un fichier de config de l'utilisateur ne soit jamais chargé.

Contrat mesuré avant d'être écrit, sur six configurations (défaut, json, yaml, `handle_response=False`,
`use_rich_help=False`, sans option automatique) : `--help` donne 0, `hello` donne 0, une commande inconnue
donne 2, et les noms d'options suivent les drapeaux `add_*_option`. Avec `handle_response=False`, `hello`
n'imprime rien : le contrat ne vérifie alors que le code de sortie.

**L'appel nu n'est pas dans le contrat.** Mesuré : il rend l'aide avec le code 2 sur ces six configurations,
mais la spec demandait de le mesurer avant de l'affirmer ; la matrice de l'item 3 le consigne.

Tests du harnais (`test_harness.py`, 19 cas) : 12 applications saines (six formats de sortie, sans aide Rich,
sans option automatique, sans traitement des réponses, avec `timer`) et 7 défauts simulés, tous détectés avec
un message qui nomme le problème : option dupliquée, option absente pour un drapeau actif, option présente
pour un drapeau inactif, avertissement à la construction, commande en échec, sortie JSON invalide, commande
inconnue qui ne sort pas avec le code 2.

## ✅ Item 3 : Matrice `GroupConfig` — mesure

`tests/integration/test_group_config_matrix.py` : 48 configurations croisées (`TestMainAxes`), 28
variations d'un champ (`TestSingleFields`) et les effets observables (`TestFieldEffects`). **Aucune correction
à cet item.** Chaque attente a été mesurée sur le code avant d'être écrite.

| Mesure (122 configurations au relevé)                         | Résultat                                                      |
|---------------------------------------------------------------|---------------------------------------------------------------|
| Construction, `--help`, `hello`, commande inconnue, options    | sains, sauf le défaut ci-dessous                              |
| Appel nu                                                       | l'aide, code 2, dans 100 % des cas                            |
| `--config fichier hello` (cas qui ont l'option)               | code 0, dans 100 % des cas                                    |
| Commande qui lève une exception                               | code 1, dans 100 % des cas                                    |
| `unhandled_exception_log_level`                               | le niveau de l'enregistrement suit la config (error, warning, critical) |
| `exit_codes_class`                                            | un code personnalisé devient le code de sortie ; une classe invalide lève `ValueError` |
| `name`                                                        | nom de l'application et ligne d'usage                         |

**Défaut trouvé (1)** : `output_format_default` est **ignoré quand `add_output_format_option=False`**.
Dans une même application (`output_format_default="json"`, sans `--output-format`), une commande inconnue
répond en JSON, tandis qu'une commande normale et une commande en échec répondent en `table`
(« No dataset available. »). Avec l'option présente, la commande en échec répond bien en JSON ou YAML
(`success: false`, `error_code: 1`). Un format par défaut invalide (`"bogus"`) est rejeté avec l'option
(code 2) et ignoré en silence sans elle. Cas concernés : option absente, `handle_response` actif, format json
ou yaml, soit 4 configurations ; ils sont marqués `xfail(strict=True)` (8 résultats : 2 tests chacun).

**Non observé** : l'effet de `use_rich_logging`, `enable_secrets_filter` et `sensitive_fields` (masquage des
secrets, gestionnaire Rich). Ces champs sont construits et lancés sans erreur seulement, et déclarés comme tels
dans `scenarios.py`. À mesurer avec les options de journalisation de l'item 4.

**Durée** : la matrice ajoute environ 10 s (sans mesure de couverture) à la suite, soit près du double de
la durée actuelle, répartis uniformément sur 299 tests. Si cela gêne, un marqueur `integration` permettra de
l'exclure du cycle rapide.

## Item 4 : Options automatiques

Pour chaque `add_*_option` et `timer` (et l'effet réel de `use_rich_logging`, `enable_secrets_filter`,
`sensitive_fields`, non observé à l'item 3) : présence ; valeur par défaut ; variable d'environnement
(`auto_envvar_prefix`) ; effet réel (`--verbosity` change le niveau de journalisation, `--log-file` crée le
fichier, `--version` affiche la version, `--config` charge le fichier, `--output-format` choisit le rendu).

## Item 5 : Propagation et parité

Les invariants de la décision 5, sur les chemins Rich et non Rich.

## Item 6 : API publique

Chaque symbole de `pyclifer.__all__` est importable et utilisable dans une application minimale (les types
Click réexportés, le journaliseur, les classes de réponse et de rendu).

## Item 7 : Défaut — `output_format_default` ignoré sans `--output-format`

Trouvé à l'item 3 (voir son rapport). Tests en échec : les 8 `xfail(strict=True)` de la matrice, qui doivent
« passer » visiblement une fois corrigé, ce qui oblige à retirer les marqueurs. Décision à prendre avec
l'utilisateur avant de corriger : sans l'option, `output_format_default` doit-il fixer le format pour toute
l'application (hypothèse la plus cohérente avec la réponse déjà donnée aux erreurs d'usage), et que fait
un format invalide ?

## Item 7+ : Autres défauts trouvés

Un item par défaut mesuré aux items 3 à 6 : test en échec, correctif minimal, mise à jour de la documentation,
et validation de l'utilisateur si le comportement change.

## Item final : Vérification complète et documentation

`ruff`, `pytest`, `tox` (Python 3.10 à 3.13), `mkdocs build --strict`, durée de la suite relevée, mise à jour de
`CLAUDE.md` et de `docs/development.md`. Archivage de la spec quand tous les items sont `✅`.

Procédure par item (CLAUDE.md) : branche, TDD, ruff, pytest, un commit (code, tests, docs, spec avec `✅`),
validation de l'utilisateur, fusion dans `main`, branche supprimée.
