# Erreurs d'usage Click répondues dans le format structuré

**Issue GitHub :** [#9 — Usage errors bypass the JSON response: exit code 2 with an empty stdout](https://github.com/bahamut45/pyclifer/issues/9)

**Objectif :** Avec `handle_response=True` et un format de sortie structuré (`json` par défaut,
`yaml`), une erreur d'usage Click (option manquante, option ou commande inconnue, valeur invalide)
doit être répondue sur stdout avec le même schéma que n'importe quel autre échec, au lieu d'une
sortie vide. Le code de sortie reste 2 et la boîte Rich sur stderr est conservée pour un humain
devant un terminal.

**Constat (reproduit sur `main`, click-extra 9.5.1) :** application de test de l'issue.

| Commande                          | Sortie                                         |
|-----------------------------------|------------------------------------------------|
| `--token t greet --name bob`      | exit 0, JSON `success: true`                   |
| `--token t greet` (`--name` absent) | exit 2, **stdout vide**, raison sur stderr   |
| `--token t greet --nope`          | exit 2, **stdout vide**                        |
| `greet --name bob` (`--token` absent) | exit 2, **stdout vide**                    |
| `--token t nosuchcommand`         | exit 2, **stdout vide**                        |
| `--token t --verbosity NOPE greet ...` | exit 2, **stdout vide**                   |
| `--help`, `--version`             | exit 0, texte (inchangé)                       |

**Cause :** le framework ne gère aucune erreur d'usage (ni `UsageError`, ni `ClickException`, ni
surcharge de `main()`). Les échecs en cours d'exécution passent par `returns_response`
(`core/decorators.py`), mais une erreur d'usage est levée avant, pendant la lecture des arguments
(`Group.parse_args` pour les options du groupe, `Group.invoke` pour la résolution des
sous-commandes et leurs options). Click l'attrape alors lui-même, l'affiche sur stderr et quitte.

**Cas d'usage cible :** un programme (plugin, script, service) qui appelle une application pyclifer
et lit stdout reçoit toujours un JSON analysable, y compris quand son appel est invalide (version
de l'appelant et de l'application différentes, option renommée ou supprimée) :

```json
{
  "success": false,
  "message": "Missing option '--name'.",
  "error_code": 2,
  "data": {"results": [], "error_type": "usage_error", "command": "repro_app greet"}
}
```

**Stack :** aucune nouvelle dépendance.

---

## Design

### Décision 1 — Intercepter dans `HandleResponseMixin`, au niveau du groupe

`HandleResponseMixin` (déjà présent dans `PycliferExtraGroup` et `PycliferRichGroup`) surcharge deux
méthodes :

- `parse_args(ctx, args)` : options propres au groupe, dont les options globales requises ou
  invalides (`--token` manquant, `--verbosity NOPE`) ;
- `invoke(ctx)` : tout ce qui se passe en dessous (commande inconnue, option inconnue ou manquante
  d'une sous-commande, valeur invalide).

Chacune attrape `click_extra.ClickException`, appelle un helper commun, puis relève l'exception
d'origine si le helper n'a rien répondu (comportement Click inchangé). `Exit` et `Abort` ne sont pas
des `ClickException` et restent intacts, donc `--help`, `--version` et `ctx.exit()` ne changent pas.

Alternative écartée : surcharger `main()` avec `standalone_mode=False`. Il faudrait réimplémenter les
sorties (`Exit`, `Abort`, code de retour), plus risqué que deux surcharges ciblées.

### Décision 2 — Uniquement avec `handle_response=True` et un format structuré

Le helper ne répond que si `handle_response_by_default` est vrai et si le format résolu est `json`
ou `yaml` (les formats que `returns_response` considère déjà comme structurés). Pour `table`, `rich`
et `raw`, et pour les applications sans `handle_response`, le comportement actuel est conservé.

### Décision 3 — Résolution du format avant que `--output-format` soit lu

Le format se lit dans `ctx.find_root().meta["pyclifer.output_format"]`. Si l'erreur survient avant
que l'option ait été traitée (`--token` manquant, option `--output-format` elle-même invalide), la
valeur n'existe pas encore : on retombe sur le défaut de l'application. `GroupDecorator` mémorise
`config.output_format_default` sur le groupe créé (attribut `output_format_default`, `"table"` par
défaut sur le mixin) pour que le helper puisse le lire.

### Décision 4 — Code d'erreur : `ExitCode.USAGE_ERROR = 2`

`ExitCode.ALREADY_EXISTS` vaut déjà 2, comme le code d'erreur d'usage de Click. On ajoute
`USAGE_ERROR = 2` (alias, nom `UPPER_SNAKE` selon la convention du projet). `ExitCode` est une classe
d'entiers ordinaires, sans recherche par valeur, et `validate_exit_codes_class` compare des
ensembles de valeurs : l'alias est sans risque.

`error_code` de la réponse et code de sortie du processus valent `exception.exit_code` (2 pour une
`UsageError`, 1 pour une `ClickException` simple), ce qui conserve l'invariant actuel
`error_code == code de sortie` de `returns_response`.

Comme l'appelant qui ne lit que `error_code` ne distingue pas `USAGE_ERROR` de `ALREADY_EXISTS`,
`data` porte un marqueur : `"error_type": "usage_error"` (`UsageError`) ou `"click_error"` (autre
`ClickException`).

### Décision 5 — Contenu de la réponse

`Response(success=False, message=exception.format_message(), error_code=exception.exit_code,
data={"results": [], "error_type": ..., "command": ctx.command_path})`. Le texte d'usage complet
n'est pas dupliqué dans `data` : il reste sur stderr.

### Décision 6 — La boîte Rich sur stderr est conservée

Le helper appelle `exception.show()` (stderr) puis imprime la réponse sur stdout, puis
`ctx.exit(exception.exit_code)`. Un humain devant un terminal voit toujours l'erreur lisible ;
un programme lit stdout.

### Limites connues

- Seul le format est consulté : un `--output-format` invalide dans l'appel est traité avec le défaut
  de l'application.
- Les applications écrites avec des groupes Click natifs (sans le mixin) ne sont pas concernées.

---

## Fichiers à modifier

| Fichier                                   | Changement                                                         |
|-------------------------------------------|--------------------------------------------------------------------|
| `src/pyclifer/core/output/exit_codes.py`  | `ExitCode.USAGE_ERROR = 2`                                         |
| `src/pyclifer/core/mixins/response.py`    | surcharges `parse_args` / `invoke`, helper de réponse              |
| `src/pyclifer/core/decorators.py`         | `GroupDecorator` mémorise `output_format_default` sur le groupe    |
| `tests/core/output/test_exit_codes.py`    | test de `USAGE_ERROR`                                              |
| `tests/core/mixins/test_response.py`      | tests des erreurs d'usage                                          |
| `docs/output-formatting.md`               | section sur les erreurs d'usage en format structuré                |
| `docs/api/mixins.md`, `docs/api/output.md` | `HandleResponseMixin` ; `ExitCode.USAGE_ERROR`                    |

---

## Tâche 1 : Branche

- [ ] `git checkout -b fix/usage-errors-json-response`

## Tâche 2 : `ExitCode.USAGE_ERROR` (TDD)

- [ ] **Étape 1 (rouge) :** dans `tests/core/output/test_exit_codes.py`, `test_usage_error_equals_two`
  (`ExitCode.USAGE_ERROR == 2`) et `test_subclass_keeps_usage_error` (une sous-classe de projet
  valide hérite de `USAGE_ERROR` et passe `validate_exit_codes_class`).
- [ ] **Étape 2 (vert) :** ajouter `USAGE_ERROR = 2` avec un commentaire expliquant l'alias.

## Tâche 3 : Tests des erreurs d'usage (rouge)

**Fichier :** `tests/core/mixins/test_response.py`. Application de test à partir de l'issue (groupe
racine `json` par défaut, `--token` requis, sous-commande avec `--name` requis), via
`pyclifer.testing`.

- [ ] `test_missing_command_option_answers_json` : stdout JSON, `success` faux, message
  `Missing option '--name'.`, `error_code` 2, `data.error_type == "usage_error"`, exit 2.
- [ ] `test_unknown_option_answers_json`, `test_unknown_command_answers_json`.
- [ ] `test_missing_global_option_answers_json_with_default_format` : `--token` absent, aucun
  `--output-format` lu, le défaut `json` s'applique.
- [ ] `test_invalid_value_answers_json` (`--verbosity NOPE`).
- [ ] `test_explicit_yaml_format_answers_yaml` : `--output-format yaml` puis erreur → YAML sur stdout.
- [ ] `test_table_format_keeps_click_behavior` : `--output-format table` → stdout vide, boîte sur stderr.
- [ ] `test_stderr_message_is_kept` : le message est aussi sur stderr en mode JSON.
- [ ] `test_without_handle_response_keeps_click_behavior` : application sans `handle_response`.
- [ ] `test_help_and_version_are_unaffected`.
- [ ] `test_plain_click_exception_uses_click_error_type` : une `ClickException` simple (exit 1) →
  `error_type == "click_error"`, `error_code` 1.
- [ ] `python -m pytest tests/core/mixins/test_response.py -v` → les nouveaux tests échouent.

## Tâche 4 : Implémentation (vert)

- [ ] **Étape 1 :** `GroupDecorator` mémorise `output_format_default` sur le groupe.
- [ ] **Étape 2 :** `HandleResponseMixin` : attribut `output_format_default = "table"`, helper
  privé de réponse, surcharges `parse_args` et `invoke` (docstrings Google, imports `click_extra`).
- [ ] **Étape 3 :** `python -m pytest tests/ -v` → tout passe, 100 % de couverture de branches.

## Tâche 5 : Documentation

- [ ] `docs/output-formatting.md` : section « Usage errors » (comportement, exemple, `error_type`).
- [ ] `docs/api/mixins.md` et `docs/api/output.md` : `HandleResponseMixin`, `ExitCode.USAGE_ERROR`.
- [ ] `mkdocs build --strict`.

## Tâche 6 : Vérification complète

- [ ] `ruff check src/ tests/` et `ruff format src/ tests/`.
- [ ] `tox` (Python 3.10 à 3.13).
- [ ] Rejouer le tableau du constat avec l'application de test de l'issue : plus aucune sortie vide
  en JSON, `--help` et `--version` inchangés.

## Tâche 7 : Commit

```bash
git add src/ tests/ docs/ .claude/specs/
git commit  # 🐛 fix(response): answer Click usage errors in structured output formats
```

Fermer l'issue #9 après fusion (`Fixes #9` dans la description d'une éventuelle pull request, ou
manuellement). Obtenir la validation utilisateur avant de fusionner dans `main`, puis supprimer
la branche. Archiver la spec dans `.claude/specs/archived/` une fois toutes les tâches cochées `✅`.
