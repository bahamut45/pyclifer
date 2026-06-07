# Interfaces

## BaseInterface

Base class for the pyclifer service layer. Subclass it to group all data-access and
business-logic operations for a resource. Declare a `renderers` dict to associate each method
with its renderer, then call `respond()` from commands — it handles list vs generator
detection, renderer selection, and `Response` construction automatically.

::: pyclifer.BaseInterface

---

## Full example

### 1. Declare the renderer

```python
from pyclifer import BaseRenderer


class ArticleRenderer(BaseRenderer):
    fields = ["id", "title", "author", "published"]  # JSON / YAML / raw
    columns = ["id", "title", "author"]               # table columns
    rich_title = "Articles"
    success_message = "Articles retrieved."
    failure_message = "Failed to retrieve articles."


class ArticleCreateRenderer(BaseRenderer):
    fields = ["item", "action", "success"]
    columns = ["item", "action"]
    rich_title = "Create Article"
    success_message = "Article created."
    failure_message = "Article creation failed."
```

### 2. Implement the interface

Interface methods return `list[OperationResult]` for batch operations, or
`Iterator[OperationResult]` for generators (streaming). They never raise for expected business
failures — return `OperationResult.error()` instead.

```python
from collections.abc import Iterator
from pyclifer import BaseInterface, OperationResult


class ArticleInterface(BaseInterface):
    renderers = {
        "list_articles": ArticleRenderer,
        "create_article": ArticleCreateRenderer,
        "import_articles": ArticleCreateRenderer,
    }

    def list_articles(self) -> list[OperationResult]:
        """Return all articles as a list of results."""
        articles = self._db.all()
        return [
            OperationResult.ok(a.id, data={"id": a.id, "title": a.title, "author": a.author})
            for a in articles
        ]

    def create_article(self, title: str, author: str) -> list[OperationResult]:
        """Create a single article."""
        if self._db.exists(title=title):
            return [OperationResult.error(title, f"'{title}' already exists.", error_code=2)]
        article = self._db.create(title=title, author=author)
        return [OperationResult.ok(article.id, data={"id": article.id, "action": "created"})]

    def import_articles(self, paths: list[str]) -> Iterator[OperationResult]:
        """Import articles from files — yields one result per file for live output."""
        for path in paths:
            try:
                article = self._import_file(path)
                yield OperationResult.ok(path, data={"id": article.id, "action": "created"})
            except ValueError as exc:
                yield OperationResult.error(path, str(exc))
```

### 3. Write the commands

Commands are thin views. Call `respond()` and return the result — no try/except, no renderer
wiring.

```python
from pyclifer import Response, argument, command, option, pass_context

from .interfaces import ArticleInterface


@command()
@pass_context
def list_articles(ctx) -> Response:
    """List all articles."""
    return ArticleInterface(ctx).respond("list_articles")


@command()
@argument("title")
@option("--author", required=True)
@pass_context
def create_article(ctx, title: str, author: str) -> Response:
    """Create a new article."""
    return ArticleInterface(ctx).respond("create_article", title, author)
```

For streaming commands (generator methods), `respond()` automatically wraps the generator in
`Response.from_stream()`:

```python
@command()
@argument("paths", nargs=-1)
@pass_context
def import_articles(ctx, paths: tuple[str, ...]) -> Response:
    """Import articles from files."""
    return ArticleInterface(ctx).respond("import_articles", list(paths))
```

With `--output-format rich`, the framework drives a `Live` context and calls
`renderer.rich_on_item()` after each yielded result. With all other formats the stream is
materialized first, then dispatched normally.

### 4. Default renderer fallback

When a method has no entry in `renderers`, `renderer_class` is used:

```python
class ArticleInterface(BaseInterface):
    renderer_class = ArticleRenderer   # fallback for methods not in renderers
    renderers = {
        "create_article": ArticleCreateRenderer,
    }
    # list_articles, import_articles, etc. will use ArticleRenderer automatically
```