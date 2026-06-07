# Models

## BaseModel

Base class for pyclifer domain models. Extends `pydantic.BaseModel` with three helpers that
integrate with `OperationResult` and `BaseRenderer`:

- `to_dict()` — serializes the model to a JSON-compatible dict (called automatically by
  `BaseRenderer._result_to_row()` when `result.data` is a model instance)
- `from_dict()` — builds and validates an instance from a raw dict (API response, DB row, …)
- `field_names()` — returns declared field names in order; used by `BaseRenderer.get_fields()`
  when `model_class` is set and no explicit `fields` list is declared

::: pyclifer.BaseModel

---

## Usage

### 1. Declare a model

```python
# src/my_project/apps/articles/models.py
import datetime
import pydantic
from pyclifer import BaseModel

STATUSES = ("draft", "published", "archived")


class Article(BaseModel):
    id: str
    title: str
    author: str
    status: str = "draft"
    published_at: datetime.datetime | None = None

    @pydantic.field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Reject status values outside the allowed set."""
        if v not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}, got {v!r}")
        return v
```

### 2. Use in an interface

Interface methods attach model instances to `OperationResult.data`. The framework serializes
them automatically via `to_dict()` — no manual conversion needed.

```python
from pyclifer import BaseInterface, OperationResult
from .models import Article


class ArticleInterface(BaseInterface):
    renderers = {"list_articles": ArticleListRenderer}

    def list_articles(self) -> list[OperationResult]:
        rows = self._db.all()
        return [
            OperationResult.ok(row["id"], data=Article.from_dict(row))
            for row in rows
        ]
```

### 3. Wire to a renderer via `model_class`

Setting `model_class` on a renderer lets `BaseRenderer.get_fields()` fall back to
`Article.field_names()` automatically — no need to repeat the field list.

```python
from pyclifer import BaseRenderer
from .models import Article


class ArticleListRenderer(BaseRenderer):
    model_class = Article               # fields derived from Article.field_names()
    columns = ["id", "title", "author", "status"]
    rich_title = "Articles"
    success_message = "Articles retrieved."
```

Declare an explicit `fields` list on the renderer to override the model's field order or
restrict which fields appear in JSON/YAML output.

---

## Integration points

| Where | How `BaseModel` is used |
|---|---|
| `OperationResult.data` | Store a model instance directly — `BaseRenderer._result_to_row()` calls `to_dict()` automatically |
| `BaseRenderer.model_class` | Set to the model class — `get_fields()` and `get_columns()` fall back to `field_names()` |
| `from_dict()` | Validate raw dicts from external sources (API responses, DB rows, config files) at the boundary |