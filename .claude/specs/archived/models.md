# Models — couche domaine avec Pydantic

## Contexte

La couche modèle (MTV : Model-Template-View) est la seule absente du framework.
`models.py` est généré vide. Chaque projet invente son propre pattern `to_dict()` pour
remplir `OperationResult.data`, ce qui rend les renderers fragiles et non-typés.

## Décision : Pydantic comme fondation

`BaseModel` étend directement `pydantic.BaseModel`. Pydantic devient une dépendance
runtime de pyclifer.

**Pourquoi Pydantic et pas `@dataclass` ?**

Construire notre propre système de validation (à la Django) reviendrait à réimplémenter
Pydantic — en moins bon. Django a pu le faire parce que ses champs (`CharField`,
`IntegerField`) portent eux-mêmes la coercition de types. Pour des annotations Python
modernes (`int | None`, `list[str]`, `datetime`, modèles imbriqués, références forward),
la validation runtime correcte nécessite exactement ce que Pydantic fait, avec ses années
de corrections de cas limites.

| Besoin | `@dataclass` | Pydantic |
|--------|:------------:|:--------:|
| Validation de type runtime (`id: int` reçoit `"abc"`) | ❌ silencieux | ✅ `ValidationError` clair |
| Coercition (`"42"` → `42`) | ❌ | ✅ configurable |
| Règle métier (`status` ∈ liste) | ✅ via `__post_init__` | ✅ via `@field_validator` |
| Champ requis absent du dict | ❌ `TypeError` cryptique | ✅ `ValidationError` |
| Sérialisation de types complexes (`datetime`, `UUID`) | ❌ manuel | ✅ `model_dump()` |
| Introspection des champs | ❌ fragile | ✅ `model_fields` |
| `from_dict()` générique | ❌ `Model(**d)` explose si clés inconnues | ✅ `model_validate()` |

**Le poids de la dépendance** (~1.5 MB de code Rust via `pydantic-core`) est raisonnable
pour un framework dont la vocation est de consommer des APIs. Pydantic est déjà la
dépendance transitive de nombreux outils Python modernes.

## `BaseModel` — design

`BaseModel` étend `pydantic.BaseModel` avec des helpers framework qui exposent une
interface cohérente avec le reste de pyclifer :

```python
import pydantic
from typing import Any, Self

class BaseModel(pydantic.BaseModel):
    """Base class for pyclifer domain models.

    Extends pydantic.BaseModel with to_dict(), from_dict() and field_names()
    for integration with OperationResult and BaseRenderer.
    """

    def to_dict(self) -> dict[str, Any]:
        """Serialize the model to a JSON-compatible dict."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build an instance from a dict with Pydantic validation."""
        return cls.model_validate(data)

    @classmethod
    def field_names(cls) -> list[str]:
        """Return the declared field names — used by BaseRenderer."""
        return list(cls.model_fields.keys())
```

### Exemple d'utilisation

```python
# models.py
from pyclifer import BaseModel
from pydantic import field_validator

class Article(BaseModel):
    id: int
    title: str
    status: str
    created_at: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("draft", "published"):
            raise ValueError(f"status invalide : {v!r}")
        return v

# interfaces.py
class ArticleInterface(BaseInterface):
    renderers = {"list": ArticleListRenderer}

    def list(self) -> list[OperationResult]:
        items = self._api.get("/articles")
        return [OperationResult.ok(str(a["id"]), data=Article.from_dict(a)) for a in items]

# renderers.py
class ArticleListRenderer(BaseRenderer):
    model_class = Article             # fields auto-déduits via field_names()
    columns = ["id", "title", "status"]
    success_message = "Articles fetched."
```

## `BaseModel` générique — renderer typé

`BaseRenderer` peut être paramétré par le type de modèle qu'il affiche. C'est une
extension optionnelle : le renderer sait quel modèle il manipule, ce qui permet
l'autocomplétion et la vérification statique dans les IDEs.

```python
from typing import Generic, TypeVar

M = TypeVar("M", bound=BaseModel)

class BaseRenderer(Generic[M]):
    model_class: ClassVar[type[M] | None] = None
    ...

# Renderer typé — l'IDE connaît le type de `result.data`
class ArticleListRenderer(BaseRenderer[Article]):
    model_class = Article
    columns = ["id", "title", "status"]
```

Sans paramètre de type, `BaseRenderer` reste utilisable tel quel — le générique est
opt-in et non-cassant pour le code existant.

## Flow complet avec modèle

```
API / DB
  ↓
Interface.list()  →  Article.from_dict(raw)   ← validation Pydantic ici
  ↓
OperationResult.ok(str(article.id), data=article)
  ↓
BaseRenderer._result_to_row()  →  article.to_dict()
  ↓
JSON / YAML / Table / Rich
```

Les erreurs de l'API sont attrapées à la construction du modèle, pas au moment du rendu.

## Intégration avec `OperationResult`

Aucun changement de signature — `data: Any` reste `Any`. La compatibilité descendante
est préservée :

- `data=article` — `BaseModel` passé directement, `to_dict()` appelé à la lecture
- `data=article.to_dict()` — dict explicite, fonctionne toujours

## Intégration avec `BaseRenderer`

### Nouvel attribut `model_class`

Quand `model_class` est déclaré, `get_fields()` retourne `model_class.field_names()`
si `fields` est vide. `columns` reste manuel — tous les champs ne sont pas affichables
en table.

```python
class BaseRenderer:
    model_class: ClassVar[type[BaseModel] | None] = None

    def get_fields(self) -> list[str]:
        if self.fields:
            return list(self.fields)
        if self.model_class is not None:
            return self.model_class.field_names()
        return []
```

### `_result_to_row()` et `serialize()` — gestion de `BaseModel` en data

La détection se fait via `to_dict` — compatible `BaseModel` pyclifer et tout objet
exposant la même interface.

```python
def _result_to_row(self, result: OperationResult, columns: list[str]) -> dict:
    data = result.data
    if hasattr(data, "to_dict") and callable(data.to_dict):
        data = data.to_dict()
    # ... accès au dict résultant
```

`serialize()` applique le même pattern avant d'extraire les champs déclarés.

## Steps de livraison

| #  | Livrable | Statut |
|----|----------|--------|
| 1  | Ajouter `pydantic>=2.0,<3.0` dans `pyproject.toml` | ✅ |
| 2  | `core/models.py` — `BaseModel(pydantic.BaseModel)` avec `to_dict()`, `from_dict()`, `field_names()` | ✅ |
| 3  | `core/output/renderer.py` — `model_class` sur `BaseRenderer` ; `get_fields()` fallback via `model_class` ; `_result_to_row()` + `serialize()` gèrent `BaseModel` | ✅ |
| 4  | `core/output/responses.py` — `Response._serialize_data()` gère `BaseModel` dans les valeurs du dict | ✅ |
| 5  | `pyclifer/__init__.py` — ajouter `BaseModel` dans `__all__` | ✅ |
| 6  | Templates — `app_models.py.jinja2` avec un modèle Pydantic concret + `@field_validator` ; `app_interfaces.py.jinja2` avec `Article.from_dict()` | ✅ |
| 7  | Tests — `tests/core/test_models.py` : `to_dict`, `from_dict`, `field_names`, validation Pydantic, `ValidationError` sur type invalide | ✅ |
| 8  | Tests — `tests/core/test_renderer.py` : `model_class` déduit les fields ; `_result_to_row` avec `BaseModel` ; `serialize` avec `BaseModel` | ✅ |
| 9  | Tests — `tests/core/test_output.py` : `_serialize_data` avec `BaseModel` dans les valeurs du dict | ✅ |
| 10 | Docs — `docs/api/models.md` créé et enregistré dans `mkdocs.yml` | ✅ |

## Ce qui ne change pas

- `OperationResult` — signature inchangée, `data: Any` reste `Any`
- `BaseInterface.respond()` — inchangé
- `Response.from_results()` / `from_stream()` — inchangés
- Les 4 décorateurs — inchangés
- Les commandes et renderers existants — inchangés (compatibilité descendante)

## Extensions futures (hors scope)

- `BaseCRUDInterface` — stubs génériques `list / get / create / update / delete`
- Validation des options CLI via Pydantic (`--config` parsé en modèle)
- Génération automatique du renderer depuis le modèle (`ArticleRenderer = BaseRenderer.from_model(Article)`)
