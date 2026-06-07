# Framework improvements — ctx.meta cohérence, secrets masker, output filter, pagination

## Contexte

Améliorations ciblées identifiées lors d'une revue du code `core/`. L'étape 0 est un
prérequis bloquant — elle rend le code cohérent avant tout autre changement. Les étapes
suivantes sont indépendantes et livrables dans n'importe quel ordre, sauf la pagination
qui dépend de l'étape 0.

| #  | Feature                                         | Effort | Dépend de | Statut |
|----|-------------------------------------------------|--------|-----------|--------|
| 0  | `ctx.meta` — uniformiser les clés               | Petit  | —         | ✅ fait |
| 1  | `CliMetadata` — metadata structurée (optionnel) | Moyen  | 0         | ❌ abandonné |
| 2  | `SecretsMasker` configurable                    | Petit  | —         | ✅ fait |
| 3  | Output filter — feedback explicite              | Petit  | —         | ✅ fait |
| 4  | Pagination — options standard                   | Moyen  | —         | ✅ fait |

---

## 0. `ctx.meta` — uniformiser les clés (prérequis)

### Problème

`get_meta_storing_callback` dans `core/callbacks.py` impose la convention `pyclifer.{param.name}`
(séparateur point). Mais certaines clés liées au logging ont été écrites à la main avec un
séparateur underscore, hors convention :

```python
# Convention appliquée par get_meta_storing_callback
ctx.meta["pyclifer.output_format"]
ctx.meta["pyclifer.verbosity"]

# Hors convention — écrites manuellement ailleurs
ctx.meta["pyclif_log_file_path"]
ctx.meta["pyclif_log_file_level"]
```

### Décision

Renommer les clés hors convention pour suivre `pyclifer.{param.name}` :

```python
ctx.meta["pyclif_log_file_path"]  →  ctx.meta["pyclifer.log_file_path"]
ctx.meta["pyclif_log_file_level"] →  ctx.meta["pyclifer.log_file_level"]
```

Mettre à jour tous les sites de lecture pour utiliser les nouveaux noms. Aucun changement
de logique, uniquement du renommage.

### Impact par fichier

| Fichier              | Changement                                     |
|----------------------|------------------------------------------------|
| `core/log/config.py` | Renommer les clés à l'écriture et à la lecture |
| `core/decorators.py` | Mettre à jour les lectures si présentes        |

---

## 1. `CliMetadata` — metadata structurée sur le contexte

### Problème

`ctx.meta` est un dict brut avec des clés string dispersées dans le code, sans convention
stable. Deux bugs de nommage existent déjà :

- `ctx.meta["pyclifer.output_format"]` — séparateur point
- `ctx.meta["pyclif_log_file_path"]` — séparateur underscore

Une faute de frappe retourne `None` silencieusement. Il n'y a ni type safety, ni
discoverabilité, ni endroit unique pour voir toute la metadata du framework.

### Décision de design

Un dataclass `CliMetadata` remplace l'accès direct au dict. Il vit dans `core/context.py`
aux côtés de `BaseContext` et s'accède via une propriété `pyclifer` sur `BaseContext`.

```python
@dataclass
class CliMetadata:
    output_format: str = "table"
    output_filter: str | None = None
    verbosity: str = "WARNING"
    log_file_path: str | None = None
    log_file_level: str = "DEBUG"
    unhandled_exception_log_level: str = "error"
    extra: dict[str, Any] = field(default_factory=dict)
```

Avant / après :

```python
# Avant
ctx.meta["pyclifer.output_format"]
ctx.meta["pyclif_log_file_path"]

# Après
ctx.pyclifer.output_format
ctx.pyclifer.log_file_path
```

Pour les options utilisateur avec `store_in_meta=True`, le dict `extra` préserve la
compatibilité :

```python
# @option("--my-flag", store_in_meta=True) écrit ici
ctx.pyclifer.extra["my_flag"]
```

### Intégration dans `BaseContext`

La propriété initialise `CliMetadata` à la première demande — lazy init dans `ctx.meta`
pour rester compatible avec le cycle de vie Click.

```python
class BaseContext(OutputFormatMixin, RichHelpersMixin):

    @property
    def pyclifer(self) -> CliMetadata:
        """Return the framework metadata object for this context."""
        if "pyclif_metadata" not in self.meta:
            self.meta["pyclif_metadata"] = CliMetadata()
        return self.meta["pyclif_metadata"]
```

### Impact par fichier

| Fichier | Changement |
|---------|-----------|
| `core/context.py` | Ajouter `CliMetadata` ; propriété `pyclifer` sur `BaseContext` |
| `core/mixins/output.py` | `ctx.meta["pyclifer.output_format"]` → `ctx.pyclifer.output_format` |
| `core/mixins/output.py` | `ctx.meta["pyclifer.output_filter"]` → `ctx.pyclifer.output_filter` |
| `core/mixins/cli.py` | `ctx.meta["pyclifer.verbosity"]` → `ctx.pyclifer.verbosity` |
| `core/log/config.py` | `ctx.meta["pyclif_log_file_*"]` → `ctx.pyclifer.log_file_*` |
| `core/decorators.py` | Toutes les écritures `ctx.meta[...]` des clés framework |
| `core/callbacks.py` | `get_meta_storing_callback` écrit dans `ctx.pyclifer.extra` |
| `pyclifer/__init__.py` | Ajouter `CliMetadata` à `__all__` |

### Tests

`tests/core/test_context.py` — nouveaux cas :
- `pyclifer` property initialise `CliMetadata` avec les valeurs par défaut
- Deuxième accès retourne la même instance (pas de re-création)
- `extra` dict accessible et modifiable

### Migration

Remplacement mécanique des clés string — aucun changement de logique. Le lazy init dans la
propriété garantit la rétrocompatibilité pendant la migration.

---

## 2. `SecretsMasker` configurable à l'exécution

### Problème

`REGEX_SENSITIVE_FIELDS` est compilé une fois au chargement du module. Un projet avec des
noms de champs spécifiques (`bearer_token`, `api_secret_key`) ne peut pas les ajouter
sans patcher le framework — ce qui est inacceptable pour un usage sécurité.

### Décision de design

`@app_group` accepte `sensitive_fields: list[str]`. Les valeurs sont fusionnées avec la
liste par défaut au moment de la configuration du logging.

```python
@app_group(
    handle_response=True,
    sensitive_fields=["bearer_token", "api_secret_key"],
)
def main(): ...
```

#### `SecretsMasker` — construction du regex à l'instance

Le regex passe de constante de module à attribut d'instance. `DEFAULT_FIELDS` reste un
attribut de classe pour rester surchargeable dans des sous-classes.

`sensitive_fields` est un **ajout** à `DEFAULT_FIELDS` — les champs par défaut sont
toujours actifs. Passer `sensitive_fields=["bearer_token"]` ne remplace pas `password`,
`api_key`, etc. Le développeur n'a pas besoin de redéclarer les defaults.

```python
class SecretsMasker(logging.Filter):
    DEFAULT_FIELDS: ClassVar[frozenset[str]] = frozenset([
        "access_token", "api_key", "password", "secret", "token",
        "private_key", "auth", "credential",
    ])

    def __init__(self, sensitive_fields: list[str] | None = None) -> None:
        """Initialize the masker, merging sensitive_fields into DEFAULT_FIELDS.

        Args:
            sensitive_fields: Additional field names to mask on top of DEFAULT_FIELDS.
                              None and [] are equivalent — only DEFAULT_FIELDS are used.
        """
        super().__init__()
        all_fields = self.DEFAULT_FIELDS | set(sensitive_fields or [])
        pattern = "|".join(re.escape(f) for f in sorted(all_fields))
        self._regex = re.compile(rf"\b({pattern})\b", re.IGNORECASE)
```

#### `GroupConfig` — nouveau champ

```python
@dataclass
class GroupConfig:
    ...
    sensitive_fields: list[str] = field(default_factory=list)
```

#### `configure_rich_logging()` — paramètre `sensitive_fields`

```python
def configure_rich_logging(
    log_level: int = logging.WARNING,
    sensitive_fields: list[str] | None = None,
) -> None:
    """Configure Rich logging globally.

    Args:
        sensitive_fields: Additional field names to mask on top of the defaults.
                          Merged into SecretsMasker.DEFAULT_FIELDS — does not replace them.
    """
    ...
    handler.addFilter(SecretsMasker(sensitive_fields=sensitive_fields))
```

`GroupDecorator._apply_logging()` lit `config.sensitive_fields` et le transmet :

```python
configure_rich_logging(sensitive_fields=config.sensitive_fields or None)
```

Idem pour `RichExtraStreamHandler` et `setup_file_logging` qui instancient `SecretsMasker`
directement — ils reçoivent aussi `sensitive_fields` et le transmettent.

### Impact par fichier

| Fichier | Changement |
|---------|-----------|
| `core/log/filters.py` | `SecretsMasker.__init__` accepte `sensitive_fields` ; regex instance |
| `core/log/handlers.py` | `RichExtraStreamHandler.__init__` accepte `sensitive_fields` |
| `core/log/config.py` | `configure_rich_logging()` et `setup_file_logging()` acceptent `sensitive_fields` |
| `core/classes.py` | `GroupConfig.sensitive_fields: list[str]` |
| `core/decorators.py` | `GroupDecorator._apply_logging()` lit `config.sensitive_fields` |

### Tests

`tests/core/log/test_rich_logging.py` (`TestSecretsMasker`) — nouveaux cas :
- `SecretsMasker()` sans args masque les champs par défaut
- `SecretsMasker(sensitive_fields=["bearer_token"])` masque aussi `bearer_token`
- `sensitive_fields=[]` et `sensitive_fields=None` se comportent identiquement aux defaults
- Les champs par défaut sont toujours présents quand `sensitive_fields` est fourni (pas de remplacement)

---

## 3. Output filter — feedback explicite sur les chemins invalides

### Problème

`--output-filter results.0.nonexistent` retourne `None` silencieusement. Déboguer nécessite
d'inspecter le JSON brut puis de deviner quelle partie du chemin est incorrecte.

### Décision de design

Quand le chemin de filtre ne se résout pas, le framework écrit un message explicite sur
stderr avec les clés disponibles au dernier nœud valide, puis quitte avec le code 2.

#### Format de l'erreur — via le système Response existant

Plutôt que de dupliquer la logique de format (json.dumps / yaml.dump / texte), le framework
construit un `Response(success=False)` et le passe à `print_result_based_on_format()` —
qui sait déjà dispatcher vers le bon format. L'erreur s'affiche exactement comme n'importe
quelle autre réponse d'erreur, dans le format actif.

```python
# Chemin invalide → Response d'erreur passée au système de dispatch normal
message = f"filter path '{filter_path}' not found in response."
result = OperationResult(
    success=False,
    item="output-filter",
    message=message,
    error_code=2,
    data={"available_keys": sorted(available_keys)},
)
error_response = Response.from_results([result], message=message)
self.print_result_based_on_format(error_response)
raise SystemExit(2)
```

Le renderer utilisé est `_ExceptionRenderer` (déjà présent dans `output.py`), qui affiche
le message d'erreur dans tous les formats. `data["available_keys"]` est inclus dans les
sorties JSON et YAML automatiquement via `serialize()`.

#### `_resolve_filter_path()` — remplace `_extract_filter_value()`

Retourne un tuple `(value, found)` au lieu de retourner `None` pour les deux cas (valeur
absente vs valeur trouvée mais `None`).

```python
@staticmethod
def _resolve_filter_path(data: dict, path: str) -> tuple[Any, bool]:
    """Traverse a dotted path in a nested dict or list.

    Args:
        data: The dict to traverse.
        path: Dotted path — numeric segments are treated as list indices,
              negative indices are supported (e.g. 'results.-1.id').

    Returns:
        A tuple of (resolved value, found). If the path does not exist,
        found is False and value is None.
    """
    segments = path.split(".")
    node: Any = data
    for segment in segments:
        if isinstance(node, list):
            if not segment.lstrip("-").isdigit():
                return None, False
            idx = int(segment)
            if idx >= len(node) or idx < -len(node):
                return None, False
            node = node[idx]
        elif isinstance(node, dict):
            if segment not in node:
                return None, False
            node = node[segment]
        else:
            return None, False
    return node, True
```

Le chemin est résolu en deux passes : d'abord dans `data["data"]` (payload structuré),
puis dans le dict racine de la réponse. Le premier `found=True` gagne.

Les **indices négatifs** sont supportés : `results.-1.id` pointe sur le dernier élément.

### Impact par fichier

| Fichier                 | Changement                                                                                       |
|-------------------------|--------------------------------------------------------------------------------------------------|
| `core/mixins/output.py` | Renommer `_extract_filter_value` → `_resolve_filter_path` ; tuple de retour ; erreur via Response |

### Tests

`tests/core/mixins/test_output.py` — nouveaux cas :
- `_resolve_filter_path` : chemin valide retourne `(value, True)`
- `_resolve_filter_path` : clé absente retourne `(None, False)`
- `_resolve_filter_path` : indice de liste hors bornes retourne `(None, False)`
- `_resolve_filter_path` : indice négatif résout depuis la fin
- Chemin invalide → `print_result_based_on_format` appelé avec une Response `success=False` + `SystemExit(2)`

---

## 4. Pagination — options standard pour les commandes list

### Problème

Les commandes `list` n'ont aucune convention partagée. Chaque projet crée ses propres
options `--page` / `--limit` avec des noms, des défauts et des messages d'aide différents.
Le JSON de réponse ne porte pas de métadonnées de pagination, ce qui complique les clients
API qui consomment les sorties.

### Décision de design

Deux ajouts indépendants et opt-in :

- `pagination_options()` — décorateur qui injecte `--page` et `--limit` et les stocke dans
  `ctx.pyclifer` (dépend de l'amélioration 1)
- `PaginatedResponse` — sous-classe de `Response` qui ajoute un bloc `pagination` dans
  la sortie JSON/YAML

#### `pagination_options()` — décorateur

```python
def pagination_options(
    default_limit: int = 20,
    max_limit: int = 100,
) -> Callable:
    """Inject --page and --limit options into a command.

    Options are stored in ctx.meta under the keys 'pyclifer.page' and 'pyclifer.limit'.

    Args:
        default_limit: Default number of results per page.
        max_limit: Maximum allowed value for --limit.

    Returns:
        A decorator that adds the two options to the decorated function.
    """
    def decorator(f: Callable) -> Callable:
        f = option(
            "--limit", "-l",
            default=default_limit,
            type=click.IntRange(1, max_limit),
            help=f"Results per page. [default: {default_limit}]",
            store_in_meta=True,
        )(f)
        f = option(
            "--page", "-p",
            default=1,
            type=click.IntRange(min=1),
            help="Page number (1-indexed).",
            store_in_meta=True,
        )(f)
        return f
    return decorator
```

Utilisation dans une commande :

```python
@command()
@pagination_options(default_limit=50)
@pass_cli_context
def list_articles(ctx) -> Response:
    """List articles."""
    return ArticleInterface(ctx).respond(
        "list",
        page=ctx.meta["pyclifer.page"],
        limit=ctx.meta["pyclifer.limit"],
    )
```

#### `PaginatedResponse` — métadonnées de pagination

```python
@dataclass
class PaginatedResponse(Response):
    """Response carrying pagination metadata in its serialized output."""
    page: int = 1
    limit: int = 20
    total: int | None = None

    def to_dict(self) -> dict:
        """Include a 'pagination' block in the serialized output."""
        base = super().to_dict()
        base["pagination"] = {
            "page": self.page,
            "limit": self.limit,
            "total": self.total,
        }
        return base
```

La sortie JSON gagne un bloc `pagination` automatiquement :

```json
{
  "success": true,
  "message": "Articles fetched.",
  "pagination": {"page": 1, "limit": 20, "total": 142},
  "data": {"results": [...]}
}
```

L'interface retourne `PaginatedResponse` à la place de `Response` quand elle connaît le
total. Si le total est inconnu (API sans comptage), `total=None` est sérialisé tel quel.

### Impact par fichier

| Fichier | Changement |
|---------|-----------|
| `core/decorators.py` | Ajouter `pagination_options()` |
| `core/output/responses.py` | Ajouter `PaginatedResponse` |
| `pyclifer/__init__.py` | Exporter `pagination_options`, `PaginatedResponse` |
| `docs/api/output.md` | Documenter `PaginatedResponse` |
| `docs/api/decorators.md` | Documenter `pagination_options()` |

### Tests

`tests/core/output/test_responses.py` — nouveaux cas :
- `PaginatedResponse.to_dict()` contient le bloc `pagination`
- `total=None` est sérialisé sans erreur
- `PaginatedResponse` hérite correctement de `Response.from_results()`

`tests/core/test_decorators.py` — nouveaux cas :
- `pagination_options()` injecte `--page` et `--limit` avec les bonnes valeurs par défaut
- `max_limit` est respecté (`click.IntRange`)

### Ce qui ne change pas

`pagination_options()` est purement additif. `PaginatedResponse` est opt-in. Les commandes
existantes ne sont pas affectées.