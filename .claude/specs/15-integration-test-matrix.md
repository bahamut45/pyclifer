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
ou yaml, soit 4 configurations, marquées `xfail(strict=True)` à l'item 3 (8 résultats : 2 tests chacun) puis
corrigées à l'item 7.

**Non observé** : l'effet de `use_rich_logging`, `enable_secrets_filter` et `sensitive_fields` (masquage des
secrets, gestionnaire Rich). Ces champs sont construits et lancés sans erreur seulement, et déclarés comme tels
dans `scenarios.py`. À mesurer avec les options de journalisation de l'item 4.

**Durée** : la matrice ajoute environ 10 s (sans mesure de couverture) à la suite, soit près du double de
la durée actuelle, répartis uniformément sur 299 tests. Si cela gêne, un marqueur `integration` permettra de
l'exclure du cycle rapide.

## ✅ Item 4 : Options automatiques — mesure

`tests/integration/test_automatic_options.py` (39 tests) : l'effet réel de chaque option, mesuré avant d'être
écrit, **dans un processus neuf** chaque fois que l'état global de la journalisation pouvait fausser la réponse
(deux mesures en un seul processus avaient d'abord donné de faux résultats). Un fixture restaure tous les
loggers entre tests : les gestionnaires de fichier des tests précédents fuyaient, ce que le test de rotation a
révélé.

| Option ou champ | Effet observé |
|---|---|
| `--version` | affiche la version déclarée (`cli, version 1.2.3`) |
| `--verbosity` | défaut WARNING ; DEBUG et INFO montrent plus ; acceptée après la sous-commande ; valeur invalide : code 2 ; `verbosity_default_level` ; variable d'environnement |
| `--log-file` | fichier créé ; niveau du fichier indépendant de la console (TRACE par défaut) ; `log_file_default_level` ; `when`, `interval` et `backupCount` atteignent le gestionnaire |
| `--config` | les valeurs du fichier deviennent des défauts ; un argument explicite l'emporte |
| `--output-format` | `-o` et forme longue ; variable d'environnement ; valeur invalide : code 2 |
| `timer` | `execution_time` et `execution_time_str` dans les données, `Execution time:` en table |
| Variables d'environnement | `auto_envvar_prefix` renomme les variables et pilote les options |
| Fabriques d'options | les 7 fonctionnent sur une commande seule, hors `app_group` |

**Un seul gestionnaire de fichier** est attaché à deux loggers (`root` et `click_extra`) : la ligne n'est écrite
qu'une fois. Ce n'est pas un défaut.

**Observation, non assertée** : sans `version=` ni paquet installé, `--version` affiche `cli, version None`.

**Défauts trouvés (4), chacun en `xfail(strict=True)`, aucun corrigé à cet item** :

1. **`--verbosity ERROR` n'a aucun effet** (corrigé à l'item 8). Les avertissements restent affichés, alors que click-extra seul et
   `verbosity_default_level="ERROR"` les masquent. Le niveau passé en ligne de commande ne peut pas être plus strict
   que le défaut. La logique `set_level` de pyclifer ignore un niveau « moins verbeux » que celui déjà posé.
2. **`show_envvar=False` n'a aucun effet** (corrigé à l'item 9). `GroupConfig.show_envvar` n'est lu nulle part dans le code et n'est
   pas documenté.
3. **`enable_secrets_filter=False` n'a aucun effet.** Le masquage reste actif.
4. **`sensitive_fields` n'a aucun effet.** Un champ personnalisé n'est pas masqué, alors que la documentation
   promet qu'il l'est « en plus des défauts », console et fichier.

Les défauts 3 et 4 ont été corrigés à l'item 10 (cause mesurée : voir cet item).

## ✅ Item 5 : Propagation et parité

`tests/integration/test_propagation.py` (122 cas : 120 passent, 2 `xfail` stricts). Un arbre à trois niveaux (racine,
groupes `ops` et `deep`, une feuille par niveau) avec une option globale `--region` et une option de contexte `--env`,
construit des trois façons dont un utilisateur enregistre ses commandes (décorateur du groupe ; groupes remplis puis
rattachés de bas en haut ; groupes rattachés puis remplis de haut en bas), sur les deux chemins d'aide.

**Mesuré, puis figé par des tests.** L'option globale donnée à la feuille arrive à son callback aux trois niveaux, dans
les trois ordres, en Rich et en plain, et figure dans l'aide de la feuille. Les options de `cli`, de chaque groupe et de
chaque feuille sont identiques sur les deux chemins ; `group()` et `command()` n'ont aucune option propre.
`context_factory` reçoit la valeur de `--env` donnée avant la sous-commande, sur la feuille, par `CLI_ENV` ou par défaut,
est appelé une fois, et ne l'est pas pour afficher l'aide. `on=` et `cli.on()` exécutent leurs gestionnaires dans
l'ordre, un `Event` personnalisé est émis, un nom inconnu est refusé. Un groupe assemblé à la main avec les trois mixins
publics propage, répond et émet ; `PycliferGroup` est la variante plain du groupe d'application (un groupe d'application
Rich n'en est pas une instance). Contrôle par mutation : cinq lignes de production neutralisées, toutes détectées.

**Écart 3 — valeur donnée avant la sous-commande : documenté, comportement figé.** `cli --region X leaf` donne `X` à
la racine et laisse la valeur par défaut à la feuille, qui analyse sa propre copie du paramètre ; une option globale
`required=True` donnée avant la sous-commande sort avec le code 2. C'est cohérent avec `docs/api/mixins.md` (« real
subcommand parameters »). Arbitrage de l'utilisateur : documenter (avertissement ajouté à `docs/api/mixins.md`), pas de
changement de comportement.

**Défauts trouvés, arbitrés avec l'utilisateur, un item chacun.**
- Item 14 : une option globale propagée n'apparaît pas dans l'aide d'une commande créée par `cli.command()` quand
  l'application est plain (`use_rich_help=False`) et qu'elle n'a pas d'option de contexte. Mon arbre le masquait : l'option
  de contexte reconstruit le cache d'options de cloup par effet de bord.
- Item 15 : l'option de contexte et son panneau manquent dans l'aide des commandes de profondeur 2 et plus quand leur
  groupe a été rattaché avant d'être rempli (2 ordres sur 3, Rich et plain). Arbitrage : corriger.
- Item 16 : `use_rich_help=False` ne rend plain que le groupe racine et les commandes de `cli.command()` ; `group()` et
  `command()` produisent des classes Rich, d'où des boîtes Rich dans une application plain. Arbitrage : corriger.
- Item 17 : un groupe intermédiaire dont le callback n'accepte pas l'option globale plante (`TypeError`, y compris pour
  `ops leaf --help`). Arbitrage : ne lui passer que ce que son callback accepte.
- Item 18 : la variable d'environnement d'une option globale n'est pas lue de la même façon sur les deux chemins
  (voir l'item). Arbitrage en attente.

## Item 6 : API publique

Chaque symbole de `pyclifer.__all__` est importable et utilisable dans une application minimale (les types
Click réexportés, le journaliseur, les classes de réponse et de rendu).

## ✅ Item 7 : Défaut — `output_format_default` ignoré sans `--output-format`

Décision de l'utilisateur : `output_format_default` **conditionne toute l'application**. Une application
déclarée en json ne répond jamais dans un autre format de son propre chef : résultats, échecs et erreurs
d'usage. L'option `--output-format`, quand elle est exposée, surcharge le défaut pour l'appel.

Correctif (tests d'abord : les 8 `xfail` de la matrice ont été retirés pour devenir 8 échecs réels, puis
5 tests unitaires et 4 tests de `formats.py` ont été ajoutés) :

- `core/output/formats.py` : `OUTPUT_FORMATS`, liste unique des formats (l'option `--output-format` en
  dérive) et `validate_output_format` ;
- `GroupDecorator` : `output_format_default` est validé au début de `__call__` (une valeur inconnue lève
  `ValueError` à la décoration, comme `exit_codes_class`) et posé dans `ctx.meta["pyclifer.output_format"]`
  à la racine quand rien d'autre ne l'a posé. Un sous-groupe créé par `group()` ne le remplace pas ;
- documentation : `docs/output-formatting.md` (« The default format is the contract of the application »)
  et la docstring d'`app_group`.

**Défaut trouvé en chemin, corrigé dans la foulée.** Une commande définie avec `@sub.command()` sur un
sous-groupe créé par `group()`, **avant** que ce sous-groupe soit rattaché à l'application, n'imprimait rien
quand elle retournait une `Response`, même si l'application avait `handle_response=True` (sortie vide, code 0).
Mesuré identique avant le correctif du format. Cause lue dans le code : `HandleResponseMixin.command()` marquait
la commande « décidée » (désactivée) parce que le sous-groupe n'avait pas encore reçu le réglage, puis
`_apply_handle_response_to_group` sautait les commandes « décidées ». Cela contredisait « `handle_response=True`
enveloppe aussi les sous-groupes imbriqués » du `CLAUDE.md`. Correctif : seule une demande **explicite**
(`handle_response=True` ou `False`) pose la marque ; sans choix, la commande reste indécise et la propagation
peut l'envelopper. Trois tests : enveloppée une fois le sous-groupe rattaché, refus explicite respecté, rien
d'enveloppé quand l'application ne gère pas les réponses.

**`handle_response` devient tri-état sur le groupe** (décision de l'utilisateur, même sémantique que sur la
commande) : `None` hérite (défaut de `group()`), `True` active, `False` protège tout le sous-arbre. Avant, le
défaut `False` ne se distinguait pas d'un refus explicite. `app_group` garde `True` comme défaut, et `None`
y signifie ce défaut. Neuf tests (trois valeurs, deux ordres de rattachement, groupe imbriqué, `None` sur
l'application). Le mixin retient le refus explicite (`handle_response_opted_out`) et la propagation saute ce
sous-arbre ; la vérification est stricte (`is True`) pour ne pas confondre avec les doubles de test. Aucune
autre lecture de `GroupConfig.handle_response` dans le dépôt ni dans les templates du scaffolding.
L'item 5 couvre les deux ordres sur les chemins Rich et non Rich.

## ✅ Item 8 : Défaut — `--verbosity` ne pouvait pas être plus strict que le défaut

Décision de l'utilisateur : les niveaux de log doivent être respectés dans les deux sens.

**Cause, tracée appel par appel.** `--verbosity ERROR hello` provoque trois appels à `set_level` : la racine reçoit
`ERROR`, la pré-analyse reçoit `ERROR` (sans effet), puis la **sous-commande**, qui porte une copie de l'option
globale, reçoit sa valeur **par défaut** `WARNING`. La règle « le plus verbeux gagne » (`ERROR` est à l'indice 1,
`WARNING` à l'indice 2) laissait ce défaut écraser le choix de l'utilisateur. Un défaut était traité comme un choix.

**Correctif.** `set_level` lit la source du paramètre (`ParameterSource.DEFAULT` ou non) : une valeur par défaut ne
remplace jamais un niveau déjà posé, et un niveau choisi (ligne de commande, environnement, fichier de config)
remplace un niveau qui ne venait que d'un défaut. Entre deux niveaux choisis, la règle d'origine est conservée :
le plus verbeux gagne (mesuré dans les deux ordres). `ctx.meta["pyclifer.verbosity_from_default"]` retient
l'origine du niveau courant.

**Une erreur d'analyse corrigée en route.** J'avais d'abord écrit que `hello --verbosity ERROR` (option après la
sous-commande) échouait aussi : le test, écrit avant le code, passait déjà, donc c'était faux. Seuls le placement
avant la sous-commande et la variable d'environnement étaient touchés.

Neuf configurations vérifiées de bout en bout, un processus chacune (défaut, ERROR, CRITICAL, DEBUG, avant et après
la sous-commande, environnement, `verbosity_default_level` ERROR et DEBUG). Cinq tests unitaires de la règle et
quatre tests d'intégration. Documenté dans `docs/logging.md`.

## ✅ Item 9 : Défaut — `show_envvar` sans effet

Trouvé à l'item 4 : `GroupConfig.show_envvar` n'était lu nulle part. Décision de l'utilisateur : le champ fixe
`show_envvar` de **toutes les options automatiques** ; les options déclarées avec `@option` gardent leur propre
argument. Correctif : `GroupDecorator._apply_automatic_options` le transmet à `--output-format`, `--config`,
`--verbosity`, `--log-file` et `--time`. Tests : chacune des quatre variables est affichée par défaut et masquée
avec `show_envvar=False`, et l'aide ne contient plus aucun « env var » avec `timer=True`. Documenté dans
`docs/api/decorators.md`.

## ✅ Item 10 : Défaut — `enable_secrets_filter` et `sensitive_fields` perdus à l'exécution

Le plus grave des défauts trouvés : le framework promet de masquer les secrets (`docs/logging.md`) et ne le
faisait pas pour un champ personnalisé, ni ne pouvait être désactivé. Il y avait **deux causes indépendantes**,
mesurées une à une :

1. **Configuration perdue à l'exécution.** À la décoration, le gestionnaire de la console est créé avec la bonne
   configuration (sans filtre pour `enable_secrets_filter=False`, avec les champs pour `sensitive_fields`). Puis
   `PycliferVerbosityOption.set_level` appelle `configure_rich_logging(force_reconfigure=True)` **sans argument** et
   le reconstruit avec les valeurs par défaut. Correctif : l'option reçoit `enable_secrets_filter` et
   `sensitive_fields` de l'application (`verbosity_option`, `GroupDecorator`) et les repasse à chaque
   reconfiguration.
2. **`SecretsMasker` ignorait ses propres champs.** `_redact` décidait avec la fonction de module
   `should_hide_value_for_key`, qui ne connaît que `DEFAULT_SENSITIVE_FIELDS` ; la liste de l'instance ne servait
   qu'à un test de vérité. Même un `SecretsMasker(sensitive_fields=["mycode"])` construit seul ne masquait pas
   `mycode`. Correctif : la méthode `_hides` utilise les champs de l'instance (insensible à la casse, par
   sous-chaîne comme pour les défauts).

**Pourquoi les tests ne l'avaient pas vu.** `test_sensitive_fields_are_added_to_defaults` utilisait `bearer_token`,
qui contient `token`, un champ par défaut : le test passait pour la mauvaise raison. Quatre tests avec `mycode`
(aucun champ par défaut dans son nom) ont été ajoutés ; l'ancien reste, il vérifie autre chose.

Vérifié de bout en bout, un processus par configuration, console et fichier : défaut (mot de passe masqué,
`mycode` visible), filtre désactivé (tout visible), champ personnalisé (les deux masqués, la valeur ordinaire
reste visible). Les deux `xfail` de secrets de l'item 4 ont été retirés.

## ✅ Item 11 : Défaut — `use_rich_logging=False` perdu à l'exécution

Trouvé en corrigeant l'item 10, même cause : `set_level` reconstruisait un gestionnaire Rich quoi que dise la
configuration. Mesuré avant : aucun gestionnaire après la décoration, un `RichExtraStreamHandler` après
l'exécution, sortie formatée par Rich.

**Décision proposée à l'utilisateur et appliquée** : sans Rich, la console utilise la journalisation standard de
click-extra (`basicConfig(force=True)`, un `StreamHandler` simple, lignes `niveau: message` sans horodatage), avec
le même masquage des secrets, le même respect de `--verbosity` et la même préservation du fichier de log.

Correctif : `configure_rich_logging(use_rich=False)` installe ce gestionnaire (`_configure_plain_logging`) au lieu de
ne rien faire ; `GroupDecorator._setup_logging` l'appelle toujours, avec `use_rich` ; `PycliferVerbosityOption`
retient `use_rich` et le repasse à chaque reconfiguration. Le gestionnaire installé par pyclifer porte une marque
(`_pyclifer_console`), ce qui rend fiable le test « déjà configuré » et la pose du niveau (le type de classe ne
l'est pas : le gestionnaire de click-extra est une sous-classe de `StreamHandler`, ce que ma première mesure,
qui ne lisait que le nom de la classe, avait masqué).

Deux tests existants figeaient l'ancien comportement (« `use_rich_logging=False` n'appelle pas la configuration »,
« `basicConfig` n'est pas appelé ») : leur contrat change volontairement et ils sont mis à jour. Douze tests
ajoutés (six unitaires du gestionnaire simple, deux du décorateur, cinq d'intégration : pas de gestionnaire
Rich, lignes simples, niveaux, secrets masqués, fichier de log). Contrôle de bout en bout, un processus par mode.
Documenté dans `docs/logging.md`.

## ✅ Item 12 : Amélioration — masquer aussi le texte libre (option `mask_free_text`)

Issu de l'item 10. Décision : une option **`mask_free_text`, à `False` par défaut**, parce qu'un motif sur du texte
produit des faux positifs que l'utilisateur ne comprendrait pas (`max_tokens=100`, `token: expired`), et que le
comportement actuel ne change pas pour qui ne l'active pas.

**Ce qu'elle fait.** `SecretsMasker(mask_free_text=True)` formate le message (`record.getMessage()`, arguments
repliés dans le texte), le passe à `redact_text`, puis vide `record.args`. `redact_text` reconnaît un nom qui
contient un champ sensible, suivi de `=` ou `:`, d'un schéma d'autorisation optionnel (`Bearer`, `Basic`, `Token`) et
de la valeur : entre guillemets jusqu'au guillemet fermant, sinon jusqu'à un espace ou un délimiteur. Même règle de
correspondance que pour les clés. Un message qui ne peut pas être formaté est laissé tel quel (c'est `logging` qui le
signalera) ; le filtre de sécurité ne doit jamais faire planter la journalisation.

**Plomberie.** `GroupConfig.mask_free_text` est transmis par douze sites (décorateur, option `--verbosity`,
option `--log-file`, gestionnaire Rich, gestionnaire simple, fichier). Un contrôle par **mutation** a neutralisé
chaque site l'un après l'autre : tous sont détectés par au moins un test. Il a révélé un cas subtil : le filtre de la
console modifie l'enregistrement sur place, donc il cachait le câblage du fichier ; seul un enregistrement **sous le
niveau de la console** (`--verbosity ERROR`) oblige le fichier à masquer lui-même, d'où un test dédié.

**Limites mesurées, documentées dans `docs/logging.md`.** « the password is hunter2 » n'est pas trouvé (aucun nom à
côté) ; les faux positifs ci-dessus ; **les traces d'exception ne sont pas analysées** (le secret d'un message
d'exception apparaît dans la console et le fichier, avec les deux gestionnaires). Corriger ce dernier point en
formatant la trace avant le gestionnaire ferait perdre le rendu Rich des traces (mesuré à l'item 13) : le correctif
retenu masque à la source et le garde, voir l'item 13.

**Défaut de mon code de production trouvé en chemin.** `_configure_plain_logging` marquait et filtrait *tous* les
gestionnaires de la racine après `basicConfig`, en supposant que celui-ci avait tout effacé. Un test existant simule
`basicConfig` : les gestionnaires de capture de pytest restaient alors sur la racine, recevaient la marque et un filtre,
et faussaient ensuite la détection « déjà configuré ». Il ne décore plus que le gestionnaire qu'il vient de créer
(test dédié).

**Observation, non corrigée.** Sans `force_reconfigure`, `configure_rich_logging` considère la console comme déjà
configurée dès qu'un gestionnaire de pyclifer existe : dans un même processus, la journalisation de la **deuxième**
application déclarée n'est pas appliquée. Sans effet pour une application en ligne de commande (un processus, une
application), mais cela oblige les tests d'intégration à repartir d'une racine vide, ce que fait le fixture.

## ✅ Item 13 : Défaut — les traces d'exception échappaient à `mask_free_text`

Issu de l'item 12. Le secret d'un message d'exception (`ConnectionError("GET /x?api_key=abc failed")`) apparaissait
dans la console et le fichier, avec `mask_free_text=True`, en mode Rich comme en mode simple.

**Mesure d'abord (un processus par cas).** Trois approches comparées sur un même scénario :
- *Actuel* : fuite du message de l'exception dans les deux modes (`hunter2`, `abc123`, `URLKEY999`) ; la variable
  locale nommée comme un secret ne fuit pas (`show_locals=False`).
- *B, masquer le texte formaté de la trace* : plus de fuite, mais le panneau Rich (`╭─ Traceback ─╮`) est remplacé par
  le texte brut `Traceback (most recent call last):`. La perte de rendu annoncée à l'item 12 est **confirmée**.
- *C, masquer à la source* : remplacer l'exception de `exc_info` par une copie dont `__str__` renvoie le texte masqué.
  Plus de fuite et le panneau Rich est **conservé** ; la sortie simple est identique à l'actuelle.

**Cas voisins mesurés avec C** : constructeur atypique avec `__str__` propre, `OSError` (qui devient
`PermissionError`), `KeyError` (qui affiche le `repr`), chaînage explicite (`from`) et implicite : tous masqués.
`ExceptionGroup` : les sous-exceptions fuyaient avec la copie simple, d'où un traitement récursif de `exceptions`.
**Lignes de source : elles fuient dans les deux modes** (Python 3.13 les affiche en simple ; en Rich elles ne
paraissaient pas parce que le panneau étroit les tronquait, avec `COLUMNS=250` elles sont là). Un secret écrit en
littéral dans la ligne qui lève l'exception ne peut pas être masqué sans réécrire la source : limite documentée.

**Ce que fait le code.** `SecretsMasker._mask_exception` (actif avec `mask_free_text` seulement) remplace
`record.exc_info` par une copie masquée. La copie est une instance d'une sous-classe du type d'origine, de même nom et
même module, dont `str()` est le texte masqué ; elle reprend le traceback, le `__dict__`, la cause, le contexte,
l'indicateur `__suppress_context__`, les sous-exceptions d'un groupe et les notes (`__notes__`), tous masqués. Une
chaîne qui boucle est coupée par une table des copies. Le texte déjà mis en cache dans `record.exc_text` par un autre
gestionnaire est masqué aussi, parce que le formateur le réutiliserait. Une exception qui ne peut pas être copiée est
remplacée par une `RuntimeError` portant le texte masqué, jamais laissée telle quelle. L'exception de l'utilisateur
n'est pas modifiée.

**Défauts de mon propre code trouvés par le contrôle par mutation.** Neutraliser `__traceback__` de la copie n'était
détecté par aucun test : le traceback de la **cause** disparaissait de l'affichage. Neutraliser la restauration de
`__suppress_context__` non plus : affecter `__cause__` force l'indicateur à `True`, ce qui cache le contexte implicite
d'une exception. Deux tests ajoutés, vérifiés sur le texte réellement imprimé.

**Non couvert, non mesuré.** `args` de la copie n'est pas masqué : un `repr(exception)` pris par un gestionnaire
personnalisé montrerait la valeur (ni Rich ni le module `traceback` n'utilisent `repr`). Tests des `skipif`
(`ExceptionGroup`, notes) exécutés sous Python 3.13 seulement jusqu'au passage de `tox`.

Vingt-trois tests ajoutés à `tests/core/log/test_rich_logging.py` (21 unitaires, 2 de bout en bout, Rich et simple),
couverture de branches de `filters.py` à 100 %. Documenté dans `docs/logging.md`.

## ✅ Item 14 : Défaut — option globale absente de l'aide en mode plain

Trouvé à l'item 5. Dans une application `use_rich_help=False`, `cli.command()` crée une commande click-extra
(cloup) qui garde, pour son aide, des listes d'arguments, de groupes d'options et d'options sans groupe construites
une fois. L'option globale propagée est ajoutée à `params` : elle est analysée (la valeur arrive au callback) mais
**jamais listée dans l'aide**. Mesuré sur huit cas (Rich et plain × `cli.command()` ou `add_command(command())` ×
premier niveau ou imbriqué, sans option de contexte) : seul le cas plain + `cli.command()` échouait. La même
défaillance existait avec `PycliferGroup` et avec un groupe assemblé des mixins publics (`GlobalOptionsMixin` seul).
`docs/api/mixins.md` promet pourtant « visible in help ».

**Pourquoi l'arbre de l'item 5 ne le voyait pas.** La propagation des options de **contexte** reconstruisait ces
listes pour la commande entière, ce qui faisait apparaître l'option globale par effet de bord. Il a fallu un test sans
option de contexte.

**Correctif.** `GlobalOptionsMixin._rebuild_help_cache` (extrait du code qui existait déjà pour les options de
contexte) est appelé aussi après l'ajout d'une option globale, seulement quand une option a été ajoutée. Une commande
Click pure, sans ces listes, n'est pas touchée. Cinq tests unitaires (`tests/core/mixins/test_cli.py`) et huit cas
d'intégration ; neutraliser l'appel fait échouer exactement le cas mesuré. `mixins/cli.py` à 100 % de branches.

## ✅ Item 15 : Défaut — option de contexte absente de l'aide des commandes profondes

Trouvé à l'item 5. Mesuré sur les trois ordres d'enregistrement, Rich et plain : l'option `context=True` et son panneau
manquent dans l'aide d'une commande de profondeur 2 ou 3 quand son groupe avait déjà été rattaché au parent
(« décorateur » et « de haut en bas ») ; elle est présente quand tout est rattaché de bas en haut, et à la profondeur 1.
`docs/api/mixins.md` promet ces copies dans l'aide « des sous-commandes ».

**Cause.** `add_command` ne propage que les options qui ont `context=True`. La copie d'affichage reçue par un groupe
a `context=False` (pour ne jamais être analysée ni passée à un callback), donc ce groupe ne la retransmettait pas aux
commandes ajoutées après coup. S'y ajoutait le nom du panneau : un groupe créé par `group()` n'a pas de
`_context_options_panel`, il aurait retransmis le panneau par défaut au lieu de celui de l'application.

**Correctif.** La copie est marquée (`context_display_copy`) ; `add_command` retransmet les copies que le groupe porte,
sous le panneau qu'elles portent déjà. Les copies restent non exposées, non requises, et ne sont pas des options de
contexte réelles. Cinq tests unitaires et dix-huit cas d'intégration (trois profondeurs, trois ordres, deux
chemins) ; le nom du panneau n'est affirmé que sur le chemin Rich, car l'aide plain de cloup n'a pas de titre de
panneau (l'option y figure dans la liste des options) : mesuré, ajusté aussi dans les tests de l'item 5.
Neutraliser la retransmission, ou la remplacer par le panneau par défaut, fait échouer les tests.

## Item 16 : Défaut — `use_rich_help=False` non appliqué aux sous-groupes et sous-commandes

À faire.

## Item 17 : Défaut — groupe intermédiaire qui ne peut pas recevoir l'option globale

À faire.

## Item 18 : Défaut — variable d'environnement d'une option globale, Rich et plain

Mesuré avec une application nommée `cli` et `--region` globale : sur le chemin Rich la feuille lit `CLI_LEAF_REGION` et
ignore `CLI_REGION` (`option.envvar` vaut `None`, préfixe du contexte `CLI_LEAF`) ; sur le chemin plain elle lit
`CLI_REGION` et ignore `CLI_LEAF_REGION` (`option.envvar` vaut `('CLI_REGION',)`, préfixe du contexte `LEAF`). La doc
(`docs/configuration.md`) ne décrit que les options de la racine. Deux tests `xfail` stricts consignent l'écart ; le
choix de la variable canonique reste à arbitrer.

## Item 19+ : Autres défauts trouvés

Un item par défaut mesuré aux items 5 et 6.

## Item final : Vérification complète et documentation

`ruff`, `pytest`, `tox` (Python 3.10 à 3.13), `mkdocs build --strict`, durée de la suite relevée, mise à jour de
`CLAUDE.md` et de `docs/development.md`. Archivage de la spec quand tous les items sont `✅`.

Procédure par item (CLAUDE.md) : branche, TDD, ruff, pytest, un commit (code, tests, docs, spec avec `✅`),
validation de l'utilisateur, fusion dans `main`, branche supprimée.
