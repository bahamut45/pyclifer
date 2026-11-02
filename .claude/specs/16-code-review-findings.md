# Spec 16 (TEMPORAIRE) : Findings du code-review de la branche `feat/integration-test-inventory`

> Spec jetable : elle sert au débrief, puis elle est soit transformée en items à implémenter, soit supprimée.
> **Aucun correctif n'est appliqué.** Rien dans `src/` ni `tests/` n'a changé pour cette spec.

## Plan de correction (source de vérité du suivi)

Branche `feat/integration-test-inventory`, non fusionnée, non poussée : **elle ne se fusionne qu'après ce plan**, avec la
validation de l'utilisateur. Chaque ligne = test écrit d'abord et vu échouer, un commit, doc et spec mis à jour (CLAUDE.md :
préfixer le titre de l'item par ✅ quand il est fait, archiver la spec quand tous le sont).

| Ordre | Item | Quoi | Statut |
|---|---|---|---|
| 1 | 1 | `option(cls=...)` : parcourir le MRO pour `is_global` | ✅ fait |
| 2 | 2 | YAML : représenteurs `dict`, `list`, `tuple` avant `object` | à faire |
| 3 | 3 | regex du texte libre non quadratique | à faire |
| 4 | 4 | `output_format_default` insensible à la casse | à faire |
| 5 | 5 et 6 | variable d'environnement : chaîne dans l'aide, nom par contexte | à faire |
| 6 | 7, 8 | docstring `log_file_option`, imports locaux redondants | à faire |
| 7 | 9 | `GroupConfig.replace_root_handlers` (décidé, faux par défaut) | à faire |
| 8 | 10 | `@group()` ne configure plus le logging (option A, décidé) | à faire |
| après | spec 17 | initialiser à l'exécution (option B) : comparaison d'abord, après les specs 09 et 10 | brouillon |

Non retenu : item 11. Hors branche : item 12. Rejouer la suite d'intégration entière et tox 3.10 à 3.13 avant la validation
du merge.

## Méthode

`/code-review high` sur `main..HEAD` (29 commits) a rendu 10 findings. Chacun a été reproduit dans une application de
test, dans un processus neuf, hors du dépôt, sur la branche **et sur `main`** (un `git worktree` de `main`), pour séparer
les régressions introduites par la branche des comportements qui existaient déjà. Deux constats de plus sont sortis
de ces essais (11 et 12). `KeyboardInterrupt` a aussi été testé, sans problème (voir la fin).

## Synthèse

| # | Finding | Mesuré | Sur `main` ? | À prendre en compte ? |
|---|---|---|---|---|
| 3 | `option(cls=...)` refuse une sous-classe de `PycliferOption` qui passe `**kwargs` | oui | fonctionnait | **Oui, bloquant** (régression de l'item 23) |
| 4 | YAML : `OrderedDict`, `Counter`, `defaultdict`, namedtuple mal écrits | oui | tags Python, données présentes | **Oui, bloquant** (perte de données silencieuse, item 20) |
| 5 | Regex de masquage du texte libre quadratique | oui | n'existait pas | **Oui, bloquant** (item 12, option `mask_free_text`) |
| 8 | `output_format_default="JSON"` refusé | oui | acceptait | **Oui** (régression de l'item 7) |
| 11 | Aide Rich d'une feuille : `[env var: ('CLI_REGION',)]` (tuple) | oui | `CLI_GO_REGION` | **Oui** (régression d'affichage de l'item 18) |
| 6 | Nom de variable figé sur l'objet d'option partagé | oui | pas figé | **Oui, à grouper avec 11** (même code, item 18) |
| 9 | Docstring de `log_file_option` : ligne au mauvais endroit | oui | n'existait pas | **Oui**, trivial |
| 10 | Imports locaux redondants, sans commentaire | oui | à vérifier | **Oui**, trivial (règle du dépôt) |
| 1 | Les handlers de la racine sont supprimés par la config de logging | oui | en partie | **Décidé** : option `replace_root_handlers`, faux par défaut |
| 2 | Le premier groupe déclaré décide de la config de la console | oui | oui | **Décidé** : seul l'`app_group` configure le logging (option A) ; option B dans la spec 17 |
| 7 | Rendu de repli après sortie partielle ou deuxième échec | oui | non applicable | **Non** (comportement voulu et documenté) |
| 12 | JSON d'une `Enum` : `__objclass__` et attributs internes | oui | oui | **Hors branche**, à noter seulement |

Ordre proposé : 3, 4, 5 d'abord (elles empêcheraient le merge), puis 8, 11 + 6, 9, 10 (rapides), puis 1 et 2 (décidés, voir leurs items).

---

## ✅ Item 1 : Régression — `option(cls=...)` refuse une sous-classe de `PycliferOption` avec `**kwargs` (finding 3)

**Reproduit.**
```python
class MyOpt(PycliferOption):
    def __init__(self, *a, **kw): super().__init__(*a, **kw)

@app_group(name="cli")
@option("--region", cls=MyOpt, is_global=True, default="r0")
```
- `main` : fonctionne, la feuille reçoit `--region x`.
- branche : `TypeError: option() cannot make an option global with cls=MyOpt: MyOpt does not accept is_global. Use a PycliferOption subclass.`
  Même résultat avec une sous-classe qui déclare un autre argument nommé (`extra=None`) en plus de `**kwargs`.

**Cause.** `_declares_argument` (item 23) cherche `is_global` dans la signature du constructeur de la seule classe donnée.
Une sous-classe qui délègue par `**kwargs` ne le déclare pas, alors que `PycliferOption` plus haut dans son MRO le fait.
Le message demande d'utiliser « une sous-classe de `PycliferOption` », ce que l'appelant a déjà fait.

**Verdict : oui, bloquant.** Sous-classer `PycliferOption` est le cas d'usage normal, et il est refusé. Les tests de l'item 23
n'utilisaient que `TimerOption` et une classe sans constructeur propre.

**Correctif proposé.** Parcourir le MRO : `is_global` est accepté si l'`__init__` d'une des classes du MRO le déclare
(`PycliferOption`, `CustomConfigOption`, `PycliferVerbosityOption` le font), pas si la classe a seulement `**kwargs`
(`TimerOption` en a, et c'est justement le cas qui plantait). Test d'abord : sous-classe avec `**kwargs`, sous-classe
avec argument en plus, sous-classe de `CustomConfigOption`, et `TimerOption` toujours refusé avec `is_global=True`.

## Item 2 : Régression — le YAML écrit mal les sous-classes de conteneurs (finding 4)

**Reproduit** avec `Response(data={...})` contenant `OrderedDict(a=1)`, `defaultdict(int, b=2)`, `Counter("aab")`,
`namedtuple P(1, 2)`, comparé en JSON et en YAML :

| Valeur | JSON (branche) | YAML `main` | YAML branche |
|---|---|---|---|
| `OrderedDict(a=1)` | `{"a": 1}` | tag `!!python/object/apply`, données présentes | **`{}`** |
| `Counter("aab")` | `{"a": 2, "b": 1}` | tag Python, données présentes | **`{}`** |
| `defaultdict(int, b=2)` | `{"b": 2}` | tag Python, données présentes | chaîne `"defaultdict(<class 'int'>, {'b': 2})"` |
| namedtuple `P(1, 2)` | `[1, 2]` | tag Python | chaîne `"P(x=1, y=2)"` |

**Cause.** `SafeDumper` n'a un représenteur que pour les types exacts (`dict`, `list`, `tuple`). Une sous-classe tombe sur
le représenteur de repli `object` ajouté à l'item 20, qui lit `__dict__` : vide pour `OrderedDict` et `Counter`, d'où `{}`.

**Verdict : oui, bloquant.** Le correctif de l'item 20 a remplacé un YAML laid mais complet par un YAML lisible qui **perd
des données sans erreur**, et JSON et YAML ne s'accordent plus. Mes quatre tests de l'item 20 ne contenaient aucun
conteneur d'une sous-classe.

**Correctif proposé.** Ajouter des représenteurs multiples pour `dict`, `list` et `tuple` (qui couvrent leurs sous-classes)
avant celui de `object`, pour que YAML suive la structure comme JSON. Test d'abord sur ces quatre types, avec comparaison
JSON/YAML des valeurs. Le cas des `set` (JSON : chaîne `"{1}"`, YAML : `!!set`) est à trancher dans le même item.

## Item 3 : Défaut — la regex du texte libre est quadratique (finding 5)

**Reproduit** avec `SecretsMasker(sensitive_fields=["token"], mask_free_text=True).redact_text(texte)`, texte sans
séparateur `=` ni `:` :

| Taille | Suite de caractères de mot | Base64 aléatoire | Chemins `/usr/lib/x.` |
|---|---|---|---|
| 500 | 24 ms | 28 ms | 0,3 ms |
| 1 000 | 99 ms | 116 ms | 0,6 ms |
| 2 000 | 395 ms | 464 ms | 1,2 ms |
| 4 000 | 1,6 s | 1,9 s | 2,4 ms |
| 8 000 | 6,2 s | 7,4 s | 5,1 ms |

Temps ×4 quand la taille ×2 : croissance quadratique. Un message de 64 Ko (blob base64, dump hexadécimal) bloquerait
l'appel de log plusieurs minutes. Un premier essai à 64 000 caractères n'avait pas fini après 180 secondes.

**Cause.** La regex place `[\w.\-]*(?:champs)[\w.\-]*` avant le séparateur : à chaque position de départ, le préfixe glouton
va jusqu'à la fin de la suite de caractères, puis recule sur chaque alternative.

**Verdict : oui, bloquant.** C'est une fonction de l'item 12, désactivée par défaut, mais elle s'applique à des journaux
qui peuvent contenir des données arbitraires (c'est justement le cas où on veut masquer). Un log qui gèle le processus est
inacceptable.

**Correctif proposé.** Ancrer la regex sur le séparateur au lieu du préfixe (chercher d'abord `clé[=:]`, puis remonter),
ou borner le préfixe (`{0,N}`), ou découper le texte en jetons avant d'appliquer la regex. Test d'abord : un texte de
50 000 caractères doit se traiter sous un seuil fixe (par exemple 0,5 s), plus les tests de masquage existants intacts.

## Item 4 : Régression — `output_format_default` n'accepte plus les majuscules (finding 8)

**Reproduit.** `@app_group(output_format_default="JSON")` :
- `main` : accepté, sortie JSON.
- branche : `ValueError: Unknown output_format_default 'JSON'. Valid formats: json, yaml, ...` à la déclaration.
- `--output-format JSON` fonctionne toujours (le `Choice` est insensible à la casse), donc l'option et la valeur par défaut
  ne se comportent plus pareil.

**Cause.** `validate_output_format` (item 7) compare en sensible à la casse.

**Verdict : oui.** Régression de comportement, et incohérence avec l'option qui accepte `JSON`.

**Correctif proposé.** Normaliser en minuscules avant de valider (même règle que l'option). Test d'abord : `"JSON"`,
`"Json"` acceptés et produisent du JSON ; `"nope"` toujours refusé.

## Item 5 : Régression d'affichage — la variable s'affiche comme un tuple dans l'aide Rich d'une feuille (constat 11)

Non signalé par le review, trouvé en reproduisant le finding 6. Aide Rich de `cli go --help`, avec une option globale :
- `main` : `[env var: CLI_GO_REGION]`
- branche : `[env var: ('CLI_REGION',)]`, et de même `('CLI_VERBOSITY',)`, `('CLI_OUTPUT_FORMAT',)`.
L'aide Rich de la racine et l'aide plain sont correctes.

**Cause.** `_name_global_envvars` (item 18) écrit un tuple dans `param.envvar` ; rich-click le formate avec `str()` quand il
dessine l'aide d'une feuille. Les tests de l'item 18 cherchent `"CLI_REGION" in texte`, ce qui passe aussi avec le tuple.

**Verdict : oui.** Régression visible de tous les utilisateurs de l'aide d'une sous-commande. À grouper avec l'item 6.

**Correctif proposé.** Écrire une chaîne quand il n'y a qu'un nom (ou vérifier ce que rich-click attend). Test d'abord :
l'aide Rich de la feuille contient `[env var: CLI_REGION]` et ne contient pas `(`.

## Item 6 : Défaut — le nom de variable est figé sur l'objet d'option partagé (finding 6)

**Reproduit** en invoquant la même application deux fois avec des `prog_name` différents (cas des tests `CliRunner`),
`FIRST_REGION=from-first` puis `SECOND_REGION=from-second` et `FIRST_REGION=stale` :
- `main` : les deux appels ignorent la variable (la lecture passait par un autre chemin, celui de l'item 18) ; l'aide suit
  le `prog_name` (`FIRST_REGION`, puis `SECOND_REGION`).
- branche : premier appel `region=from-first`, second appel `region=stale` : il lit encore `FIRST_REGION`, et
  `param.envvar` vaut `('FIRST_REGION',)` pour tout le processus.

**Cause.** `_name_global_envvars` écrit `param.envvar` sur l'objet partagé seulement quand il vaut `None`. La valeur reste
pour la suite du processus.

**Verdict : oui, faible gravité.** Un binaire de production ne tourne qu'avec un seul `prog_name`. Mais les tests unitaires
d'une application cliente le rencontrent, et la cause est la même que l'item 5 : un seul correctif.

**Correctif proposé.** Ne pas modifier l'option partagée : calculer le nom par contexte (ou le remettre à `None` à la
fermeture du contexte racine). Test d'abord : deux appels avec deux `prog_name` lisent chacun leur variable.

## Item 7 : Documentation — ligne au mauvais endroit dans `log_file_option` (finding 9)

Confirmé à la lecture de `src/pyclifer/core/decorators.py` (docstring de `log_file_option`). La ligne « Merged into
SecretsMasker.DEFAULT_FIELDS — does not replace them. » est sous `mask_free_text` au lieu de `sensitive_fields`, donc la
doc générée décrit mal les deux. `config.py` a le bon ordre. **Verdict : oui**, correction d'une ligne.

## Item 8 : Qualité — imports locaux redondants (finding 10)

Confirmé : `core/log/config.py:330` importe `SecretsMasker` en local alors qu'il est importé en tête de module (ligne 12) ;
`core/decorators.py` importe `configure_rich_logging` et `PYCLIFER_LOG_LEVELS` en local alors que `.log.config` est déjà
importé en tête de module (ligne 27). Aucun commentaire n'explique un cycle d'imports, que `.claude/CLAUDE.md` exige.
**Verdict : oui**, mais à vérifier import par import qu'aucun ne casse réellement un cycle avant de les remonter.

## Décidé — Item 9 : les handlers de la racine sont supprimés par la config de logging (finding 1)

**Reproduit.** Un `StreamHandler` ajouté sur le logger racine avant la déclaration de l'application :

| Mode | `main` après déclaration | branche après déclaration | après le callback `--verbosity` |
|---|---|---|---|
| `use_rich_logging=False` | conservé | **supprimé** | supprimé (déjà sur `main`) |
| `use_rich_logging=True` | supprimé | supprimé | supprimé (déjà sur `main`) |

**Cause.** `basicConfig(force=True)` retire tous les handlers de la racine, y compris ceux de tiers (Sentry, syslog) et
le `caplog` de pytest.

**Verdict : à discuter.** Le comportement existait déjà sur `main` (mode Rich, et callback `--verbosity` dans les deux
modes). La branche l'étend au mode plain dès la déclaration, ce qui l'aligne sur le mode Rich. C'est un vrai défaut pour
qui intègre pyclifer dans une application qui a déjà ses handlers, mais ce n'est pas une régression propre à la branche.
Pistes : ne retirer que les handlers que pyclifer a créés (il sait déjà les reconnaître, `_is_console_handler`), ou
documenter. **Hors merge**, à ouvrir en spec séparée si on le garde.

**Décision de l'utilisateur.** Une option. Nouveau champ `GroupConfig.replace_root_handlers`, **faux par défaut** :
pyclifer ne retire que les handlers qu'il a créés (reconnus par `_is_console_handler`) et laisse ceux des autres
(Sentry, syslog, `caplog`). Vrai redonne le comportement actuel (`basicConfig(force=True)`). Une heuristique par type est
exclue : le handler de `caplog` est une sous-classe de `StreamHandler`. Un changement de défaut est accepté avant la 1.0.
Risque connu, non mesuré : si une bibliothèque a appelé `basicConfig()` avant l'application, la console peut s'afficher
deux fois avec le défaut ; l'option sert à ce cas.

**À faire.** Test d'abord, dans `tests/integration/` : un handler tiers survit à la déclaration et au callback `--verbosity`
dans les deux modes (Rich et plain), et disparaît avec `replace_root_handlers=True`. Le nouveau champ exige une entrée
dans `scenarios.py` (garde de l'inventaire), la doc de `GroupConfig` (`docs/api/classes.md`) et `docs/logging.md`.

## Décidé — Item 10 : le premier groupe déclaré décide de la config de la console (finding 2)

**Reproduit.** Un `@group()` déclaré avant l'`@app_group(use_rich_logging=False, sensitive_fields=["tok"], mask_free_text=True,
add_verbosity_option=False)` : la console reste en Rich, sans masquage (`main` donne le même résultat). Avec l'option
`--verbosity` par défaut, son callback reconfigure tout avec force : la console est plain et masquée, dans les deux ordres.

**Verdict : à discuter, priorité basse.** Il faut la combinaison sous-groupe déclaré d'abord (l'ordre normal dans le gabarit
de `pyclifer project`, où `cli.py` importe les apps) **et** `add_verbosity_option=False`. Antérieur à la branche. Piste :
ne configurer la console que depuis l'`app_group`.

**Décision de l'utilisateur.** Option A : `@group()` ne configure plus le logging, seul l'`app_group` l'initialise. L'ordre
de déclaration reste libre : `src/pyclifer/cli.py` et le gabarit généré importent les sous-groupes avant d'écrire
`@app_group()`, donc interdire cet ordre casserait le framework lui-même.

**Mesuré** (prototype jetable, `--verbosity TRACE --config fichier.toml`) : les logs de l'option `--config` (« Load
configuration matching », parsing TOML, `New defaults`, lignes TRACE) sont identiques avec et sans l'initialisation par les
sous-groupes, car ils sont émis à l'exécution. Seule perte : un log de niveau module émis entre la déclaration d'un
sous-groupe et celle de l'`app_group` n'est plus formaté par Rich (sortie brute de Python, WARNING et au-dessus). Autre
conséquence : un `@group()` utilisé sans `app_group` n'a plus de logging configuré.

**À faire.** Test d'abord : après un `@group()` seul, aucun handler de pyclifer n'est installé ; `group()` déclaré avant
l'`app_group(use_rich_logging=False, mask_free_text=True, add_verbosity_option=False)` : la console est plain et masque, dans
les deux ordres de déclaration. Option B (initialiser à l'exécution) : voir la spec 17, sans se l'interdire.

## Non retenu — Item 11 : rendu de repli (finding 7)

**Reproduit.** (A) Un renderer dont `rich()` dessine un panneau puis lève : le panneau reste à l'écran, suivi du panneau
d'erreur, code 1. (B) Un `BaseContext` dont `print_result_based_on_format` lève toujours : le repli lève aussi, traceback
brute, stdout vide, comme avant l'item 25.

**Verdict : non.** (A) est le comportement que la doc décrit (« un affichage Rich déjà à l'écran reste »), et JSON/YAML
s'impriment en un seul appel, donc il n'y a pas de sortie tronquée mesurable. (B) ne régresse pas. Le repli ne passe pas
l'option de filtre de sortie exprès. Si on veut aller plus loin, imprimer un JSON minimal à la main en dernier recours :
amélioration, pas défaut.

## Hors branche — Item 12 : le JSON d'une `Enum` expose des attributs internes

Trouvé en testant le finding 4, identique sur `main`. Une valeur `Enum` dans `data` sort en JSON comme
`{"_value_": 1, "_name_": "RED", "__objclass__": "{'_generate_next_value_': ...", "_sort_order_": 0}`, parce que
`_FallbackEncoder` lit `__dict__`. La sortie utile serait la valeur (ou le nom). À traiter avec le finding 4 si on
revoit le repli de `_FallbackEncoder` et de `_FallbackDumper` en même temps.

## Vérifié sans problème

`KeyboardInterrupt` dans le corps d'une commande et dans un renderer : `main` et branche donnent « Aborted. » et le code 1,
car ce n'est pas une `Exception` et Click l'a déjà converti en `Abort`. La liste des exceptions qui traversent
`returns_response` (`ClickException`, `Abort`, `Exit`) est complète pour ce cas.
