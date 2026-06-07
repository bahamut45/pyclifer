# API Reference

Complete reference for all public symbols exported from `pyclifer`.

All symbols are importable directly from the top-level package:

```python
from pyclifer import app_group, BaseContext, BaseInterface, BaseModel, Response, get_logger
```

Never import from `pyclifer.core.*` — those paths are internal and may change.

---

## Module map

```
pyclifer
├── Decorators       @app_group  @group  @command  @option  + helpers
├── Context          BaseContext  (subclass + make_pass_decorator)
├── Interfaces       BaseInterface  →  respond()
├── Output           Response  OperationResult  PaginatedResponse  ExitCode
│   └── Renderers    BaseRenderer  ResponseRenderer
│   └── Tables       CliTable  CliTableColumn  ExceptionTable
├── Models           BaseModel
├── Logging          get_logger  SecretsMasker  TRACE  …
├── Core Classes     PycliferOption  PycliferGroup  CustomConfigOption  (advanced)
└── Mixins           GlobalOptionsMixin  HandleResponseMixin  …  (advanced)
```

---

## Where to start

| I want to… | Go to |
|---|---|
| Build a CLI from scratch | [Decorators](decorators.md) |
| Add project-specific state to commands | [Context](context.md) |
| Implement the service layer | [Interfaces](interfaces.md) |
| Control command output formats | [Output & Response](output.md) |
| Model domain objects with validation | [Models](models.md) |
| Configure logging | [Logging](logging.md) |
| Subclass Click internals | [Core Classes](classes.md) |
| Compose custom group/context classes | [Mixins](mixins.md) |

---

## Typical import surface

Most projects only need these symbols day-to-day:

```python
# Decorators
from pyclifer import app_group, group, command, option

# Context
from pyclifer import BaseContext, make_pass_decorator

# Service layer
from pyclifer import BaseInterface, BaseRenderer, ResponseRenderer

# Output
from pyclifer import Response, OperationResult, PaginatedResponse, ExitCode

# Domain models
from pyclifer import BaseModel

# Logging
from pyclifer import get_logger
```

Everything else (`PycliferGroup`, `GlobalOptionsMixin`, `RichHelpersMixin`, …) is available
for advanced use cases — subclassing, custom group behavior, or extending the framework.