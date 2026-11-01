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
- `load_conf` peut être visité plus d'une fois pour un même appel (garde `_PRELOADED` de click-extra,
  deux appels observés dans un essai). L'émission doit donc être **unique par contexte racine**.

---

## Design

### Décision 1 — Ensemble fermé de noms, constantes de chaînes

`core/events.py` contient les noms d'événements en constantes `UPPER_SNAKE` (`CONFIG_LOADED =
"config.loaded"`) et `EVENTS: frozenset[str]`. Une enum n'est pas utilisée : `StrEnum` n'existe qu'à
partir de Python 3.11 et le projet supporte 3.10. Les utilisateurs écrivent la chaîne.
Un nom inconnu lève `ValueError` à l'inscription, en listant les noms valides (une faute de frappe ne
doit jamais être silencieuse). Chaque spec consommatrice ajoute ses noms à `EVENTS`.

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

- émis une seule fois par contexte (drapeau dans `ctx.meta`) ;
- émis que le fichier existe ou non (`ctx.meta[CONF_SOURCE]` dit lequel) ;
- **non émis** si `ctx.resilient_parsing` (aide, complétion), comme click-extra ne lit pas le fichier
  dans ce cas.

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
| `docs/api/classes.md`                  | `GroupConfig.on`, `CustomConfigOption` (émission)                     |
| `docs/how-to/lifecycle-events.md` (nouveau) | Guide d'usage                                                    |
| `mkdocs.yml`                           | Ajouter la page au `nav`                                              |

---

## Item 1 : Constantes d'événements et validation des noms

Test d'abord (`tests/core/test_events.py`) :

- `CONFIG_LOADED == "config.loaded"` et `CONFIG_LOADED in EVENTS` ;
- `EVENTS` est un `frozenset`.

Puis `core/events.py`. Branche : `feat/lifecycle-events-registry`.

## Item 2 : `EventsMixin`

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

## Item 3 : Câblage `GroupConfig.on`, groupes composites, `_configure_events`

Tests d'abord (`tests/core/test_decorators.py`) : `@app_group(on={"config.loaded": [h]})` inscrit `h` ;
un nom inconnu dans `on=` lève `ValueError` à la décoration ; sans `on`, aucun handler.
Bases : `PycliferExtraGroup(EventsMixin, HandleResponseMixin, GlobalOptionsMixin, click_extra.Group)`
et `PycliferRichGroup(EventsMixin, HandleResponseMixin, GlobalOptionsMixin, RichGroup)`.

## Item 4 : Émission de `config.loaded`

Tests d'abord (`tests/core/options/test_custom_config_option.py`, application réelle via `invoke`) :

- fichier de config présent : le handler est appelé une fois, avec `ctx.meta[CONF_SOURCE]` renseigné ;
- aucun fichier ou `--no-config` : le handler est appelé quand même, une fois ;
- un appel qui visite `load_conf` plusieurs fois n'émet qu'une fois (cas `_PRELOADED`) ;
- `--help` (`resilient_parsing`) : pas d'émission ;
- sans handler inscrit, aucun effet de bord.

Premier travail de l'item : **reproduire le double appel de `load_conf`** observé dans un essai
(commande exécutée avec `--config`), pour fixer le drapeau d'unicité sur un fait et non sur une supposition.

## Item 5 : Vérification complète

```bash
ruff check src/ tests/ && ruff format src/ tests/
python -m pytest tests/ -v
tox
```

Couverture de branches à 100 % sur les modules touchés.

## Item 6 : Documentation

- `docs/how-to/lifecycle-events.md` (nouveau) : modèle mental (l'application déclare, les événements
  étendent), `on=` et `cli.on(...)`, liste des événements disponibles (pour l'instant `config.loaded`),
  règles d'ordre et d'erreur (ordre d'inscription, exceptions propagées).
- `docs/api/mixins.md` : `EventsMixin`. `docs/api/classes.md` : `GroupConfig.on`.
- `mkdocs.yml` : ajouter la page au `nav` dans le même commit.
- `mkdocs build --strict`.

Commit unique par item (format de `.claude/CLAUDE.md`), spec incluse avec le `✅` sur l'item. Fusion
dans `main` après validation de l'utilisateur.
