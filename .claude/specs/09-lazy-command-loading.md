# Chargement paresseux / conditionnel des groupes de commandes

**Issue GitHub :** [#7 — Lazy / conditional command group loading](https://github.com/bahamut45/pyclifer/issues/7)

**Dépend de :** spec 14 (événements de cycle de vie) pour `commands.collect`.

**Objectif :** Permettre de n'importer un sous-ensemble configurable de commandes qu'à leur
première invocation, pour éviter de charger des dépendances lourdes (`proxmoxer`, `redfish`,
`paramiko`, ...) chez un utilisateur qui n'active jamais les fonctionnalités correspondantes.
Généralise le pattern `CommandRegistry` / `LazyCommandGroup` de `ra-tools` sans aucun couplage à
un système de configuration particulier.

**Révision :** la première version de cette spec (avant la montée vers click-extra 9.5.1) réécrivait
un mixin de chargement paresseux. Elle est remplacée : on **étend** `click_extra.commands.LazyGroup`
au lieu de le dupliquer, après les constats mesurés ci-dessous.

**Cas d'usage cible :**

```python
from pyclifer import app_group, LazySubcommand, pass_cli_context

LAZY = {
    "proxmox": "myapp.apps.proxmox.commands.proxmox_group",
    "redfish": LazySubcommand("myapp.apps.redfish.commands.redfish_group", section=hardware),
}


def enabled_commands() -> list[str]:
    """Read from config/env which optional command groups the user activated."""
    return read_enabled_features_from_config()


@app_group(
    lazy_subcommands=LAZY,
    enabled_commands_resolver=enabled_commands,
    lazy_command_disabled_message="'{name}' n'est pas activé — voir `myapp config init`.",
)
@pass_cli_context
def cli(ctx): ...
```

```bash
myapp proxmox list        # importe myapp.apps.proxmox.commands seulement maintenant
myapp redfish list        # si "redfish" absent de enabled_commands() → message clair, pas d'import
```

Variantes : un `CommandRegistry` (déclaration depuis plusieurs modules, tags) ou un handler de
l'événement `commands.collect` (commandes connues seulement à l'exécution, plugins).

**Stack :** `click_extra.commands.LazyGroup` (déjà une dépendance), stdlib. Aucune nouvelle dépendance.

---

## Constats mesurés (click-extra 9.5.1, prototypes jetables)

1. **`LazyGroup` ne marche pas tel quel dans la pile pyclifer.** Il appelle
   `add_command(cmd, section=..., fallback_to_default_section=...)` ; `HandleResponseMixin.add_command(cmd, name=None)`
   n'accepte pas de `**kwargs` → `TypeError: unexpected keyword argument 'section'`. Le même défaut touche
   tout `add_command(cmd, section=...)` eager sur un groupe pyclifer.
2. **Un fichier de config chargé défait le chargement paresseux.** `ConfigOption.load_conf` parcourt
   tout l'arbre (`list_commands` + `get_command`) pour construire `params_template` : toutes les commandes
   paresseuses sont importées. Avec un filtre qui lève dans `get_command`, la config échoue (exit 2) avant même
   de lancer la commande demandée.
3. **`included_params` n'est pas une solution générale** : liste statique de clés autorisées, la config
   d'une commande hors liste est ignorée sans avertissement, et la commande autorisée est importée même si on en
   lance une autre.
4. **Un `descend` conscient du lazy, passé à `walk_params`, résout le problème** : seule la commande
   demandée est importée, sa section de config lui arrive via `LazyGroup._apply_config_to_parent_context`, et une
   commande désactivée n'est jamais touchée.

| Scénario (3 commandes `a`, `b`, `c` ; `c` désactivée ; config avec sections `a` et `b`) | Importés | Config reçue |
|---|---|---|
| Sans correctif, lancer `a` | `a`, `b` | échec exit 2 |
| `included_params`, lancer `b` | `a`, `b` | ignorée |
| `descend` conscient du lazy, lancer `a` | `a` | `FROM_CONFIG` |
| `descend` conscient du lazy, lancer `b` | `b` | `B_CONFIG` |
| `descend` conscient du lazy, lancer `c` | aucun | exit 2, `'c' is disabled` |

Non testé à ce jour : `strict=True` sur la config, groupes paresseux imbriqués, `--params`, complétion.
Ils sont des cas de test explicites des items 2 et 3.

---

## Design

### Décision 1 — Étendre `LazyGroup`, ne pas le dupliquer

Les groupes composites héritent de `LazyGroup` (import, cache dans `self.commands`, vérifications de type,
sections cloup, injection de la config dans `default_map`). `lazy_subcommands` est transmis au
constructeur par `click_kwargs`. `LazyCommandsMixin` n'apporte que ce que `LazyGroup` n'a pas : le filtre
d'activation et le message.

- `PycliferExtraGroup(EventsMixin, HandleResponseMixin, GlobalOptionsMixin, LazyCommandsMixin, LazyGroup)`
- `PycliferRichGroup(EventsMixin, HandleResponseMixin, GlobalOptionsMixin, LazyCommandsMixin, LazyGroup, RichGroup)`

L'enveloppement par `returns_response` et la propagation des options globales se font au premier
`get_command`, via `add_command`, une fois `HandleResponseMixin.add_command` corrigé (item 1).

### Décision 2 — Le filtre cache dans `list_commands`, refuse dans `resolve_command`

`enabled_commands_resolver` retourne des **noms** de commandes (le `tag` n'est qu'une métadonnée du
registre). Pas de résolveur : toutes les commandes sont actives.

- `list_commands` omet les commandes paresseuses désactivées (elles n'apparaissent pas dans l'aide) ;
- `get_command` reste **pur** : il ne lève jamais (les parcours de click-extra l'appellent : config,
  `--params`, complétion, documentation) ;
- `resolve_command(ctx, args)` lève `click_extra.UsageError(message.format(name=name), ctx=ctx)` quand le
  nom demandé est enregistré mais désactivé. `HandleResponseMixin.invoke` convertit cette erreur en réponse
  structurée (spec 13 / bug #9). Une commande inconnue garde le "No such command" de Click, distinct du
  message de désactivation.

### Décision 3 — Parcours de config conscient du lazy

`CustomConfigOption.walk_params` est surchargé pour composer un `descend` qui répond `False` pour une
sous-commande d'un `LazyGroup` pas encore importée. Les clés de `descend` incluent le nom racine : le
chemin vers le parent se suit dans `commands` (sans jamais appeler `get_command`). Pendant ce parcours,
`ctx.meta["pyclifer.config_walk"]` est posé : `LazyCommandsMixin` s'en sert pour ne pas appeler le résolveur
ni émettre `commands.collect` avant que la config soit chargée.

### Décision 4 — `commands.collect` (événement, spec 14)

Émis **une seule fois** par groupe, au premier `list_commands` / `resolve_command` hors parcours de
config, donc après `config.loaded` quand il y a une config. Signature d'un handler :
`(ctx) -> Mapping[str, str | LazySubcommand] | None`. Les mappings renvoyés sont fusionnés dans
`lazy_subcommands` (sections déclarées au passage, comme dans `LazyGroup.__init__`).
Cela couvre les plugins tardifs et les commandes dépendant de la config, sans registre vivant.

### Décision 5 — `CommandRegistry` mince et optionnel

Un conteneur déclaratif sans import (c'est `LazyGroup` qui importe) :
`register(name, import_path, tag="default", section=None)`, `names(tag=None)`, `__contains__`,
`lazy_subcommands()` (le dict), `collect(ctx)` (handler pour `commands.collect`). Pas de champ
`command_registry` dans `GroupConfig` : le registre s'utilise via `lazy_subcommands=registry.lazy_subcommands()`
ou `on={"commands.collect": [registry.collect]}` (ce dernier tolère les enregistrements tardifs).

### Décision 6 — Limites assumées et documentées

- `--help` sur le groupe importe toutes les commandes activées (l'aide courte vient de la commande).
- Le lien avec `pyclifer project add integration` (activer une intégration générée selon la config) est
  hors sujet : ticket séparé.

---

## Fichiers à modifier

| Fichier                            | Changement                                                            |
|------------------------------------|------------------------------------------------------------------------|
| `src/pyclifer/core/mixins/response.py` | `add_command` accepte et transmet `**kwargs`                       |
| `src/pyclifer/core/mixins/cli.py`  | `LazyCommandsMixin`                                                    |
| `src/pyclifer/core/mixins/__init__.py` | Exporter `LazyCommandsMixin`                                       |
| `src/pyclifer/core/classes.py`     | Bases des groupes ; `GroupConfig` : `enabled_commands_resolver`, `lazy_command_disabled_message` ; `CustomConfigOption.walk_params` |
| `src/pyclifer/core/decorators.py`  | `GroupDecorator._configure_lazy_commands()` ; `lazy_subcommands` transmis au constructeur |
| `src/pyclifer/core/events.py`      | Ajouter `COMMANDS_COLLECT` à `EVENTS`                                  |
| `src/pyclifer/core/registry.py` (nouveau) | `CommandRegistry`                                               |
| `src/pyclifer/__init__.py`         | Exporter `CommandRegistry`, `LazySubcommand`                           |
| `tests/fixtures/lazy_targets.py` (nouveau) | Commandes cibles d'import                                       |
| `tests/core/test_registry.py` (nouveau) | Tests `CommandRegistry`                                           |
| `tests/core/mixins/test_response.py` | Régression `add_command(section=...)`                               |
| `tests/core/mixins/test_cli.py`    | `TestLazyCommandsMixin`                                                |
| `tests/core/options/test_custom_config_option.py` | Parcours de config conscient du lazy                    |
| `tests/core/test_lazy_commands_integration.py` (nouveau) | Bout-en-bout                               |
| `docs/api/mixins.md`, `docs/api/classes.md`, `docs/how-to/lifecycle-events.md` | Voir item 8                |
| `docs/how-to/lazy-commands.md` (nouveau) | Guide d'usage                                                    |
| `mkdocs.yml`                       | Ajouter la page au `nav`                                               |

---

## Item 1 : `HandleResponseMixin.add_command` transmet `**kwargs`

Branche : `fix/add-command-kwargs`. Test d'abord (`tests/core/mixins/test_response.py`) : sur un groupe
pyclifer, `group.add_command(cmd, section=Section("S"))` ne lève pas, enregistre la commande, et la range
dans la section ; avec `handle_response_by_default=True`, le callback est toujours enveloppé une seule fois.
Attendu avant le correctif : `TypeError ... unexpected keyword argument 'section'`.
Correctif : `def add_command(self, cmd, name=None, **kwargs)` et `super().add_command(cmd, name=name, **kwargs)`.

## Item 2 : Parcours de config conscient du lazy

Branche : `feat/lazy-aware-config-walk`. Tests d'abord, avec un `Finder` d'import qui compte les modules
importés (voir le prototype de la révision) :

- config chargée, lancer `a` : seul `a` est importé et reçoit sa section de config ;
- idem pour `b` ; la commande `c` désactivée n'est jamais importée ni interrogée ;
- sans fichier de config : comportement inchangé ;
- `strict=True` : une section de commande pas encore importée n'est pas signalée comme inconnue ;
- groupe paresseux imbriqué : seul le chemin demandé est importé ;
- `ctx.meta["pyclifer.config_walk"]` vaut vrai pendant le parcours et faux ensuite.

Implémenter la surcharge de `walk_params` dans `CustomConfigOption`. Ajouter un test de non-régression qui
échoue explicitement si la signature de `walk_params` ou `descend` change dans click-extra.

## Item 3 : `LazyCommandsMixin` (filtre et message)

Branche : `feat/lazy-commands-mixin`. Tests d'abord (`tests/core/mixins/test_cli.py`) :

- `list_commands` omet une commande paresseuse désactivée et garde les eager ;
- `get_command` sur une commande désactivée renvoie `None`, sans lever ;
- `resolve_command` sur une commande désactivée lève `UsageError` avec le message formaté et `ctx` renseigné ;
- une commande inconnue garde le "No such command" ;
- sans résolveur, toutes les commandes sont actives ;
- pendant le parcours de config (`ctx.meta["pyclifer.config_walk"]`), le résolveur n'est pas appelé.

Groupe de test : `class _LazyGroup(LazyCommandsMixin, LazyGroup)`.

## Item 4 : Événement `commands.collect`

Branche : `feat/commands-collect-event`. Test d'abord :

- un handler qui renvoie `{"x": "mod.cmd"}` rend `x` visible et importable ;
- émis une seule fois même après plusieurs `list_commands` / `resolve_command` ;
- non émis tant que le groupe n'est pas interrogé ;
- non émis pendant le parcours de config, émis après `config.loaded` ;
- un handler renvoyant `None` ne change rien ; une exception de handler se propage ;
- un `LazySubcommand` avec section est enregistré avec sa section.

Ajouter `COMMANDS_COLLECT` à `core/events.py`.

## Item 5 : Câblage `GroupConfig`, groupes composites, exports

Branche : `feat/lazy-commands-wiring`. Tests d'abord (`tests/core/test_decorators.py`) :
`@app_group(lazy_subcommands=..., enabled_commands_resolver=..., lazy_command_disabled_message=...)`
configure le groupe ; `lazy_subcommands` atteint bien le constructeur de `LazyGroup` via `click_kwargs`
(à vérifier en premier : c'était une hypothèse non testée) ; `from pyclifer import LazySubcommand` fonctionne.

## Item 6 : `CommandRegistry`

Branche : `feat/command-registry`. Tests d'abord (`tests/core/test_registry.py`) : `register` / `names` /
filtre par `tag` / `__contains__` / `lazy_subcommands()` (valeurs `LazySubcommand`, section conservée) /
`collect(ctx)` renvoie le même mapping ; un enregistrement après la décoration est vu via `collect` mais pas
via `lazy_subcommands=registry.lazy_subcommands()` (instantané).

## Item 7 : Tests d'intégration bout-en-bout

Branche : `feat/lazy-commands-integration`. Avec `@app_group(...)` et `pyclifer.testing.invoke()` :

- commande activée : exit 0, importée seulement à l'appel ;
- commande désactivée : exit 2, **stdout = JSON** `error_type: "usage_error"` avec le message personnalisé,
  module non importé ;
- commande inconnue : exit 2, JSON `No such command` sur stdout ;
- avec fichier de config : seule la commande lancée est importée, sa config est appliquée ;
- `--help` : n'affiche pas les commandes désactivées.

## Item 8 : Documentation

Dans le même commit que le dernier code (règle du `.claude/CLAUDE.md`) :
`docs/how-to/lazy-commands.md` (cas d'usage, `LazySubcommand`, résolveur, message, registre, `commands.collect`,
limites de `--help`), `docs/api/mixins.md` (`LazyCommandsMixin`), `docs/api/classes.md` (champs de `GroupConfig`,
`CustomConfigOption.walk_params`), `docs/how-to/lifecycle-events.md` (ajouter `commands.collect`),
`mkdocs.yml` (nav). Puis `mkdocs build --strict`.

## Item 9 : Vérification complète

```bash
ruff check src/ tests/ && ruff format src/ tests/
python -m pytest tests/ -v
tox
mkdocs build --strict
graphify update .
```

Procédure par item (CLAUDE.md) : branche, TDD, ruff, pytest, un commit (code, tests, docs, spec avec `✅`),
validation de l'utilisateur, fusion dans `main`, branche supprimée. Fermer l'issue #7 au dernier item
(`Closes #7`) ; la spec est archivée quand tous les items sont `✅`.
