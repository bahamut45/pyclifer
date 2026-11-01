# Événements de cycle de vie (`on()`, `config.loaded`)

**Contexte :** socle partagé par les specs 09 (commandes paresseuses), 05 (hooks avant/après
commande) et 06 (plugins). Pas d'issue dédiée : la spec naît de l'analyse de l'issue #7.

**Objectif :** Donner au framework un seul mécanisme d'extension : des points de cycle de vie
nommés auxquels l'application ou un plugin attache des fonctions. Cette spec pose l'infrastructure
(`EventsMixin`, `on()`, `emit()`, ensemble fermé de noms) et le premier événement, `config.loaded`.
Chaque spec consommatrice déclare ses propres événements : 09 ajoute `commands.collect`, 05 ajoutera
`before_invoke` / `after_invoke`.

**Dépend de :** rien. **Débloque :** 09, 05, 06.

**Cas d'usage cible :**

```python
from pyclifer import app_group


def on_config_loaded(ctx) -> None:
    """React once the configuration file is resolved."""
    ...


@app_group(on={"config.loaded": [on_config_loaded]})
def cli(): ...


@cli.on("config.loaded")  # inscription après coup, utilisable en décorateur (plugins)
def another(ctx) -> None: ...
```

**Stack :** stdlib uniquement, aucune nouvelle dépendance.

---

## Constat préalable (mesuré sur click-extra 9.5.1)

`ConfigOption.load_conf` lit et parse le fichier, puis construit `params_template` en parcourant tout
l'arbre de commandes (`list_commands` puis `get_command`). Deux conséquences pour ce socle :

- `config.loaded` doit être émis **après** `load_conf`, quand `ctx.meta[CONF_SOURCE]` et
  `ctx.meta[CONF_FULL]` sont renseignés (voir la docstring de `load_conf`).
- `load_conf` est visité **une seule fois** par exécution dans une application pyclifer ordinaire
  (mesuré sur 8 scénarios : sous-commande, sous-groupe, `--help`, appel nu, avec ou sans fichier).
  Il peut l'être **deux fois pour la même option** dans un seul cas : un appel sans aucun argument dont
  le fichier de config, trouvé automatiquement, contient `_default_subcommands`. La seconde visite est
  alors un no-op de click-extra (garde `_PRELOADED`), mais notre émission, placée après `super().load_conf()`,
  se déclencherait deux fois. Le double appel vu dans un premier prototype était un autre phénomène :
  une commande construite avec `click_extra.command` embarque **sa propre** `ConfigOption`, d'où une
  visite pour `cli` et une pour `cli hello` (deux options, deux contextes).
- **Erreur avalée sur tout appel nu (mesuré à l'item 4).** Sur **tout** appel sans argument, avec ou
  sans `_default_subcommands`, la première visite est entourée d'un `try/except ClickException` côté
  click-extra (`_resolve_subcommands_eagerly`). Une `ClickException` levée par un handler y est avalée :
  click-extra conclut qu'il n'y a rien à injecter, **n'effectue pas de seconde visite** et Click affiche
  l'aide (code 2) sans le message. Sur une sous-commande explicite, l'erreur remonte normalement.
  Réponse de cette spec (voir décision 5) : l'erreur est gardée puis rapportée par le groupe.

---

## Design

### Décision 1 — Ensemble fermé de noms, constantes de chaînes

`core/events.py` contient les noms d'événements en constantes `UPPER_SNAKE` (`CONFIG_LOADED =
"config.loaded"`) et `EVENTS: frozenset[str]`. Une enum n'est pas utilisée : `StrEnum` n'existe qu'à
partir de Python 3.11 et le projet supporte 3.10. Les utilisateurs écrivent la chaîne.
Une **chaîne simple** inconnue lève `ValueError` à l'inscription, en listant les noms valides (une faute
de frappe ne doit jamais être silencieuse). Chaque spec consommatrice ajoute ses noms à `EVENTS`.
Les événements définis par l'utilisateur passent par la classe `Event` (décision 6).

### Décision 2 — `EventsMixin`, par groupe

`core/mixins/events.py` : `EventsMixin` porte `_event_handlers: dict[str, list[Callable]]` et deux
méthodes.

- `on(event, handler=None)` : inscrit `handler`, ou renvoie un décorateur si `handler` est omis.
- `emit(event, ctx)` : appelle les handlers dans l'ordre d'inscription avec `ctx` et renvoie la liste
  de leurs résultats (utile aux événements qui collectent, comme `commands.collect` en spec 09).

Une exception levée par un handler **se propage** (pas d'avalement silencieux). Pas de priorités,
pas d'async, pas d'événements définis par l'utilisateur dans cette version. Le mixin se place en
tête des bases de `PycliferExtraGroup` et `PycliferRichGroup`.

### Décision 3 — Inscription déclarative via `GroupConfig.on`

`GroupConfig.on: dict[str, list[Callable]] | None`. `GroupDecorator._configure_events(f)` inscrit
chaque handler sur l'instance du groupe, appelé dans `__call__` à côté de `_configure_handle_response`.
L'API objet (`cli.on(...)`) reste disponible pour les plugins.

### Décision 4 — `config.loaded` émis par `CustomConfigOption`

`CustomConfigOption.load_conf` appelle `super().load_conf(...)`, puis émet `config.loaded` sur
`ctx.command` si c'est un `EventsMixin`. Règles :

- émis une seule fois par contexte : `ctx.meta["pyclifer.events.config_loaded"]` contient l'ensemble des
  `command_path` déjà émis (`ctx.meta` est partagé dans toute la hiérarchie de contextes, le chemin
  distingue donc les groupes). Le chemin est ajouté **après** l'émission réussie, pour qu'une
  émission interrompue par une exception ne soit pas enregistrée comme faite ;
- non émis pour une option qui n'appartient pas à un `EventsMixin` (cas d'une commande `click_extra.command`
  autonome portant sa propre `ConfigOption`) ;
- aucune dépendance à la constante privée `_PRELOADED` de click-extra (rejeté : elle peut changer) ;
- émis que le fichier existe ou non (`ctx.meta[CONF_SOURCE]` dit lequel) ;
- **non émis** si `ctx.resilient_parsing` (aide, complétion), comme click-extra ne lit pas le fichier
  dans ce cas.

### Décision 5 — Une erreur de handler n'est jamais perdue sur un appel nu

Quand l'émission de `config.loaded` lève une `ClickException`, `CustomConfigOption.load_conf` la range
dans `ctx.meta[PENDING_ERROR_META]` (constante de `core/events.py`) puis la relance. Sur un appel normal,
elle remonte jusqu'à `HandleResponseMixin.parse_args`, qui reconnaît la même instance et ne fait rien de
plus (pas de doublon). Sur un appel nu, click-extra l'avale puis Click lève l'erreur d'aide : `parse_args`
trouve alors une erreur en attente qui n'est pas celle qu'il attrape. En format structuré, il répond avec
l'erreur du handler (et sort) ; en format texte, il affiche le message du handler puis laisse l'aide.

### Décision 6 — Événements définis par l'utilisateur : la classe `Event`

Un système de plugins (spec 06) où seul le framework peut définir des événements empêcherait les
plugins de se parler : un plugin qui expose un point d'extension doit pouvoir l'émettre, et un autre
doit pouvoir s'y brancher. `core/events.py` définit donc `class Event(str)` :

```python
class Event(str):
    """A named lifecycle event. Create your own with Event("myplugin.ready")."""

CONFIG_LOADED = Event("config.loaded")
```

- `Event` hérite de `str` : `CONFIG_LOADED == "config.loaded"`, même hachage, donc tout le code écrit
  avec des chaînes (dict `on=`, `EVENTS`, tests, doc) reste valable. Mesuré sur un script jetable :
  égalité, appartenance à un `frozenset`, recherche dans un dict par chaîne ou par `Event`.
- `on()` accepte un objet `Event` **quel qu'il soit**, sans enregistrement préalable : l'ordre de
  chargement des plugins n'a aucune importance. Une chaîne simple reste limitée aux événements du
  framework (`EVENTS`). La faute de frappe sur un événement personnalisé devient une erreur d'import.
- Un plugin définit `READY = Event("myplugin.ready")` dans son module, l'émet avec `emit(READY, ctx)`,
  et les autres l'importent. Les handlers restent **par groupe** (pas de registre global).
- `on()` et `emit()` appliquent la **même règle** (méthode partagée `_check_event`) : un `Event`, ou le nom
  d'un événement du framework. Sans cela, une faute de frappe dans `emit()` n'appellerait aucun handler,
  sans erreur (corrigé après l'item 7 : la première version de `emit()` ne validait rien).
- `Event` est exporté par `pyclifer/__init__.py`. Les specs 09, 05 et 06 déclarent leurs événements
  comme des `Event`.

---

## Fichiers à modifier

| Fichier                                | Changement                                                            |
|----------------------------------------|-----------------------------------------------------------------------|
| `src/pyclifer/core/events.py` (nouveau) | `CONFIG_LOADED`, `EVENTS`                                            |
| `src/pyclifer/core/mixins/events.py` (nouveau) | `EventsMixin`                                                 |
| `src/pyclifer/core/mixins/__init__.py` | Exporter `EventsMixin`                                                |
| `src/pyclifer/core/classes.py`         | `EventsMixin` dans les bases des groupes ; `GroupConfig.on` ; émission dans `CustomConfigOption.load_conf` |
| `src/pyclifer/core/decorators.py`      | `GroupDecorator._configure_events()`                                  |
| `tests/core/test_events.py` (nouveau)  | Constantes et validation des noms                                     |
| `tests/core/mixins/test_events.py` (nouveau) | `EventsMixin`                                                   |
| `tests/core/options/test_custom_config_option.py` | Émission de `config.loaded`                                |
| `tests/core/test_decorators.py`        | Inscription via `@app_group(on=...)`                                  |
| `docs/api/mixins.md`                   | Documenter `EventsMixin`                                              |
| `docs/api/classes.md`                  | `PycliferGroup` (bases), `CustomConfigOption` (émission)              |
| `docs/api/decorators.md`               | Paramètre `on` de `app_group` / `group` (les paramètres de groupe y sont documentés, pas dans `classes.md`) |
| `src/pyclifer/__init__.py`             | Exporter `EventsMixin` (API publique, comme les autres mixins)        |
| `tests/test_init.py` (nouveau)         | `EventsMixin` exporté et listé dans `__all__`                         |
| `docs/how-to/lifecycle-events.md` (nouveau) | Guide d'usage                                                    |
| `mkdocs.yml`                           | Ajouter la page au `nav`                                              |

---

## ✅ Item 1 : Constantes d'événements et validation des noms

Test d'abord (`tests/core/test_events.py`) :

- `CONFIG_LOADED == "config.loaded"` et `CONFIG_LOADED in EVENTS` ;
- `EVENTS` est un `frozenset`.

Puis `core/events.py`. Branche : `feat/lifecycle-events-registry`.

## ✅ Item 2 : `EventsMixin`

Tests d'abord (`tests/core/mixins/test_events.py`, groupe minimal `_Group(EventsMixin, click_extra.Group)`) :

- `on` avec handler direct, puis `emit` l'appelle avec le contexte ;
- `on` sans handler s'utilise en décorateur et renvoie la fonction inchangée ;
- plusieurs handlers s'exécutent dans l'ordre d'inscription et `emit` renvoie leurs résultats dans cet ordre ;
- `emit` sans handler inscrit renvoie `[]` ;
- `on("typo")` lève `ValueError` avec `match="Unknown event 'typo'"` et la liste des noms valides ;
- une exception de handler se propage.

Squelette :

```python
class EventsMixin:
    """Mixin that lets a group attach handlers to named lifecycle events."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the handler registry then chain to the next class.

        Args:
            *args: Positional arguments for the parent class.
            **kwargs: Keyword arguments for the parent class.
        """
        self._event_handlers: dict[str, list[EventHandler]] = {}
        super().__init__(*args, **kwargs)
```

## ✅ Item 3 : Câblage `GroupConfig.on`, groupes composites, `_configure_events`

Tests d'abord (`tests/core/test_decorators.py`) : `@app_group(on={"config.loaded": [h]})` inscrit `h` ;
un nom inconnu dans `on=` lève `ValueError` à la décoration ; sans `on`, aucun handler.
Bases : `PycliferExtraGroup(EventsMixin, HandleResponseMixin, GlobalOptionsMixin, click_extra.Group)`
et `PycliferRichGroup(EventsMixin, HandleResponseMixin, GlobalOptionsMixin, RichGroup)`.

## ✅ Item 4 : Émission de `config.loaded`

Tests d'abord (`tests/core/options/test_custom_config_option.py`, application réelle via `invoke`) :

- fichier de config présent : le handler est appelé une fois, avec `ctx.meta[CONF_SOURCE]` renseigné ;
- aucun fichier trouvé : le handler est appelé quand même, une fois (`app_group` n'expose pas
  `--no-config`, il n'est donc pas testé) ;
- appel **nu** dont le fichier de config (découvert via `XDG_CONFIG_HOME`) contient `_default_subcommands` :
  `load_conf` est visité deux fois pour la même option, le handler n'est appelé qu'une fois ;
- un handler qui lève une `ClickException` sur un appel normal (`hello`) : code de sortie 2 et message sur
  stderr, affichés une seule fois ;
- un handler qui lève une `ClickException` sur un **appel nu** (sans config, puis avec
  `_default_subcommands`) : code 2, message du handler sur stderr, puis l'aide ;
- le même appel nu avec `output_format_default="json"` : réponse JSON dont le message est celui du handler
  et `error_type` vaut `usage_error` (le groupe répond avec l'erreur du handler, pas avec l'aide) ;
- une sous-commande construite avec `click_extra.command` (donc avec sa propre `ConfigOption`) n'émet rien
  et n'empêche pas l'émission de la racine ;
- `--help` (`resilient_parsing`) : pas d'émission ;
- sans handler inscrit, aucun effet de bord.

Le double appel est déjà mesuré (voir « Constat préalable ») : le test de l'appel nu avec
`_default_subcommands` est le premier à écrire, et il doit échouer avec deux émissions avant l'ajout du
marqueur. Pour le construire : `XDG_CONFIG_HOME` pointé vers un dossier temporaire, fichier
`<dossier>/<nom-de-l-app>/config.toml` contenant `[<app>]` et `_default_subcommands = ["<commande>"]`.

## ✅ Item 5 : Vérification complète

```bash
ruff check src/ tests/ && ruff format src/ tests/
python -m pytest tests/ -v
tox
```

Couverture de branches à 100 % sur les modules touchés.

## ✅ Item 6 : Documentation

- `docs/how-to/lifecycle-events.md` (nouveau) : modèle mental (l'application déclare, les événements
  étendent), `on=` et `cli.on(...)`, liste des événements disponibles (pour l'instant `config.loaded`),
  règles d'ordre et d'erreur (ordre d'inscription, exceptions propagées).
- `docs/api/mixins.md` : `EventsMixin`. `docs/api/decorators.md` : paramètre `on`.
  `docs/api/classes.md` : bases de `PycliferGroup` et émission de `CustomConfigOption`.
- Le guide ne décrit que des comportements mesurés (quand `config.loaded` est émis, y compris
  `--config fichier --help`) ; `EventsMixin` est exporté par `pyclifer/__init__.py` pour que
  `::: pyclifer.EventsMixin` fonctionne dans `mkdocs`.
- `mkdocs.yml` : ajouter la page au `nav` dans le même commit.
- `mkdocs build --strict`.

## ✅ Item 7 : Événements définis par l'utilisateur (`Event`)

Tests d'abord :

- `tests/core/test_events.py` : `CONFIG_LOADED` est une instance d'`Event` et égale à `"config.loaded"` ;
  un `Event` personnalisé n'est pas dans `EVENTS` ; une chaîne simple n'est pas une instance d'`Event` ;
- `tests/core/mixins/test_events.py` : `on(Event("x.y"), handler)` puis `emit` appelle le handler sans
  enregistrement préalable ; la forme décorateur fonctionne ; une chaîne simple inconnue lève toujours
  `ValueError` (le message suggère `Event(...)`) ; la chaîne `"config.loaded"` reste acceptée ;
- `tests/core/test_decorators.py` : `@app_group(on={Event("x.y"): [h]})` attache le handler ; un plugin
  peut émettre depuis une commande avec `ctx.find_root().command.emit(EVENT, ctx)` ;
- `tests/test_init.py` : `Event` est exporté et listé dans `__all__`.

Puis `Event` dans `core/events.py`, la condition de `on()`, l'export, et la documentation (section
« Define your own events » du guide, `Event` dans `docs/api/mixins.md`). Vérification complète à la fin.

Commit unique par item (format de `.claude/CLAUDE.md`), spec incluse avec le `✅` sur l'item. Fusion
dans `main` après validation de l'utilisateur.
