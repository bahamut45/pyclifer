# Spec 17 (BROUILLON) : Initialiser le logging à l'exécution plutôt qu'à la déclaration

> Brouillon, issu du finding 2 de la spec 16. **Rien n'est décidé.** La première étape est une comparaison avec d'autres
> frameworks CLI Python. À faire de préférence après les specs 09 et 10, qui modifient les mêmes classes de groupe, pour
> rejouer la suite d'intégration une seule fois.

## Contexte

Aujourd'hui `GroupDecorator.__call__` configure le logging au moment de la **déclaration** (au chargement du module).
La spec 16, option A, limite cela à l'`app_group`. Option B : ne rien configurer à la déclaration et initialiser au premier
appel (création du contexte racine). Un point d'accroche existe déjà (`GroupDecorator._patch_make_context`, et le callback de
`--verbosity` qui reconfigure déjà à l'exécution).

Avantages attendus de B : aucun effet de bord à l'import (même pour l'`app_group`), deux `app_group` dans un processus ne
se gênent plus, la configuration vient du contexte et pas de l'ordre d'import.
Coûts attendus de B : un log émis au niveau module après l'`app_group` n'est plus formaté jusqu'au premier appel ; tous les
chemins `--help`, `--version`, erreur d'usage et `add_verbosity_option=False` sont à revérifier.

## Item 1 : Comparer avec d'autres frameworks (mesuré, pas de mémoire)

Pour chaque framework, installer la version courante dans un environnement jetable hors du dépôt, écrire la plus petite
application avec une sous-commande, et **observer** :

| Question | Click | Typer | Cement | Autre (argparse, cleo, ...) |
|---|---|---|---|---|
| Qui configure le logging, et quand : au décorateur ou à la définition de classe (import), à `run()`, ou jamais ? | | | | |
| Un sous-groupe ou une sous-commande peut-il la déclencher avant l'application principale ? | | | | |
| Que devient un log émis au niveau module avant l'initialisation ? | | | | |
| Les handlers déjà présents sur la racine sont-ils conservés ? | | | | |
| Le niveau de verbosité est-il lu avant ou après le parsing ? Les logs du parsing de la config sont-ils visibles ? | | | | |
| Deux applications dans un même processus (tests) : ont-elles chacune leur configuration ? | | | | |

À regarder aussi dans la documentation de chaque projet (citer la source) : la recommandation officielle pour initialiser
le logging d'une application en ligne de commande.

## Item 2 : Décision

Selon la comparaison : garder A seul, passer à B, ou une variante (par exemple initialiser à `run()` seulement quand
l'application est lancée comme binaire). Écrire ici la décision de l'utilisateur et ses raisons.

## Item 3 : Implémentation (seulement si B est retenu)

- Test d'abord, dans `tests/integration/` : aucun handler pyclifer n'existe après l'import d'un module qui déclare
  `@app_group` et `@group` ; le premier appel (`--help`, commande, erreur d'usage) l'installe ; deux applications dans le
  même processus utilisent chacune leur configuration.
- Rejouer la matrice `GroupConfig` complète, les scénarios de propagation et d'aide (items 4 et 5 de la spec 15).
- Documentation : `docs/logging.md`, `docs/api/decorators.md`.
